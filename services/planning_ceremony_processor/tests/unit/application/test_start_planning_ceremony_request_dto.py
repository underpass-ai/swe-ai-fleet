"""Tests for StartPlanningCeremonyRequestDTO."""

import pytest

from services.planning_ceremony_processor.application.dto.start_planning_ceremony_request_dto import (
    StartPlanningCeremonyRequestDTO,
)


def test_start_planning_ceremony_request_dto_happy_path() -> None:
    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id="corr-1",
        inputs={"input_data": "value"},
        step_ids=("submit_architect",),
        requested_by="product_owner",
    )

    assert dto.ceremony_id == "cer-1"
    assert dto.definition_name == "planning_ceremony"


def test_start_planning_ceremony_request_dto_rejects_empty_ceremony_id() -> None:
    with pytest.raises(ValueError, match="ceremony_id cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=None,
            inputs={},
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_whitespace_ceremony_id() -> None:
    with pytest.raises(ValueError, match="ceremony_id cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id=" ",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=None,
            inputs={},
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_empty_definition_name() -> None:
    with pytest.raises(ValueError, match="definition_name cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="",
            story_id="story-1",
            correlation_id=None,
            inputs={},
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_empty_story_id() -> None:
    with pytest.raises(ValueError, match="story_id cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="planning_ceremony",
            story_id="",
            correlation_id=None,
            inputs={},
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_blank_correlation_id_when_provided() -> None:
    with pytest.raises(ValueError, match="correlation_id cannot be blank when provided"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=" ",
            inputs={},
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_inputs_not_dict() -> None:
    with pytest.raises(ValueError, match="inputs must be a dict"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=None,
            inputs="not_a_dict",  # type: ignore[arg-type]
            step_ids=("submit_architect",),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_empty_step_ids() -> None:
    with pytest.raises(ValueError, match="step_ids cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=None,
            inputs={},
            step_ids=(),
            requested_by="product_owner",
        )


def test_start_planning_ceremony_request_dto_rejects_blank_requested_by() -> None:
    with pytest.raises(ValueError, match="requested_by cannot be empty"):
        StartPlanningCeremonyRequestDTO(
            ceremony_id="cer-1",
            definition_name="planning_ceremony",
            story_id="story-1",
            correlation_id=None,
            inputs={},
            step_ids=("submit_architect",),
            requested_by=" ",
        )


def test_start_planning_ceremony_request_dto_accepts_none_correlation_id() -> None:
    dto = StartPlanningCeremonyRequestDTO(
        ceremony_id="cer-1",
        definition_name="planning_ceremony",
        story_id="story-1",
        correlation_id=None,
        inputs={},
        step_ids=("submit_architect",),
        requested_by="product_owner",
    )
    assert dto.correlation_id is None
