"""Use case for starting a planning ceremony execution."""

from dataclasses import dataclass
from datetime import UTC, datetime

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects import (
    ContextEntry,
    ContextKey,
    ExecutionContext,
    StepId,
    StepOutputMap,
    StepStatus,
    StepStatusEntry,
    StepStatusMap,
)
from services.planning_ceremony_processor.application.dto.start_planning_ceremony_request_dto import (
    StartPlanningCeremonyRequestDTO,
)
from services.planning_ceremony_processor.application.ports.ceremony_definition_port import (
    CeremonyDefinitionPort,
)


@dataclass
class StartPlanningCeremonyUseCase:
    """Start a planning ceremony (fire-and-forget)."""

    definition_port: CeremonyDefinitionPort
    step_handler_port: StepHandlerPort
    persistence_port: PersistencePort
    messaging_port: MessagingPort

    def __post_init__(self) -> None:
        if not self.definition_port:
            raise ValueError("definition_port is required (fail-fast)")
        if not self.step_handler_port:
            raise ValueError("step_handler_port is required (fail-fast)")
        if not self.persistence_port:
            raise ValueError("persistence_port is required (fail-fast)")
        if not self.messaging_port:
            raise ValueError("messaging_port is required (fail-fast)")

    async def execute(self, request: StartPlanningCeremonyRequestDTO) -> CeremonyInstance:
        """Start a ceremony execution and submit initial steps."""
        definition = await self.definition_port.load_definition(request.definition_name)
        merged_inputs = {
            **request.inputs,
            "story_id": request.story_id,
            "ceremony_id": request.ceremony_id,
        }
        self._validate_inputs(definition, merged_inputs)
        self._validate_step_ids(definition, request.step_ids)
        initial_state = self._get_initial_state_id(definition)
        instance_id = f"{request.ceremony_id}:{request.story_id}"
        correlation_id = request.correlation_id or instance_id
        now = datetime.now(UTC)

        step_status = StepStatusMap(
            entries=tuple(
                StepStatusEntry(step_id=step.id, status=StepStatus.PENDING)
                for step in definition.steps
            )
        )

        instance = CeremonyInstance(
            instance_id=instance_id,
            definition=definition,
            current_state=initial_state,
            step_status=step_status,
            step_outputs=StepOutputMap(entries=()),
            correlation_id=correlation_id,
            idempotency_keys=frozenset(),
            created_at=now,
            updated_at=now,
        )

        await self.persistence_port.save_instance(instance)

        inputs = merged_inputs
        context = ExecutionContext(
            entries=(ContextEntry(key=ContextKey.INPUTS, value=inputs),)
        )

        runner = CeremonyRunner(
            step_handler_port=self.step_handler_port,
            messaging_port=self.messaging_port,
            persistence_port=self.persistence_port,
        )

        for step_id in request.step_ids:
            instance = await runner.execute_step(instance, StepId(step_id), context)

        return instance

    @staticmethod
    def _get_initial_state_id(definition: CeremonyDefinition) -> str:
        """Extract initial state ID from definition."""
        for state in definition.states:
            if state.initial:
                return state.id
        raise ValueError("No initial state found in ceremony definition")

    @staticmethod
    def _validate_inputs(
        definition: CeremonyDefinition, inputs: dict[str, str]
    ) -> None:
        """Ensure required inputs are present."""
        missing = [name for name in definition.inputs.required if name not in inputs]
        if missing:
            raise ValueError(f"Missing required inputs: {missing}")

    @staticmethod
    def _validate_step_ids(
        definition: CeremonyDefinition, step_ids: tuple[str, ...]
    ) -> None:
        """Ensure requested step IDs exist in definition."""
        known = {step.id.value for step in definition.steps}
        invalid = [step_id for step_id in step_ids if step_id not in known]
        if invalid:
            raise ValueError(f"Unknown step_ids: {invalid}")
