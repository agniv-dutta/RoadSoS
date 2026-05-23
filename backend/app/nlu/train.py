import json
import math
import os
from pathlib import Path
from typing import Dict

import numpy as np
import torch
from sklearn.metrics import accuracy_score
from transformers import AdamW, get_cosine_schedule_with_warmup, AutoTokenizer

from dataset_loader import EmergencyDataset
from model import EmergencyNLUModel


# Config
CONFIG: Dict = {
    "pretrained_model": "xlm-roberta-base",
    "max_length": 128,
    "batch_size": 16,
    "epochs": 20,
    "lr": 2e-5,
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,
    "gradient_clipping": 1.0,
    "patience": 3,
    "output_dir": "app/nlu/checkpoints",
}


def collate_batch(batch):
    # batch is list of dicts with tensors of same shape (because padding='max_length')
    input_ids = torch.stack([b["input_ids"] for b in batch])
    attention_mask = torch.stack([b["attention_mask"] for b in batch])
    intent_labels = torch.stack([b["intent_label"] for b in batch])
    slot_labels = torch.stack([b["slot_labels"] for b in batch])
    word_ids = [b["word_ids"] for b in batch]
    ids = [b.get("id") for b in batch]
    return {
        "input_ids": input_ids,
        "attention_mask": attention_mask,
        "intent_label": intent_labels,
        "slot_labels": slot_labels,
        "word_ids": word_ids,
        "ids": ids,
    }


def evaluate_model(model, dataloader, id2intent, id2slot, device):
    model.eval()
    all_true_intents = []
    all_pred_intents = []

    true_slot_seqs = []
    pred_slot_seqs = []

    frame_matches = 0
    total = 0

    with torch.no_grad():
        for batch in dataloader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)

            intent_logits, pred_tags = model(input_ids, attention_mask)

            pred_intents = intent_logits.argmax(dim=-1).cpu().tolist()
            true_intents = batch["intent_label"].cpu().tolist()

            all_true_intents.extend(true_intents)
            all_pred_intents.extend(pred_intents)

            # pred_tags is list[list[tag_id]] where tag ids correspond to token-level
            for i in range(len(pred_tags)):
                word_ids = batch["word_ids"][i]
                # build word-level predicted tags
                pred_tag_ids = pred_tags[i]
                word_pred = []
                ptr = 0
                for wid in word_ids:
                    if wid is None:
                        continue
                    # take first subword prediction only
                    if ptr >= len(pred_tag_ids):
                        break
                    if (len(word_pred) == 0) or (wid != (len(word_pred) - 1)):
                        # append
                        word_pred.append(id2slot[pred_tag_ids[ptr]])
                    ptr += 1

                # true tags: reconstruct from slot_labels
                slot_labels = batch["slot_labels"][i].cpu().tolist()
                word_true = []
                for j, wid in enumerate(word_ids):
                    if wid is None:
                        continue
                    if slot_labels[j] == -100:
                        # continuation subword -> skip
                        continue
                    word_true.append(id2slot[slot_labels[j]])

                pred_slot_seqs.append(word_pred)
                true_slot_seqs.append(word_true)

                # frame match: intent + slot sequence exact
                if (id2intent[true_intents[i]] == id2intent[pred_intents[i]]) and (word_pred == word_true):
                    frame_matches += 1
                total += 1

    intent_acc = accuracy_score(all_true_intents, all_pred_intents)
    # slot metrics will be computed in evaluate.py using seqeval for better reporting
    frame_acc = frame_matches / max(1, total)
    return intent_acc, true_slot_seqs, pred_slot_seqs, frame_acc


def train():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # allow overrides via environment variables for quick runs
    import os
    epochs_override = os.getenv("EPOCHS")
    if epochs_override is not None:
        try:
            CONFIG["epochs"] = int(epochs_override)
        except Exception:
            pass

    # adjust batch size if no GPU
    batch_size = CONFIG["batch_size"] if torch.cuda.is_available() else max(8, CONFIG["batch_size"] // 2)

    train_ds = EmergencyDataset("app/nlu/dataset/train.json", tokenizer_name=CONFIG["pretrained_model"], max_length=CONFIG["max_length"])
    val_ds = EmergencyDataset("app/nlu/dataset/val.json", tokenizer_name=CONFIG["pretrained_model"], max_length=CONFIG["max_length"], intent2id=train_ds.intent2id, slot2id=train_ds.slot2id)

    id2intent = {v: k for k, v in train_ds.intent2id.items()}
    id2slot = {v: k for k, v in train_ds.slot2id.items()}

    tokenizer = AutoTokenizer.from_pretrained(CONFIG["pretrained_model"])

    train_loader = torch.utils.data.DataLoader(train_ds, batch_size=batch_size, shuffle=True, collate_fn=collate_batch)
    val_loader = torch.utils.data.DataLoader(val_ds, batch_size=batch_size, shuffle=False, collate_fn=collate_batch)

    model = EmergencyNLUModel(num_intents=len(train_ds.intent2id), num_slot_tags=len(train_ds.slot2id), pretrained_model=CONFIG["pretrained_model"]).to(device)

    if not torch.cuda.is_available():
        try:
            model.encoder.gradient_checkpointing_enable()
        except Exception:
            pass

    t_total = len(train_loader) * CONFIG["epochs"]
    warmup_steps = int(CONFIG["warmup_ratio"] * t_total)

    optimizer = AdamW(model.parameters(), lr=CONFIG["lr"], weight_decay=CONFIG["weight_decay"]) 
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=t_total)

    best_frame = -1.0
    patience_counter = 0
    os.makedirs(CONFIG["output_dir"], exist_ok=True)

    global_step = 0
    for epoch in range(CONFIG["epochs"]):
        model.train()
        for step, batch in enumerate(train_loader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            intent_labels = batch["intent_label"].to(device)
            slot_labels = batch["slot_labels"].to(device)

            out = model(input_ids, attention_mask, intent_labels=intent_labels, slot_labels=slot_labels)
            loss = out["loss"]

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), CONFIG["gradient_clipping"])
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

            if global_step % 50 == 0:
                print(f"Step {global_step}: loss={loss.item():.4f} intent={out['loss_intent'].item():.4f} slot={out['loss_slot'].item():.4f}")

            global_step += 1

        # validation
        intent_acc, true_slots, pred_slots, frame_acc = evaluate_model(model, val_loader, id2intent, id2slot, device)
        print(f"Epoch {epoch} validation: intent_acc={intent_acc:.4f} frame_acc={frame_acc:.4f}")

        if frame_acc > best_frame:
            best_frame = frame_acc
            patience_counter = 0
            # save checkpoint
            ckpt_path = Path(CONFIG["output_dir"]) / "best_model.pt"
            torch.save({
                "model_state_dict": model.state_dict(),
                "intent2id": train_ds.intent2id,
                "slot2id": train_ds.slot2id,
            }, ckpt_path)
            tokenizer.save_pretrained(CONFIG["output_dir"]) 
            with open(Path(CONFIG["output_dir"]) / "meta.json", "w", encoding="utf8") as fh:
                json.dump({"config": CONFIG, "intent2id": train_ds.intent2id, "slot2id": train_ds.slot2id}, fh, ensure_ascii=False, indent=2)
        else:
            patience_counter += 1
            if patience_counter >= CONFIG["patience"]:
                print("Early stopping triggered")
                break

    print("Training complete. Best frame acc:", best_frame)


if __name__ == "__main__":
    train()
