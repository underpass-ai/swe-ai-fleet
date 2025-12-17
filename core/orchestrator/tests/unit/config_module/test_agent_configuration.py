from core.orchestrator.config_module.agent_configuration import AgentConfig


class TestAgentConfig:
    def test_required_fields_and_defaults_are_set(self) -> None:
        config = AgentConfig(sprint_id="SPR-1", role="DEV")

        assert config.sprint_id == "SPR-1"
        assert config.role == "DEV"
        assert config.workspace == "/workspace"
        assert config.pick_first_ready is True

    def test_is_frozen_and_immutable(self) -> None:
        config = AgentConfig(sprint_id="SPR-1", role="DEV")

        # Dataclass is frozen: attempting to mutate should raise FrozenInstanceError
        from dataclasses import FrozenInstanceError

        try:
            config.sprint_id = "OTHER"  # type: ignore[misc]
        except FrozenInstanceError:
            # Expected path
            return

        # If we reach this point, the dataclass is not frozen as expected
        raise AssertionError("AgentConfig should be immutable (frozen dataclass)")
