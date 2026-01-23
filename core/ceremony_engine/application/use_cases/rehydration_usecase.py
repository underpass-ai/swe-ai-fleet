"""Use case for rehydrating ceremony instances."""

from dataclasses import dataclass

from core.ceremony_engine.application.ports.definition_port import DefinitionPort
from core.ceremony_engine.application.ports.rehydration_port import RehydrationPort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance


@dataclass
class RehydrationUseCase:
    """Rehydrate ceremony instances and validate against current definitions."""

    rehydration_port: RehydrationPort
    definition_port: DefinitionPort

    def __post_init__(self) -> None:
        if not self.rehydration_port:
            raise ValueError("rehydration_port is required (fail-fast)")
        if not self.definition_port:
            raise ValueError("definition_port is required (fail-fast)")

    async def rehydrate_instance(self, instance_id: str) -> CeremonyInstance | None:
        if not instance_id or not instance_id.strip():
            raise ValueError("instance_id cannot be empty")
        instance = await self.rehydration_port.rehydrate_instance(instance_id)
        if instance is None:
            return None
        await self._validate_definition(instance)
        return instance

    async def rehydrate_instances_by_correlation_id(
        self, correlation_id: str
    ) -> list[CeremonyInstance]:
        if not correlation_id or not correlation_id.strip():
            raise ValueError("correlation_id cannot be empty")
        instances = await self.rehydration_port.rehydrate_instances_by_correlation_id(
            correlation_id
        )
        for instance in instances:
            await self._validate_definition(instance)
        return instances

    async def _validate_definition(self, instance: CeremonyInstance) -> None:
        """Validate instance against the current definition."""
        definition = await self.definition_port.load_definition(instance.definition.name)
        instance_step_ids = {step.id for step in instance.definition.steps}
        current_step_ids = {step.id for step in definition.steps}
        if instance_step_ids != current_step_ids:
            raise ValueError(
                "Rehydrated instance does not match current definition step IDs"
            )
        instance_state_ids = {state.id for state in instance.definition.states}
        current_state_ids = {state.id for state in definition.states}
        if instance_state_ids != current_state_ids:
            raise ValueError(
                "Rehydrated instance does not match current definition states"
            )
