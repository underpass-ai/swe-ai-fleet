"""Unit tests for StepOutputEntry and StepOutputMap."""

import pytest

from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_output_entry import StepOutputEntry
from core.ceremony_engine.domain.value_objects.step_output_map import StepOutputMap


def test_step_output_entry_happy_path() -> None:
    entry = StepOutputEntry(step_id=StepId("process_step"), output={"value": 1})
    assert entry.output["value"] == 1


def test_step_output_entry_rejects_non_dict_output() -> None:
    with pytest.raises(ValueError, match="output must be a dict"):
        StepOutputEntry(step_id=StepId("process_step"), output="bad")  # type: ignore[arg-type]


def test_step_output_map_get_and_with_output() -> None:
    step_id = StepId("process_step")
    output_map = StepOutputMap(entries=())
    updated = output_map.with_output(step_id, {"value": "ok"})
    assert updated.get(step_id) == {"value": "ok"}


def test_step_output_map_rejects_duplicate_step_ids() -> None:
    step_id = StepId("process_step")
    with pytest.raises(ValueError, match="Duplicate step_id"):
        StepOutputMap(
            entries=(
                StepOutputEntry(step_id=step_id, output={}),
                StepOutputEntry(step_id=step_id, output={}),
            )
        )
