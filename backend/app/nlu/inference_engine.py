from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

try:
    import torch
except Exception:  # pragma: no cover - runtime fallback when dependency is absent
    torch = None

try:
    import onnxruntime as ort
except Exception:  # pragma: no cover - runtime fallback when dependency is absent
    ort = None

try:
    from transformers import AutoTokenizer
except Exception:  # pragma: no cover - runtime fallback when dependency is absent
    AutoTokenizer = None

from app.nlu.slots import ExtractedSlots, HazardType, Intent, compute_triage_level


logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).resolve().parent / "checkpoints"
DEFAULT_MAX_LENGTH = 128


@dataclass
class NLUResult:
    intent: str
    triage: str
    confidence: float
    slots: dict[str, Any]
    language: str
    latency_ms: float
    timings_ms: dict[str, float] = field(default_factory=dict)
    backend: str = "onnx_int8"
    runtime_mode: str = "onnx_int8"
    slot_tags: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckpointArtifacts:
    checkpoint_dir: Path
    model_path: Path
    meta_path: Path
    tokenizer_dir: Path
    meta: dict[str, Any]
    config: dict[str, Any]
    intent2id: dict[str, int]
    slot2id: dict[str, int]
    id2intent: dict[int, str]
    id2slot: dict[int, str]


_CASUALTY_PATTERNS = [
    r"\b(\d{1,2})\s*(?:people|persons?|log|jon|lok|jana|jone|bande|manush|casualties|injured|hurt|victims?|passengers?)\b",
    r"\b(\d{1,2})\s*(?:ta|ti|to|te|jono)\b",
    r"\b(?:one|ek|1)\b.*?\b(?:person|log|jon|lok)\b",
    r"\b(?:two|dui|dui jon|2)\b.*?\b(?:people|log|jon)\b",
    r"\b(?:three|tin|3)\b.*?\b(?:people|log|jon)\b",
    r"\b(?:four|char|4)\b.*?\b(?:people|log|jon)\b",
    r"\b(?:five|panch|5)\b.*?\b(?:people|log|jon)\b",
]

_WORD_TO_NUM = {
    "one": 1,
    "ek": 1,
    "dui": 2,
    "two": 2,
    "tin": 3,
    "three": 3,
    "char": 4,
    "four": 4,
    "panch": 5,
    "five": 5,
    "six": 6,
    "cha": 6,
    "sat": 7,
    "seven": 7,
    "aat": 8,
    "eight": 8,
    "noy": 9,
    "nine": 9,
    "das": 10,
    "ten": 10,
}

_ENTRAPMENT_KEYWORDS = [
    r"\b(?:stuck|trapped|atke|atokte|phanse|phasa|phans[ae]|inside|andar|bhetre|caught)\b",
    r"\b(?:cannot get out|ber hote parche na|ber hoite parteche na|nikalna)\b",
    r"\b(?:door|doors?) (?:jammed|stuck|won.t open)\b",
]

_FIRE_KEYWORDS = [r"\b(?:fire|agun|aag|jalchhe|jwalchhe|burning|flames?|smoke|dhoa|dhuan)\b"]
_FUEL_KEYWORDS = [
    r"\b(?:petrol|fuel|diesel|gas|oil)\s*(?:leak|spill|leaking|spilling|berchohe|pore|porte ache|sorbochhe)\b",
    r"\b(?:petrol|fuel|diesel)\b.*\b(?:everywhere|chhoriteyche)\b",
]
_CHILD_KEYWORDS = [
    r"\b(?:child|children|kids?|bachha|bachcha|baccha|baches?|shishu|minor|baby|babies|infant|school\s*(?:bus|van)|bache)\b",
]
_LOCATION_PATTERNS = [
    r"\b(?:near|beside|at|on|by)\s+([\w\s]{3,30}?)(?:\s*,|\s+\d|\.|$)",
    r"\b(highway|bridge|flyover|junction|roundabout|market|school|hospital|airport|toll|checkpoint|river|mountain|road)\b",
    r"\b(?:AH\d+|NH\d+|km\s*\d+|marker\s*\d+)\b",
]

_INTENT_KEYWORDS = [
    (
        Intent.EMERGENCY_CRASH,
        (r"\b(accident|crash|collision|wreck|roll(?:ed)? over|hit|smashed)\b",),
    ),
    (
        Intent.FIRE_HAZARD,
        (r"\b(fire|smoke|burning|flame|fuel leak|petrol leak|gas leak|explosion)\b",),
    ),
    (
        Intent.MEDICAL_EMERGENCY,
        (r"\b(injured|hurt|bleeding|unconscious|ambulance|medical|hospital|hurt badly)\b",),
    ),
    (
        Intent.VEHICLE_ASSISTANCE,
        (r"\b(breakdown|tow|towing|stalled|flat tyre|flat tire|battery|mechanic)\b",),
    ),
]


