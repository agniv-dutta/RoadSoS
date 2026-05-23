import json
import re

from app.nlu.cap_exporter import CAPv12Exporter


def test_p1_alert_maps_to_immediate():
    exporter = CAPv12Exporter()
    nlu = {
        "intent": "emergency_crash",
        "triage": "P1",
        "confidence": 0.99,
        "slots": {"LOCATION": "Highway A1", "CASUALTY_COUNT": "3"},
        "language": "en",
        "raw_text": "accident on highway",
    }
    cap = exporter.build_alert(nlu, sender="test-sender", source_message=nlu["raw_text"])
    assert cap["alert"]["info"]["urgency"] == "Immediate"
    assert cap["alert"]["info"]["severity"] == "Extreme"
    ok, errors = exporter.validate_cap(cap)
    assert ok, f"Validation failed: {errors}"


def test_missing_location_areadesc_unknown():
    exporter = CAPv12Exporter()
    nlu = {
        "intent": "medical_emergency",
        "triage": "P2",
        "confidence": 0.8,
        "slots": {"CASUALTY_COUNT": "1", "LOCATION": None},
        "language": "en",
        "raw_text": "man collapsed",
    }
    cap = exporter.build_alert(nlu, sender="s", source_message=nlu["raw_text"])
    assert cap["alert"]["info"]["area"]["areaDesc"] == "Location unknown"


def test_null_slots_excluded_from_parameters():
    exporter = CAPv12Exporter()
    nlu = {
        "intent": "fire_hazard",
        "triage": "P2",
        "confidence": 0.7,
        "slots": {"CASUALTY_COUNT": None, "ENTRAPMENT": "true"},
        "language": "en",
        "raw_text": "tanker leak",
    }
    cap = exporter.build_alert(nlu, sender="s", source_message=nlu["raw_text"])
    names = [p["valueName"] for p in cap["alert"]["info"]["parameter"]]
    assert "casualtyCount" not in names
    assert "entrapment" in names


def test_validate_catches_missing_fields():
    exporter = CAPv12Exporter()
    # craft a broken CAP missing sender and info
    broken = {"alert": {"identifier": "x"}}
    ok, errors = exporter.validate_cap(broken)
    assert not ok
    assert "alert.sender" in errors or any(e.startswith("alert.") for e in errors)


def test_identifier_uniqueness():
    exporter = CAPv12Exporter()
    nlu = {"intent": "vehicle_assistance", "triage": "P3", "slots": {}, "language": "en", "raw_text": "need tow"}
    cap1 = exporter.build_alert(nlu, sender="s", source_message=nlu["raw_text"])
    cap2 = exporter.build_alert(nlu, sender="s", source_message=nlu["raw_text"])
    id1 = cap1["alert"]["identifier"]
    id2 = cap2["alert"]["identifier"]
    assert id1 != id2


def test_bengali_preserved_in_serialization():
    exporter = CAPv12Exporter()
    bengali_text = "দুর্ঘটনা ৩ জন আটকে আছেন"
    nlu = {"intent": "emergency_crash", "triage": "P1", "slots": {"LOCATION": "ঢাকা"}, "language": "bn", "raw_text": bengali_text}
    cap = exporter.build_alert(nlu, sender="roadsos", source_message=bengali_text)
    s = exporter.to_json(cap)
    # ensure non-ascii Bengali snippet is present in JSON (ensure_ascii=False)
    assert "দুর্ঘটনা" in s
