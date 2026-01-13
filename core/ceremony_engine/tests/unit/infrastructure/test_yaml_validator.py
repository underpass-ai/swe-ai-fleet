"""Unit tests for CeremonyDefinitionValidator."""

import pytest
import yaml
from pathlib import Path
from tempfile import NamedTemporaryFile

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.infrastructure.yaml_validator import CeremonyDefinitionValidator


def test_validate_and_parse_from_file_happy_path() -> None:
    """Test parsing valid ceremony YAML file."""
    yaml_content = """version: "1.0"
name: "dummy_ceremony"
description: "Minimal example ceremony for testing"
inputs:
  required:
    - input_data
  optional: []
outputs:
  result:
    type: object
    schema:
      status: string
      value: string
states:
  - id: STARTED
    description: "Ceremony started"
    initial: true
    terminal: false
  - id: PROCESSED
    description: "Processing complete"
    initial: false
    terminal: true
transitions:
  - from: STARTED
    to: PROCESSED
    trigger: "process"
    guards: []
    description: "Process input"
steps:
  - id: process_step
    state: STARTED
    handler: aggregation_step
    config:
      operation: echo
guards: {}
roles:
  - id: SYSTEM
    description: "System role"
    allowed_actions: []
timeouts:
  step_default: 60
  step_max: 3600
  ceremony_max: 86400
retry_policies:
  default:
    max_attempts: 3
    backoff_seconds: 5
    exponential_backoff: false
"""

    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as tmp_file:
        tmp_file.write(yaml_content)
        tmp_file_path = tmp_file.name

    try:
        definition = CeremonyDefinitionValidator.validate_and_parse_from_file(tmp_file_path)

        assert isinstance(definition, CeremonyDefinition)
        assert definition.name == "dummy_ceremony"
        assert definition.version == "1.0"
        assert len(definition.states) == 2
        assert len(definition.transitions) == 1
        assert len(definition.steps) == 1
        assert len(definition.roles) == 1
    finally:
        Path(tmp_file_path).unlink(missing_ok=True)


def test_validate_and_parse_from_file_not_found() -> None:
    """Test that FileNotFoundError is raised for non-existent file."""
    with pytest.raises(FileNotFoundError):
        CeremonyDefinitionValidator.validate_and_parse_from_file("non_existent.yaml")


def test_validate_and_parse_happy_path() -> None:
    """Test parsing valid ceremony YAML data."""
    yaml_data = {
        "version": "1.0",
        "name": "test_ceremony",
        "description": "Test ceremony",
        "inputs": {"required": ["input1"], "optional": []},
        "outputs": {"result": {"type": "object", "schema": {}}},
        "states": [
            {"id": "STARTED", "description": "Started", "initial": True, "terminal": False},
            {"id": "COMPLETED", "description": "Completed", "initial": False, "terminal": True},
        ],
        "transitions": [
            {
                "from": "STARTED",
                "to": "COMPLETED",
                "trigger": "complete",
                "guards": [],
                "description": "Complete",
            }
        ],
        "steps": [
            {
                "id": "process",
                "state": "STARTED",
                "handler": "aggregation_step",
                "config": {"operation": "echo"},
            }
        ],
        "guards": {},
        "roles": [{"id": "SYSTEM", "description": "System", "allowed_actions": []}],
        "timeouts": {"step_default": 60, "step_max": 3600, "ceremony_max": 86400},
        "retry_policies": {
            "default": {"max_attempts": 3, "backoff_seconds": 5, "exponential_backoff": False}
        },
    }

    definition = CeremonyDefinitionValidator.validate_and_parse(yaml_data)

    assert definition.name == "test_ceremony"
    assert definition.version == "1.0"
    assert len(definition.states) == 2
    assert len(definition.transitions) == 1
    assert len(definition.steps) == 1