def _load_json(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf8") as fh:
        return json.load(fh)


def load_checkpoint_artifacts(checkpoint_dir: Path | None = None) -> CheckpointArtifacts | None:
    checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    model_path = checkpoint_dir / "model_int8.onnx"
    meta_path = checkpoint_dir / "meta.json"
    tokenizer_dir = checkpoint_dir

    if not model_path.exists() or not meta_path.exists():
        return None

    try:
        meta = _load_json(meta_path)
    except Exception as exc:
        logger.warning("Failed to read NLU metadata from %s: %s", meta_path, exc)
        return None

    config = meta.get("config") or {}
    intent2id = {str(k): int(v) for k, v in (meta.get("intent2id") or {}).items()}
    slot2id = {str(k): int(v) for k, v in (meta.get("slot2id") or {}).items()}

    if not intent2id or not slot2id:
        return None

    return CheckpointArtifacts(
        checkpoint_dir=checkpoint_dir,
        model_path=model_path,
        meta_path=meta_path,
        tokenizer_dir=tokenizer_dir,
        meta=meta,
        config=config,
        intent2id=intent2id,
        slot2id=slot2id,
        id2intent={v: k for k, v in intent2id.items()},
        id2slot={v: k for k, v in slot2id.items()},
    )


def load_training_artifacts(checkpoint_dir: Path | None = None) -> CheckpointArtifacts | None:
    checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
    model_path = checkpoint_dir / "model.onnx"
    meta_path = checkpoint_dir / "meta.json"
    tokenizer_dir = checkpoint_dir

    if not meta_path.exists():
        return None

    try:
        meta = _load_json(meta_path)
    except Exception as exc:
        logger.warning("Failed to read NLU metadata from %s: %s", meta_path, exc)
        return None

    config = meta.get("config") or {}
    intent2id = {str(k): int(v) for k, v in (meta.get("intent2id") or {}).items()}
    slot2id = {str(k): int(v) for k, v in (meta.get("slot2id") or {}).items()}

    if not intent2id or not slot2id:
        return None

    return CheckpointArtifacts(
        checkpoint_dir=checkpoint_dir,
        model_path=model_path,
        meta_path=meta_path,
        tokenizer_dir=tokenizer_dir,
        meta=meta,
        config=config,
        intent2id=intent2id,
        slot2id=slot2id,
        id2intent={v: k for k, v in intent2id.items()},
        id2slot={v: k for k, v in slot2id.items()},
    )


def _detect_language(text: str) -> str:
    if any("\u0980" <= ch <= "\u09ff" for ch in text):
        return "bn"
    if any("\u0e00" <= ch <= "\u0e7f" for ch in text):
        return "th"
    if any("\u0d80" <= ch <= "\u0dff" for ch in text):
        return "si"
    if any("\u0900" <= ch <= "\u097f" for ch in text):
        return "hi"
    return "en"


def _extract_casualties(text: str) -> int | None:
    text_lower = text.lower()

    for word, num in _WORD_TO_NUM.items():
        if re.search(rf"\b{word}\b", text_lower):
            context_window = r".{0,20}"
            people_words = r"(?:people|person|log|jon|lok|injured|hurt|trapped|inside)"
            if re.search(rf"\b{word}\b{context_window}{people_words}|{people_words}{context_window}\b{word}\b", text_lower):
                return num

    for pattern in _CASUALTY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                return int(match.group(1))
            except (IndexError, ValueError):
                continue

    digits = re.findall(r"\b(\d{1,2})\b", text)
    if digits:
        candidates = [int(d) for d in digits if 1 <= int(d) <= 50]
        if candidates:
            return candidates[0]

    return None


def _extract_entrapment(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in _ENTRAPMENT_KEYWORDS)


def _extract_hazard(text: str) -> HazardType:
    text_lower = text.lower()
    if any(re.search(pattern, text_lower) for pattern in _FIRE_KEYWORDS):
        if any(re.search(pattern, text_lower) for pattern in _FUEL_KEYWORDS):
            return HazardType.FUEL_LEAK
        return HazardType.FIRE
    if any(re.search(pattern, text_lower) for pattern in _FUEL_KEYWORDS):
        return HazardType.FUEL_LEAK
    return HazardType.NONE


def _extract_child(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(pattern, text_lower) for pattern in _CHILD_KEYWORDS)


def _extract_location(text: str) -> str | None:
    text_lower = text.lower()
    for pattern in _LOCATION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            location = match.group(0).strip()
            if len(location) >= 3 and location not in {"road", "on"}:
                return location
    return None


def _extract_rule_based_slots(text: str) -> dict[str, Any]:
    return {
        "casualties": _extract_casualties(text),
        "entrapment": _extract_entrapment(text),
        "hazard_type": _extract_hazard(text).value,
        "child_involved": _extract_child(text),
        "location_mention": _extract_location(text),
    }


def _fallback_intent_scores(text: str) -> dict[Intent, float]:
    text_lower = text.lower()
    scores: dict[Intent, float] = {
        Intent.EMERGENCY_CRASH: 0.3,
        Intent.FIRE_HAZARD: 0.3,
        Intent.MEDICAL_EMERGENCY: 0.3,
        Intent.VEHICLE_ASSISTANCE: 0.2,
        Intent.GENERAL_HELP: 0.15,
    }
    for intent, patterns in _INTENT_KEYWORDS:
        for pattern in patterns:
            if re.search(pattern, text_lower):
                scores[intent] += 1.0
    if not any(score > 0.3 for score in scores.values()):
        scores[Intent.GENERAL_HELP] += 0.5
    return scores


def _softmax(values: np.ndarray) -> np.ndarray:
    shifted = values - np.max(values)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


def _load_onnx_session(model_path: Path) -> Any:
    if ort is None:
        raise RuntimeError("onnxruntime is not available")

    session_options = ort.SessionOptions()
    session_options.intra_op_num_threads = 1
    session_options.inter_op_num_threads = 1
    session_options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
    session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

    return ort.InferenceSession(
        str(model_path),
        sess_options=session_options,
        providers=["CPUExecutionProvider"],
    )


def _load_tokenizer(tokenizer_dir: Path, fallback_model: str = "xlm-roberta-base") -> Any:
    if AutoTokenizer is None:
        raise RuntimeError("transformers is not available")

    try:
        return AutoTokenizer.from_pretrained(str(tokenizer_dir), use_fast=True)
    except Exception:
        return AutoTokenizer.from_pretrained(fallback_model, use_fast=True)


def _load_crf_parameters(checkpoint_dir: Path) -> dict[str, np.ndarray] | None:
    if torch is None:
        return None

    ckpt_path = checkpoint_dir / "best_model.pt"
    if not ckpt_path.exists():
        return None

    try:
        ckpt = torch.load(ckpt_path, map_location="cpu")
    except Exception as exc:
        logger.warning("Failed to load PyTorch checkpoint for CRF decoding: %s", exc)
        return None

    state_dict = ckpt.get("model_state_dict") if isinstance(ckpt, dict) else None
    if not isinstance(state_dict, dict):
        return None

    start = state_dict.get("crf.start_transitions")
    end = state_dict.get("crf.end_transitions")
    transitions = state_dict.get("crf.transitions")
    if start is None or end is None or transitions is None:
        return None

    return {
        "start_transitions": start.detach().cpu().numpy().astype(np.float32),
        "end_transitions": end.detach().cpu().numpy().astype(np.float32),
        "transitions": transitions.detach().cpu().numpy().astype(np.float32),
    }


def _viterbi_decode(emissions: np.ndarray, mask: np.ndarray, crf_params: dict[str, np.ndarray] | None) -> list[int]:
    if crf_params is None:
        valid = int(mask.sum())
        return emissions[:valid].argmax(axis=-1).tolist()

    valid = int(mask.sum())
    if valid <= 0:
        return []

    emissions = emissions[:valid]
    score = emissions[0] + crf_params["start_transitions"]
    history: list[np.ndarray] = []

    for timestep in range(1, valid):
        next_score = score[:, None] + crf_params["transitions"]
        best_prev = np.argmax(next_score, axis=0)
        score = np.max(next_score, axis=0) + emissions[timestep]
        history.append(best_prev)

    score = score + crf_params["end_transitions"]
    best_last = int(np.argmax(score))
    best_path = [best_last]

    for best_prev in reversed(history):
        best_last = int(best_prev[best_last])
        best_path.append(best_last)

    best_path.reverse()
    return best_path


def _convert_slot_tags(slot_tag_ids: list[int], id2slot: dict[int, str]) -> list[str]:
    return [id2slot.get(tag_id, "O") for tag_id in slot_tag_ids]


def _build_slot_entities(text: str, slot_tags: list[str]) -> dict[str, Any]:
    slots = _extract_rule_based_slots(text)
    if any(tag.endswith("LOCATION") for tag in slot_tags if tag != "O"):
        slots["location_mention"] = slots["location_mention"] or _extract_location(text)
    if any(tag.endswith("CASUALTY_COUNT") for tag in slot_tags if tag != "O"):
        slots["casualties"] = slots["casualties"] if slots["casualties"] is not None else _extract_casualties(text)
    if any(tag.endswith("ENTRAPMENT") for tag in slot_tags if tag != "O"):
        slots["entrapment"] = bool(slots["entrapment"] or _extract_entrapment(text))
    if any(tag.endswith("CHILD_INVOLVED") for tag in slot_tags if tag != "O"):
        slots["child_involved"] = bool(slots["child_involved"] or _extract_child(text))
    if any(tag.endswith("HAZARD_TYPE") for tag in slot_tags if tag != "O"):
        slots["hazard_type"] = _extract_hazard(text).value
    return slots


def _build_nlu_result(
    text: str,
    intent: str,
    confidence: float,
    slots: dict[str, Any],
    slot_tags: list[str] | None,
    latency_ms: float,
    timings_ms: dict[str, float],
    backend: str,
) -> NLUResult:
    intent_enum = Intent(intent) if intent in Intent._value2member_map_ else Intent.UNKNOWN
    hazard_value = slots.get("hazard_type", HazardType.NONE.value)
    try:
        hazard = HazardType(hazard_value)
    except Exception:
        hazard = HazardType.NONE

    extracted = ExtractedSlots(
        casualties=slots.get("casualties"),
        entrapment=bool(slots.get("entrapment", False)),
        hazard_type=hazard,
        child_involved=bool(slots.get("child_involved", False)),
        location_mention=slots.get("location_mention"),
    )
    triage = compute_triage_level(extracted, intent_enum).value

    return NLUResult(
        intent=intent_enum.value,
        triage=triage,
        confidence=float(confidence),
        slots=slots,
        language=_detect_language(text),
        latency_ms=float(latency_ms),
        timings_ms=timings_ms,
        backend=backend,
        runtime_mode=backend,
        slot_tags=slot_tags,
    )


class ONNXInferenceEngine:
    def __init__(self, checkpoint_dir: Path | None = None):
        self.checkpoint_dir = checkpoint_dir or CHECKPOINT_DIR
        self.artifacts = load_checkpoint_artifacts(self.checkpoint_dir)
        self.available = False
        self.session: Any = None
        self.tokenizer: Any = None
        self.max_length = DEFAULT_MAX_LENGTH
        self.id2intent: dict[int, str] = {}
        self.id2slot: dict[int, str] = {}
        self.crf_params = None

        if self.artifacts is None:
            logger.warning("ONNX artifacts not found in %s; using heuristic fallback.", self.checkpoint_dir)
            return

        self.max_length = int(self.artifacts.config.get("max_length", DEFAULT_MAX_LENGTH))
        self.id2intent = self.artifacts.id2intent
        self.id2slot = self.artifacts.id2slot

        try:
            self.session = _load_onnx_session(self.artifacts.model_path)
            self.tokenizer = _load_tokenizer(self.artifacts.tokenizer_dir)
            self.crf_params = _load_crf_parameters(self.checkpoint_dir)
            self.available = True
            logger.info("Loaded ONNX NLU engine from %s", self.artifacts.model_path)
        except Exception as exc:
            logger.warning("Failed to initialise ONNX NLU engine: %s", exc)
            self.available = False

    def warm_up(self) -> None:
        texts = [
            "accident near road 2 people",
            "fire and smoke near bridge",
            "medical emergency ambulance needed",
            "vehicle breakdown need towing",
            "help me please",
        ]
        for text in texts:
            try:
                self.predict(text)
            except Exception:
                break

    def predict(self, text: str) -> NLUResult:
        if not text or not text.strip():
            return _build_nlu_result(
                text=text,
                intent=Intent.UNKNOWN.value,
                confidence=0.0,
                slots=_extract_rule_based_slots(text or ""),
                slot_tags=[],
                latency_ms=0.0,
                timings_ms={"tokenization_ms": 0.0, "inference_ms": 0.0, "crf_decoding_ms": 0.0, "post_processing_ms": 0.0},
                backend="fallback",
            )

        if not self.available or self.session is None or self.tokenizer is None:
            return self._predict_fallback(text)

        total_start = time.perf_counter()

        token_start = time.perf_counter()
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
        )
        input_ids = np.asarray([encoding["input_ids"]], dtype=np.int64)
        attention_mask = np.asarray([encoding["attention_mask"]], dtype=np.int64)
        tokenization_ms = (time.perf_counter() - token_start) * 1000.0

        inference_start = time.perf_counter()
        outputs = self.session.run(
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
            },
        )
        inference_ms = (time.perf_counter() - inference_start) * 1000.0

        intent_logits = np.asarray(outputs[0], dtype=np.float32)[0]
        slot_emissions = np.asarray(outputs[1], dtype=np.float32)[0]
        intent_probs = _softmax(intent_logits)
        intent_idx = int(np.argmax(intent_probs))
        intent = self.id2intent.get(intent_idx, Intent.UNKNOWN.value)
        confidence = float(intent_probs[intent_idx])

        crf_start = time.perf_counter()
        mask = np.asarray(attention_mask[0] > 0, dtype=np.bool_)
        slot_tag_ids = _viterbi_decode(slot_emissions, mask, self.crf_params)
        slot_tags = _convert_slot_tags(slot_tag_ids, self.id2slot)
        crf_ms = (time.perf_counter() - crf_start) * 1000.0

        post_start = time.perf_counter()
        slots = _build_slot_entities(text, slot_tags)
        post_processing_ms = (time.perf_counter() - post_start) * 1000.0
        latency_ms = (time.perf_counter() - total_start) * 1000.0

        return _build_nlu_result(
            text=text,
            intent=intent,
            confidence=confidence,
            slots=slots,
            slot_tags=slot_tags,
            latency_ms=latency_ms,
            timings_ms={
                "tokenization_ms": tokenization_ms,
                "inference_ms": inference_ms,
                "crf_decoding_ms": crf_ms,
                "post_processing_ms": post_processing_ms,
            },
            backend="onnx_int8",
        )

    def batch_predict(self, texts: list[str]) -> list[NLUResult]:
        return [self.predict(text) for text in texts]

    def _predict_fallback(self, text: str) -> NLUResult:
        total_start = time.perf_counter()
        token_start = time.perf_counter()
        slots = _extract_rule_based_slots(text)
        tokenization_ms = (time.perf_counter() - token_start) * 1000.0

        inference_start = time.perf_counter()
        scores = _fallback_intent_scores(text)
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        raw_scores = np.asarray([score for _, score in ordered], dtype=np.float32)
        probabilities = _softmax(raw_scores)
        best_index = int(np.argmax(probabilities))
        intent = ordered[best_index][0].value
        confidence = float(probabilities[best_index])
        inference_ms = (time.perf_counter() - inference_start) * 1000.0

        crf_start = time.perf_counter()
        slot_tags: list[str] = []
        crf_ms = (time.perf_counter() - crf_start) * 1000.0

        post_start = time.perf_counter()
        post_processing_ms = (time.perf_counter() - post_start) * 1000.0
        latency_ms = (time.perf_counter() - total_start) * 1000.0

        return _build_nlu_result(
            text=text,
            intent=intent,
            confidence=confidence,
            slots=slots,
            slot_tags=slot_tags,
            latency_ms=latency_ms,
            timings_ms={
                "tokenization_ms": tokenization_ms,
                "inference_ms": inference_ms,
                "crf_decoding_ms": crf_ms,
                "post_processing_ms": post_processing_ms,
            },
            backend="fallback",
        )


