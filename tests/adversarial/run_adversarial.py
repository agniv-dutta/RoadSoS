from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any
import sys

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from noise_injector import NoiseInjector


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DEFAULT_TIMEOUT = 10.0

_SLOT_ALIASES = {
    "casualties": "CASUALTY_COUNT",
    "casualty_count": "CASUALTY_COUNT",
    "CASUALTY_COUNT": "CASUALTY_COUNT",
    "entrapment": "ENTRAPMENT",
    "ENTRAPMENT": "ENTRAPMENT",
    "hazard_type": "HAZARD_TYPE",
    "HAZARD_TYPE": "HAZARD_TYPE",
    "child_involved": "CHILD_INVOLVED",
    "CHILD_INVOLVED": "CHILD_INVOLVED",
    "location_mention": "LOCATION",
    "LOCATION": "LOCATION",
}


def _load_dataset(name: str) -> list[dict[str, Any]]:
    path = BASE_DIR / f"{name}_dataset.json"
    with open(path, encoding="utf8") as fh:
        return json.load(fh)


def _canonical_slot_name(name: str) -> str:
    return _SLOT_ALIASES.get(name, name.upper())


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        lowered = text.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        if lowered in {"none", "null", ""}:
            return None
        return lowered
    return value


def _slot_value_matches(expected: Any, actual: Any, slot_name: str) -> bool:
    expected_norm = _normalize_value(expected)
    actual_norm = _normalize_value(actual)

    if expected_norm is None:
        return actual_norm is None
    if isinstance(expected_norm, bool):
        return bool(actual_norm) is expected_norm
    if isinstance(expected_norm, (int, float)):
        try:
            return float(actual_norm) == float(expected_norm)
        except Exception:
            return False

    expected_text = str(expected_norm).strip().lower()
    actual_text = "" if actual_norm is None else str(actual_norm).strip().lower()
    if slot_name == "LOCATION":
        return expected_text in actual_text or actual_text in expected_text
    return expected_text == actual_text


def _extract_actual_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    actual_slots = payload.get("filled_slots") or payload.get("slots") or {}
    normalized_slots: dict[str, Any] = {}
    for key, value in actual_slots.items():
        normalized_slots[_canonical_slot_name(key)] = value

    intent = payload.get("intent")
    if not intent and isinstance(payload.get("cap_alert"), dict):
        event = (((payload.get("cap_alert") or {}).get("alert") or {}).get("info") or {}).get("event")
        event_to_intent = {
            "Road Traffic Accident": "emergency_crash",
            "Vehicle Fire / Fuel Hazard": "fire_hazard",
            "Medical Emergency — Road Incident": "medical_emergency",
            "Vehicle Breakdown": "vehicle_assistance",
            "General Distress Call": "general_help",
            "Unclassified Emergency": "unknown",
        }
        intent = event_to_intent.get(event, "unknown")

    triage = payload.get("triage_result") or payload.get("triage_level")
    follow_up_question = payload.get("follow_up_question")
    return {
        "intent": intent or "unknown",
        "triage": triage or "unknown",
        "slots": normalized_slots,
        "follow_up_question": follow_up_question,
        "state": payload.get("state"),
        "session_id": payload.get("session_id"),
        "runtime_mode": payload.get("runtime_mode"),
        "status_code": payload.get("status_code", 200),
    }


def _compute_slot_f1(truth_rows: list[dict[str, Any]], pred_rows: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    slot_names = ["CASUALTY_COUNT", "ENTRAPMENT", "HAZARD_TYPE", "CHILD_INVOLVED", "LOCATION"]
    metrics: dict[str, dict[str, float]] = {}

    for slot_name in slot_names:
        tp = fp = fn = 0
        support = 0
        for expected, actual in zip(truth_rows, pred_rows):
            expected_has = expected.get(slot_name) is not None
            actual_has = actual.get(slot_name) is not None
            if expected_has:
                support += 1
            matches = _slot_value_matches(expected.get(slot_name), actual.get(slot_name), slot_name)
            if expected_has and actual_has and matches:
                tp += 1
            elif expected_has and (not actual_has or not matches):
                fn += 1
                if actual_has and not matches:
                    fp += 1
            elif actual_has and not expected_has:
                fp += 1

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        metrics[slot_name] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": float(support),
        }
    return metrics


def _phase_short_name(path: Path) -> str:
    return path.stem.replace("_dataset", "")


def _wait_for_server(base_url: str, timeout: float = DEFAULT_TIMEOUT) -> None:
    deadline = time.time() + timeout
    health_url = f"{base_url.rstrip('/')}/api/triage/health"
    last_error = None
    while time.time() < deadline:
        try:
            response = requests.get(health_url, timeout=2.0)
            if response.status_code == 200:
                return
            last_error = f"HTTP {response.status_code}: {response.text}"
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.5)
    raise RuntimeError(f"API did not become ready at {health_url}: {last_error}")


