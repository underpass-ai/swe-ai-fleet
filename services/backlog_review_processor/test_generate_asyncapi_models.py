import pytest

from services.backlog_review_processor.scripts.generate_asyncapi_models import (
    build_agent_response_json_schema,
)


def test_build_agent_response_json_schema_uses_https_schema() -> None:
    payload = {
        "description": "Test description",
        "properties": {
            "foo": {"type": "string"},
        },
        "required": ["foo"],
    }
    schema = build_agent_response_json_schema(payload)
    assert schema["$schema"] == "https://json-schema.org/draft-07/schema#"
    assert schema["type"] == "object"
    assert schema["title"] == "AgentResponsePayload"
    assert schema["description"] == "Test description"
    assert schema["properties"] == payload["properties"]
    assert schema["required"] == payload["required"]


@pytest.mark.parametrize(
    "payload, expected_description, expected_properties, expected_required",
    [
        ({}, "", {}, []),
        (
            {"description": "Only description"},
            "Only description",
            {},
            [],
        ),
        (
            {"properties": {"bar": {"type": "integer"}}},
            "",
            {"bar": {"type": "integer"}},
            [],
        ),
        (
            {"required": ["bar"]},
            "",
            {},
            ["bar"],
        ),
    ],
)
def test_build_agent_response_json_schema_defaults_and_partial_payloads(
    payload: dict[str, object],
    expected_description: str,
    expected_properties: dict[str, object],
    expected_required: list[str],
) -> None:
    schema = build_agent_response_json_schema(payload)

    assert schema["$schema"] == "https://json-schema.org/draft-07/schema#"
    assert schema["type"] == "object"
    assert schema["title"] == "AgentResponsePayload"
    assert schema["description"] == expected_description
    assert schema["properties"] == expected_properties
    assert schema["required"] == expected_required