def test_validate_and_parse_rejects_missing_version() -> None:
    """Test that missing version raises ValueError."""
    yaml_data = {
        "name": "test",
        "states": [],
        "transitions": [],
    }

    with pytest.raises(ValueError, match="Missing required key: version"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_rejects_missing_name() -> None:
    """Test that missing name raises ValueError."""
    yaml_data = {
        "version": "1.0",
        "states": [],
        "transitions": [],
    }

    with pytest.raises(ValueError, match="Missing required key: name"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_rejects_missing_states() -> None:
    """Test that missing states raises ValueError."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "transitions": [],
    }

    with pytest.raises(ValueError, match="Missing required key: states"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_rejects_missing_transitions() -> None:
    """Test that missing transitions raises ValueError."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "states": [],
    }

    with pytest.raises(ValueError, match="Missing required key: transitions"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_rejects_non_dict_root() -> None:
    """Test that non-dict YAML data raises ValueError."""
    with pytest.raises(ValueError, match="YAML data must be a dict"):
        CeremonyDefinitionValidator.validate_and_parse("not a dict")  # type: ignore[arg-type]


def test_validate_and_parse_invalid_step_handler() -> None:
    """Test that invalid step handler type raises ValueError."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "states": [{"id": "STARTED", "description": "Started", "initial": True, "terminal": False}],
        "transitions": [],
        "steps": [
            {
                "id": "process",
                "state": "STARTED",
                "handler": "invalid_handler",
                "config": {"operation": "echo"},
            }
        ],
        "guards": {},
        "roles": [],
        "timeouts": {"step_default": 60, "step_max": 3600, "ceremony_max": 86400},
        "retry_policies": {},
    }

    with pytest.raises(ValueError, match="Invalid step handler type"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_invalid_guard_type() -> None:
    """Test that invalid guard type raises ValueError."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "states": [{"id": "STARTED", "description": "Started", "initial": True, "terminal": False}],
        "transitions": [],
        "steps": [],
        "guards": {"test_guard": {"type": "invalid_type", "check": "expression"}},
        "roles": [],
        "timeouts": {"step_default": 60, "step_max": 3600, "ceremony_max": 86400},
        "retry_policies": {},
    }

    with pytest.raises(ValueError, match="Invalid guard type"):
        CeremonyDefinitionValidator.validate_and_parse(yaml_data)


def test_validate_and_parse_with_retry_policy() -> None:
    """Test parsing step with retry policy."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "description": "Test",
        "inputs": {"required": [], "optional": []},
        "outputs": {},
        "states": [{"id": "STARTED", "description": "Started", "initial": True, "terminal": False}],
        "transitions": [],
        "steps": [
            {
                "id": "process",
                "state": "STARTED",
                "handler": "aggregation_step",
                "config": {"operation": "echo"},
                "retry": {"max_attempts": 3, "backoff_seconds": 5, "exponential_backoff": True},
            }
        ],
        "guards": {},
        "roles": [],
        "timeouts": {"step_default": 60, "step_max": 3600, "ceremony_max": 86400},
        "retry_policies": {},
    }

    definition = CeremonyDefinitionValidator.validate_and_parse(yaml_data)

    assert definition.steps[0].retry is not None
    assert definition.steps[0].retry.max_attempts == 3
    assert definition.steps[0].retry.backoff_seconds == 5
    assert definition.steps[0].retry.exponential_backoff is True


def test_validate_and_parse_with_timeout() -> None:
    """Test parsing step with timeout."""
    yaml_data = {
        "version": "1.0",
        "name": "test",
        "description": "Test",
        "inputs": {"required": [], "optional": []},
        "outputs": {},
        "states": [{"id": "STARTED", "description": "Started", "initial": True, "terminal": False}],
        "transitions": [],
        "steps": [
            {
                "id": "process",
                "state": "STARTED",
                "handler": "aggregation_step",
                "config": {"operation": "echo"},
                "timeout_seconds": 120,
            }
        ],
        "guards": {},
        "roles": [],
        "timeouts": {"step_default": 60, "step_max": 3600, "ceremony_max": 86400},
        "retry_policies": {},
    }

    definition = CeremonyDefinitionValidator.validate_and_parse(yaml_data)

    assert definition.steps[0].timeout_seconds == 120
