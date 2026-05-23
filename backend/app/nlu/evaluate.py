import json
from pathlib import Path

import torch
from sklearn.metrics import classification_report, confusion_matrix
from seqeval.metrics import classification_report as seq_classification_report, f1_score as seq_f1_score

from dataset_loader import EmergencyDataset
from model import EmergencyNLUModel


def load_checkpoint(ckpt_path: str, device):
    ckpt = torch.load(ckpt_path, map_location=device)
    return ckpt


def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    out_dir = Path("app/nlu/checkpoints")
    ckpt_path = out_dir / "best_model.pt"
    meta = json.load(open(out_dir / "meta.json", encoding="utf8"))

    intent2id = meta["intent2id"]
    slot2id = meta["slot2id"]
    id2intent = {v: k for k, v in intent2id.items()}
    id2slot = {v: k for k, v in slot2id.items()}

    test_ds = EmergencyDataset("app/nlu/dataset/test.json", tokenizer_name="xlm-roberta-base", max_length=meta["config"]["max_length"], intent2id=intent2id, slot2id=slot2id)
    test_loader = torch.utils.data.DataLoader(test_ds, batch_size=meta["config"]["batch_size"], collate_fn=lambda x: x)

    ckpt = load_checkpoint(str(ckpt_path), device)
    model = EmergencyNLUModel(num_intents=len(intent2id), num_slot_tags=len(slot2id), pretrained_model="xlm-roberta-base")
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device)
    model.eval()

    all_true_intents = []
    all_pred_intents = []
    true_slots = []
    pred_slots = []

    with torch.no_grad():
        for batch in test_loader:
            # batch is list of items
            input_ids = torch.stack([b["input_ids"] for b in batch]).to(device)
            attention_mask = torch.stack([b["attention_mask"] for b in batch]).to(device)
            intent_labels = torch.tensor([b["intent_label"].item() for b in batch], dtype=torch.long)

            intent_logits, pred_tags = model(input_ids, attention_mask)
            pred_intents = intent_logits.argmax(dim=-1).cpu().tolist()
            true_intents = [b["intent_label"].item() for b in batch]

            all_true_intents.extend(true_intents)
            all_pred_intents.extend(pred_intents)

            for i in range(len(batch)):
                word_ids = batch[i]["word_ids"]
                slot_labels = batch[i]["slot_labels"].cpu().tolist()

                pred_tag_ids = pred_tags[i]
                # reconstruct word-level preds
                ptr = 0
                word_pred = []
                for wid in word_ids:
                    if wid is None:
                        continue
                    if ptr >= len(pred_tag_ids):
                        break
                    # first subword mapping
                    if (len(word_pred) == 0) or (wid != (len(word_pred) - 1)):
                        word_pred.append(id2slot[pred_tag_ids[ptr]])
                    ptr += 1

                # true
                word_true = []
                for j, wid in enumerate(word_ids):
                    if wid is None:
                        continue
                    if slot_labels[j] == -100:
                        continue
                    word_true.append(id2slot[slot_labels[j]])

                pred_slots.append(word_pred)
                true_slots.append(word_true)

    # Intent metrics
    intent_report = classification_report(all_true_intents, all_pred_intents, target_names=[intent for intent in intent2id.keys()], zero_division=0, output_dict=True)

    # Slot metrics via seqeval
    slot_report_text = seq_classification_report(true_slots, pred_slots)
    slot_f1 = seq_f1_score(true_slots, pred_slots)

    # Frame accuracy: exact match intent & slot
    frame_exact = 0
    for ti, pi, ts, ps in zip(all_true_intents, all_pred_intents, true_slots, pred_slots):
        if ti == pi and ts == ps:
            frame_exact += 1
    frame_acc = frame_exact / max(1, len(all_true_intents))

    report = {
        "intent_report": intent_report,
        "slot_f1": slot_f1,
        "frame_accuracy": frame_acc,
        "slot_report_text": slot_report_text,
    }

    out_json = out_dir / "results" / "evaluation_report.json"
    out_md = out_dir / "results" / "evaluation_report.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)

    with open(out_json, "w", encoding="utf8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    with open(out_md, "w", encoding="utf8") as fh:
        fh.write("# Evaluation Report\n\n")
        fh.write("## Intent Classification\n\n")
        fh.write(json.dumps(intent_report, indent=2))
        fh.write("\n\n## Slot tagging (seqeval)\n\n")
        fh.write(slot_report_text)
        fh.write(f"\n\nFrame Accuracy: {frame_acc:.4f}\n")

    # confusion matrix
    cm = confusion_matrix(all_true_intents, all_pred_intents)
    print("Intent classification report:\n", json.dumps(intent_report, indent=2))
    print("Slot F1:", slot_f1)
    print("Frame accuracy:", frame_acc)
    print("Confusion matrix:\n", cm)


if __name__ == "__main__":
    main()
