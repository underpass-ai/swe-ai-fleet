"""Unit tests for ValkeyPersistenceAdapter."""

import asyncio
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Callable, cast
from unittest.mock import MagicMock

import pytest

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    Inputs,
    State,
    Step,
    StepHandlerType,
    StepId,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
    Timeouts,
    Transition,
    TransitionTrigger,
)
from core.ceremony_engine.infrastructure.adapters.valkey_persistence_adapter import (
    ValkeyPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_instance_mapper import (
    CeremonyInstanceMapper,
)


def _ceremonies_dir() -> Path:
    return Path(__file__).resolve().parents[6] / "config" / "ceremonies"


def _definition() -> CeremonyDefinition:
    states = (
        State(id="STARTED", description="Started", initial=True, terminal=False),
        State(id="COMPLETED", description="Completed", initial=False, terminal=True),
    )
    transitions = (
        Transition(
            from_state="STARTED",
            to_state="COMPLETED",
            trigger=TransitionTrigger("complete"),
            guards=(),
            description="Complete",
        ),
    )
    steps = (
        Step(
            id=StepId("process_step"),
            state="STARTED",
            handler=StepHandlerType.AGGREGATION_STEP,
            config={"operation": "test"},
        ),
    )
    return CeremonyDefinition(
        version="1.0",
        name="test_ceremony",
        description="Test ceremony",
        inputs=Inputs(required=(), optional=()),
        outputs={},
        states=states,
        transitions=transitions,
        steps=steps,
        guards={},
        roles=(),
        timeouts=Timeouts(step_default=300, step_max=600, ceremony_max=3600),
        retry_policies={},
    )


def _instance(definition: CeremonyDefinition) -> CeremonyInstance:
    now = datetime.now(UTC)
    return CeremonyInstance(
        instance_id="instance-1",
        definition=definition,
        current_state="STARTED",
        step_status=StepStatusMap(
            entries=(StepStatusEntry(step_id=StepId("process_step"), status=StepStatus.COMPLETED),)
        ),
        correlation_id="corr-1",
        idempotency_keys=frozenset({"key-1"}),
        created_at=now,
        updated_at=now,
    )


@pytest.fixture
def adapter() -> ValkeyPersistenceAdapter:
    adapter = ValkeyPersistenceAdapter.__new__(ValkeyPersistenceAdapter)
    adapter.client = MagicMock()
    adapter.ceremonies_dir = str(_ceremonies_dir())
    return adapter


@pytest.fixture(autouse=True)
def _patch_to_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _to_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        await asyncio.sleep(0)
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _to_thread)


@pytest.mark.asyncio
async def test_save_instance_writes_keys(adapter: ValkeyPersistenceAdapter) -> None:
    definition = _definition()
    instance = _instance(definition)

    await adapter.save_instance(instance)

    instance_key = adapter._instance_key(instance.instance_id)
    client = cast(MagicMock, adapter.client)
    client.set.assert_called_once()
    client.sadd.assert_any_call(adapter._all_instances_set_key(), instance.instance_id)
    client.sadd.assert_any_call(
        adapter._correlation_set_key(instance.correlation_id),
        instance.instance_id,
    )
    assert client.set.call_args[0][0] == instance_key


@pytest.mark.asyncio
async def test_load_instance_not_found(adapter: ValkeyPersistenceAdapter) -> None:
    client = cast(MagicMock, adapter.client)
    client.get.return_value = None

    result = await adapter.load_instance("missing")

    assert result is None


@pytest.mark.asyncio
async def test_load_instance_returns_instance(
    adapter: ValkeyPersistenceAdapter,
) -> None:
    definition = CeremonyDefinitionMapper.load_by_name(
        "dummy_ceremony", ceremonies_dir=adapter.ceremonies_dir
    )
    instance = _instance(definition)
    json_str = CeremonyInstanceMapper.to_valkey_json(instance)
    client = cast(MagicMock, adapter.client)
    client.get.return_value = json_str

    result = await adapter.load_instance("instance-1")

    assert result is not None
    assert result.instance_id == instance.instance_id
    client.get.assert_called_once()


@pytest.mark.asyncio
async def test_find_instances_by_correlation_id_empty(
    adapter: ValkeyPersistenceAdapter,
) -> None:
    client = cast(MagicMock, adapter.client)
    client.smembers.return_value = set()

    result = await adapter.find_instances_by_correlation_id("corr-1")

    assert result == []


@pytest.mark.asyncio
class _TestValkeyAdapter(ValkeyPersistenceAdapter):
    _test_instance: CeremonyInstance

    async def load_instance(self, instance_id: str) -> CeremonyInstance | None:
        await asyncio.sleep(0)
        if instance_id == "instance-1":
            return self._test_instance
        return None


@pytest.mark.asyncio
async def test_find_instances_by_correlation_id_loads_instances() -> None:
    definition = _definition()
    instance = _instance(definition)

    adapter = _TestValkeyAdapter.__new__(_TestValkeyAdapter)
    adapter.client = MagicMock()
    adapter.ceremonies_dir = str(_ceremonies_dir())
    adapter._test_instance = instance
    client = cast(MagicMock, adapter.client)
    client.smembers.return_value = {"instance-1", "instance-2"}

    result = await adapter.find_instances_by_correlation_id("corr-1")

    assert len(result) == 1
    assert result[0].instance_id == "instance-1"
