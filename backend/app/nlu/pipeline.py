"""
NLU Pipeline for PS #9 — Emergency Intent Parsing & Triage Slot Filling.

Baseline approach (no GPU / training required):
  - Intent classification: facebook/bart-large-mnli (zero-shot)
  - Slot extraction:       regex + spaCy rule-based NER
  - Triage assignment:     rule-based (slots.py)

Upgrade path (for fine-tuning):
  - Replace zero-shot classifier with fine-tuned xlm-roberta-base
  - Replace regex slots with CRF token classifier on panic_data.json
"""

import re
import logging
from typing import Optional

try:
    from transformers import pipeline as hf_pipeline
except Exception:
    hf_pipeline = None

from app.nlu.slots import (
    ExtractedSlots,
    HazardType,
    Intent,
    TriageLevel,
    compute_triage_level,
    get_follow_up,
)

logger = logging.getLogger(__name__)

# ─── Intent Classifier ────────────────────────────────────────────────────────

# Loaded once at startup; zero-shot — no fine-tuning needed
_classifier = None

INTENT_CANDIDATE_LABELS = [
    "road accident or vehicle crash",
    "fire or fuel explosion hazard",
    "medical emergency or injury",
    "vehicle breakdown or towing assistance",
    "general help request",
]

LABEL_TO_INTENT = {
    "road accident or vehicle crash":     Intent.EMERGENCY_CRASH,
    "fire or fuel explosion hazard":       Intent.FIRE_HAZARD,
    "medical emergency or injury":         Intent.MEDICAL_EMERGENCY,
    "vehicle breakdown or towing assistance": Intent.VEHICLE_ASSISTANCE,
    "general help request":               Intent.GENERAL_HELP,
}


def load_classifier():
    global _classifier
    if _classifier is None:
        logger.info("Loading zero-shot classifier (facebook/bart-large-mnli)...")
        _classifier = hf_pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1,          # CPU; set to 0 for GPU
        )
        logger.info("Classifier loaded.")
    return _classifier


# ─── Slot Extraction via Regex ─────────────────────────────────────────────────

# Casualty patterns — handles digits and word numbers in EN/BN/mixed
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
    "one": 1, "ek": 1, "dui": 2, "two": 2, "tin": 3, "three": 3,
    "char": 4, "four": 4, "panch": 5, "five": 5, "six": 6, "cha": 6,
    "sat": 7, "seven": 7, "aat": 8, "eight": 8, "noy": 9, "nine": 9,
    "das": 10, "ten": 10,
}

_ENTRAPMENT_KEYWORDS = [
    r"\b(?:stuck|trapped|atke|atokte|phanse|phasa|phans[ae]|inside|andar|bhetre|caught)\b",
    r"\b(?:cannot get out|ber hote parche na|ber hoite parteche na|nikalna)\b",
    r"\b(?:door|doors?) (?:jammed|stuck|won.t open)\b",
]

_FIRE_KEYWORDS = [
    r"\b(?:fire|agun|aag|jalchhe|jwalchhe|burning|flames?|smoke|dhoa|dhuan)\b",
]

_FUEL_KEYWORDS = [
    r"\b(?:petrol|fuel|diesel|gas|oil)\s*(?:leak|spill|leaking|spilling|berchohe|pore|porte ache|sorbochhe)\b",
    r"\b(?:petrol|fuel|diesel)\b.*\b(?:everywhere|chhoriteyche)\b",
]

_CHILD_KEYWORDS = [
    r"\b(?:child|children|kids?|bachha|bachcha|baccha|baches?|shishu|minor|baby|babies|infant|school\s*(?:bus|van)|bache)\b",
]

# Common location words to extract
_LOCATION_PATTERNS = [
    r"\b(?:near|beside|at|on|by)\s+([\w\s]{3,30}?)(?:\s*,|\s+\d|\.|$)",
    r"\b(highway|bridge|flyover|junction|roundabout|market|school|hospital|airport|toll|checkpoint|river|mountain|road)\b",
    r"\b(?:AH\d+|NH\d+|km\s*\d+|marker\s*\d+)\b",
]


