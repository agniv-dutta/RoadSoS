# backend/app/dialogue/state_machine.py
"""
Multi-turn slot recovery FSM for RoadSoS triage dialogue.
Zero external dependencies — FSM logic is implemented with plain Python.
"""

import time
import uuid
from typing import Any, Dict, Optional

try:
    from app.nlu.pipeline import run_nlu_pipeline
except Exception:
    # Fallback stub for test environments (tests will monkeypatch this)
    def run_nlu_pipeline(message: str) -> Dict[str, Any]:
        return {
            "intent": "unknown",
            "triage_level": "P3",
            "confidence": 0.0,
            "slots": {},
            "language": "en",
            "raw_text": message,
        }

from app.nlu.inference_engine import normalise_slot_keys
from app.nlu.cap_exporter import CAPv12Exporter
from app.dialogue.session_store import SessionState, SessionStore


# ─── Follow-up question templates ────────────────────────────────────────────

_FOLLOWUP_TEMPLATES: Dict[str, Dict[str, str]] = {
    "LOCATION": {
        "en": "Where exactly did this happen? Road name, landmark, or area?",
        "hi": "यह कहाँ हुआ? सड़क का नाम या पास का landmark बताएं।",
        "bn": "এটা কোথায় হয়েছে? রাস্তার নাম বা কাছের জায়গা বলুন।",
        "th": "เหตุการณ์เกิดขึ้นที่ไหน? ใกล้จุดสังเกต ถนน หรือพื้นที่ใด?",
        "si": "මෙය ඇත්තටම කොහිද සිදුවා තිබෙන්නේ? නීරදිස්ථාන, මාර්ග නාමය හෝ ප්‍රදේශය කියන්න.",
    },
    "CASUALTY_COUNT": {
        "en": "How many people are injured or need help?",
        "hi": "कितने लोग घायल हैं?",
        "bn": "কতজন আহত হয়েছেন?",
        "th": "มีกี่คนบาดเจ็บหรือต้องการความช่วยเหลือ?",
        "si": "ක්‍රමාංකිතව කොච්චර පුද්ගලයන් තුවාල ඇතිද?",
    },
    "HAZARD_TYPE": {
        "en": "Is there fire, fuel leak, or other danger at the scene?",
        "hi": "क्या स्थल पर आग, ईंधन रिसाव, या अन्य कोई ख़तरा है?",
        "bn": "সাইটে কি আগুন, জ্বালানি লিক বা অন্য কোনো বিপদ আছে?",
        "th": "มีไฟไหม้ การรั่วไหลของเชื้อเพลิง หรืออันตรายอื่นๆ ที่เกิดขึ้นหรือไม่?",
        "si": "ස්ථානයේ ගිනි, ඉන්ධන ලීකයක් හෝ වෙනත් අනතුරක් තිබේද?",
    },
}

# Ordered by priority for asking
_CRITICAL_SLOTS = ("LOCATION", "CASUALTY_COUNT")
_IMPORTANT_SLOTS = ("HAZARD_TYPE", "ENTRAPMENT")

# Valid FSM states
STATES = (
    "INITIAL",
    "COLLECTING_LOCATION",
    "COLLECTING_CASUALTIES",
    "COLLECTING_HAZARD",
    "COMPLETE",
    "DISPATCHING",
)

# Map slot name → collecting state
_SLOT_TO_STATE: Dict[str, str] = {
    "LOCATION":      "COLLECTING_LOCATION",
    "CASUALTY_COUNT": "COLLECTING_CASUALTIES",
    "HAZARD_TYPE":   "COLLECTING_HAZARD",
}


