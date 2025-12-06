"""Tests for infrastructure PlanSnapshotDTO."""

from __future__ import annotations

import pytest
from task_derivation.infrastructure.dto.plan_snapshot_dto import PlanSnapshotDTO


def _valid_dto() -> PlanSnapshotDTO:
    return PlanSnapshotDTO(
        plan_id="plan-1",
        story_id="story-1",
        title="Implement auth",
        description="Detailed plan",
        acceptance_criteria=("AC1",),
        technical_notes="Not specified",
        roles=("DEVELOPER",),
    )


def test_plan_snapshot_dto_accepts_valid_payload() -> None:
    dto = _valid_dto()
    assert dto.title == "Implement auth"


@pytest.mark.parametrize(
    "field",
    ["plan_id", "story_id", "title", "description", "technical_notes"],
)
def test_plan_snapshot_dto_rejects_blank_text(field: str) -> None:
    kwargs = _valid_dto().__dict__ | {field: " "}
    with pytest.raises(ValueError):
        PlanSnapshotDTO(**kwargs)  # type: ignore[arg-type]


def test_plan_snapshot_dto_requires_acceptance_criteria() -> None:
    kwargs = _valid_dto().__dict__ | {"acceptance_criteria": ()}
    with pytest.raises(ValueError, match="acceptance_criteria cannot be empty"):
        PlanSnapshotDTO(**kwargs)  # type: ignore[arg-type]


def test_plan_snapshot_dto_rejects_blank_acceptance_entry() -> None:
    kwargs = _valid_dto().__dict__ | {"acceptance_criteria": (" ",)}
    with pytest.raises(ValueError, match="entries cannot be empty"):
        PlanSnapshotDTO(**kwargs)  # type: ignore[arg-type]


def test_plan_snapshot_dto_rejects_blank_role() -> None:
    kwargs = _valid_dto().__dict__ | {"roles": (" ",)}
    with pytest.raises(ValueError, match="roles entries cannot be empty"):
        PlanSnapshotDTO(**kwargs)  # type: ignore[arg-type]

