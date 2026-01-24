"""E2E tests for Ceremony Engine using YAML-defined ceremonies."""

import os
from dataclasses import replace
from datetime import datetime, UTC
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_status_map import StepStatusMap
from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger
from core.ceremony_engine.infrastructure.adapters.step_handlers.step_handler_registry import (
    StepHandlerRegistry,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)


def _resolve_ceremonies_dir() -> Path:
    env_dir = os.getenv("CEREMONIES_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(__file__).resolve().parents[3] / "config" / "ceremonies"


def _build_instance(definition_name: str) -> CeremonyInstance:
    ceremonies_dir = _resolve_ceremonies_dir()
    definition = CeremonyDefinitionMapper.load_by_name(
        definition_name,
        ceremonies_dir=ceremonies_dir,
    )
    initial_state = definition.get_initial_state().id
    now = datetime.now(UTC)
    return CeremonyInstance(
        instance_id=f"{definition.name}-instance-1",
        definition=definition,
        current_state=initial_state,
        step_status=StepStatusMap(entries=()),
        correlation_id=f"{definition.name}-corr-1",
        idempotency_keys=frozenset(),
        created_at=now,
        updated_at=now,
    )


def _build_messaging_port() -> AsyncMock:
    return AsyncMock(spec=MessagingPort)


def _build_deliberation_use_case() -> SubmitDeliberationUseCase:
    deliberation_port = AsyncMock(spec=DeliberationPort)
    deliberation_port.submit_backlog_review_deliberation.return_value = "delib-123"
    return SubmitDeliberationUseCase(deliberation_port)


def _build_task_extraction_use_case() -> SubmitTaskExtractionUseCase:
    task_extraction_port = AsyncMock(spec=TaskExtractionPort)
    task_extraction_port.submit_task_extraction.return_value = "delib-456"
    return SubmitTaskExtractionUseCase(task_extraction_port)


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_aggregation_ceremony_completes() -> None:
    instance = _build_instance("e2e_aggregation")

    persistence_port = AsyncMock(spec=PersistencePort)
    runner = CeremonyRunner(
        step_handler_port=StepHandlerRegistry(
            _build_deliberation_use_case(),
            _build_task_extraction_use_case(),
            _build_messaging_port(),
            AsyncMock(spec=IdempotencyPort),
        ),
        messaging_port=_build_messaging_port(),
        persistence_port=persistence_port,
    )

    result = await runner.execute_step(
        instance,
        StepId("process_step"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.INPUTS,
                    value={"input_data": "value"},
                ),
            )
        ),
    )

    assert result.get_step_status(StepId("process_step")) == StepStatus.COMPLETED
    assert result.current_state == "COMPLETED"
    persistence_port.save_instance.assert_awaited()


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_human_gate_waits_then_transitions() -> None:
    instance = _build_instance("e2e_human_gate")

    runner = CeremonyRunner(
        step_handler_port=StepHandlerRegistry(
            _build_deliberation_use_case(),
            _build_task_extraction_use_case(),
            _build_messaging_port(),
            AsyncMock(spec=IdempotencyPort),
        ),
        messaging_port=_build_messaging_port(),
    )

    waiting_result = await runner.execute_step(
        instance,
        StepId("approval_step"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.HUMAN_APPROVALS,
                    value={},
                ),
            )
        ),
    )

    assert waiting_result.get_step_status(StepId("approval_step")) == StepStatus.WAITING_FOR_HUMAN
    assert waiting_result.current_state == "STARTED"

    approved_result = await runner.transition_state(
        waiting_result,
        TransitionTrigger("approve"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.HUMAN_APPROVALS,
                    value={"human_approved": True},
                ),
            )
        ),
    )

    assert approved_result.current_state == "APPROVED"


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_multi_step_ceremony_runs_all_handlers() -> None:
    instance = _build_instance("e2e_multi_step")
    runner = CeremonyRunner(
        step_handler_port=StepHandlerRegistry(
            _build_deliberation_use_case(),
            _build_task_extraction_use_case(),
            _build_messaging_port(),
            AsyncMock(spec=IdempotencyPort),
        ),
        messaging_port=_build_messaging_port(),
    )

    after_deliberation = await runner.execute_step(
        instance,
        StepId("deliberate"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.INPUTS,
                    value={
                        "input_data": "value",
                        "story_id": "story-1",
                        "ceremony_id": "e2e_multi_step",
                    },
                ),
            )
        ),
    )
    assert after_deliberation.get_step_status(StepId("deliberate")) == StepStatus.COMPLETED
    assert after_deliberation.current_state == "EXTRACTING"

    after_extraction = await runner.execute_step(
        after_deliberation,
        StepId("extract_tasks"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.INPUTS,
                    value={
                        "input_data": "value",
                        "story_id": "story-1",
                        "ceremony_id": "e2e_multi_step",
                        "agent_deliberations": [
                            {"agent_id": "a1", "role": "DEV", "proposal": {"content": "x"}},
                        ],
                    },
                ),
            )
        ),
    )
    assert after_extraction.get_step_status(StepId("extract_tasks")) == StepStatus.COMPLETED
    assert after_extraction.current_state == "PUBLISHING"

    final_result = await runner.execute_step(
        after_extraction,
        StepId("publish_results"),
        context=ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.INPUTS,
                    value={
                        "ceremony_id": "e2e_multi_step",
                        "story_id": "story-1",
                    },
                ),
                ContextEntry(
                    key=ContextKey.PUBLISH_DATA,
                    value={"result": "ok"},
                ),
            )
        ),
    )
    assert final_result.get_step_status(StepId("publish_results")) == StepStatus.COMPLETED
    assert final_result.current_state == "COMPLETED"
