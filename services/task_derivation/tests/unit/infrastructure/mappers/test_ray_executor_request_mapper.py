"""Tests for RayExecutorRequestMapper."""

from __future__ import annotations

from unittest.mock import patch

from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.task_derivation.prompt.llm_prompt import (
    LLMPrompt,
)
from task_derivation.domain.value_objects.task_derivation.roles.executor_role import (
    ExecutorRole,
)
from task_derivation.infrastructure.mappers.ray_executor_request_mapper import (
    RayExecutorRequestMapper,
)


class FakeAgentProto:
    """Test double mimicking generated Agent proto constructor."""

    def __init__(
        self,
        id: str,
        role: str,
        model: str,
        prompt_template: str,
    ) -> None:
        self.id = id
        self.role = role
        self.model = model
        self.prompt_template = prompt_template


class FakeTaskConstraintsProto:
    """Test double mimicking generated TaskConstraints proto constructor."""

    def __init__(
        self,
        story_id: str,
        plan_id: str,
        timeout_seconds: int,
        max_retries: int,
    ) -> None:
        self.story_id = story_id
        self.plan_id = plan_id
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries


class FakeExecuteDeliberationRequestProto:
    """Test double mimicking generated ExecuteDeliberationRequest proto constructor."""

    def __init__(
        self,
        task_id: str,
        task_description: str,
        role: str,
        constraints: FakeTaskConstraintsProto,
        agents: list[FakeAgentProto],
        vllm_url: str,
        vllm_model: str,
    ) -> None:
        self.task_id = task_id
        self.task_description = task_description
        self.role = role
        self.constraints = constraints
        self.agents = agents
        self.vllm_url = vllm_url
        self.vllm_model = vllm_model


class TestRayExecutorRequestMapperToExecuteDeliberationRequest:
    """Test to_execute_deliberation_request method."""

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_maps_domain_vos_to_proto_success(self, mock_pb2) -> None:
        """Test successful mapping of domain VOs to protobuf request."""
        # Setup mock proto classes
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-123")
        prompt = LLMPrompt("Decompose this plan into tasks")
        role = ExecutorRole("SYSTEM")
        vllm_url = "http://vllm:8000"
        vllm_model = "Qwen/Qwen2.5-7B-Instruct"

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url=vllm_url,
            vllm_model=vllm_model,
        )

        # Verify request structure
        assert isinstance(request, FakeExecuteDeliberationRequestProto)
        assert request.task_id == "derive-plan-123"
        assert request.task_description == "Decompose this plan into tasks"
        assert request.role == "SYSTEM"
        assert request.vllm_url == "http://vllm:8000"
        assert request.vllm_model == "Qwen/Qwen2.5-7B-Instruct"

        # Verify constraints
        assert isinstance(request.constraints, FakeTaskConstraintsProto)
        assert request.constraints.story_id == ""
        assert request.constraints.plan_id == "plan-123"
        assert request.constraints.timeout_seconds == 120
        assert request.constraints.max_retries == 2

        # Verify agent configuration
        assert len(request.agents) == 1
        agent = request.agents[0]
        assert isinstance(agent, FakeAgentProto)
        assert agent.id == "task-deriver-001"
        assert agent.role == "SYSTEM"
        assert agent.model == "Qwen/Qwen2.5-7B-Instruct"
        assert agent.prompt_template == ""

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_task_id_format(self, mock_pb2) -> None:
        """Test that task_id is formatted correctly with derive- prefix."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("my-plan-456")
        prompt = LLMPrompt("Test prompt")
        role = ExecutorRole("SYSTEM")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        assert request.task_id == "derive-my-plan-456"

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_agent_configuration(self, mock_pb2) -> None:
        """Test that agent is configured correctly for task derivation."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-789")
        prompt = LLMPrompt("Another prompt")
        role = ExecutorRole("DEVELOPER")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Mistral-7B-Instruct",
        )

        agent = request.agents[0]
        assert agent.id == "task-deriver-001"
        assert agent.role == "DEVELOPER"  # Role from domain VO
        assert agent.model == "Mistral-7B-Instruct"  # Model from parameter
        assert agent.prompt_template == ""  # Direct prompt, no template

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_constraints_configuration(self, mock_pb2) -> None:
        """Test that task constraints are set correctly."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-999")
        prompt = LLMPrompt("Test")
        role = ExecutorRole("SYSTEM")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        constraints = request.constraints
        assert constraints.story_id == ""  # Not applicable for task derivation
        assert constraints.plan_id == "plan-999"
        assert constraints.timeout_seconds == 120  # 2 minutes
        assert constraints.max_retries == 2

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_prompt_value_extraction(self, mock_pb2) -> None:
        """Test that prompt value is extracted from LLMPrompt VO."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-111")
        prompt = LLMPrompt("Complex prompt with\nmultiple lines\nand details")
        role = ExecutorRole("SYSTEM")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        assert request.task_description == "Complex prompt with\nmultiple lines\nand details"

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_role_value_extraction(self, mock_pb2) -> None:
        """Test that role value is extracted from ExecutorRole VO."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-222")
        prompt = LLMPrompt("Test")
        role = ExecutorRole("ARCHITECT")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        assert request.role == "ARCHITECT"
        assert request.agents[0].role == "ARCHITECT"

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_plan_id_value_extraction(self, mock_pb2) -> None:
        """Test that plan_id value is extracted from PlanId VO."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("unique-plan-id-333")
        prompt = LLMPrompt("Test")
        role = ExecutorRole("SYSTEM")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        assert request.task_id == "derive-unique-plan-id-333"
        assert request.constraints.plan_id == "unique-plan-id-333"

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_vllm_configuration(self, mock_pb2) -> None:
        """Test that vLLM URL and model are passed through correctly."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-444")
        prompt = LLMPrompt("Test")
        role = ExecutorRole("SYSTEM")
        custom_vllm_url = "https://custom-vllm.example.com:9000"
        custom_vllm_model = "Llama-3.1-8B-Instruct"

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url=custom_vllm_url,
            vllm_model=custom_vllm_model,
        )

        assert request.vllm_url == custom_vllm_url
        assert request.vllm_model == custom_vllm_model
        assert request.agents[0].model == custom_vllm_model

    @patch("task_derivation.infrastructure.mappers.ray_executor_request_mapper.ray_executor_pb2")
    def test_single_agent_in_list(self, mock_pb2) -> None:
        """Test that exactly one agent is created in the agents list."""
        mock_pb2.Agent = FakeAgentProto
        mock_pb2.TaskConstraints = FakeTaskConstraintsProto
        mock_pb2.ExecuteDeliberationRequest = FakeExecuteDeliberationRequestProto

        plan_id = PlanId("plan-555")
        prompt = LLMPrompt("Test")
        role = ExecutorRole("SYSTEM")

        request = RayExecutorRequestMapper.to_execute_deliberation_request(
            plan_id=plan_id,
            prompt=prompt,
            role=role,
            vllm_url="http://vllm:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
        )

        assert len(request.agents) == 1
        assert isinstance(request.agents[0], FakeAgentProto)





