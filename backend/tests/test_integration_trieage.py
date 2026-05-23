from fastapi.testclient import TestClient
import uuid

from app.main import app


def test_single_turn_trieage_all_slots(monkeypatch):
    client = TestClient(app)

    # stub NLU to return all slots
    def stub_run(msg):
        return {"intent": "emergency_crash", "triage_level": "P1", "confidence": 0.98, "slots": {"LOCATION": "Main Rd", "CASUALTY_COUNT": "2", "ENTRAPMENT": "false"}, "language": "en", "raw_text": msg}

    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: stub_run(m))

    resp = client.post("/api/triage", json={"message": "accident on main rd 2 people"})
    assert resp.status_code == 200
    data = resp.json()
    assert "cap_alert" in data
    assert data["cap_alert"] is not None
    # follow-up may be present (legacy 'follow_up') — ensure response contains session info
    assert "session_id" in data


def test_parse_message_session_flow(monkeypatch):
    client = TestClient(app)

    # turn 1: missing location
    def nlu_missing_loc(msg):
        return {"intent": "emergency_crash", "triage_level": "P1", "confidence": 0.9, "slots": {"LOCATION": None, "CASUALTY_COUNT": "3"}, "language": "bn", "raw_text": msg}

    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: nlu_missing_loc(m))
    r1 = client.post("/api/triage/parse-message", json={"text": "accident 3 people", "language_hint": "bn"})
    assert r1.status_code == 200
    d1 = r1.json()
    sid = d1.get("session_id")
    assert d1.get("follow_up_question") is not None

    # turn 2: user provides location
    def nlu_with_loc(msg):
        return {"intent": "emergency_crash", "triage_level": "P1", "confidence": 0.88, "slots": {"LOCATION": "Dhaka Toll", "CASUALTY_COUNT": "3"}, "language": "bn", "raw_text": msg}

    monkeypatch.setattr('app.dialogue.state_machine.run_nlu_pipeline', lambda m: nlu_with_loc(m))
    r2 = client.post("/api/triage/parse-message", json={"text": "Dhaka Toll", "session_id": sid, "language_hint": "bn"})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2.get("state") == "DISPATCHING"
    assert d2.get("cap_alert") is not None
