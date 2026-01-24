#!/usr/bin/env python3
"""E2E Test: Ceremony Engine (E0) against YAML ceremonies."""

import asyncio
import os
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from core.ceremony_engine.application.ports.deliberation_port import DeliberationPort
from core.ceremony_engine.application.ports.task_extraction_port import TaskExtractionPort
from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step_handler_type import StepHandlerType
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.step_status_map import StepStatusMap
from core.ceremony_engine.infrastructure.adapters.step_handlers.step_handler_registry import (
    StepHandlerRegistry,
)
from core.ceremony_engine.infrastructure.mappers.ceremony_definition_mapper import (
    CeremonyDefinitionMapper,
)
from core.shared.idempotency.idempotency_port import IdempotencyPort


ceremonies_dir = os.getenv("CEREMONIES_DIR", "/app/config/ceremonies")
ceremony_names_raw = os.getenv(
    "CEREMONY_NAMES",
    "dummy_ceremony,e2e_aggregation,e2e_human_gate,e2e_multi_step",
)
ceremony_names = [name.strip() for name in ceremony_names_raw.split(",") if name.strip()]

if not ceremony_names:
    print("ERROR: No ceremony names provided")
    sys.exit(1)

class StubDeliberationPort(DeliberationPort):
    async def submit_backlog_review_deliberation(
        self,
        task_id: str,
        task_description: str,
        role: str,
        story_id: str,
        num_agents: int,
        constraints: dict[str, object] | None = None,
    ) -> str:
        return "delib-123"


class StubTaskExtractionPort(TaskExtractionPort):
    async def submit_task_extraction(
        self,
        task_id: str,
        task_description: str,
        story_id: str,
        ceremony_id: str,
    ) -> str:
        return "delib-456"


runner = CeremonyRunner(
    step_handler_port=StepHandlerRegistry(
        SubmitDeliberationUseCase(StubDeliberationPort()),
        SubmitTaskExtractionUseCase(StubTaskExtractionPort()),
        AsyncMock(),
        AsyncMock(spec=IdempotencyPort),
    ),
    messaging_port=AsyncMock(),
)

for ceremony_name in ceremony_names:
    print(f"Running ceremony: {ceremony_name}")

    definition = CeremonyDefinitionMapper.load_by_name(
        definition_name=ceremony_name,
        ceremonies_dir=ceremonies_dir,
    )
    initial_state = definition.get_initial_state().id
    terminal_states = [state.id for state in definition.states if state.terminal]
    if len(terminal_states) != 1:
        print(f"ERROR: Ceremony {ceremony_name} must have exactly one terminal state")
        sys.exit(1)
    terminal_state = terminal_states[0]

    now = datetime.now(UTC)
    instance = CeremonyInstance(
        instance_id=f"{ceremony_name}-instance-1",
        definition=definition,
        current_state=initial_state,
        step_status=StepStatusMap(entries=()),
        correlation_id=f"{ceremony_name}-corr-1",
        idempotency_keys=frozenset(),
        created_at=now,
        updated_at=now,
    )

    for step in definition.steps:
        human_approvals: dict[str, bool] = {}
        context = ExecutionContext(
            entries=(
                ContextEntry(
                    key=ContextKey.INPUTS,
                    value={
                        "input_data": "value",
                        "approval_context": "approve",
                        "story_id": "story-1",
                        "ceremony_id": ceremony_name,
                        "agent_deliberations": [
                            {
                                "agent_id": "agent-1",
                                "role": "DEV",
                                "proposal": {"content": "proposal"},
                            }
                        ],
                    },
                ),
                ContextEntry(
                    key=ContextKey.PUBLISH_DATA,
                    value={"result": "ok"},
                ),
                ContextEntry(
                    key=ContextKey.HUMAN_APPROVALS,
                    value=human_approvals,
                ),
            )
        )

        if step.handler == StepHandlerType.HUMAN_GATE_STEP:
            result = asyncio.run(runner.execute_step(instance, step.id, context=context))
            if result.get_step_status(step.id) != StepStatus.WAITING_FOR_HUMAN:
                print(f"ERROR: Expected WAITING_FOR_HUMAN for {ceremony_name}:{step.id}")
                sys.exit(1)
            instance = result

            human_approvals[f"{step.id.value}:PRODUCT_OWNER"] = True
            human_approvals["human_approved"] = True
            context = ExecutionContext(
                entries=(
                    ContextEntry(
                        key=ContextKey.INPUTS,
                        value={"input_data": "value", "approval_context": "approve"},
                    ),
                    ContextEntry(
                        key=ContextKey.PUBLISH_DATA,
                        value={"result": "ok"},
                    ),
                    ContextEntry(
                        key=ContextKey.HUMAN_APPROVALS,
                        value=human_approvals,
                    ),
                )
            )
            instance = asyncio.run(runner.execute_step(instance, step.id, context=context))
            if instance.get_step_status(step.id) != StepStatus.COMPLETED:
                print(f"ERROR: Expected COMPLETED after approval for {ceremony_name}:{step.id}")
                sys.exit(1)
        else:
            instance = asyncio.run(runner.execute_step(instance, step.id, context=context))
            if instance.get_step_status(step.id) != StepStatus.COMPLETED:
                print(f"ERROR: Step {ceremony_name}:{step.id} did not complete")
                sys.exit(1)

    if instance.current_state != terminal_state:
        print(
            "ERROR: Ceremony did not reach terminal state. "
            f"expected={terminal_state}, got={instance.current_state}"
        )
        sys.exit(1)

    print(f"OK: Ceremony {ceremony_name} reached terminal state {terminal_state}")

print("ALL CEREMONIES COMPLETED")