_ENGINE: ONNXInferenceEngine | None = None


def get_nlu_engine() -> ONNXInferenceEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = ONNXInferenceEngine()
    return _ENGINE


def normalise_slot_keys(slots: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "casualties": "CASUALTY_COUNT",
        "casualty_count": "CASUALTY_COUNT",
        "entrapment": "ENTRAPMENT",
        "hazard_type": "HAZARD_TYPE",
        "child_involved": "CHILD_INVOLVED",
        "location_mention": "LOCATION",
        "LOCATION": "LOCATION",
        "CASUALTY_COUNT": "CASUALTY_COUNT",
        "ENTRAPMENT": "ENTRAPMENT",
        "HAZARD_TYPE": "HAZARD_TYPE",
        "CHILD_INVOLVED": "CHILD_INVOLVED",
    }
    normalised: dict[str, Any] = {}
    for key, value in (slots or {}).items():
        normalised[mapping.get(key, key)] = value
    return normalised


def nlu_result_to_pipeline_dict(result: NLUResult, raw_text: str) -> dict[str, Any]:
    return {
        "intent": result.intent,
        "triage_level": result.triage,
        "confidence": result.confidence,
        "slots": result.slots,
        "language": result.language,
        "latency_ms": result.latency_ms,
        "timings_ms": result.timings_ms,
        "backend": result.backend,
        "raw_text": raw_text,
        "slot_tags": result.slot_tags,
    }
