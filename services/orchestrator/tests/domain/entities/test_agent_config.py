from __future__ import annotations

from typing import Any

import pytest

from services.orchestrator.domain.entities.agent_config import AgentConfig


class TestAgentConfigToFromDict:
    def test_to_dict_includes_extra_params(self) -> None:
        config = AgentConfig(
            agent_id="agent-1",
            role="DEV",
            vllm_url="http://vllm",
            model="model-x",
            agent_type="vllm",
            temperature=0.8,
            extra_params={"max_tokens": 256, "stop": ["\n"]},
        )

        as_dict = config.to_dict()

        assert as_dict["agent_id"] == "agent-1"
        assert as_dict["role"] == "DEV"
        assert as_dict["vllm_url"] == "http://vllm"
        assert as_dict["model"] == "model-x"
        assert as_dict["agent_type"] == "vllm"
        assert as_dict["temperature"] == pytest.approx(0.8)
        # extra_params merged
        assert as_dict["max_tokens"] == 256
        assert as_dict["stop"] == ["\n"]

    def test_from_dict_round_trip_and_extra_params_collected(self) -> None:
        data: dict[str, Any] = {
            "agent_id": "agent-2",
            "role": "ARCHITECT",
            "vllm_url": "http://vllm-2",
            "model": "model-y",
            "agent_type": "mock",
            "temperature": 0.5,
            "top_p": 0.9,
        }
        # Keep a copy because from_dict mutates the dict via pop
        original = dict(data)

        config = AgentConfig.from_dict(data)

        assert config.agent_id == original["agent_id"]
        assert config.role == original["role"]
        assert config.vllm_url == original["vllm_url"]
        assert config.model == original["model"]
        assert config.agent_type == original["agent_type"]
        assert config.temperature == pytest.approx(original["temperature"])
        assert config.extra_params == {"top_p": 0.9}


class TestAgentConfigWithOverrides:
    def test_with_overrides_returns_new_config_with_updates(self) -> None:
        base = AgentConfig(
            agent_id="agent-1",
            role="DEV",
            vllm_url="http://vllm",
            model="model-x",
        )

        new_config = base.with_overrides(temperature=0.95, model="model-z")

        assert new_config is not base
        assert new_config.agent_id == base.agent_id
        assert new_config.role == base.role
        assert new_config.vllm_url == base.vllm_url
        assert new_config.model == "model-z"
        assert new_config.temperature == pytest.approx(0.95)


class TestAgentConfigCreateFactory:
    class _DummyVLLMConfig:
        def __init__(self, base_url: str, base_model: str, base_temp: float) -> None:
            self.base_url = base_url
            self.base_model = base_model
            self.base_temp = base_temp

        def to_agent_config(self, agent_id: str, role: str) -> AgentConfig:
            return AgentConfig(
                agent_id=agent_id,
                role=role,
                vllm_url=self.base_url,
                model=self.base_model,
                temperature=self.base_temp,
            )

    def test_create_uses_vllm_config_defaults_when_no_custom_params(self) -> None:
        vllm_config = self._DummyVLLMConfig(
            base_url="http://vllm-base",
            base_model="model-base",
            base_temp=0.3,
        )

        config = AgentConfig.create(
            agent_id="agent-1",
            role="DEV",
            index=0,
            vllm_config=vllm_config,  # type: ignore[arg-type]
            custom_params=None,
        )

        assert config.vllm_url == "http://vllm-base"
        assert config.model == "model-base"
        assert config.temperature == pytest.approx(0.3)

    def test_create_applies_custom_overrides(self) -> None:
        vllm_config = self._DummyVLLMConfig(
            base_url="http://vllm-base",
            base_model="model-base",
            base_temp=0.3,
        )

        config = AgentConfig.create(
            agent_id="agent-2",
            role="ARCHITECT",
            index=1,
            vllm_config=vllm_config,  # type: ignore[arg-type]
            custom_params={
                "vllm_url": "http://custom-vllm",
                "model": "model-custom",
                "temperature": "0.9",  # ensure cast to float
            },
        )

        assert config.vllm_url == "http://custom-vllm"
        assert config.model == "model-custom"
        assert config.temperature == pytest.approx(0.9)
