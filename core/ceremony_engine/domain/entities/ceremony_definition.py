"""CeremonyDefinition: Aggregate Root for ceremony definitions."""

from dataclasses import dataclass

from core.ceremony_engine.domain.value_objects import (
    Guard,
    Inputs,
    Output,
    RetryPolicy,
    Role,
    State,
    Step,
    Timeouts,
    Transition,
)


@dataclass(frozen=True)
class CeremonyDefinition:
    """
    Aggregate Root: Ceremony definition.

    Represents a complete ceremony definition loaded from YAML configuration.
    This is the main aggregate that groups all ceremony components together.

    Domain Invariants:
    - version must be "1.0" (for now)
    - name must be non-empty, snake_case
    - description must be non-empty
    - Exactly one state must have initial=True
    - Terminal states cannot have outgoing transitions
    - All transitions reference existing states
    - All steps reference existing states
    - All guards referenced in transitions must exist
    - All roles.allowed_actions reference existing steps or triggers
    - Immutable (frozen=True)

    Business Rules:
    - Ceremony definitions are loaded from YAML and validated
    - Once created, definitions are immutable
    - Validation ensures ceremony is executable
    """

    version: str
    name: str
    description: str
    inputs: Inputs
    outputs: dict[str, Output]
    states: tuple[State, ...]
    transitions: tuple[Transition, ...]
    steps: tuple[Step, ...]
    guards: dict[str, Guard]
    roles: tuple[Role, ...]
    timeouts: Timeouts
    retry_policies: dict[str, RetryPolicy]

    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).

        Raises:
            ValueError: If any invariant is violated
        """
        self._validate_version()
        self._validate_name()
        self._validate_description()
        state_ids = self._get_state_ids()
        self._validate_initial_state()
        self._validate_terminal_states()
        self._validate_transition_state_references(state_ids)
        self._validate_step_state_references(state_ids)
        guard_names = set(self.guards.keys())
        self._validate_transition_guards(guard_names)
        step_ids = {step.id for step in self.steps}
        trigger_names = {transition.trigger for transition in self.transitions}
        self._validate_role_actions(step_ids, trigger_names)

    def _validate_version(self) -> None:
        """Validate ceremony version."""
        if self.version != "1.0":
            raise ValueError(f"Unsupported ceremony definition version: {self.version} (expected '1.0')")

    def _validate_name(self) -> None:
        """Validate ceremony name (snake_case)."""
        if not self.name or not self.name.strip():
            raise ValueError("Ceremony name cannot be empty")
        if " " in self.name or not self.name.replace("_", "").isalnum():
            raise ValueError(f"Ceremony name must be snake_case: {self.name}")

    def _validate_description(self) -> None:
        """Validate ceremony description."""
        if not self.description or not self.description.strip():
            raise ValueError("Ceremony description cannot be empty")

    def _get_state_ids(self) -> set[str]:
        """Build state IDs lookup set."""
        return {state.id for state in self.states}

    def _validate_initial_state(self) -> None:
        """Validate exactly one initial state exists."""
        initial_states = [s for s in self.states if s.initial]
        if len(initial_states) != 1:
            raise ValueError(
                f"Exactly one state must have initial=True, found {len(initial_states)}: "
                f"{[s.id for s in initial_states]}"
            )

    def _validate_terminal_states(self) -> None:
        """Validate terminal states have no outgoing transitions."""
        terminal_state_ids = {s.id for s in self.states if s.terminal}
        for transition in self.transitions:
            if transition.from_state in terminal_state_ids:
                raise ValueError(
                    f"Terminal state '{transition.from_state}' cannot have outgoing transitions"
                )

    def _validate_transition_state_references(self, state_ids: set[str]) -> None:
        """Validate transitions reference existing states."""
        for transition in self.transitions:
            if transition.from_state not in state_ids:
                raise ValueError(
                    f"Transition references non-existent state '{transition.from_state}'"
                )
            if transition.to_state not in state_ids:
                raise ValueError(
                    f"Transition references non-existent state '{transition.to_state}'"
                )

    def _validate_step_state_references(self, state_ids: set[str]) -> None:
        """Validate steps reference existing states."""
        for step in self.steps:
            if step.state not in state_ids:
                raise ValueError(f"Step '{step.id}' references non-existent state '{step.state}'")

    def _validate_transition_guards(self, guard_names: set[str]) -> None:
        """Validate guards referenced in transitions exist."""
        for transition in self.transitions:
            for guard_name in transition.guards:
                if guard_name not in guard_names:
                    raise ValueError(
                        f"Transition '{transition.trigger}' references non-existent guard '{guard_name}'"
                    )

    def _validate_role_actions(self, step_ids: set[str], trigger_names: set[str]) -> None:
        """Validate roles.allowed_actions reference existing steps or triggers."""
        for role in self.roles:
            for action in role.allowed_actions:
                if action not in step_ids and action not in trigger_names:
                    raise ValueError(
                        f"Role '{role.id}' references non-existent action '{action}' "
                        f"(must be a step id or trigger name)"
                    )

    def get_initial_state(self) -> State:
        """Get the initial state of the ceremony.

        Returns:
            The state with initial=True

        Raises:
            ValueError: If no initial state exists (should not happen after validation)
        """
        initial_states = [s for s in self.states if s.initial]
        if not initial_states:
            raise ValueError("No initial state found (should not happen after validation)")
        return initial_states[0]

    def get_state_by_id(self, state_id: str) -> State | None:
        """Get a state by its ID.

        Args:
            state_id: State ID to lookup

        Returns:
            State if found, None otherwise
        """
        for state in self.states:
            if state.id == state_id:
                return state
        return None