class TriageStateMachine:
    """
    Plain-Python finite state machine for multi-turn triage slot recovery.
    No external FSM libraries — transitions are implemented as simple state
    string assignments, which are sufficient for a linear triage dialogue.
    """

    def __init__(self, session_store: SessionStore):
        self.store = session_store

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _followup(self, slot: str, lang: str) -> str:
        templates = _FOLLOWUP_TEMPLATES.get(slot, _FOLLOWUP_TEMPLATES["LOCATION"])
        return templates.get(lang, templates["en"])

    def _missing_critical(self, triage: str, filled: Dict[str, Any]) -> list:
        """Return list of critical missing slots given triage level."""
        missing = []
        if triage == "P1":
            # Both LOCATION and CASUALTY_COUNT block dispatch for P1
            for slot in _CRITICAL_SLOTS:
                val = filled.get(slot)
                if not val or val == "unknown":
                    missing.append(slot)
        else:
            # For P2/P3, LOCATION is still the primary missing slot to collect
            if not filled.get("LOCATION"):
                missing.append("LOCATION")
        return missing

    def _build_and_dispatch(
        self,
        s: SessionState,
        nlu: Dict[str, Any],
        triage: str,
        intent: str,
        message: str,
        language_hint: Optional[str],
    ) -> Dict[str, Any]:
        """Build CAP alert, mark session as DISPATCHING, return result dict."""
        s.state = "DISPATCHING"
        exporter = CAPv12Exporter()
        cap = exporter.build_alert(
            {
                "intent":     intent,
                "triage":     triage,
                "confidence": nlu.get("confidence", 0.0),
                "slots":      s.filled_slots,
                "language":   nlu.get("language") or language_hint or "en",
                "raw_text":   nlu.get("raw_text") or message,
            },
            sender="roadsos-nlu-v1",
            source_message=message,
        )
        valid, errors = exporter.validate_cap(cap)
        return {
            "session_id":           s.id,
            "turn":                 s.turn_count,
            "state":                s.state,
            "triage":               triage,
            "filled_slots":         dict(s.filled_slots),
            "missing_critical_slots": [],
            "follow_up_question":   None,
            "cap_alert":            cap if valid else None,
            "cap_validation_errors": errors if not valid else None,
            "ready_to_dispatch":    True,
            "intent":               intent,
        }

    # ── Core ─────────────────────────────────────────────────────────────────

    def process_turn(
        self,
        session_id: str,
        message: str,
        language_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process one dialogue turn for the given session.

        Turn 1: Run NLU, check critical slots, decide state.
        Turn 2+: Attempt to fill missing slot; if filled → dispatch.
                 If still missing after 2 attempts → mark 'unknown' → dispatch.

        Returns a rich dict (see module docstring for full schema).
        """
        # ── Retrieve or create session ───────────────────────────────────────
        s = self.store.get(session_id)
        if s is None:
            s = self.store.create(session_id)

        s.turn_count += 1
        s.last_active = time.time()

        # ── Run NLU ──────────────────────────────────────────────────────────
        nlu = run_nlu_pipeline(message)
        raw_slots = nlu.get("slots") or {}
        slots = normalise_slot_keys(raw_slots)

        # Merge newly extracted non-null slots into session
        for k, v in slots.items():
            if v is not None:
                s.filled_slots[k] = v

        # Resolve triage and intent (NLU result takes precedence)
        triage = (
            nlu.get("triage_level")
            or nlu.get("triage")
            or s.filled_slots.get("_triage")
            or "P3"
        )
        # Store triage in session for subsequent turns
        s.filled_slots["_triage"] = triage

        intent = nlu.get("intent") or "unknown"

        # Update detected language
        detected_lang = nlu.get("language") or language_hint or s.detected_language or "en"
        s.detected_language = detected_lang

        # ── Check which critical slots are still missing ──────────────────────
        missing = self._missing_critical(triage, s.filled_slots)

        if not missing:
            # All critical slots collected → go to COMPLETE then DISPATCHING
            s.state = "COMPLETE"
            return self._build_and_dispatch(s, nlu, triage, intent, message, language_hint)

        # ── We still have missing slots ───────────────────────────────────────
        slot_to_ask = missing[0]  # highest priority missing slot

        # Increment ask count for this slot
        s.ask_counts[slot_to_ask] = s.ask_counts.get(slot_to_ask, 0) + 1

        # If we've already asked more than 2 times → give up, mark unknown, dispatch
        if s.ask_counts[slot_to_ask] > 2:
            s.filled_slots[slot_to_ask] = "unknown"
            return self._build_and_dispatch(s, nlu, triage, intent, message, language_hint)

        # ── Ask the follow-up question ────────────────────────────────────────
        question = self._followup(slot_to_ask, detected_lang)
        s.state = _SLOT_TO_STATE.get(slot_to_ask, "COLLECTING_LOCATION")

        return {
            "session_id":             s.id,
            "turn":                   s.turn_count,
            "state":                  s.state,
            "triage":                 triage,
            "filled_slots":           dict(s.filled_slots),
            "missing_critical_slots": missing,
            "follow_up_question":     question,
            "cap_alert":              None,
            "cap_validation_errors":  None,
            "ready_to_dispatch":      False,
            "intent":                 intent,
        }

    def export_graph(self, session_id: str) -> str:
        """Return a DOT (Graphviz) representation of the FSM for audit purposes."""
        s = self.store.get(session_id)
        transitions = [
            ("INITIAL", "COLLECTING_LOCATION"),
            ("INITIAL", "COLLECTING_CASUALTIES"),
            ("INITIAL", "COLLECTING_HAZARD"),
            ("INITIAL", "COMPLETE"),
            ("COLLECTING_LOCATION", "COMPLETE"),
            ("COLLECTING_CASUALTIES", "COMPLETE"),
            ("COLLECTING_HAZARD", "COMPLETE"),
            ("COMPLETE", "DISPATCHING"),
            ("COLLECTING_LOCATION", "DISPATCHING"),
            ("COLLECTING_CASUALTIES", "DISPATCHING"),
            ("COLLECTING_HAZARD", "DISPATCHING"),
        ]
        current_state = s.state if s else "INITIAL"
        lines = ["digraph triage_fsm {", "  rankdir=LR;"]
        for st in STATES:
            shape = "doublecircle" if st == current_state else "circle"
            lines.append(f'  "{st}" [shape={shape}];')
        for src, dst in transitions:
            lines.append(f'  "{src}" -> "{dst}";')
        lines.append("}")
        return "\n".join(lines)
    