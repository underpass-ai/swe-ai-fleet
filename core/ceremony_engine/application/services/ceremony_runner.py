"""CeremonyRunner: Application service for executing ceremonies."""

import asyncio
import logging
from typing import Any

from core.ceremony_engine.application.ports.ceremony_metrics_port import (
    CeremonyMetricsPort,
)
from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.ports.step_handler_port import StepHandlerPort
from core.ceremony_engine.domain.entities.ceremony_instance import CeremonyInstance
from core.ceremony_engine.domain.value_objects.context_entry import ContextEntry
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.retry_policy import RetryPolicy
from core.ceremony_engine.domain.value_objects.role import Role
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_id import StepId
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.domain.value_objects.step_status import StepStatus
from core.ceremony_engine.domain.value_objects.transition import Transition
from core.ceremony_engine.domain.value_objects.transition_trigger import TransitionTrigger
from core.shared.events.helpers import create_event_envelope
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState

logger = logging.getLogger(__name__)

SUBJECT_STEP_EXECUTED = "ceremony.step.executed"
SUBJECT_TRANSITION_APPLIED = "ceremony.transition.applied"


class CeremonyRunner:
    """
    Application Service: Ceremony execution runner.

    Orchestrates the execution of ceremonies by:
    - Evaluating transitions and guards
    - Executing steps via step handlers
    - Managing state transitions
    - Handling retries and timeouts

    Following Hexagonal Architecture:
    - Depends on Ports (interfaces), not concrete adapters
    - Orchestrates domain logic (CeremonyInstance, CeremonyDefinition)
    - Delegates to ports for side effects (messaging, persistence)

    Business Rules:
    - Steps can only execute when instance is in the correct state
    - Guards must pass before transitions
    - Retries are handled per step's retry policy
    - State transitions follow definition's transitions
    """

    def __init__(
        self,
        step_handler_port: StepHandlerPort,
        messaging_port: MessagingPort,
        persistence_port: PersistencePort | None = None,
        idempotency_port: IdempotencyPort | None = None,
        metrics_port: CeremonyMetricsPort | None = None,
        in_progress_ttl_seconds: int = 300,
        stale_max_age_seconds: int = 600,
        completed_ttl_seconds: int | None = None,
    ) -> None:
        """Initialize CeremonyRunner.

        Args:
            step_handler_port: Port for executing steps (required)
            messaging_port: Port for publishing events (required)
            persistence_port: Port for persisting instances (optional)
            idempotency_port: Port for idempotency (optional)
            metrics_port: Port for step/publish metrics (optional)
        """
        if not step_handler_port:
            raise ValueError("step_handler_port is required (fail-fast)")
        if not messaging_port:
            raise ValueError("messaging_port is required (fail-fast)")

        if in_progress_ttl_seconds <= 0:
            raise ValueError("in_progress_ttl_seconds must be positive (fail-fast)")
        if stale_max_age_seconds <= 0:
            raise ValueError("stale_max_age_seconds must be positive (fail-fast)")

        self._step_handler_port = step_handler_port
        self._messaging_port = messaging_port
        self._persistence_port = persistence_port
        self._idempotency_port = idempotency_port
        self._metrics_port = metrics_port
        self._in_progress_ttl_seconds = in_progress_ttl_seconds
        self._stale_max_age_seconds = stale_max_age_seconds
        self._completed_ttl_seconds = completed_ttl_seconds

    async def execute_step(
        self,
        instance: CeremonyInstance,
        step_id: StepId,
        context: ExecutionContext | None = None,
    ) -> CeremonyInstance:
        """Execute a step in a ceremony instance.

        Handles retries and timeouts according to step configuration and ceremony definition.

        Args:
            instance: Ceremony instance to execute step in
            step_id: ID of step to execute
            context: Execution context (inputs, etc.)

        Returns:
            Updated CeremonyInstance with step result and potentially new state

        Raises:
            ValueError: If step cannot be executed (invalid state, step not found, etc.)
            TimeoutError: If step execution exceeds timeout
        """
        if context is None:
            context = ExecutionContext.builder().build()
        context = self._with_step_outputs(context, instance)
        context = self._with_definition(context, instance)

        # Find step in definition
        step = self._find_step(instance, step_id)
        self._enforce_step_role_allowed_actions(instance, step)

        # Validate step can be executed
        self._validate_step_executable(instance, step)

        # Validate and get timeout for step
        timeout_seconds = self._get_step_timeout(instance, step)

        # Get retry policy for step
        retry_policy = self._get_retry_policy(instance, step)

        # Idempotency gate (optional)
        idempotency_key = self._resolve_step_idempotency_key(instance, step_id, context)
        should_skip = await self._idempotency_should_skip(idempotency_key)
        if should_skip:
            return instance

        self._log_step_start(instance, step_id, step)
        step_result = await self._execute_step_with_retry_and_timeout(
            step, context, timeout_seconds, retry_policy
        )
        updated_instance = self._update_instance_with_result(instance, step_id, step_result)
        self._record_step_metrics(step_result)
        self._log_step_end(updated_instance, step_id, step_result)
        await self._publish_step_executed_with_metrics_and_log(
            updated_instance, step_id, step_result
        )
        if step_result.is_success():
            updated_instance = await self._handle_successful_step_transition(
                updated_instance, context, idempotency_key
            )
        if self._persistence_port:
            await self._persistence_port.save_instance(updated_instance)
        return updated_instance

    async def transition_state(
        self,
        instance: CeremonyInstance,
        trigger: TransitionTrigger,
        context: ExecutionContext | None = None,
    ) -> CeremonyInstance:
        """Trigger a state transition by trigger.

        Args:
            instance: Ceremony instance
            trigger: Transition trigger
            context: Execution context (for guard evaluation)

        Returns:
            Updated CeremonyInstance with new state if transition is valid

        Raises:
            ValueError: If transition cannot be executed (no matching transition, guards fail, etc.)
        """
        if context is None:
            context = ExecutionContext.builder().build()
        context = self._with_step_outputs(context, instance)
        context = self._with_definition(context, instance)

        # Idempotency gate (optional)
        idempotency_key = self._resolve_transition_idempotency_key(instance, trigger, context)
        should_skip = await self._idempotency_should_skip(idempotency_key)
        if should_skip:
            return instance

        # Find transition by trigger
        transition = self._find_transition_by_trigger(instance, trigger)
        self._enforce_transition_role_allowed_actions(instance, trigger, context)

        # Validate transition can be executed
        self._validate_transition_executable(instance, transition)

        # Evaluate guards
        guards_passed = self._evaluate_guards(instance, transition, context)
        if not guards_passed:
            raise ValueError(
                f"Transition '{trigger.value}' guards not satisfied (cannot transition from "
                f"'{transition.from_state}' to '{transition.to_state}')"
            )

        # Execute transition
        updated_instance = self._apply_transition(instance, transition)

        # Mark idempotency completed and persist if port is available
        await self._mark_idempotency_completed(idempotency_key)
        await self._publish_transition_applied_with_metrics_and_log(
            instance=updated_instance,
            transition=transition,
            trigger=trigger,
        )
        if self._persistence_port:
            await self._persistence_port.save_instance(updated_instance)

        return updated_instance

    def _find_step(self, instance: CeremonyInstance, step_id: StepId) -> Step:
        """Find step in ceremony definition.

        Args:
            instance: Ceremony instance
            step_id: Step ID to find

        Returns:
            Step if found

        Raises:
            ValueError: If step not found
        """
        for step in instance.definition.steps:
            if step.id == step_id:
                return step

        raise ValueError(f"Step '{step_id.value}' not found in ceremony definition")

    @staticmethod
    def _find_role(instance: CeremonyInstance, role_id: str) -> Role:
        for role in instance.definition.roles:
            if role.id == role_id:
                return role
        raise ValueError(f"Role '{role_id}' not found in ceremony definition")

    def _enforce_step_role_allowed_actions(
        self, instance: CeremonyInstance, step: Step
    ) -> None:
        role_id = step.config.get("role")
        if role_id is None:
            return
        if not isinstance(role_id, str) or not role_id.strip():
            raise ValueError("Step role must be a non-empty string")
        role = self._find_role(instance, role_id)
        if step.id.value not in role.allowed_actions:
            raise ValueError(
                f"Role '{role_id}' is not allowed to execute step '{step.id.value}'"
            )

    def _enforce_transition_role_allowed_actions(
        self,
        instance: CeremonyInstance,
        trigger: TransitionTrigger,
        context: ExecutionContext,
    ) -> None:
        inputs = context.get_mapping(ContextKey.INPUTS) or {}
        role_id = inputs.get("role")
        if role_id is None:
            return
        if not isinstance(role_id, str) or not role_id.strip():
            raise ValueError("Transition role must be a non-empty string")
        role = self._find_role(instance, role_id)
        if trigger.value not in role.allowed_actions:
            raise ValueError(
                f"Role '{role_id}' is not allowed to execute trigger '{trigger.value}'"
            )

    def _resolve_step_idempotency_key(
        self,
        instance: CeremonyInstance,
        step_id: StepId,
        context: ExecutionContext,
    ) -> str | None:
        """Resolve idempotency key for a step execution.

        Priority:
        - ContextKey.IDEMPOTENCY_KEY if provided
        - deterministic key based on instance_id + step_id
        """
        explicit_key = context.get(ContextKey.IDEMPOTENCY_KEY)
        if explicit_key is not None:
            return str(explicit_key)
        return f"ceremony:step:{instance.instance_id}:{step_id.value}"

    def _resolve_transition_idempotency_key(
        self,
        instance: CeremonyInstance,
        trigger: TransitionTrigger,
        context: ExecutionContext,
    ) -> str | None:
        """Resolve idempotency key for a transition trigger.

        Priority:
        - ContextKey.IDEMPOTENCY_KEY if provided
        - deterministic key based on instance_id + trigger
        """
        explicit_key = context.get(ContextKey.IDEMPOTENCY_KEY)
        if explicit_key is not None:
            return str(explicit_key)
        return f"ceremony:transition:{instance.instance_id}:{trigger.value}"

    async def _idempotency_should_skip(self, idempotency_key: str | None) -> bool:
        """Return True if operation should be skipped due to idempotency."""
        if not self._idempotency_port or not idempotency_key:
            return False

        status = await self._idempotency_port.check_status(idempotency_key)
        if status == IdempotencyState.COMPLETED:
            logger.info(
                "Skipping already completed operation: "
                f"idempotency_key={idempotency_key[:16]}..."
            )
            return True

        if status == IdempotencyState.IN_PROGRESS:
            is_stale = await self._idempotency_port.is_stale(
                idempotency_key, self._stale_max_age_seconds
            )
            if not is_stale:
                logger.info(
                    "Skipping in-progress operation (not stale): "
                    f"idempotency_key={idempotency_key[:16]}..."
                )
                return True

        marked = await self._idempotency_port.mark_in_progress(
            idempotency_key, self._in_progress_ttl_seconds
        )
        if not marked:
            final_status = await self._idempotency_port.check_status(idempotency_key)
            if final_status == IdempotencyState.COMPLETED:
                logger.info(
                    "Skipping completed operation after race: "
                    f"idempotency_key={idempotency_key[:16]}..."
                )
                return True

        return False

    async def _mark_idempotency_completed(self, idempotency_key: str | None) -> None:
        """Mark idempotency as COMPLETED after successful operation."""
        if not self._idempotency_port:
            return
        if not idempotency_key:
            raise ValueError("idempotency_key is required when idempotency_port is set")
        await self._idempotency_port.mark_completed(
            idempotency_key, ttl_seconds=self._completed_ttl_seconds
        )

    def _validate_step_executable(
        self,
        instance: CeremonyInstance,
        step: Step,
    ) -> None:
        """Validate that step can be executed.

        Args:
            instance: Ceremony instance
            step: Step to validate

        Raises:
            ValueError: If step cannot be executed
        """
        instance.ensure_step_in_state(step)

        # Check step status allows execution
        current_status = instance.get_step_status(step.id)
        if not current_status.is_executable():
            raise ValueError(
                f"Step '{step.id.value}' cannot be executed from status '{current_status.value}'"
            )

        # Check instance is not terminal
        if instance.is_terminal():
            raise ValueError(
                f"Cannot execute steps in terminal state '{instance.current_state}'"
            )

    def _update_instance_with_result(
        self,
        instance: CeremonyInstance,
        step_id: StepId,
        result: StepResult,
    ) -> CeremonyInstance:
        """Update instance with step execution result.

        Args:
            instance: Current instance
            step_id: Step ID that was executed
            result: Step execution result

        Returns:
            New CeremonyInstance with updated step status

        Note:
            This creates a new instance (immutability) and uses domain builders
            inside CeremonyInstance to avoid direct mutation.
        """
        return instance.apply_step_result(step_id, result)

    def _find_transition_by_trigger(
        self,
        instance: CeremonyInstance,
        trigger: TransitionTrigger,
    ) -> Transition:
        """Find transition by trigger from current state.

        Args:
            instance: Ceremony instance
            trigger: Transition trigger

        Returns:
            Transition if found

        Raises:
            ValueError: If transition not found
        """
        return instance.find_transition_by_trigger(trigger)

    def _validate_transition_executable(
        self,
        instance: CeremonyInstance,
        transition: Transition,
    ) -> None:
        """Validate that transition can be executed.

        Args:
            instance: Ceremony instance
            transition: Transition to validate

        Raises:
            ValueError: If transition cannot be executed
        """
        instance.ensure_transition_executable(transition)

    def _evaluate_guards(
        self,
        instance: CeremonyInstance,
        transition: Transition,
        context: ExecutionContext,
    ) -> bool:
        """Evaluate guards for a transition.

        Args:
            instance: Ceremony instance
            transition: Transition to evaluate guards for
            context: Execution context (for guard evaluation)

        Returns:
            True if all guards pass, False otherwise

        Note:
            - AUTOMATED guards are evaluated programmatically (simple expression evaluation)
            - HUMAN guards require explicit approval in context (ContextKey.HUMAN_APPROVALS)
        """
        return transition.evaluate_guards(
            instance=instance,
            context=context,
            guards=instance.definition.guards,
        )

    def _evaluate_transitions(
        self,
        instance: CeremonyInstance,
        context: ExecutionContext,
    ) -> tuple[CeremonyInstance, Transition | None]:
        """Evaluate available transitions from current state and apply if guards pass.

        Args:
            instance: Ceremony instance
            context: Execution context

        Returns:
            Updated instance (may have new state if transition occurred)

        Note:
            This method finds transitions from the current state and evaluates their guards.
            If a transition's guards pass, it is applied automatically.
            In practice, you might want to:
            - Only evaluate transitions triggered by step completion
            - Support explicit transition triggers
            - Handle multiple valid transitions (choose first, or require explicit trigger)
        """
        # Find transitions from current state
        available_transitions = instance.available_transitions()

        # Evaluate each transition's guards
        for transition in available_transitions:
            guards_passed = self._evaluate_guards(instance, transition, context)
            logger.info(
                "transition_evaluate instance_id=%s from_state=%s to_state=%s "
                "trigger=%s guards_passed=%s correlation_id=%s",
                instance.instance_id,
                transition.from_state,
                transition.to_state,
                transition.trigger.value,
                guards_passed,
                instance.correlation_id,
                extra={
                    "event": "transition_evaluate",
                    "instance_id": instance.instance_id,
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "trigger": transition.trigger.value,
                    "guards_passed": guards_passed,
                    "correlation_id": instance.correlation_id,
                },
            )
            if guards_passed:
                applied = self._apply_transition(instance, transition)
                logger.info(
                    "transition_applied instance_id=%s from_state=%s to_state=%s "
                    "trigger=%s correlation_id=%s",
                    instance.instance_id,
                    transition.from_state,
                    transition.to_state,
                    transition.trigger.value,
                    instance.correlation_id,
                    extra={
                        "event": "transition_applied",
                        "instance_id": instance.instance_id,
                        "from_state": transition.from_state,
                        "to_state": transition.to_state,
                        "trigger": transition.trigger.value,
                        "correlation_id": instance.correlation_id,
                    },
                )
                return applied, transition

        logger.info(
            "transition_none_applied instance_id=%s current_state=%s correlation_id=%s",
            instance.instance_id,
            instance.current_state,
            instance.correlation_id,
            extra={
                "event": "transition_none_applied",
                "instance_id": instance.instance_id,
                "current_state": instance.current_state,
                "correlation_id": instance.correlation_id,
            },
        )
        return instance, None

    @staticmethod
    def _with_step_outputs(
        context: ExecutionContext, instance: CeremonyInstance
    ) -> ExecutionContext:
        """Return context with step outputs merged in."""
        outputs = {
            entry.step_id.value: entry.output for entry in instance.step_outputs.entries
        }
        entries = tuple(
            entry for entry in context.entries if entry.key != ContextKey.STEP_OUTPUTS
        )
        return ExecutionContext(
            entries=(*entries, ContextEntry(key=ContextKey.STEP_OUTPUTS, value=outputs))
        )

    @staticmethod
    def _with_definition(
        context: ExecutionContext, instance: CeremonyInstance
    ) -> ExecutionContext:
        """Return context with ceremony definition included."""
        entries = tuple(
            entry for entry in context.entries if entry.key != ContextKey.DEFINITION
        )
        return ExecutionContext(
            entries=(*entries, ContextEntry(key=ContextKey.DEFINITION, value=instance.definition))
        )

    def _apply_transition(
        self,
        instance: CeremonyInstance,
        transition: Transition,
    ) -> CeremonyInstance:
        """Apply a state transition to an instance.

        Args:
            instance: Current instance
            transition: Transition to apply

        Returns:
            New CeremonyInstance with updated state

        Note:
            This creates a new instance (immutability).
        """
        return instance.apply_transition(transition)

    def _log_step_start(
        self,
        instance: CeremonyInstance,
        step_id: StepId,
        step: Step,
    ) -> None:
        """Log step start."""
        logger.info(
            "step_start instance_id=%s step_id=%s state=%s handler=%s correlation_id=%s",
            instance.instance_id,
            step_id.value,
            instance.current_state,
            step.handler.value,
            instance.correlation_id,
            extra={
                "event": "step_start",
                "instance_id": instance.instance_id,
                "step_id": step_id.value,
                "current_state": instance.current_state,
                "handler": step.handler.value,
                "correlation_id": instance.correlation_id,
            },
        )

    def _log_step_end(
        self,
        updated_instance: CeremonyInstance,
        step_id: StepId,
        step_result: StepResult,
    ) -> None:
        """Log step end."""
        logger.info(
            "step_end instance_id=%s step_id=%s status=%s success=%s correlation_id=%s",
            updated_instance.instance_id,
            step_id.value,
            step_result.status.value,
            step_result.is_success(),
            updated_instance.correlation_id,
            extra={
                "event": "step_end",
                "instance_id": updated_instance.instance_id,
                "step_id": step_id.value,
                "status": step_result.status.value,
                "success": step_result.is_success(),
                "correlation_id": updated_instance.correlation_id,
            },
        )

    def _record_step_metrics(self, step_result: StepResult) -> None:
        """Record step success/failure metrics if metrics port is set."""
        if self._metrics_port:
            if step_result.is_success():
                self._metrics_port.increment_step_success()
            else:
                self._metrics_port.increment_step_failure()

    async def _publish_step_executed_with_metrics_and_log(
        self,
        updated_instance: CeremonyInstance,
        step_id: StepId,
        step_result: StepResult,
    ) -> None:
        """Publish step executed event, record metrics and log. Re-raises on failure."""
        try:
            await self._publish_step_executed_event(
                instance=updated_instance,
                step_id=step_id,
                step_result=step_result,
            )
            if self._metrics_port:
                self._metrics_port.increment_publish_success()
            logger.info(
                "publish_outcome subject=%s outcome=success "
                "instance_id=%s step_id=%s correlation_id=%s",
                SUBJECT_STEP_EXECUTED,
                updated_instance.instance_id,
                step_id.value,
                updated_instance.correlation_id,
                extra={
                    "event": "publish_outcome",
                    "subject": SUBJECT_STEP_EXECUTED,
                    "outcome": "success",
                    "instance_id": updated_instance.instance_id,
                    "step_id": step_id.value,
                    "correlation_id": updated_instance.correlation_id,
                },
            )
        except Exception:
            if self._metrics_port:
                self._metrics_port.increment_publish_failure()
            raise

    async def _publish_transition_applied_with_metrics_and_log(
        self,
        instance: CeremonyInstance,
        transition: Transition,
        trigger: TransitionTrigger,
    ) -> None:
        """Publish transition applied event, record metrics and log. Re-raises on failure."""
        try:
            await self._publish_transition_applied_event(
                instance=instance,
                transition=transition,
                trigger=trigger,
            )
            if self._metrics_port:
                self._metrics_port.increment_publish_success()
            logger.info(
                "publish_outcome subject=%s outcome=success "
                "instance_id=%s from_state=%s to_state=%s trigger=%s correlation_id=%s",
                SUBJECT_TRANSITION_APPLIED,
                instance.instance_id,
                transition.from_state,
                transition.to_state,
                trigger.value,
                instance.correlation_id,
                extra={
                    "event": "publish_outcome",
                    "subject": SUBJECT_TRANSITION_APPLIED,
                    "outcome": "success",
                    "instance_id": instance.instance_id,
                    "from_state": transition.from_state,
                    "to_state": transition.to_state,
                    "trigger": trigger.value,
                    "correlation_id": instance.correlation_id,
                },
            )
        except Exception:
            if self._metrics_port:
                self._metrics_port.increment_publish_failure()
            raise

    async def _handle_successful_step_transition(
        self,
        updated_instance: CeremonyInstance,
        context: ExecutionContext,
        idempotency_key: str,
    ) -> CeremonyInstance:
        """Mark idempotency completed, evaluate transitions, publish if applied. Returns instance."""
        await self._mark_idempotency_completed(idempotency_key)
        updated_instance, applied_transition = self._evaluate_transitions(
            updated_instance, context
        )
        if applied_transition is not None:
            await self._publish_transition_applied_with_metrics_and_log(
                instance=updated_instance,
                transition=applied_transition,
                trigger=applied_transition.trigger,
            )
        return updated_instance

    async def _publish_step_executed_event(
        self,
        instance: CeremonyInstance,
        step_id: StepId,
        step_result: StepResult,
    ) -> None:
        payload: dict[str, Any] = {
            "instance_id": instance.instance_id,
            "step_id": step_id.value,
            "status": step_result.status.value,
            "current_state": instance.current_state,
            "output": step_result.output,
        }
        # Only include error_message if present (optional field)
        if step_result.error_message is not None:
            payload["error_message"] = step_result.error_message
        envelope = create_event_envelope(
            event_type=SUBJECT_STEP_EXECUTED,
            payload=payload,
            producer="ceremony-engine",
            entity_id=instance.instance_id,
            operation=f"step:{step_id.value}",
            correlation_id=instance.correlation_id,
        )
        await self._messaging_port.publish_event(
            subject=SUBJECT_STEP_EXECUTED,
            envelope=envelope,
        )

    async def _publish_transition_applied_event(
        self,
        instance: CeremonyInstance,
        transition: Transition,
        trigger: TransitionTrigger,
    ) -> None:
        payload = {
            "instance_id": instance.instance_id,
            "from_state": transition.from_state,
            "to_state": transition.to_state,
            "trigger": trigger.value,
        }
        envelope = create_event_envelope(
            event_type=SUBJECT_TRANSITION_APPLIED,
            payload=payload,
            producer="ceremony-engine",
            entity_id=instance.instance_id,
            operation=f"transition:{trigger.value}",
            correlation_id=instance.correlation_id,
        )
        await self._messaging_port.publish_event(
            subject=SUBJECT_TRANSITION_APPLIED,
            envelope=envelope,
        )

    def _get_step_timeout(self, instance: CeremonyInstance, step: Step) -> int:
        """Get timeout for step execution, validating against ceremony limits.

        Args:
            instance: Ceremony instance
            step: Step to get timeout for

        Returns:
            Timeout in seconds

        Raises:
            ValueError: If step timeout exceeds ceremony limits
        """
        # Use step-specific timeout if provided, otherwise use default
        timeout = step.timeout_seconds
        if timeout is None:
            timeout = instance.definition.get_step_default_timeout()

        # Validate timeout doesn't exceed step_max
        step_max = instance.definition.get_step_max_timeout()
        if timeout > step_max:
            raise ValueError(
                f"Step '{step.id.value}' timeout ({timeout}s) exceeds ceremony step_max "
                f"({step_max}s)"
            )

        return timeout

    def _get_retry_policy(self, instance: CeremonyInstance, step: Step) -> RetryPolicy | None:
        """Get retry policy for step.

        Args:
            instance: Ceremony instance
            step: Step to get retry policy for

        Returns:
            RetryPolicy if step has one, or default policy from definition, or None
        """
        # Step-specific retry policy takes precedence
        if step.retry is not None:
            return step.retry

        # Fall back to default retry policy from definition
        return instance.definition.get_default_retry_policy()

    async def _execute_step_with_retry_and_timeout(
        self,
        step: Step,
        context: ExecutionContext,
        timeout_seconds: int,
        retry_policy: RetryPolicy | None,
    ) -> StepResult:
        """Execute step with retry logic and timeout.

        Args:
            step: Step to execute
            context: Execution context
            timeout_seconds: Timeout for each attempt
            retry_policy: Retry policy (None means no retries)

        Returns:
            StepResult from execution (after retries if needed)

        Raises:
            TimeoutError: If step execution exceeds timeout
        """
        max_attempts = retry_policy.max_attempts if retry_policy else 1
        backoff_seconds = retry_policy.backoff_seconds if retry_policy else 0
        exponential_backoff = retry_policy.exponential_backoff if retry_policy else False
        for attempt in range(1, max_attempts + 1):
            step_result = await self._execute_step_once(
                step=step,
                context=context,
                timeout_seconds=timeout_seconds,
                attempt=attempt,
                max_attempts=max_attempts,
            )

            if step_result.is_success():
                if attempt > 1:
                    logger.info(
                        f"Step '{step.id.value}' succeeded on attempt {attempt}/{max_attempts}"
                    )
                return step_result

            if step_result.is_failure() and attempt < max_attempts:
                logger.warning(
                    f"Step '{step.id.value}' failed on attempt {attempt}/{max_attempts}: "
                    f"{step_result.error_message}"
                )
                await self._apply_backoff(
                    backoff_seconds=backoff_seconds,
                    exponential_backoff=exponential_backoff,
                    attempt=attempt,
                )
                continue

            return step_result

        return StepResult(
            status=StepStatus.FAILED,
            output={},
            error_message=f"Step '{step.id.value}' failed after {max_attempts} attempts",
        )

    async def _execute_step_once(
        self,
        step: Step,
        context: ExecutionContext,
        timeout_seconds: int,
        attempt: int,
        max_attempts: int,
    ) -> StepResult:
        """Execute a single step attempt with timeout handling."""
        try:
            return await asyncio.wait_for(
                self._step_handler_port.execute_step(step, context),
                timeout=timeout_seconds,
            )
        except TimeoutError:
            error_msg = (
                f"Step '{step.id.value}' timed out after {timeout_seconds}s "
                f"(attempt {attempt}/{max_attempts})"
            )
            logger.error(error_msg)
            return StepResult(
                status=StepStatus.FAILED,
                output={},
                error_message=error_msg,
            )
        except Exception as e:
            error_msg = (
                f"Step '{step.id.value}' raised exception on attempt "
                f"{attempt}/{max_attempts}: {e}"
            )
            logger.error(error_msg, exc_info=True)
            return StepResult(
                status=StepStatus.FAILED,
                output={},
                error_message=error_msg,
            )

    async def _apply_backoff(
        self,
        backoff_seconds: int,
        exponential_backoff: bool,
        attempt: int,
    ) -> None:
        """Apply backoff before retrying a step."""
        if backoff_seconds <= 0:
            return

        wait_time = backoff_seconds
        if exponential_backoff:
            wait_time = backoff_seconds * (2 ** (attempt - 1))

        logger.info(
            f"Waiting {wait_time}s before retry (exponential={exponential_backoff})"
        )
        await asyncio.sleep(wait_time)
