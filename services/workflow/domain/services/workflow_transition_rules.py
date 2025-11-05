"""Workflow transition rules (FSM configuration reader and validator).

Loads FSM configuration from YAML and validates state transitions.
Following Domain-Driven Design principles.
"""

from dataclasses import dataclass
from typing import Any

from core.agents_and_tools.agents.domain.entities.rbac.action import ActionEnum
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum


@dataclass(frozen=True)
class TransitionRule:
    """Represents a single transition rule in the FSM.
    
    Immutable following DDD principles.
    """
    
    from_state: WorkflowStateEnum
    to_state: WorkflowStateEnum
    action: ActionEnum
    allowed_roles: tuple[str, ...]
    auto: bool = False
    guards: tuple[str, ...] = ()
    
    def __post_init__(self) -> None:
        """Validate business invariants (fail-fast).
        
        Type validation is handled by type hints.
        No business rules to validate (all fields are valid by construction).
        """
        pass
    
    def can_execute(self, role: str) -> bool:
        """Check if a role can execute this transition."""
        if self.auto:
            return True  # Auto-transitions don't need role check
        
        if not self.allowed_roles:
            return True  # No role restrictions (system transitions)
        
        return role in self.allowed_roles


class WorkflowTransitionRules:
    """Domain service for workflow transition rules.
    
    Encapsulates FSM transition logic.
    Loaded from config/workflow.fsm.yaml.
    
    Following DDD: This is a domain service (stateless business logic).
    """
    
    def __init__(self, fsm_config: dict[str, Any]) -> None:
        """Initialize transition rules from FSM configuration.
        
        Args:
            fsm_config: Parsed YAML FSM configuration
        """
        self._transitions: dict[tuple[WorkflowStateEnum, ActionEnum], TransitionRule] = {}
        self._auto_transitions: dict[WorkflowStateEnum, WorkflowStateEnum] = {}
        self._state_roles: dict[WorkflowStateEnum, tuple[str, ...]] = {}
        
        self._parse_fsm_config(fsm_config)
    
    def _parse_fsm_config(self, config: dict[str, Any]) -> None:
        """Parse FSM configuration and build transition rules."""
        # Parse states and their allowed roles
        for state_config in config.get("states", []):
            state_id = state_config["id"]
            try:
                state = WorkflowStateEnum(state_id)
            except ValueError:
                continue  # Skip unknown states
            
            allowed_roles = tuple(state_config.get("allowed_roles", []))
            self._state_roles[state] = allowed_roles
            
            # Handle auto-transitions
            if "auto_transition_to" in state_config:
                target_id = state_config["auto_transition_to"]
                try:
                    target_state = WorkflowStateEnum(target_id)
                    self._auto_transitions[state] = target_state
                except ValueError:
                    pass  # Skip invalid target
        
        # Parse transitions
        for transition_config in config.get("transitions", []):
            from_id = transition_config["from"]
            to_id = transition_config["to"]
            action_str = transition_config["action"]
            
            try:
                from_state = WorkflowStateEnum(from_id)
                to_state = WorkflowStateEnum(to_id)
                action = ActionEnum(action_str)
            except ValueError:
                continue  # Skip invalid transitions
            
            auto = transition_config.get("auto", False)
            guards = tuple(transition_config.get("guards", []))
            
            # Allowed roles come from the FROM state
            allowed_roles = self._state_roles.get(from_state, ())
            
            rule = TransitionRule(
                from_state=from_state,
                to_state=to_state,
                action=action,
                allowed_roles=allowed_roles,
                auto=auto,
                guards=guards,
            )
            
            self._transitions[(from_state, action)] = rule
    
    def can_transition(
        self,
        from_state: WorkflowStateEnum,
        action: ActionEnum,
        role: str,
    ) -> bool:
        """Check if a transition is allowed.
        
        Args:
            from_state: Current state
            action: Action to execute
            role: Role attempting the action
            
        Returns:
            True if transition is allowed
        """
        rule = self._transitions.get((from_state, action))
        if not rule:
            return False
        
        return rule.can_execute(role)
    
    def get_next_state(
        self,
        from_state: WorkflowStateEnum,
        action: ActionEnum,
    ) -> WorkflowStateEnum | None:
        """Get the next state after executing an action.
        
        Args:
            from_state: Current state
            action: Action to execute
            
        Returns:
            Next state, or None if transition not allowed
        """
        rule = self._transitions.get((from_state, action))
        if not rule:
            return None
        
        return rule.to_state
    
    def get_auto_transition_target(
        self,
        current_state: WorkflowStateEnum,
    ) -> WorkflowStateEnum | None:
        """Get auto-transition target for a state.
        
        Args:
            current_state: Current state
            
        Returns:
            Target state if auto-transition defined, None otherwise
        """
        return self._auto_transitions.get(current_state)
    
    def is_auto_transition_state(self, state: WorkflowStateEnum) -> bool:
        """Check if a state has an auto-transition."""
        return state in self._auto_transitions
    
    def get_allowed_roles(self, state: WorkflowStateEnum) -> tuple[str, ...]:
        """Get roles allowed to act in a state."""
        return self._state_roles.get(state, ())
    
    def get_allowed_actions(
        self,
        from_state: WorkflowStateEnum,
        role: str,
    ) -> list[ActionEnum]:
        """Get allowed actions for a role in a state.
        
        Args:
            from_state: Current state
            role: Role to check
            
        Returns:
            List of allowed actions
        """
        allowed = []
        for (state, action), rule in self._transitions.items():
            if state == from_state and rule.can_execute(role):
                allowed.append(action)
        return allowed

