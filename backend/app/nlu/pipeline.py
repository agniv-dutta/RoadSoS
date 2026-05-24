import logging
from app.nlu.inference_engine import get_nlu_engine, nlu_result_to_pipeline_dict
from app.nlu.slots import ExtractedSlots, HazardType, get_follow_up

logger = logging.getLogger(__name__)

def run_nlu_pipeline(message: str) -> dict:
    engine = get_nlu_engine()
    result = engine.predict(message)
    pipeline_result = nlu_result_to_pipeline_dict(result, raw_text=message)

    if not message or not message.strip():
        pipeline_result["follow_up_question"] = "Can you describe what happened?"
        pipeline_result["missing_slots"] = ["location_mention", "casualties"]
        return pipeline_result

    slots = result.slots or {}
    extracted = ExtractedSlots(
        casualties=slots.get("casualties"),
        entrapment=bool(slots.get("entrapment", False)),
        hazard_type=HazardType(slots.get("hazard_type", HazardType.NONE.value))
        if slots.get("hazard_type") in HazardType._value2member_map_
        else HazardType.NONE,
        child_involved=bool(slots.get("child_involved", False)),
        location_mention=slots.get("location_mention"),
    )

    missing_slots = []
    if extracted.location_mention is None:
        missing_slots.append("location_mention")
    if extracted.casualties is None:
        missing_slots.append("casualties")
    if not extracted.entrapment and extracted.casualties and extracted.casualties > 0:
        missing_slots.append("entrapment")

    pipeline_result["missing_slots"] = missing_slots
    pipeline_result["follow_up_question"] = get_follow_up(extracted)
    pipeline_result["runtime_mode"] = result.runtime_mode
    return pipeline_result


def load_classifier():
    """Backward-compatible loader name retained for existing startup hooks."""
    return get_nlu_engine()
