import uuid
import json
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, List


class CAPv12Exporter:
    """Deterministic transformer from NLU output to CAP v1.2 JSON.

    Works offline (no external calls). All fields are generated deterministically.
    """

    TRIAGE_MAP = {
        "P1": {"urgency": "Immediate", "severity": "Extreme", "certainty": "Observed"},
        "P2": {"urgency": "Expected",  "severity": "Severe",  "certainty": "Likely"},
        "P3": {"urgency": "Future",    "severity": "Moderate","certainty": "Possible"},
    }

    SLOT_PARAM_MAPPING = {
        "CASUALTY_COUNT": "casualtyCount",
        "HAZARD_TYPE": "hazardType",
        "ENTRAPMENT": "entrapment",
        "CHILD_INVOLVED": "vulnerablePersons",
        "triage": "triageLevel",
    }

    def build_alert(self, nlu_result: Dict[str, Any], sender: str, source_message: str) -> Dict[str, Any]:
        triage = nlu_result.get("triage") or nlu_result.get("triage_level") or nlu_result.get("triageLevel")
        triage = triage if triage in self.TRIAGE_MAP else "P3"

        mapped = self.TRIAGE_MAP.get(triage, self.TRIAGE_MAP["P3"])

        info = {
            "language": nlu_result.get("language") or "en",
            "category": "Transport",
            "event": nlu_result.get("intent", "unknown"),
            "urgency": mapped["urgency"],
            "severity": mapped["severity"],
            "certainty": mapped["certainty"],
            "description": source_message,
            "area": {"areaDesc": "Location unknown"},
            "parameter": [],
            "resource": [],
        }

        slots = nlu_result.get("slots") or {}
        # LOCATION special handling
        loc = slots.get("LOCATION") if isinstance(slots, dict) else None
        if loc:
            info["area"]["areaDesc"] = loc

        # parameters: include only non-null slots per mapping
        for slot_key, param_name in self.SLOT_PARAM_MAPPING.items():
            # triage param should reflect triage variable
            if slot_key == "triage":
                value = triage
            else:
                value = slots.get(slot_key)
            if value is None:
                continue
            # Normalize boolean-ish strings
            if isinstance(value, str) and value.lower() in {"true", "false"}:
                val = value.lower()
            else:
                val = value
            info["parameter"].append({"valueName": param_name, "value": str(val)})

        # Always include triageLevel parameter even if not present in slots
        if not any(p["valueName"] == "triageLevel" for p in info["parameter"]):
            info["parameter"].append({"valueName": "triageLevel", "value": triage})

        alert = {
            "alert": {
                "identifier": f"ROADSOS-{uuid.uuid4()}",
                "sender": sender,
                "sent": datetime.now(timezone.utc).isoformat(),
                "status": "Actual",
                "msgType": "Alert",
                "scope": "Restricted",
                "restriction": "Emergency responders only",
                "info": info,
            }
        }

        return alert

    def validate_cap(self, cap_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not isinstance(cap_dict, dict) or "alert" not in cap_dict:
            return False, ["alert"]
        a = cap_dict["alert"]
        # top-level mandatory fields
        for f in ["identifier", "sender", "sent", "status", "msgType", "scope"]:
            if not a.get(f):
                errors.append(f"alert.{f}")

        info = a.get("info")
        if not info or not isinstance(info, dict):
            errors.append("alert.info")
            return False, errors

        for f in ["language", "category", "event", "urgency", "severity", "certainty", "description"]:
            if not info.get(f):
                errors.append(f"alert.info.{f}")

        area = info.get("area")
        if not area or not area.get("areaDesc"):
            errors.append("alert.info.area.areaDesc")

        # triage consistency check: if triageLevel param exists and equals P1, urgency must be Immediate
        params = info.get("parameter") or []
        triage_val = None
        for p in params:
            if p.get("valueName") == "triageLevel":
                triage_val = p.get("value")
                break

        if triage_val == "P1" and info.get("urgency") != "Immediate":
            errors.append("alert.info.urgency_inconsistent_with_triage")

        return (len(errors) == 0), errors

    def to_json(self, cap_dict: Dict[str, Any]) -> str:
        return json.dumps(cap_dict, ensure_ascii=False, indent=2)
