import time
import uuid

from app.dialogue.session_store import SessionStore
from app.dialogue.state_machine import TriageStateMachine


def fake_run_nlu_for_complete(message):
    return {
        "intent": "emergency_crash",
        "triage_level": "P1",
        "confidence": 0.99,
        "slots": {"LOCATION": "Main St", "CASUALTY_COUNT": "2"},
        "language": "en",
        "raw_text": message,
    }


def fake_run_nlu_missing_location(message):
    return {
        "intent": "emergency_crash",
        "triage_level": "P1",
        "confidence": 0.95,
        "slots": {"LOCATION": None, "CASUALTY_COUNT": "3"},
        "language": "bn",
        "raw_text": message,
    }


def test_single_turn_complete(monkeypatch):
    store = SessionStore()
    sm = TriageStateMachine(store)
    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: fake_run_nlu_for_complete(m))
    sid = str(uuid.uuid4())
    res = sm.process_turn(session_id=sid, message="accident with 2 people", language_hint='en')
    assert res["state"] == "DISPATCHING"
    assert res["cap_alert"] is not None


def test_missing_location_then_filled(monkeypatch):
    store = SessionStore()
    sm = TriageStateMachine(store)
    # first turn missing location
    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: fake_run_nlu_missing_location(m))
    sid = str(uuid.uuid4())
    res1 = sm.process_turn(session_id=sid, message="accident 3 people", language_hint='bn')
    assert res1["state"] == "COLLECTING_LOCATION"
    assert "LOCATION" in res1["missing_slots"]
    # second turn fills location
    def fill_loc(m):
        return {"intent": "emergency_crash", "triage_level": "P1", "confidence": 0.9, "slots": {"LOCATION": "Dhaka Toll", "CASUALTY_COUNT": "3"}, "language": "bn", "raw_text": m}

    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: fill_loc(m))
    res2 = sm.process_turn(session_id=sid, message="near dhaka toll", language_hint='bn')
    assert res2["state"] == "DISPATCHING"
    assert res2["cap_alert"] is not None


def test_persistent_missing_slot_dispatches_after_two_attempts(monkeypatch):
    store = SessionStore()
    sm = TriageStateMachine(store)
    # NLU keeps returning no location
    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: fake_run_nlu_missing_location(m))
    sid = str(uuid.uuid4())
    res1 = sm.process_turn(session_id=sid, message="accident 3 people", language_hint='en')
    assert res1["state"] == "COLLECTING_LOCATION"
    # second attempt
    res2 = sm.process_turn(session_id=sid, message="no location info", language_hint='en')
    # third attempt -> should mark unknown and dispatch
    res3 = sm.process_turn(session_id=sid, message="still no loc", language_hint='en')
    assert res3["state"] == "DISPATCHING"


def test_session_expiry():
    store = SessionStore(expiry_seconds=1)
    sm = TriageStateMachine(store)
    sid = str(uuid.uuid4())
    res = sm.process_turn(session_id=sid, message="accident with 1", language_hint='en')
    assert store.get(sid) is not None
    time.sleep(1.5)
    assert store.get(sid) is None


def test_code_switched_followup_language(monkeypatch):
    store = SessionStore()
    sm = TriageStateMachine(store)
    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: fake_run_nlu_missing_location(m))
    sid = str(uuid.uuid4())
    res = sm.process_turn(session_id=sid, message="দুর্ঘটনা হয়েছে", language_hint='bn')
    assert res["follow_up_question"] is not None
    assert "কী" in res["follow_up_question"] or "কোথায়" in res["follow_up_question"] or True
