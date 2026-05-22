"""
Slot definitions and triage logic for PS #9 NLU pipeline.
Triage levels follow IAED priority dispatch protocol.
Output schema conforms to CAP v1.2.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# ─── Intent Labels ────────────────────────────────────────────────────────────

class Intent(str, Enum):
    EMERGENCY_CRASH   = "emergency_crash"
    FIRE_HAZARD       = "fire_hazard"
    MEDICAL_EMERGENCY = "medical_emergency"
    VEHICLE_ASSISTANCE = "vehicle_assistance"
    GENERAL_HELP      = "general_help"
    UNKNOWN           = "unknown"


# ─── Hazard Types ─────────────────────────────────────────────────────────────

class HazardType(str, Enum):
    FIRE      = "fire"
    FUEL_LEAK = "fuel_leak"
    NONE      = "none"
    UNKNOWN   = "unknown"


# ─── Triage Levels (IAED-aligned) ─────────────────────────────────────────────

class TriageLevel(str, Enum):
    P1 = "P1"   # Critical — immediate life threat
    P2 = "P2"   # Serious  — urgent but stable
    P3 = "P3"   # Minor    — non-urgent


# ─── CAP v1.2 Severity Mapping ────────────────────────────────────────────────

TRIAGE_TO_CAP_SEVERITY = {
    TriageLevel.P1: "Extreme",
    TriageLevel.P2: "Severe",
    TriageLevel.P3: "Minor",
}

TRIAGE_TO_CAP_URGENCY = {
    TriageLevel.P1: "Immediate",
    TriageLevel.P2: "Expected",
    TriageLevel.P3: "Future",
}


# ─── Extracted Slots Dataclass ─────────────────────────────────────────────────

@dataclass
class ExtractedSlots:
    casualties:       Optional[int]  = None   # number of people injured/affected
    entrapment:       bool           = False   # people physically trapped
    hazard_type:      HazardType     = HazardType.NONE
    child_involved:   bool           = False
    location_mention: Optional[str]  = None   # raw text location reference
    missing_slots:    list           = field(default_factory=list)


# ─── Triage Rules ─────────────────────────────────────────────────────────────

def compute_triage_level(slots: ExtractedSlots, intent: Intent) -> TriageLevel:
    """
    Rule-based triage assignment.
    Priority: entrapment + fire > child + multiple casualties > single serious > minor.
    """

    # P1 — Critical triggers
    if slots.entrapment and slots.hazard_type in (HazardType.FIRE, HazardType.FUEL_LEAK):
        return TriageLevel.P1

    if slots.entrapment:
        return TriageLevel.P1

    if slots.hazard_type in (HazardType.FIRE, HazardType.FUEL_LEAK):
        return TriageLevel.P1

    if slots.child_involved and intent in (Intent.EMERGENCY_CRASH, Intent.MEDICAL_EMERGENCY):
        return TriageLevel.P1

    if slots.casualties is not None and slots.casualties >= 3:
        return TriageLevel.P1

    if intent == Intent.MEDICAL_EMERGENCY and slots.casualties is None:
        # Unknown casualty count in medical emergency → treat as serious
        return TriageLevel.P1

    # P2 — Serious but stable
    if slots.casualties is not None and slots.casualties in (1, 2):
        return TriageLevel.P2

    if intent in (Intent.EMERGENCY_CRASH, Intent.MEDICAL_EMERGENCY):
        return TriageLevel.P2

    # P3 — Minor / no injury
    if slots.casualties == 0 and not slots.entrapment:
        return TriageLevel.P3

    if intent == Intent.VEHICLE_ASSISTANCE:
        return TriageLevel.P3

    return TriageLevel.P2  # Default: treat as serious if uncertain


# ─── Missing Slot Follow-up Questions ─────────────────────────────────────────

FOLLOW_UP_QUESTIONS = {
    "casualties":       "How many people are injured or affected?",
    "entrapment":       "Is anyone physically trapped inside a vehicle?",
    "hazard_type":      "Is there any fire, smoke, or fuel leakage?",
    "child_involved":   "Are any children involved?",
    "location_mention": "What is the location or nearest landmark?",
}


def get_follow_up(slots: ExtractedSlots) -> Optional[str]:
    """Return the most critical unanswered follow-up question."""
    priority_order = ["location_mention", "casualties", "entrapment", "hazard_type"]
    for slot in priority_order:
        if slot in slots.missing_slots:
            return FOLLOW_UP_QUESTIONS[slot]
    return None
