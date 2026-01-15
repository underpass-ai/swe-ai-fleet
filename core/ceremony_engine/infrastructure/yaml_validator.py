"""YAML validator and parser for ceremony definitions.

Following Hexagonal Architecture:
- Domain layer (CeremonyDefinition) is pure and immutable
- Infrastructure layer (this validator) handles YAML parsing and validation
- Fail-fast validation on all errors
"""

import yaml
from pathlib import Path
from typing import Any

from core.ceremony_engine.domain.entities.ceremony_definition import CeremonyDefinition
from core.ceremony_engine.domain.value_objects import (
    Guard,
    GuardType,
    Inputs,
    Output,
    RetryPolicy,
    Role,
    State,
    Step,
    StepHandlerType,
    Timeouts,
    Transition,
)


class CeremonyDefinitionValidator:
    """Validates and parses YAML ceremony definitions.

    This is infrastructure responsibility:
    - Domain entities do NOT know about YAML
    - Mapper lives in infrastructure layer
    - Handles all YAML parsing and validation
    - Fail-fast on any error

    Following DDD:
    - No from_yaml() in domain entities
    - Explicit mapper in infrastructure
    - Fail-fast validation
    """

    @staticmethod
    def validate_and_parse_from_file(file_path: str | Path) -> CeremonyDefinition:
        """Load and parse ceremony definition from YAML file.

        Args:
            file_path: Path to YAML file

        Returns:
            CeremonyDefinition (validated)

        Raises:
            FileNotFoundError: If file does not exist
            yaml.YAMLError: If YAML is malformed
            ValueError: If ceremony definition is invalid
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Ceremony definition file not found: {file_path}")

        with open(path) as f:
            yaml_data = yaml.safe_load(f)

        if not isinstance(yaml_data, dict):
            raise ValueError(f"YAML root must be a dict, got {type(yaml_data)}")

        return CeremonyDefinitionValidator.validate_and_parse(yaml_data)

    @staticmethod
    def validate_and_parse(yaml_data: dict[str, Any]) -> CeremonyDefinition:
        """Validate YAML data and construct CeremonyDefinition (fail-fast).

        Args:
            yaml_data: Parsed YAML data (dict)

        Returns:
            CeremonyDefinition (validated)

        Raises:
            KeyError: If required fields are missing
            ValueError: If ceremony definition is invalid
        """
        # Validate yaml_data is a dict (defense in depth)
        if not isinstance(yaml_data, dict):
            raise ValueError(f"YAML data must be a dict, got {type(yaml_data)}")

        # Validate required top-level keys
        required_keys = ["version", "name", "states", "transitions"]
        for key in required_keys:
            if key not in yaml_data:
                raise ValueError(f"Missing required key: {key}")

        # Parse and construct Value Objects
        version = str(yaml_data["version"])
        name = str(yaml_data["name"])
        description = str(yaml_data.get("description", ""))

        inputs = CeremonyDefinitionValidator._parse_inputs(yaml_data.get("inputs", {}))
        outputs = CeremonyDefinitionValidator._parse_outputs(yaml_data.get("outputs", {}))
        states = CeremonyDefinitionValidator._parse_states(yaml_data["states"])
        transitions = CeremonyDefinitionValidator._parse_transitions(yaml_data["transitions"])
        steps = CeremonyDefinitionValidator._parse_steps(yaml_data.get("steps", []))
        guards = CeremonyDefinitionValidator._parse_guards(yaml_data.get("guards", {}))
        roles = CeremonyDefinitionValidator._parse_roles(yaml_data.get("roles", []))
        timeouts = CeremonyDefinitionValidator._parse_timeouts(yaml_data.get("timeouts", {}))
        retry_policies = CeremonyDefinitionValidator._parse_retry_policies(
            yaml_data.get("retry_policies", {})
        )

        # Construct CeremonyDefinition (validates cross-references)
        return CeremonyDefinition(
            version=version,
            name=name,
            description=description,
            inputs=inputs,
            outputs=outputs,
            states=states,
            transitions=transitions,
            steps=steps,
            guards=guards,
            roles=roles,
            timeouts=timeouts,
            retry_policies=retry_policies,
        )

    @staticmethod
    def _parse_inputs(data: dict[str, Any]) -> Inputs:
        """Parse inputs from YAML data."""
        required = tuple(data.get("required", []))
        optional = tuple(data.get("optional", []))
        return Inputs(required=required, optional=optional)

    @staticmethod
    def _parse_outputs(data: dict[str, Any]) -> dict[str, Output]:
        """Parse outputs from YAML data."""
        outputs: dict[str, Output] = {}
        for output_name, output_data in data.items():
            if not isinstance(output_data, dict):
                raise ValueError(f"Output '{output_name}' must be a dict, got {type(output_data)}")
            output_type = str(output_data.get("type", "object"))
            schema = output_data.get("schema")
            outputs[output_name] = Output(type=output_type, schema=schema)
        return outputs

    @staticmethod
    def _parse_states(data: list[dict[str, Any]]) -> tuple[State, ...]:
        """Parse states from YAML data."""
        states: list[State] = []
        for state_data in data:
            state_id = str(state_data["id"])
            description = str(state_data["description"])
            terminal = bool(state_data.get("terminal", False))
            initial = bool(state_data.get("initial", False))
            states.append(State(id=state_id, description=description, terminal=terminal, initial=initial))
        return tuple(states)

    @staticmethod
    def _parse_transitions(data: list[dict[str, Any]]) -> tuple[Transition, ...]:
        """Parse transitions from YAML data."""
        transitions: list[Transition] = []
        for trans_data in data:
            from_state = str(trans_data["from"])
            to_state = str(trans_data["to"])
            trigger = str(trans_data["trigger"])
            guards = tuple(str(g) for g in trans_data.get("guards", []))
            description = str(trans_data["description"])
            transitions.append(
                Transition(
                    from_state=from_state,
                    to_state=to_state,
                    trigger=trigger,
                    guards=guards,
                    description=description,
                )
            )
        return tuple(transitions)

    @staticmethod
    def _parse_steps(data: list[dict[str, Any]]) -> tuple[Step, ...]:
        """Parse steps from YAML data."""
        steps: list[Step] = []
        for step_data in data:
            step_id = str(step_data["id"])
            state = str(step_data["state"])
            handler_str = str(step_data["handler"])
            try:
                handler = StepHandlerType(handler_str)
            except ValueError as e:
                raise ValueError(f"Invalid step handler type: {handler_str}") from e

            config = step_data.get("config", {})
            if not isinstance(config, dict):
                raise ValueError(f"Step '{step_id}' config must be a dict")

            retry_data = step_data.get("retry")
            retry = None
            if retry_data:
                retry = RetryPolicy(
                    max_attempts=int(retry_data["max_attempts"]),
                    backoff_seconds=int(retry_data.get("backoff_seconds", 5)),
                    exponential_backoff=bool(retry_data.get("exponential_backoff", False)),
                )

            timeout_seconds = step_data.get("timeout_seconds")
            if timeout_seconds is not None:
                timeout_seconds = int(timeout_seconds)

            steps.append(
                Step(
                    id=step_id,
                    state=state,
                    handler=handler,
                    config=config,
                    retry=retry,
                    timeout_seconds=timeout_seconds,
                )
            )
        return tuple(steps)

    @staticmethod
    def _parse_guards(data: dict[str, Any]) -> dict[str, Guard]:
        """Parse guards from YAML data."""
        guards: dict[str, Guard] = {}
        for guard_name, guard_data in data.items():
            if not isinstance(guard_data, dict):
                raise ValueError(f"Guard '{guard_name}' must be a dict, got {type(guard_data)}")
            guard_type_str = str(guard_data.get("type", "automated"))
            try:
                guard_type = GuardType(guard_type_str)
            except ValueError as e:
                raise ValueError(f"Invalid guard type: {guard_type_str}") from e

            check = str(guard_data.get("check", ""))
            role = guard_data.get("role")
            if role is not None:
                role = str(role)
            threshold = guard_data.get("threshold")
            if threshold is not None:
                threshold = float(threshold)

            guards[guard_name] = Guard(
                name=guard_name,
                type=guard_type,
                check=check,
                role=role,
                threshold=threshold,
            )
        return guards

    @staticmethod
    def _parse_roles(data: list[dict[str, Any]]) -> tuple[Role, ...]:
        """Parse roles from YAML data."""
        roles: list[Role] = []
        for role_data in data:
            role_id = str(role_data["id"])
            description = str(role_data["description"])
            allowed_actions = tuple(str(a) for a in role_data.get("allowed_actions", []))
            roles.append(Role(id=role_id, description=description, allowed_actions=allowed_actions))
        return tuple(roles)

    @staticmethod
    def _parse_timeouts(data: dict[str, Any]) -> Timeouts:
        """Parse timeouts from YAML data."""
        step_default = int(data.get("step_default", 3600))
        step_max = int(data.get("step_max", 86400))
        ceremony_max = int(data.get("ceremony_max", 604800))
        return Timeouts(step_default=step_default, step_max=step_max, ceremony_max=ceremony_max)

    @staticmethod
    def _parse_retry_policies(data: dict[str, Any]) -> dict[str, RetryPolicy]:
        """Parse retry policies from YAML data."""
        policies: dict[str, RetryPolicy] = {}
        for policy_name, policy_data in data.items():
            if not isinstance(policy_data, dict):
                raise ValueError(f"Retry policy '{policy_name}' must be a dict, got {type(policy_data)}")
            policies[policy_name] = RetryPolicy(
                max_attempts=int(policy_data["max_attempts"]),
                backoff_seconds=int(policy_data.get("backoff_seconds", 5)),
                exponential_backoff=bool(policy_data.get("exponential_backoff", False)),
            )
        return policies
