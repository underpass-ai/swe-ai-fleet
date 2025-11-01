"""
Factory for creating VLLMAgent with all dependencies (fail-fast DI).

This factory knows how to wire up all the dependencies needed by VLLMAgent
following the fail-fast dependency injection pattern.
"""

from __future__ import annotations

from core.agents_and_tools.agents.application.services.artifact_collection_service import (
    ArtifactCollectionApplicationService,
)
from core.agents_and_tools.agents.application.services.log_reasoning_service import (
    LogReasoningApplicationService,
)
from core.agents_and_tools.agents.application.services.result_summarization_service import (
    ResultSummarizationApplicationService,
)
from core.agents_and_tools.agents.application.services.step_execution_service import (
    StepExecutionApplicationService,
)
from core.agents_and_tools.agents.application.usecases.execute_task_iterative_usecase import (
    ExecuteTaskIterativeUseCase,
)
from core.agents_and_tools.agents.application.usecases.execute_task_usecase import ExecuteTaskUseCase
from core.agents_and_tools.agents.application.usecases.generate_next_action_usecase import (
    GenerateNextActionUseCase,
)
from core.agents_and_tools.agents.application.usecases.generate_plan_usecase import GeneratePlanUseCase
from core.agents_and_tools.agents.application.usecases.load_profile_usecase import LoadProfileUseCase
from core.agents_and_tools.agents.infrastructure.adapters.profile_config import ProfileConfig
from core.agents_and_tools.agents.infrastructure.adapters.tool_execution_adapter import (
    ToolExecutionAdapter,
)
from core.agents_and_tools.agents.infrastructure.adapters.vllm_client_adapter import VLLMClientAdapter
from core.agents_and_tools.agents.infrastructure.adapters.yaml_profile_adapter import (
    YamlProfileLoaderAdapter,
)
from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
    AgentInitializationConfig,
)
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.agents.infrastructure.mappers.execution_step_mapper import ExecutionStepMapper
from core.agents_and_tools.agents.infrastructure.services.json_response_parser import (
    JSONResponseParser,
)
from core.agents_and_tools.agents.infrastructure.services.prompt_loader import PromptLoader
from core.agents_and_tools.agents.vllm_agent import VLLMAgent


class VLLMAgentFactory:
    """
    Factory for creating VLLMAgent with all dependencies wired up.

    This factory encapsulates the knowledge of how to create all dependencies
    needed by VLLMAgent. It follows the fail-fast pattern - all dependencies
    are created upfront and failures happen immediately.
    """

    @staticmethod
    def create(config: AgentInitializationConfig) -> VLLMAgent:
        """
        Create VLLMAgent with all dependencies wired up (fail-fast).

        This method creates all the dependencies in the correct order:
        1. Load agent profile
        2. Create LLM client adapter
        3. Create infrastructure services
        4. Create use cases
        5. Create tool execution adapter
        6. Create step mapper
        7. Create VLLMAgent with all dependencies

        Args:
            config: Agent initialization config

        Returns:
            VLLMAgent instance with all dependencies injected

        Raises:
            ValueError: If any required dependency cannot be created
        """
        # Fail fast if config is missing required fields
        if not config.vllm_url:
            raise ValueError("vllm_url is required in AgentInitializationConfig (fail-fast)")

        # Step 1: Load agent profile
        profiles_url = ProfileConfig.get_default_profiles_url()
        profile_adapter = YamlProfileLoaderAdapter(profiles_url)
        load_profile_usecase = LoadProfileUseCase(profile_adapter)
        profile = load_profile_usecase.execute(config.role)
        
        # Fail fast if profile not found
        if not profile:
            raise ValueError(f"Profile not found for role: {config.role} (fail-fast)")

        # Step 2: Create LLM client adapter
        llm_client_port = VLLMClientAdapter(
            vllm_url=config.vllm_url,
            model=profile.model,
            temperature=profile.temperature,
            max_tokens=profile.max_tokens,
        )

        # Step 3: Create infrastructure services
        prompt_loader = PromptLoader()
        json_parser = JSONResponseParser()
        step_mapper = ExecutionStepMapper()
        artifact_mapper = ArtifactMapper()

        # Step 4: Create tool execution adapter (needed by use cases)
        tool_execution_port = ToolExecutionAdapter(
            workspace_path=config.workspace_path,
            audit_callback=config.audit_callback,
        )

        # Step 5: Create helper use cases
        generate_plan_usecase = GeneratePlanUseCase(
            llm_client=llm_client_port,
            prompt_loader=prompt_loader,
            json_parser=json_parser,
            step_mapper=step_mapper,
        )

        generate_next_action_usecase = GenerateNextActionUseCase(
            llm_client=llm_client_port,
            prompt_loader=prompt_loader,
            json_parser=json_parser,
            step_mapper=step_mapper,
        )

        # Step 6: Create application services
        log_reasoning_service = LogReasoningApplicationService(
            agent_id=config.agent_id,
            role=config.role,
        )

        result_summarization_service = ResultSummarizationApplicationService(
            tool_execution_port=tool_execution_port,
        )

        artifact_collection_service = ArtifactCollectionApplicationService(
            tool_execution_port=tool_execution_port,
            artifact_mapper=artifact_mapper,
        )

        step_execution_service = StepExecutionApplicationService(
            tool_execution_port=tool_execution_port,
        )

        # Step 7: Create main orchestration use cases
        execute_task_usecase = ExecuteTaskUseCase(
            tool_execution_port=tool_execution_port,
            step_mapper=step_mapper,
            artifact_mapper=artifact_mapper,
            generate_plan_usecase=generate_plan_usecase,
            log_reasoning_service=log_reasoning_service,
            result_summarization_service=result_summarization_service,
            artifact_collection_service=artifact_collection_service,
            step_execution_service=step_execution_service,
            agent_id=config.agent_id,
        )

        execute_task_iterative_usecase = ExecuteTaskIterativeUseCase(
            tool_execution_port=tool_execution_port,
            step_mapper=step_mapper,
            artifact_mapper=artifact_mapper,
            generate_next_action_usecase=generate_next_action_usecase,
            log_reasoning_service=log_reasoning_service,
            result_summarization_service=result_summarization_service,
            artifact_collection_service=artifact_collection_service,
            step_execution_service=step_execution_service,
            agent_id=config.agent_id,
        )

        # Step 8: Create VLLMAgent with all dependencies
        return VLLMAgent(
            config=config,
            llm_client_port=llm_client_port,
            tool_execution_port=tool_execution_port,
            generate_plan_usecase=generate_plan_usecase,
            generate_next_action_usecase=generate_next_action_usecase,
            step_mapper=step_mapper,
            execute_task_usecase=execute_task_usecase,
            execute_task_iterative_usecase=execute_task_iterative_usecase,
        )

