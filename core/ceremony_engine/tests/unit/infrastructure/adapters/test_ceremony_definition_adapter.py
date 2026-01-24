"""Unit tests for CeremonyDefinitionAdapter."""

from pathlib import Path

import pytest

from core.ceremony_engine.infrastructure.adapters.ceremony_definition_adapter import (
    CeremonyDefinitionAdapter,
)


def _ceremonies_dir() -> Path:
    """Resolve ceremonies directory relative to project root."""
    return Path(__file__).resolve().parents[6] / "config" / "ceremonies"


@pytest.mark.asyncio
async def test_ceremony_definition_adapter_loads_definition() -> None:
    adapter = CeremonyDefinitionAdapter(
        ceremonies_dir=str(_ceremonies_dir())
    )

    definition = await adapter.load_definition("dummy_ceremony")

    assert definition.name == "dummy_ceremony"


def test_ceremony_definition_adapter_rejects_empty_dir() -> None:
    with pytest.raises(ValueError, match="ceremonies_dir cannot be empty"):
        CeremonyDefinitionAdapter(ceremonies_dir=" ")


@pytest.mark.asyncio
async def test_ceremony_definition_adapter_rejects_empty_name() -> None:
    adapter = CeremonyDefinitionAdapter(
        ceremonies_dir=str(_ceremonies_dir())
    )

    with pytest.raises(ValueError, match="definition name cannot be empty"):
        await adapter.load_definition(" ")
