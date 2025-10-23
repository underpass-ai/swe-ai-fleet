"""
Orchestrator Service - gRPC Server
Coordinates multi-agent deliberation and task execution.
"""

import asyncio
import hashlib
import logging
import os
import sys
import time

import grpc

# Add project root to path to import swe_ai_fleet modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.context.streams_init import ensure_streams
from services.orchestrator.application import (
    CreateCouncilUseCase,
    DeleteCouncilUseCase,
    DeliberateUseCase,
    ListCouncilsUseCase,
)
from services.orchestrator.domain.entities import (
    CouncilRegistry,
    DeliberationResultData,
    OrchestratorStatistics,
    RoleCollection,
)
from services.orchestrator.domain.ports import (
    AgentFactoryPort,
    ArchitectPort,
    ConfigurationPort,
    CouncilFactoryPort,
    CouncilQueryPort,
    RayExecutorPort,
    ScoringPort,
)
from services.orchestrator.infrastructure.adapters import (
    ArchitectAdapter,
    CouncilQueryAdapter,
    DeliberateCouncilFactoryAdapter,
    EnvironmentConfigurationAdapter,
    GRPCRayExecutorAdapter,
    ScoringAdapter,
    VLLMAgentFactoryAdapter,
)
from services.orchestrator.infrastructure.dto import (
    OrchestratorServiceServicer as BaseServicer,
)
from services.orchestrator.infrastructure.dto import (
    add_OrchestratorServiceServicer_to_server,
    orchestrator_dto,
)
from services.orchestrator.infrastructure.handlers import (
    OrchestratorAgentResponseConsumer,
    OrchestratorContextConsumer,
    OrchestratorNATSHandler,
    OrchestratorPlanningConsumer,
)
from services.orchestrator.infrastructure.mappers import (
    CouncilInfoMapper,
    DeliberateResponseMapper,
    DeliberationResultDataMapper,
    LegacyCheckSuiteMapper,
    OrchestrateResponseMapper,
    OrchestratorStatsMapper,
    TaskConstraintsMapper,
)
from core.orchestrator.config_module.system_config import SystemConfig
from core.orchestrator.domain.tasks.task_constraints import TaskConstraints
from core.orchestrator.usecases.deliberate_async_usecase import DeliberateAsync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class OrchestratorServiceServicer(BaseServicer):
    """gRPC servicer for Orchestrator Service."""

    def __init__(
        self,
        config: SystemConfig,
        ray_executor: RayExecutorPort,
        council_query: CouncilQueryPort,
        agent_factory: AgentFactoryPort,
        council_factory: CouncilFactoryPort,
        config_port: ConfigurationPort,
        scoring: ScoringPort,
        architect: ArchitectPort,
        result_collector=None
    ):
        """Initialize Orchestrator Service with configuration.
        
        Args:
            config: System configuration
            ray_executor: Port for Ray Executor communication (injected)
            council_query: Port for council query operations (injected)
            agent_factory: Port for agent creation (injected)
            council_factory: Port for council creation (injected)
            config_port: Port for configuration access (injected)
            scoring: Port for scoring operations (injected)
            architect: Port for architect selection (injected)
            result_collector: Optional deliberation result collector
        """
        logger.info("Initializing Orchestrator Service...")
        
        self.config = config
        self.start_time = time.time()
        
        # Inject ports
        self.council_query = council_query
        self.agent_factory = agent_factory
        self.council_factory = council_factory
        self.config_port = config_port
        self.scoring = scoring
        self.architect = architect
        
        # Stats - using domain entity
        self.stats = OrchestratorStatistics()
        
        # Initialize council registry (domain entity)
        # Tell, Don't Ask: Use entity to manage councils instead of raw dicts
        self.council_registry = CouncilRegistry()
        
        # Orchestrator will be initialized lazily when councils are available
        self.orchestrator = None
        
        # Inject Ray Executor adapter (Dependency Injection)
        self.ray_executor = ray_executor
        
        # Get configuration from injected port (Dependency Injection)
        vllm_url = self.config_port.get_config_value(
            "VLLM_URL",
            "http://vllm-server-service.ray.svc.cluster.local:8000"
        )
        vllm_model = self.config_port.get_config_value("VLLM_MODEL", "Qwen/Qwen3-0.6B")
        nats_url = self.config_port.get_config_value("NATS_URL", "nats://nats:4222")
        
        # Initialize DeliberateAsync with injected Ray Executor port
        self.deliberate_async = DeliberateAsync(
            ray_executor_stub=ray_executor,  # Inject port instead of stub
            vllm_url=vllm_url,
            model=vllm_model,
            nats_url=nats_url,
        )
        
        logger.info(f"✅ Ray Executor adapter injected: {type(ray_executor).__name__}")
        
        # Injected DeliberationResultCollector (will be set by main())
        self.result_collector = result_collector
        
        logger.info("Orchestrator Service initialized successfully")
        logger.info(f"   Ray Executor: {ray_executor}")
        logger.info(f"   vLLM: {vllm_url} (model: {vllm_model})")
        logger.warning(
            "No agents configured - councils are empty. "
            "Councils must be created via CreateCouncil RPC."
        )

    async def Deliberate(self, request, context):
        """
        Execute peer deliberation on a task.
        Coordinates review between multiple agents.
        """
        try:
            logger.info(
                f"Deliberate request: role={request.role}, "
                f"rounds={request.rounds}, agents={request.num_agents}"
            )
            
            # Get council for role (Tell, Don't Ask)
            # Fail-fast: get_council() raises RuntimeError if not found
            council = self.council_registry.get_council(request.role)
            
            # Build constraints
            constraints = self._proto_to_constraints(request.constraints)
            
            # Execute deliberation via use case (includes stats update and event publishing)
            deliberate_uc = DeliberateUseCase(
                stats=self.stats,
                messaging=self.messaging
            )
            deliberation_result = await deliberate_uc.execute(
                council=council,
                role=request.role,
                task_description=request.task_description,
                constraints=constraints,
                story_id=None,  # TODO: Extract from constraints if available
                task_id=None,   # TODO: Extract from constraints if available
            )
            
            # Convert to protobuf response
            execution_id = self._generate_execution_id(request.task_description)
            response = DeliberateResponseMapper.domain_to_proto(
                results=deliberation_result.results,
                duration_ms=deliberation_result.duration_ms,
                execution_id=execution_id,
                orchestrator_pb2=orchestrator_dto,
                domain_checks_converter=LegacyCheckSuiteMapper.from_dict_or_object
            )
            
            logger.info(
                f"Deliberate response: winner={response.winner_id}, "
                f"results={len(response.results)}, duration={deliberation_result.duration_ms}ms"
            )
            
            return response

        except Exception as e:
            logger.error(f"Deliberate error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to execute deliberation: {str(e)}")
            return orchestrator_dto.DeliberateResponse()

    async def GetDeliberationResult(self, request, context):
        """
        Get the result of an async deliberation (Ray-based execution).
        
        This RPC allows clients to query the status and results of a deliberation
        that was submitted asynchronously to Ray.
        """
        try:
            task_id = request.task_id
            
            # Fail-fast: Result collector must be available
            if not self.result_collector:
                raise RuntimeError(
                    "Deliberation result collector not available. "
                    "Async deliberation requires NATS connection."
                )
            
            logger.debug(f"GetDeliberationResult request: task_id={task_id}")
            
            # Query result from collector (returns dict)
            result_dict = self.result_collector.get_deliberation_result(task_id)
            
            # Fail-fast: Task must exist
            if not result_dict:
                raise ValueError(f"Task {task_id} not found in result collector")
            
            # Convert dict to domain entity
            result_data = DeliberationResultData.from_dict(result_dict)
            
            # Convert domain entity to protobuf using mapper
            response = DeliberationResultDataMapper.domain_to_proto(result_data)
            
            logger.info(
                f"GetDeliberationResult response: task_id={task_id}, "
                f"status={result_data.status}, results={len(response.results)}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"GetDeliberationResult error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get deliberation result: {str(e)}")
            return orchestrator_dto.GetDeliberationResultResponse()

    async def Orchestrate(self, request, context):
        """
        Orchestrate complete task execution workflow.
        Includes deliberation and architect selection.
        """
        try:
            logger.info(
                f"Orchestrate request: task_id={request.task_id}, "
                f"role={request.role}"
            )
            
            start_time = time.time()
            
            # Fail-fast: Orchestrator and councils must be configured
            if not self.orchestrator or self.council_registry.is_empty:
                raise RuntimeError(
                    "No councils configured. "
                    "At least one council must be created before orchestration can occur."
                )
            
            # Build constraints
            constraints = self._proto_to_constraints(request.constraints)
            
            # Execute orchestration
            result = self.orchestrator.execute(
                role=request.role,
                task=request.task_description,
                constraints=constraints
            )
            
            # Convert to protobuf response
            duration_ms = int((time.time() - start_time) * 1000)
            # Build response using mapper directly
            execution_id = self._generate_execution_id(request.task_id)
            response = OrchestrateResponseMapper.domain_to_proto(
                result=result,
                task_id=request.task_id,
                duration_ms=duration_ms,
                execution_id=execution_id,
                orchestrator_pb2=orchestrator_dto,
                domain_checks_converter=LegacyCheckSuiteMapper.from_dict_or_object
            )
            
            # Update stats using domain entity
            self.stats.increment_orchestration(duration_ms)
            
            logger.info(
                f"Orchestrate response: task_id={request.task_id}, "
                f"winner={response.winner.proposal.author_id}, "
                f"duration={duration_ms}ms"
            )
            
            return response

        except Exception as e:
            logger.error(f"Orchestrate error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to orchestrate task: {str(e)}")
            return orchestrator_dto.OrchestrateResponse()

    async def GetStatus(self, request, context):
        """Get orchestrator service health and statistics."""
        try:
            uptime = int(time.time() - self.start_time)
            
            stats = None
            if request.include_stats:
                # Convert domain statistics to protobuf using mapper
                stats = OrchestratorStatsMapper.domain_to_proto(
                    stats=self.stats,
                    active_councils=self.council_registry.count
                )
            
            return orchestrator_dto.GetStatusResponse(
                status="healthy",
                uptime_seconds=uptime,
                stats=stats
            )

        except Exception as e:
            logger.error(f"GetStatus error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get status: {str(e)}")
            return orchestrator_dto.GetStatusResponse(status="unhealthy")

    # ========== New RPCs - Return UNIMPLEMENTED ==========
    # These RPCs are defined in the API but not yet implemented.
    # They return proper gRPC UNIMPLEMENTED status to inform callers.
    
    async def StreamDeliberation(self, request, context):
        """Stream deliberation progress.
        
        TODO: Implement streaming updates during deliberation.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Streaming deliberation not yet implemented")
        # Return empty stream (proper generator pattern)
        return iter(())  # Empty generator

    async def RegisterAgent(self, request, context):
        """Register a new agent in an existing council.
        
        Adds a vLLM agent to an existing council. The council must be created first
        using CreateCouncil.
        """
        try:
            role = request.role
            agent_id = request.agent_id if request.agent_id else f"agent-{role.lower()}-custom"
            
            logger.info(f"Registering agent {agent_id} to role={role}")
            
            # Fail-fast: Council must exist (Tell, Don't Ask)
            if not self.council_registry.has_council(role):
                raise ValueError(
                    f"Council for role {role} not found. "
                    f"Create council first with CreateCouncil."
                )
            
            # Fail-fast: Agent must not already exist
            existing_agents = self.council_registry.get_agents(role)
            if any(a.agent_id == agent_id for a in existing_agents):
                raise ValueError(
                    f"Agent {agent_id} already registered in {role} council. "
                    f"Each agent ID must be unique within a council."
                )
            
            # Create new agent using AgentFactory
            from core.orchestrator.config_module.vllm_config import VLLMConfig
            from core.orchestrator.domain.agents.agent_factory import (
                AgentFactory,
            )
            
            # Create vLLM agent (production-only, no mocks)
            vllm_config = VLLMConfig.from_env()
            agent_config = vllm_config.to_agent_config(agent_id, role)
            new_agent = AgentFactory.create_agent(**agent_config)
            
            # Add to agents list
            existing_agents.append(new_agent)
            
            # Recreate Deliberate use case with updated agent list
            from core.orchestrator.usecases.peer_deliberation_usecase import (
                Deliberate,
            )
            
            council = Deliberate(
                agents=existing_agents,
                tooling=self.scoring,
                rounds=1,
            )
            
            # Update council in registry (Tell, Don't Ask)
            self.council_registry.update_council(role, council, existing_agents)
            
            # Reinitialize orchestrator with updated councils
            from core.orchestrator.usecases.dispatch_usecase import (
                Orchestrate as OrchestrateUseCase,
            )
            
            self.orchestrator = OrchestrateUseCase(
                config=self.config,
                councils=self.council_registry.get_all_councils(),
                architect=self.architect,
            )
            
            logger.info(f"Agent {agent_id} registered successfully to {role} council")
            logger.info(f"Orchestrator reinitialized with {self.council_registry.count} councils")
            
            return orchestrator_dto.RegisterAgentResponse(
                success=True,
                message=f"Agent {agent_id} registered successfully",
                agent_id=agent_id,
            )
            
        except Exception as e:
            logger.error(f"RegisterAgent error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to register agent: {str(e)}")
            return orchestrator_dto.RegisterAgentResponse(
                success=False,
                message=str(e)
            )

    async def CreateCouncil(self, request, context):
        """Create a council for a role with vLLM agents.
        
        Creates a council with the specified number of vLLM agents
        based on the configuration provided.
        """
        try:
            role = request.role
            num_agents = request.num_agents if request.num_agents > 0 else 3
            config = request.config if request.HasField('config') else None
            
            logger.info(f"Creating council for role={role} with {num_agents} agents")
            
            # Get vLLM config (still infrastructure, could be a port later)
            from core.orchestrator.config_module.vllm_config import VLLMConfig
            
            vllm_config = VLLMConfig.from_env()
            
            # Determine agent type
            agent_type_str = config.agent_type if (config and config.agent_type) else "RAY_VLLM"
            
            # Execute council creation via use case
            # Uses injected ports for agent and council creation
            create_council_uc = CreateCouncilUseCase(council_registry=self.council_registry)
            result = create_council_uc.execute(
                        role=role,
                num_agents=num_agents,
                vllm_config=vllm_config,
                agent_factory=self.agent_factory.create_agent,  # ✅ Injected port
                council_factory=self.council_factory.create_council,  # ✅ Injected port
                scoring_tool=self.scoring,
                agent_type_str=agent_type_str,
                custom_params=config.custom_params if config else None
            )
            
            # Reinitialize orchestrator with updated councils
            from core.orchestrator.usecases.dispatch_usecase import (
                Orchestrate as OrchestrateUseCase,
            )
            
            self.orchestrator = OrchestrateUseCase(
                config=self.config,
                councils=self.council_registry.get_all_councils(),
                architect=self.architect,
            )
            
            logger.info(f"Council {result.council_id} created with {result.agents_created} agents")
            logger.info(f"Orchestrator reinitialized with {self.council_registry.count} councils")
            
            return orchestrator_dto.CreateCouncilResponse(
                council_id=result.council_id,
                agents_created=result.agents_created,
                agent_ids=result.agent_ids,
            )
            
        except Exception as e:
            logger.error(f"CreateCouncil error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to create council: {str(e)}")
            return orchestrator_dto.CreateCouncilResponse()

    async def ListCouncils(self, request, context):
        """List all active councils.
        
        Returns information about all registered councils including their agent details.
        """
        try:
            # Use case pattern with dependency injection
            list_councils_uc = ListCouncilsUseCase(council_query=self.council_query)
            council_infos = list_councils_uc.execute(
                council_registry=self.council_registry,
                include_agents=request.include_agents
            )
            
            # Convert domain CouncilInfo to proto CouncilInfo using mapper
            proto_councils = CouncilInfoMapper.domain_list_to_proto_list(council_infos)
            
            return orchestrator_dto.ListCouncilsResponse(councils=proto_councils)
        except Exception as e:
            logger.error(f"ListCouncils error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return orchestrator_dto.ListCouncilsResponse()

    async def DeleteCouncil(self, request, context):
        """Delete a council and all its agents.
        
        Removes all agents from the council and deletes the council itself.
        """
        try:
            role = request.role
            logger.info(f"Deleting council for role={role}")
            
            # Execute deletion via use case
            delete_council_uc = DeleteCouncilUseCase(council_registry=self.council_registry)
            result = delete_council_uc.execute(role=role)
            
            logger.info(f"Successfully deleted council {role} with {result.agents_removed} agents")
            
            return orchestrator_dto.DeleteCouncilResponse(
                success=result.success,
                message=result.message,
                agents_removed=result.agents_removed
            )
            
        except Exception as e:
            logger.error(f"DeleteCouncil error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error deleting council: {str(e)}")
            return orchestrator_dto.DeleteCouncilResponse(
                success=False,
                message=str(e),
                agents_removed=0
            )

    async def UnregisterAgent(self, request, context):
        """Unregister an agent from a council.
        
        TODO: Implement agent unregistration.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Agent unregistration not yet implemented")
        return orchestrator_dto.UnregisterAgentResponse(success=False, message="Not implemented")

    async def ProcessPlanningEvent(self, request, context):
        """Process a planning event from NATS.
        
        TODO: Implement event processing logic.
        This should be called internally by NATS consumer, not directly.
        """
        logger.info(f"Planning event: {request.event_type} for case {request.case_id}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Event processing not yet implemented - needs NATS integration")
        return orchestrator_dto.PlanningEventResponse(processed=False)

    async def DeriveSubtasks(self, request, context):
        """Derive atomic subtasks from a case/plan.
        
        TODO: Implement task derivation logic.
        Requires integration with Planning and Context services.
        """
        logger.info(f"Derive subtasks: case={request.case_id}, roles={request.roles}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Subtask derivation not yet implemented")
        return orchestrator_dto.DeriveSubtasksResponse(tasks=[], total_tasks=0)

    async def GetTaskContext(self, request, context):
        """Get hydrated context for a task.
        
        TODO: Implement Context Service integration.
        Should call Context Service at context:50054.
        """
        logger.info(f"Get context: task={request.task_id}, role={request.role}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Context integration not yet implemented")
        return orchestrator_dto.GetTaskContextResponse(context_text="", token_count=0)

    async def GetMetrics(self, request, context):
        """Get detailed performance metrics.
        
        TODO: Implement detailed metrics collection and reporting.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Detailed metrics not yet implemented")
        return orchestrator_dto.GetMetricsResponse()

    def _proto_to_constraints(self, proto_constraints) -> TaskConstraints:
        """Convert protobuf constraints to domain TaskConstraints using mapper.
        
        This method bridges the new VO-based architecture with the legacy
        TaskConstraints from core.orchestrator.domain.
        """
        # Use mapper to convert proto to VO
        constraints_vo = TaskConstraintsMapper.from_proto(proto_constraints)
        
        # Convert VO to legacy TaskConstraints format
        # TODO: Refactor to use TaskConstraintsVO directly in use cases
        return TaskConstraints(
            rubric=constraints_vo.rubric,
            architect_rubric=constraints_vo.architect_rubric,
            cluster_spec=None,
            additional_constraints={
                "max_iterations": constraints_vo.max_iterations,
                "timeout_seconds": constraints_vo.timeout_seconds,
                "metadata": constraints_vo.metadata,
            }
        )

    def _generate_execution_id(self, task_desc: str) -> str:
        """Generate unique execution ID."""
        content = f"{task_desc}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


async def init_default_councils_if_empty(
    servicer: "OrchestratorServiceServicer",
    agent_factory: VLLMAgentFactoryAdapter,
    council_factory: DeliberateCouncilFactoryAdapter,
    scoring_adapter: ScoringAdapter,
    vllm_url: str,
    default_model: str,
    agent_config_class: type,  # AgentConfig class injected
) -> None:
    """Initialize default councils if registry is empty.
    
    This ensures councils are always available on startup without
    requiring manual initialization job.
    
    Args:
        servicer: Orchestrator servicer with council_registry
        agent_factory: Factory for creating vLLM agents
        council_factory: Factory for creating councils
        scoring_adapter: Scoring adapter for tooling
        vllm_url: vLLM server URL
        default_model: Default model name
        agent_config_class: AgentConfig class (injected to avoid import)
    """
    
    # Check if councils already exist
    num_existing = len(servicer.council_registry.get_all_roles())
    if num_existing > 0:
        logger.info(f"✅ Found {num_existing} existing councils, skipping initialization")
        return
    
    logger.info("📋 No councils found, initializing default councils...")
    
    # Default roles to initialize
    roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
    agents_per_council = 3
    
    for role in roles:
        try:
            # Create agents for this role
            agents = []
            for i in range(agents_per_council):
                # Create agent config using injected class
                config = agent_config_class(
                    agent_id=f"agent-{role.lower()}-{i+1:03d}",
                    role=role,
                    model=default_model,
                    vllm_url=vllm_url,
                    agent_type="vllm",  # Explicit: use vLLM agents (production), not mock
                    temperature=0.7,
                )
                
                agent = agent_factory.create_agent(config)
                agents.append(agent)
            
            # Create council with agents
            # ScoringAdapter already wraps Scoring instance, use it directly
            council = council_factory.create_council(agents=agents, tooling=scoring_adapter, rounds=1)
            
            # Add to registry
            servicer.council_registry.register_council(role, council, agents)
            
            logger.info(f"✅ Initialized council for {role} with {len(agents)} agents")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize council for {role}: {e}")
            # Continue with other roles
            continue
    
    num_created = len(servicer.council_registry.get_all_roles())
    logger.info(f"✅ Initialized {num_created}/{len(roles)} councils successfully")


async def serve_async():
    """Start the gRPC server."""
    # Load configuration using adapter (Dependency Injection)
    config_adapter = EnvironmentConfigurationAdapter()
    service_config = config_adapter.get_service_configuration()
    
    logger.info("📝 Service configuration loaded:")
    logger.info(f"   gRPC port: {service_config.grpc_port}")
    logger.info(f"   Messaging URL: {service_config.messaging_url}")
    logger.info(f"   Messaging enabled: {service_config.messaging_enabled}")
    logger.info(f"   Executor address: {service_config.executor_address}")
    
    # Initialize config with default roles using domain entity
    role_collection = RoleCollection.create_default()
    
    # SystemConfig expects a list, so we pass the internal list
    # TODO: Refactor SystemConfig to use RoleCollection directly
    config = SystemConfig(roles=role_collection.roles, require_human_approval=False)
    
    # Get default model from configuration
    default_model = config_adapter.get_config_value("VLLM_MODEL", "Qwen/Qwen3-0.6B")
    
    # Create adapters (Dependency Injection)
    ray_executor_adapter = GRPCRayExecutorAdapter(address=service_config.executor_address)
    council_query_adapter = CouncilQueryAdapter(default_model=default_model)
    agent_factory_adapter = VLLMAgentFactoryAdapter()
    council_factory_adapter = DeliberateCouncilFactoryAdapter()
    scoring_adapter = ScoringAdapter()
    architect_adapter = ArchitectAdapter()
    
    logger.info(f"✅ Created Ray Executor adapter: {service_config.executor_address}")
    logger.info(f"✅ Created Council Query adapter (model: {default_model})")
    logger.info("✅ Created Agent Factory adapter (vLLM)")
    logger.info("✅ Created Council Factory adapter (Deliberate)")
    logger.info("✅ Created Scoring adapter")
    logger.info("✅ Created Architect adapter")
    
    # Fail-fast: Validate messaging is enabled
    if not service_config.is_messaging_enabled:
        raise RuntimeError(
            "Messaging system is disabled (ENABLE_NATS=false). "
            "Messaging is required for production. "
            "Set ENABLE_NATS=true to start the service."
        )
    
    # Initialize NATS handler and consumers
    try:
        logger.info("Initializing NATS handler...")
        
        # Note: DeliberationResultCollector will be initialized AFTER MessagingPort is available
        deliberation_collector = None  # Created after NATS connection
        
        # Create servicer with dependencies injected
        servicer = OrchestratorServiceServicer(
            config=config,
            ray_executor=ray_executor_adapter,
            council_query=council_query_adapter,
            agent_factory=agent_factory_adapter,
            council_factory=council_factory_adapter,
            config_port=config_adapter,
            scoring=scoring_adapter,
            architect=architect_adapter,
            result_collector=deliberation_collector
        )
            
        # Initialize default councils if registry is empty
        # This ensures councils are always available without manual init job
        vllm_url = config_adapter.get_config_value(
            "VLLM_URL", 
            "http://vllm.swe-ai-fleet.svc.cluster.local:8000"
        )
        # Import AgentConfig for council initialization
        from services.orchestrator.domain.entities import AgentConfig
        
        await init_default_councils_if_empty(
            servicer=servicer,
            agent_factory=agent_factory_adapter,
            council_factory=council_factory_adapter,
            scoring_adapter=scoring_adapter,  # Inject for tooling
            vllm_url=vllm_url,
            default_model=default_model,
            agent_config_class=AgentConfig,  # Inject class, not import in function
        )
        
        # Initialize NATS handler (now uses NATSMessagingAdapter internally)
        nats_handler = OrchestratorNATSHandler(service_config.messaging_url)
        await nats_handler.connect()
        
        # Create MessagingPort for handler injection
        messaging_port = nats_handler._adapter  # Get the underlying adapter
        
        # Inject messaging port into servicer (for use cases)
        servicer.messaging = messaging_port
        
        # Initialize DeliberationResultCollector now that MessagingPort is available
        from services.orchestrator.infrastructure.handlers import DeliberationResultCollector
        
        timeout_seconds = int(config_adapter.get_config_value("DELIBERATION_TIMEOUT", "300"))
        cleanup_seconds = int(config_adapter.get_config_value("DELIBERATION_CLEANUP", "3600"))
        
        deliberation_collector = DeliberationResultCollector(
            messaging=messaging_port,
            timeout_seconds=timeout_seconds,
            cleanup_after_seconds=cleanup_seconds,
        )
        
        # Inject collector into servicer
        servicer.result_collector = deliberation_collector
        
        # Ensure streams exist
        logger.info("Ensuring NATS streams exist...")
        await ensure_streams(nats_handler._adapter.js)
        
        # Initialize consumers with port injection only (Hexagonal Architecture)
        logger.info("Initializing NATS consumers...")
        
        # Create AutoDispatchService (Application Service for deliberation orchestration)
        from services.orchestrator.application.services import AutoDispatchService
        auto_dispatch_service = AutoDispatchService(
            council_query=council_query_adapter,
            council_registry=servicer.council_registry,
            stats=servicer.stats,
            messaging=messaging_port,
        )
        
        planning_consumer = OrchestratorPlanningConsumer(
            council_query=council_query_adapter,
            messaging=messaging_port,
            auto_dispatch_service=auto_dispatch_service,  # ← Clean DI, no dynamic imports
        )
        await planning_consumer.start()
        
        context_consumer = OrchestratorContextConsumer(
            messaging=messaging_port,
        )
        await context_consumer.start()
        
        agent_response_consumer = OrchestratorAgentResponseConsumer(
            messaging=messaging_port,
        )
        await agent_response_consumer.start()
        
        # Start DeliberationResultCollector (now using MessagingPort)
        if deliberation_collector:
            await deliberation_collector.start()
            logger.info("✓ DeliberationResultCollector started")
        
        logger.info("✓ All NATS consumers started")
        
    except Exception as e:
        # NATS is required - fail fast
        logger.error(f"❌ NATS initialization failed: {e}")
        raise RuntimeError(
            f"Failed to initialize messaging system: {e}. "
            "Messaging is required for production. "
            "Verify NATS_URL is correct and NATS is running."
        ) from e
    
    # Create ASYNC gRPC server (supports background tasks)
    server = grpc.aio.server()
    
    # Add servicer
    add_OrchestratorServiceServicer_to_server(servicer, server)
    
    # Start server (async)
    server.add_insecure_port(f"[::]:{service_config.grpc_port}")
    await server.start()
    
    logger.info(f"🚀 Orchestrator Service listening on port {service_config.grpc_port}")
    logger.info(f"   Active councils: {servicer.council_registry.count}")
    logger.info(f"   Messaging: {service_config.messaging_url} ✓")
    
    # Keep server running
    # Kubernetes will send SIGTERM when pod needs to shutdown
    await server.wait_for_termination()


def main():
    """Main entry point."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()

