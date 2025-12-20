"""JSON Schema para task extraction con structured outputs."""

from typing import Any

TASK_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "minLength": 1},
                    "description": {"type": "string", "minLength": 1},
                    "estimated_hours": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 200,
                    },
                    "deliberation_indices": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0},
                    },
                    "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                },
                "required": ["title", "description", "estimated_hours", "priority"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["tasks"],
    "additionalProperties": False,
}
