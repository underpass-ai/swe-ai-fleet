"""Tests for CeremonyDefinitionAdapter."""

import pytest

from services.planning_ceremony_processor.infrastructure.adapters.ceremony_definition_adapter import (
    CeremonyDefinitionAdapter,
)


@pytest.mark.asyncio
async def test_ceremony_definition_adapter_loads_definition(ceremonies_dir: str) -> None:
    adapter = CeremonyDefinitionAdapter(ceremonies_dir=ceremonies_dir)
    definition = await adapter.load_definition("dummy_ceremony")
    assert definition.name == "dummy_ceremony"


def test_ceremony_definition_adapter_rejects_empty_dir() -> None:
    with pytest.raises(ValueError, match="ceremonies_dir cannot be empty"):
        CeremonyDefinitionAdapter("")


def test_ceremony_definition_adapter_rejects_whitespace_dir() -> None:
    with pytest.raises(ValueError, match="ceremonies_dir cannot be empty"):
        CeremonyDefinitionAdapter(" ")


@pytest.mark.asyncio
async def test_ceremony_definition_adapter_rejects_empty_name(ceremonies_dir: str) -> None:
    adapter = CeremonyDefinitionAdapter(ceremonies_dir=ceremonies_dir)
    with pytest.raises(ValueError, match="definition name cannot be empty"):
        await adapter.load_definition("")


@pytest.mark.asyncio
async def test_ceremony_definition_adapter_rejects_whitespace_name(ceremonies_dir: str) -> None:
    adapter = CeremonyDefinitionAdapter(ceremonies_dir=ceremonies_dir)
    with pytest.raises(ValueError, match="definition name cannot be empty"):
        await adapter.load_definition(" ")
