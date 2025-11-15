"""Tests for PlanSnapshotMapper."""

from __future__ import annotations

from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.infrastructure.mappers.plan_snapshot_mapper import (
    PlanSnapshotMapper,
)


def test_mapper_builds_dto_from_payload() -> None:
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "title": "Implement auth",
        "description": "Detailed plan",
        "acceptance_criteria": ["AC1", "AC2"],
        "technical_notes": "Use FastAPI",
        "roles": ["DEVELOPER", "QA"],
    }

    dto = PlanSnapshotMapper.from_planning_payload(payload)

    assert dto.plan_id == "plan-1"
    assert dto.acceptance_criteria == ("AC1", "AC2")
    assert dto.roles == ("DEVELOPER", "QA")


def test_mapper_converts_dto_to_plan_context() -> None:
    dto = PlanSnapshotMapper.from_planning_payload(
        {
            "plan_id": "plan-1",
            "story_id": "story-1",
            "title": "Implement auth",
            "description": "Detailed plan",
            "acceptance_criteria": ["AC1"],
            "technical_notes": "Use FastAPI",
            "roles": ["DEVELOPER"],
        }
    )

    context = PlanSnapshotMapper.to_plan_context(dto)

    assert isinstance(context, PlanContext)
    assert context.plan_id.value == "plan-1"
    assert context.description.value == "Detailed plan"
    assert context.acceptance_criteria.values[0].value == "AC1"
    assert context.roles[0].value == "DEVELOPER"


def test_mapper_handles_missing_roles_by_defaulting() -> None:
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "title": "Implement auth",
        "description": "Detailed plan",
        "acceptance_criteria": "AC1",
        "technical_notes": "Use FastAPI",
        "roles": None,
    }

    dto = PlanSnapshotMapper.from_planning_payload(payload)

    assert dto.roles == ("developer",)


def test_mapper_handles_scalar_role_values() -> None:
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "title": "Implement auth",
        "description": "Detailed plan",
        "acceptance_criteria": "AC1",
        "technical_notes": "Use FastAPI",
        "roles": "DEVELOPER",
    }

    dto = PlanSnapshotMapper.from_planning_payload(payload)

    assert dto.roles == ("DEVELOPER",)

