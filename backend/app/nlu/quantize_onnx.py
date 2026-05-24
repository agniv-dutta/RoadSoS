from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

import numpy as np
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoTokenizer

from app.nlu.inference_engine import CHECKPOINT_DIR, _load_crf_parameters, _load_json, _viterbi_decode
from app.nlu.dataset_loader import EmergencyDataset


def _bio_spans(tags: list[str]) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    active_label: str | None = None
    start_index: int | None = None

    for index, tag in enumerate(tags + ["O"]):
        if tag.startswith("B-"):
            if active_label is not None and start_index is not None:
                spans.append((active_label, start_index, index - 1))
            active_label = tag[2:]
            start_index = index
        elif tag.startswith("I-") and active_label == tag[2:]:
            continue
        else:
            if active_label is not None and start_index is not None:
                spans.append((active_label, start_index, index - 1))
            active_label = None
            start_index = None
    return spans


def _slot_f1(true_sequences: list[list[str]], pred_sequences: list[list[str]]) -> float:
    true_spans = Counter()
    pred_spans = Counter()
    for tags in true_sequences:
        true_spans.update(_bio_spans(tags))
    for tags in pred_sequences:
        pred_spans.update(_bio_spans(tags))

    if not pred_spans and not true_spans:
        return 1.0
    if not pred_spans or not true_spans:
        return 0.0

    overlap = sum((true_spans & pred_spans).values())
    precision = overlap / max(1, sum(pred_spans.values()))
    recall = overlap / max(1, sum(true_spans.values()))
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _evaluate_session(session: ort.InferenceSession, dataset: EmergencyDataset, id2slot: dict[int, str], crf_params):
    tokenizer = dataset.tokenizer
    correct_intents = 0
    total = 0
    true_sequences: list[list[str]] = []
    pred_sequences: list[list[str]] = []

    for item in dataset:
        inputs = {
            "input_ids": np.asarray([item["input_ids"].numpy()], dtype=np.int64),
            "attention_mask": np.asarray([item["attention_mask"].numpy()], dtype=np.int64),
        }
        intent_logits, slot_emissions = session.run(None, inputs)
        pred_intent = int(np.argmax(intent_logits, axis=-1)[0])
        total += 1
        if pred_intent == int(item["intent_label"].item()):
            correct_intents += 1

        pred_tag_ids = _viterbi_decode(np.asarray(slot_emissions[0], dtype=np.float32), np.asarray(item["attention_mask"].numpy() > 0), crf_params)
        pred_tags = [id2slot.get(tag_id, "O") for tag_id in pred_tag_ids]

        word_ids = item["word_ids"]
        pred_words: list[str] = []
        ptr = 0
        for word_index, wid in enumerate(word_ids):
            if wid is None:
                continue
            if ptr >= len(pred_tags):
                break
            if word_index == 0 or wid != word_ids[word_index - 1]:
                pred_words.append(pred_tags[ptr])
            ptr += 1

        true_words = [id2slot[int(tag)] for tag in item["slot_labels"].tolist() if int(tag) != -100]
        pred_sequences.append(pred_words)
        true_sequences.append(true_words)

    return {
        "intent_accuracy": correct_intents / max(1, total),
        "slot_f1": _slot_f1(true_sequences, pred_sequences),
    }


def main():
    artifacts = _load_json(CHECKPOINT_DIR / "meta.json")
    model_path = CHECKPOINT_DIR / "model.onnx"
    quantized_path = CHECKPOINT_DIR / "model_int8.onnx"
    if not model_path.exists():
        raise FileNotFoundError(f"Missing FP32 ONNX model: {model_path}")

    quantize_dynamic(
        model_input=str(model_path),
        model_output=str(quantized_path),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=["MatMul", "Gather"],
    )

    original_size = os.path.getsize(model_path)
    quantized_size = os.path.getsize(quantized_path)
    size_ratio = original_size / max(1, quantized_size)

    tokenizer_name = str(CHECKPOINT_DIR) if (CHECKPOINT_DIR / "tokenizer_config.json").exists() else artifacts["config"].get("pretrained_model", "xlm-roberta-base")
    dataset = EmergencyDataset(
        str(Path(__file__).resolve().parent / "dataset" / "val.json"),
        tokenizer_name=tokenizer_name,
        max_length=int(artifacts["config"].get("max_length", 128)),
        intent2id=artifacts["intent2id"],
        slot2id=artifacts["slot2id"],
    )
    crf_params = _load_crf_parameters(CHECKPOINT_DIR)
    if crf_params is None:
        raise FileNotFoundError("CRF parameters could not be loaded from best_model.pt; quantization validation requires the trained checkpoint.")

    fp32_session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    int8_session = ort.InferenceSession(str(quantized_path), providers=["CPUExecutionProvider"])

    fp32_metrics = _evaluate_session(fp32_session, dataset, {v: k for k, v in artifacts["slot2id"].items()}, crf_params)
    int8_metrics = _evaluate_session(int8_session, dataset, {v: k for k, v in artifacts["slot2id"].items()}, crf_params)

    intent_drop = fp32_metrics["intent_accuracy"] - int8_metrics["intent_accuracy"]
    slot_drop = fp32_metrics["slot_f1"] - int8_metrics["slot_f1"]

    print(f"Original ONNX size: {original_size / 1e6:.2f} MB")
    print(f"INT8 ONNX size: {quantized_size / 1e6:.2f} MB")
    print(f"Size reduction: {size_ratio:.2f}x")
    print(f"FP32 metrics: {fp32_metrics}")
    print(f"INT8 metrics: {int8_metrics}")

    if intent_drop > 0.02 or slot_drop > 0.03:
        raise ValueError(
            "INT8 regression exceeds threshold:\n"
            f"  intent_accuracy_fp32={fp32_metrics['intent_accuracy']:.4f}\n"
            f"  intent_accuracy_int8={int8_metrics['intent_accuracy']:.4f}\n"
            f"  intent_drop={intent_drop:.4f} (threshold <= 0.02)\n"
            f"  slot_f1_fp32={fp32_metrics['slot_f1']:.4f}\n"
            f"  slot_f1_int8={int8_metrics['slot_f1']:.4f}\n"
            f"  slot_drop={slot_drop:.4f} (threshold <= 0.03)"
        )


if __name__ == "__main__":
    main()