def _evaluate_phase(base_url: str, dataset_name: str) -> dict[str, Any]:
    phase_key = f"phase_{dataset_name[-1]}" if dataset_name.startswith("phase_") else dataset_name
    examples = _load_dataset(dataset_name)
    phase_failures: list[dict[str, Any]] = []
    truth_rows: list[dict[str, Any]] = []
    pred_rows: list[dict[str, Any]] = []
    passed = 0
    crashed = 0
    intent_correct = 0
    session = requests.Session()

    for example in examples:
        payload = {
            "text": example["text"],
            "session_id": "",
            "language_hint": example.get("language"),
        }
        try:
            response = session.post(
                f"{base_url.rstrip('/')}/api/triage/parse-message",
                json=payload,
                timeout=DEFAULT_TIMEOUT,
            )
            status_code = response.status_code
            data = response.json() if status_code == 200 else {"error": response.text}
        except Exception as exc:
            crashed += 1
            phase_failures.append(
                {
                    "id": example["id"],
                    "text": example["text"],
                    "expected": {
                        "intent": example["expected_intent"],
                        "triage": example["expected_triage"],
                        "slots": example["expected_slots"],
                    },
                    "actual": {"error": str(exc), "status_code": None},
                    "failure_reason": f"request_failed: {exc}",
                }
            )
            continue

        snapshot = _extract_actual_snapshot({**data, "status_code": status_code})
        actual_slots = snapshot["slots"]
        if status_code == 200:
            crashed += 0
        else:
            crashed += 1

        expected_slots = example["expected_slots"]
        truth_row = { _canonical_slot_name(k): v for k, v in expected_slots.items() }
        pred_row = { _canonical_slot_name(k): actual_slots.get(_canonical_slot_name(k)) for k in expected_slots }
        truth_rows.append(truth_row)
        pred_rows.append(pred_row)

        intent_match = snapshot["intent"] == example["expected_intent"]
        triage_match = snapshot["triage"] == example["expected_triage"]
        slot_matches = []
        for slot_name, expected_value in truth_row.items():
            actual_value = actual_slots.get(slot_name)
            slot_ok = _slot_value_matches(expected_value, actual_value, slot_name)
            slot_matches.append(slot_ok)

        follow_up_expected = any(value is None for value in expected_slots.values())
        follow_up_ok = True
        if follow_up_expected:
            follow_up_ok = bool(snapshot.get("follow_up_question"))

        all_match = intent_match and triage_match and all(slot_matches) and follow_up_ok and status_code == 200
        if intent_match:
            intent_correct += 1
        if all_match:
            passed += 1
        else:
            reasons = []
            if status_code != 200:
                reasons.append(f"http_{status_code}")
            if not intent_match:
                reasons.append("intent_mismatch")
            if not triage_match:
                reasons.append("triage_mismatch")
            for slot_name, expected_value in truth_row.items():
                actual_value = actual_slots.get(slot_name)
                if not _slot_value_matches(expected_value, actual_value, slot_name):
                    reasons.append(f"slot_mismatch:{slot_name}")
            if follow_up_expected and not follow_up_ok:
                reasons.append("follow_up_not_triggered")

            phase_failures.append(
                {
                    "id": example["id"],
                    "text": example["text"],
                    "expected": {
                        "intent": example["expected_intent"],
                        "triage": example["expected_triage"],
                        "slots": example["expected_slots"],
                    },
                    "actual": {
                        "intent": snapshot["intent"],
                        "triage": snapshot["triage"],
                        "slots": actual_slots,
                        "follow_up_question": snapshot.get("follow_up_question"),
                        "status_code": status_code,
                    },
                    "failure_reason": ",".join(reasons) or "mismatch",
                }
            )

    no_crash_rate = 1.0 - (crashed / max(1, len(examples)))
    phase_report = {
        "pass_rate": round(passed / max(1, len(examples)), 4),
        "intent_acc": round(intent_correct / max(1, len(examples)), 4),
        "slot_f1_by_slot": _compute_slot_f1(truth_rows, pred_rows),
        "no_crash_rate": round(no_crash_rate, 4),
        "failures": phase_failures,
        "count": len(examples),
        "passed": passed,
    }
    return phase_report


def run_adversarial(base_url: str = DEFAULT_BASE_URL) -> dict[str, Any]:
    _wait_for_server(base_url)
    report: dict[str, Any] = {}
    total_messages = 0
    total_passed = 0

    for dataset_name in ("phase_a", "phase_b", "phase_c"):
        phase_report = _evaluate_phase(base_url, dataset_name)
        report[dataset_name] = {
            "pass_rate": phase_report["pass_rate"],
            "intent_acc": phase_report["intent_acc"],
            "slot_f1_by_slot": phase_report["slot_f1_by_slot"],
            "no_crash_rate": phase_report["no_crash_rate"],
            "failures": phase_report["failures"],
        }
        total_messages += phase_report["count"]
        total_passed += phase_report["passed"]

    report["overall"] = {
        "total_messages": total_messages,
        "total_passed": total_passed,
        "overall_pass_rate": round(total_passed / max(1, total_messages), 4),
    }

    output_path = BASE_DIR / "adversarial_report.json"
    with open(output_path, "w", encoding="utf8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    return report


def _assert_thresholds(report: dict[str, Any]) -> None:
    suggestions = []
    for phase_key, threshold in (("phase_a", 0.72), ("phase_b", 0.68), ("phase_c", 0.75)):
        phase_report = report[phase_key]
        if phase_report["no_crash_rate"] < 1.0:
            suggestions.append(f"{phase_key}: eliminate 500s in parse-message and state_machine paths.")
        if phase_report["pass_rate"] < threshold:
            suggestions.append(f"{phase_key}: improve parsing for fragmented/code-switched/noisy inputs.")
    if suggestions:
        raise AssertionError("Adversarial thresholds not met. Suggestions: " + " | ".join(suggestions))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RoadSoS adversarial stress tests")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    _ = NoiseInjector(seed=args.seed)
    report = run_adversarial(base_url=args.base_url)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    _assert_thresholds(report)


if __name__ == "__main__":
    main()
