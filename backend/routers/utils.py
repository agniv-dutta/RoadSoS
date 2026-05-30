from typing import Dict, Any


def mock_service_list(service_type: str, location: Dict[str, float]) -> list:
    return [
        {
            "name": f"{service_type.title()} Service A",
            "address": "123 Main St",
            "distance_km": 1.2,
        },
        {
            "name": f"{service_type.title()} Service B",
            "address": "456 Elm St",
            "distance_km": 2.8,
        },
    ]


def standard_response(message: str, data: Any = None) -> Dict[str, Any]:
    return {"status": "success", "message": message, "data": data or {}}
