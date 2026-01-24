"""Unit tests for Neo4jPersistenceAdapter."""

from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
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
from core.ceremony_engine.infrastructure.adapters.neo4j_persistence_adapter import (
    Neo4jPersistenceAdapter,
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


@contextmanager
def _session_context(session: MagicMock):
    yield session


class _TestNeo4jAdapter(Neo4jPersistenceAdapter):
    def __init__(self, session: MagicMock) -> None:
        self._session_instance = session
        self.ceremonies_dir = str(_ceremonies_dir())

    def _retry_operation(self, fn, *args, **kwargs):
        return fn(*args, **kwargs)

    def _session(self):
        return _session_context(self._session_instance)


@pytest.mark.asyncio
async def test_save_instance_sync_writes_queries() -> None:
    definition = _definition()
    instance = _instance(definition)

    tx = MagicMock()
    session = MagicMock()
    session.execute_write.side_effect = lambda fn: fn(tx)
    adapter = _TestNeo4jAdapter(session)

    adapter._save_instance_sync(instance)

    assert tx.run.call_count == 2
    session.execute_write.assert_called_once()


@pytest.mark.asyncio
async def test_load_instance_sync_returns_instance() -> None:
    definition = CeremonyDefinitionMapper.load_by_name(
        "dummy_ceremony", ceremonies_dir=str(_ceremonies_dir())
    )
    instance = _instance(definition)
    data = CeremonyInstanceMapper.to_neo4j_dict(instance)

    tx = MagicMock()
    record = {"ci": data}
    tx.run.return_value.single.return_value = record

    session = MagicMock()
    session.execute_read.side_effect = lambda fn: fn(tx)
    adapter = _TestNeo4jAdapter(session)

    restored = adapter._load_instance_sync("instance-1")

    assert restored is not None
    assert restored.instance_id == instance.instance_id


@pytest.mark.asyncio
async def test_find_instances_by_correlation_id_sync_returns_list() -> None:
    definition = CeremonyDefinitionMapper.load_by_name(
        "dummy_ceremony", ceremonies_dir=str(_ceremonies_dir())
    )
    instance = _instance(definition)
    data = CeremonyInstanceMapper.to_neo4j_dict(instance)

    tx = MagicMock()
    tx.run.return_value.__iter__.return_value = [{"ci": data}]

    session = MagicMock()
    session.execute_read.side_effect = lambda fn: fn(tx)
    adapter = _TestNeo4jAdapter(session)

    results = adapter._find_instances_by_correlation_id_sync("corr-1")

    assert len(results) == 1
    assert results[0].instance_id == instance.instance_id