def _extract_casualties(text: str) -> Optional[int]:
    text_lower = text.lower()

    # Word number check first
    for word, num in _WORD_TO_NUM.items():
        if re.search(rf"\b{word}\b", text_lower):
            # Confirm there's a people-related word nearby
            context_window = r".{0,20}"
            people_words = r"(?:people|person|log|jon|lok|injured|hurt|trapped|inside)"
            if re.search(rf"\b{word}\b{context_window}{people_words}|{people_words}{context_window}\b{word}\b", text_lower):
                return num

    # Digit patterns
    for pattern in _CASUALTY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            try:
                return int(match.group(1))
            except (IndexError, ValueError):
                pass

    # Bare digit fallback (1-2 digits followed by space)
    digits = re.findall(r"\b(\d{1,2})\b", text)
    if digits:
        candidates = [int(d) for d in digits if 1 <= int(d) <= 50]
        if candidates:
            return candidates[0]

    return None


def _extract_entrapment(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in _ENTRAPMENT_KEYWORDS)


def _extract_hazard(text: str) -> HazardType:
    text_lower = text.lower()
    if any(re.search(p, text_lower) for p in _FIRE_KEYWORDS):
        # Check if it's specifically fuel before fire
        if any(re.search(p, text_lower) for p in _FUEL_KEYWORDS):
            return HazardType.FUEL_LEAK
        return HazardType.FIRE
    if any(re.search(p, text_lower) for p in _FUEL_KEYWORDS):
        return HazardType.FUEL_LEAK
    return HazardType.NONE


def _extract_child(text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in _CHILD_KEYWORDS)


def _extract_location(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern in _LOCATION_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            loc = match.group(0).strip()
            # Filter out very short or generic hits
            if len(loc) >= 3 and loc not in {"road", "on"}:
                return loc
    return None


def _identify_missing_slots(slots: ExtractedSlots) -> list:
    missing = []
    if slots.location_mention is None:
        missing.append("location_mention")
    if slots.casualties is None:
        missing.append("casualties")
    # Only ask about entrapment if crash/fire and not already known
    if not slots.entrapment and slots.casualties and slots.casualties > 0:
        missing.append("entrapment")
    return missing


# ─── Main Pipeline ─────────────────────────────────────────────────────────────

def run_nlu_pipeline(message: str) -> dict:
    """
    Full NLU pipeline for a single emergency message.

    Returns:
        dict with keys: intent, slots, triage_level, follow_up_question, confidence
    """
    if not message or not message.strip():
        return {
            "intent": Intent.UNKNOWN,
            "slots": ExtractedSlots().__dict__,
            "triage_level": TriageLevel.P2,
            "follow_up_question": "Can you describe what happened?",
            "confidence": 0.0,
        }

    # 1. Intent Classification
    try:
        clf = load_classifier()
        result = clf(message, INTENT_CANDIDATE_LABELS, multi_label=False)
        top_label = result["labels"][0]
        confidence = round(result["scores"][0], 4)
        intent = LABEL_TO_INTENT.get(top_label, Intent.UNKNOWN)
    except Exception as e:
        logger.error(f"Intent classification failed: {e}")
        intent = Intent.UNKNOWN
        confidence = 0.0

    # 2. Slot Extraction
    slots = ExtractedSlots(
        casualties       = _extract_casualties(message),
        entrapment       = _extract_entrapment(message),
        hazard_type      = _extract_hazard(message),
        child_involved   = _extract_child(message),
        location_mention = _extract_location(message),
    )
    slots.missing_slots = _identify_missing_slots(slots)

    # 3. Triage Assignment
    triage_level = compute_triage_level(slots, intent)

    # 4. Follow-up Question
    follow_up = get_follow_up(slots)

    return {
        "intent":             intent.value,
        "confidence":         confidence,
        "slots": {
            "casualties":       slots.casualties,
            "entrapment":       slots.entrapment,
            "hazard_type":      slots.hazard_type.value,
            "child_involved":   slots.child_involved,
            "location_mention": slots.location_mention,
        },
        "triage_level":       triage_level.value,
        "follow_up_question": follow_up,
        "missing_slots":      slots.missing_slots,
    }
