from __future__ import annotations

from dataclasses import FrozenInstanceError
from importlib import import_module

import pytest

RehydrationBundle = import_module("core.context.domain.rehydration_bundle").RehydrationBundle


def test_rehydration_bundle_basic_and_frozen():
    bundle = RehydrationBundle(
        case_id="C1",
        generated_at_ms=123,
        packs={"dev": {"role": "dev"}},
        stats={"decisions": 0, "events": 0},
    )

    assert bundle.case_id == "C1"
    assert bundle.generated_at_ms == 123
    assert "dev" in bundle.packs
    assert bundle.stats["decisions"] == 0

    with pytest.raises(FrozenInstanceError):
        bundle.case_id = "changed"  # type: ignore[attr-defined]
