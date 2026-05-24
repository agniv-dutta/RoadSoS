from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from torch import nn

from app.nlu.inference_engine import CHECKPOINT_DIR, _load_tokenizer, load_training_artifacts
from app.nlu.model import EmergencyNLUModel


class ONNXExportWrapper(nn.Module):
    def __init__(self, model: EmergencyNLUModel):
        super().__init__()
        self.encoder = model.encoder
        self.intent_head = model.intent_head
        self.slot_head = model.slot_head

    def forward(self, input_ids, attention_mask):
        outputs = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        hidden = outputs.last_hidden_state
        intent_logits = self.intent_head(hidden[:, 0, :])
        slot_emissions = self.slot_head(hidden)
        return intent_logits, slot_emissions


def _load_reference_model():
    artifacts = load_training_artifacts(CHECKPOINT_DIR)
    if artifacts is None:
        raise FileNotFoundError(
            f"Missing training artifacts in {CHECKPOINT_DIR}. Expected best_model.pt and meta.json before export."
        )

    ckpt_path = CHECKPOINT_DIR / "best_model.pt"
    if not ckpt_path.exists():
        raise FileNotFoundError(f"Missing PyTorch checkpoint: {ckpt_path}")

    checkpoint = torch.load(ckpt_path, map_location="cpu")
    pretrained_model = artifacts.config.get("pretrained_model", "xlm-roberta-base")
    model = EmergencyNLUModel(
        num_intents=len(artifacts.intent2id),
        num_slot_tags=len(artifacts.slot2id),
        pretrained_model=pretrained_model,
    )
    model.load_state_dict(checkpoint["model_state_dict"], strict=False)
    model.eval()
    return model, artifacts


def _load_examples(limit: int = 20):
    test_path = Path(__file__).resolve().parent / "dataset" / "test.json"
    with open(test_path, encoding="utf8") as fh:
        examples = json.load(fh)
    rng = random.Random(42)
    rng.shuffle(examples)
    return examples[: min(limit, len(examples))]


def main():
    model, artifacts = _load_reference_model()
    tokenizer = _load_tokenizer(CHECKPOINT_DIR, fallback_model=artifacts.config.get("pretrained_model", "xlm-roberta-base"))
    export_model = ONNXExportWrapper(model)
    export_model.eval()

    sample_inputs = tokenizer(
        "accident near road",
        return_tensors="pt",
        truncation=True,
        padding="max_length",
        max_length=int(artifacts.config.get("max_length", 128)),
    )

    onnx_path = CHECKPOINT_DIR / "model.onnx"
    torch.onnx.export(
        export_model,
        (sample_inputs["input_ids"], sample_inputs["attention_mask"]),
        str(onnx_path),
        opset_version=17,
        input_names=["input_ids", "attention_mask"],
        output_names=["intent_logits", "slot_emissions"],
        dynamic_axes={
            "input_ids": {0: "batch", 1: "seq"},
            "attention_mask": {0: "batch", 1: "seq"},
        },
        do_constant_folding=True,
    )

    onnx_model = onnx.load(str(onnx_path))
    onnx.checker.check_model(onnx_model)

    ref_model = model
    examples = _load_examples(limit=20)
    max_diff = 0.0
    intent_matches = 0
    ort_session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])

    with torch.no_grad():
        for example in examples:
            encoding = tokenizer(
                example["text"],
                return_tensors="pt",
                truncation=True,
                padding="max_length",
                max_length=int(artifacts.config.get("max_length", 128)),
            )
            pt_logits, pt_slot_emissions = ref_model(encoding["input_ids"], encoding["attention_mask"])
            ort_inputs = {
                "input_ids": encoding["input_ids"].cpu().numpy().astype(np.int64),
                "attention_mask": encoding["attention_mask"].cpu().numpy().astype(np.int64),
            }
            ort_logits, ort_slot_emissions = ort_session.run(None, ort_inputs)

            pt_logits_np = pt_logits.cpu().numpy()
            diff = float(np.max(np.abs(pt_logits_np - ort_logits)))
            max_diff = max(max_diff, diff)
            if int(np.argmax(pt_logits_np, axis=-1)[0]) == int(np.argmax(ort_logits, axis=-1)[0]):
                intent_matches += 1

    if max_diff >= 1e-4:
        raise AssertionError(f"ONNX export drift too high: max abs diff={max_diff:.8f} (threshold < 1e-4)")
    if intent_matches < len(examples):
        raise AssertionError(f"Intent prediction mismatch on {len(examples) - intent_matches}/{len(examples)} validation samples")

    print(f"Exported ONNX model to {onnx_path}")
    print(f"Validated {len(examples)} samples: intent agreement={intent_matches}/{len(examples)}, max_abs_logit_diff={max_diff:.8f}")


if __name__ == "__main__":
    main()
