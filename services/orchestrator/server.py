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
from services.orchestrator.consumers import (
    DeliberationResultCollector,
    OrchestratorAgentResponseConsumer,
    OrchestratorContextConsumer,
    OrchestratorPlanningConsumer,
)
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
from services.orchestrator.nats_handler import OrchestratorNATSHandler
from swe_ai_fleet.orchestrator.config_module.system_config import SystemConfig
from swe_ai_fleet.orchestrator.domain.agents.agent import Agent
from swe_ai_fleet.orchestrator.domain.agents.services.architect_selector_service import (
    ArchitectSelectorService,
)
from swe_ai_fleet.orchestrator.domain.check_results.services.scoring import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase import DeliberateAsync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class OrchestratorServiceServicer(orchestrator_pb2_grpc.OrchestratorServiceServicer):
    """gRPC servicer for Orchestrator Service."""

    def __init__(self, config: SystemConfig, result_collector=None):
        """Initialize Orchestrator Service with configuration."""
        logger.info("Initializing Orchestrator Service...")
        
        self.config = config
        self.start_time = time.time()
        
        # Stats
        self.stats = {
            "total_deliberations": 0,
            "total_orchestrations": 0,
            "total_duration_ms": 0,
            "role_counts": {},
        }
        
        # Initialize scoring tool
        self.scoring = Scoring()
        
        # Initialize councils and agents (lazy initialization will be added when agents are available)
        # For now, councils are empty - they need to be registered externally
        self.councils = {}
        self.council_agents = {}  # Track agents per council for metadata
        
        # Initialize architect selector with default architect
        from swe_ai_fleet.orchestrator.domain.agents.architect_agent import ArchitectAgent
        self.architect = ArchitectSelectorService(architect=ArchitectAgent())
        
        # Orchestrator will be initialized lazily when councils are available
        self.orchestrator = None
        
        # Initialize Ray Executor gRPC client (replaces direct Ray connection)
        ray_executor_address = os.getenv(
            "RAY_EXECUTOR_ADDRESS",
            "ray-executor.swe-ai-fleet.svc.cluster.local:50056"
        )
        vllm_url = os.getenv("VLLM_URL", "http://vllm-server-service.ray.svc.cluster.local:8000")
        vllm_model = os.getenv("VLLM_MODEL", "Qwen/Qwen3-0.6B")
        nats_url = os.getenv("NATS_URL", "nats://nats:4222")
        
        # Create gRPC channel to Ray Executor
        self.ray_executor_channel = grpc.aio.insecure_channel(ray_executor_address)
        try:
            from gen import ray_executor_pb2_grpc
        except ModuleNotFoundError:
            # Fallback for tests where gen is in services.orchestrator.gen
            from services.orchestrator.gen import ray_executor_pb2_grpc
        self.ray_executor_stub = ray_executor_pb2_grpc.RayExecutorServiceStub(
            self.ray_executor_channel
        )
        
        # Initialize DeliberateAsync with Ray Executor stub (instead of Ray address)
        self.deliberate_async = DeliberateAsync(
            ray_executor_stub=self.ray_executor_stub,
            vllm_url=vllm_url,
            model=vllm_model,
            nats_url=nats_url,
        )
        
        logger.info(f"✅ Connected to Ray Executor: {ray_executor_address}")
        
        # Injected DeliberationResultCollector (will be set by main())
        self.result_collector = result_collector
        
        logger.info("Orchestrator Service initialized successfully")
        logger.info(f"   Ray Executor: {ray_executor_address}")
        logger.info(f"   vLLM: {vllm_url} (model: {vllm_model})")
        logger.warning("No agents configured - councils are empty. Councils must be created via CreateCouncil RPC.")

    def _create_agents_for_role(self, role_name: str, num_agents: int = 3) -> list[Agent]:
        """Create agents for a specific role.
        
        Note: This method is not currently used. In production, agents should be:
        1. Injected via constructor (dependency injection)
        2. Created by an AgentFactory with LLM backends
        3. Loaded from agent registry/pool
        
        For now, return empty list. When agents are available, use AgentFactory.
        """
        logger.warning(
            f"Agent creation called but not implemented for role: {role_name}. "
            f"Agents should be injected via AgentFactory."
        )
        return []  # Return empty list instead of raising

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
            
            start_time = time.time()
            
            # Get council for role
            council = self.councils.get(request.role)
            if not council:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details(
                    f"No agents configured for role: {request.role}. "
                    f"Agents must be registered before deliberation can occur."
                )
                return orchestrator_pb2.DeliberateResponse()
            
            # Build constraints
            constraints = self._proto_to_constraints(request.constraints)
            
            # Execute deliberation
            results = council.execute(request.task_description, constraints)
            
            # Convert to protobuf response
            duration_ms = int((time.time() - start_time) * 1000)
            response = self._deliberation_results_to_proto(
                results,
                duration_ms,
                execution_id=self._generate_execution_id(request.task_description)
            )
            
            # Update stats
            self.stats["total_deliberations"] += 1
            self.stats["total_duration_ms"] += duration_ms
            self.stats["role_counts"][request.role] = (
                self.stats["role_counts"].get(request.role, 0) + 1
            )
            
            logger.info(
                f"Deliberate response: winner={response.winner_id}, "
                f"results={len(response.results)}, duration={duration_ms}ms"
            )
            
            return response

        except Exception as e:
            logger.error(f"Deliberate error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to execute deliberation: {str(e)}")
            return orchestrator_pb2.DeliberateResponse()

    async def GetDeliberationResult(self, request, context):
        """
        Get the result of an async deliberation (Ray-based execution).
        
        This RPC allows clients to query the status and results of a deliberation
        that was submitted asynchronously to Ray.
        """
        try:
            task_id = request.task_id
            
            if not self.result_collector:
                context.set_code(grpc.StatusCode.UNAVAILABLE)
                context.set_details(
                    "Deliberation result collector not available. "
                    "Async deliberation requires NATS connection."
                )
                return orchestrator_pb2.GetDeliberationResultResponse()
            
            logger.debug(f"GetDeliberationResult request: task_id={task_id}")
            
            # Query result from collector
            result = self.result_collector.get_deliberation_result(task_id)
            
            if not result:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Task {task_id} not found")
                return orchestrator_pb2.GetDeliberationResultResponse()
            
            # Map status string to enum
            status_map = {
                "DELIBERATION_STATUS_PENDING": orchestrator_pb2.DELIBERATION_STATUS_PENDING,
                "DELIBERATION_STATUS_IN_PROGRESS": orchestrator_pb2.DELIBERATION_STATUS_IN_PROGRESS,
                "DELIBERATION_STATUS_COMPLETED": orchestrator_pb2.DELIBERATION_STATUS_COMPLETED,
                "DELIBERATION_STATUS_FAILED": orchestrator_pb2.DELIBERATION_STATUS_FAILED,
                "DELIBERATION_STATUS_TIMEOUT": orchestrator_pb2.DELIBERATION_STATUS_TIMEOUT,
            }
            
            status = status_map.get(
                result["status"],
                orchestrator_pb2.DELIBERATION_STATUS_UNKNOWN
            )
            
            # Build response
            response = orchestrator_pb2.GetDeliberationResultResponse(
                task_id=task_id,
                status=status,
                duration_ms=result.get("duration_ms", 0),
                error_message=result.get("error_message", ""),
            )
            
            # Add results if completed
            if status == orchestrator_pb2.DELIBERATION_STATUS_COMPLETED:
                for res in result.get("results", []):
                    proposal = res.get("proposal", {})
                    delib_result = orchestrator_pb2.DeliberationResult(
                        proposal=orchestrator_pb2.Proposal(
                            author_id=proposal.get("author_id", ""),
                            author_role=proposal.get("author_role", ""),
                            content=proposal.get("content", ""),
                        ),
                        score=1.0,  # Default score (can be enhanced later)
                    )
                    response.results.append(delib_result)
                
                # Set winner (first result for now)
                if result.get("results"):
                    response.winner_id = result["results"][0].get("agent_id", "")
            
            # Add metadata
            response.metadata.CopyFrom(orchestrator_pb2.OrchestratorMetadata(
                execution_id=task_id,
                total_agents=result.get("total_agents", 0),
                successful_agents=result.get("received_count", 0),
                failed_agents=result.get("failed_count", 0),
            ))
            
            logger.info(
                f"GetDeliberationResult response: task_id={task_id}, "
                f"status={status}, results={len(response.results)}"
            )
            
            return response
            
        except Exception as e:
            logger.error(f"GetDeliberationResult error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get deliberation result: {str(e)}")
            return orchestrator_pb2.GetDeliberationResultResponse()

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
            
            # Check if orchestrator is configured
            if not self.orchestrator or not self.councils:
                context.set_code(grpc.StatusCode.UNIMPLEMENTED)
                context.set_details(
                    "No agents configured. "
                    "Agents must be registered before orchestration can occur."
                )
                return orchestrator_pb2.OrchestrateResponse()
            
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
            response = self._orchestration_result_to_proto(
                result,
                request.task_id,
                duration_ms
            )
            
            # Update stats
            self.stats["total_orchestrations"] += 1
            self.stats["total_duration_ms"] += duration_ms
            self.stats["role_counts"][request.role] = (
                self.stats["role_counts"].get(request.role, 0) + 1
            )
            
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
            return orchestrator_pb2.OrchestrateResponse()

    async def GetStatus(self, request, context):
        """Get orchestrator service health and statistics."""
        try:
            uptime = int(time.time() - self.start_time)
            
            stats = None
            if request.include_stats:
                avg_duration = (
                    self.stats["total_duration_ms"] / 
                    max(1, self.stats["total_deliberations"] + self.stats["total_orchestrations"])
                )
                
                stats = orchestrator_pb2.OrchestratorStats(
                    total_deliberations=self.stats["total_deliberations"],
                    total_orchestrations=self.stats["total_orchestrations"],
                    avg_deliberation_time_ms=avg_duration,
                    active_councils=len(self.councils),
                    role_counts=self.stats["role_counts"]
                )
            
            return orchestrator_pb2.GetStatusResponse(
                status="healthy",
                uptime_seconds=uptime,
                stats=stats
            )

        except Exception as e:
            logger.error(f"GetStatus error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get status: {str(e)}")
            return orchestrator_pb2.GetStatusResponse(status="unhealthy")

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
        
        Adds a mock agent to an existing council. The council must be created first
        using CreateCouncil.
        """
        try:
            role = request.role
            agent_id = request.agent_id if request.agent_id else f"agent-{role.lower()}-custom"
            
            logger.info(f"Registering agent {agent_id} to role={role}")
            
            # Check if council exists
            if role not in self.councils:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(
                    f"Council for role {role} not found. Create council first with CreateCouncil."
                )
                return orchestrator_pb2.RegisterAgentResponse(
                    success=False,
                    message=f"Council for role {role} not found"
                )
            
            # Check if agent already exists
            existing_agents = self.council_agents.get(role, [])
            if any(a.agent_id == agent_id for a in existing_agents):
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details(f"Agent {agent_id} already registered in {role} council")
                return orchestrator_pb2.RegisterAgentResponse(
                    success=False,
                    message=f"Agent {agent_id} already exists"
                )
            
            # Create new agent using AgentFactory
            from swe_ai_fleet.orchestrator.config_module.vllm_config import VLLMConfig
            from swe_ai_fleet.orchestrator.domain.agents.agent_factory import (
                AgentFactory,
                AgentType,
            )
            
            # Determine agent type from environment or existing council
            # DEFAULT: vllm for production (real vLLM agents, not mock)
            agent_type = os.getenv("AGENT_TYPE", "vllm")
            
            if agent_type == AgentType.VLLM:
                # Create vLLM agent
                vllm_config = VLLMConfig.from_env()
                agent_config = vllm_config.to_agent_config(agent_id, role)
                new_agent = AgentFactory.create_agent(**agent_config)
            else:
                # PRODUCTION: Should NEVER reach here
                logger.error(
                    f"❌ CRITICAL: Attempted to create MOCK agent in RegisterAgent! "
                    f"agent_type={agent_type}. Use AGENT_TYPE=vllm"
                )
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details("Mock agents not allowed in production")
                return orchestrator_pb2.RegisterAgentResponse(success=False)
            
            # Add to agents list
            existing_agents.append(new_agent)
            self.council_agents[role] = existing_agents
            
            # Recreate Deliberate use case with updated agent list
            from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import (
                Deliberate,
            )
            
            self.councils[role] = Deliberate(
                agents=existing_agents,
                tooling=self.scoring,
                rounds=1,
            )
            
            # Reinitialize orchestrator with updated councils
            from swe_ai_fleet.orchestrator.usecases.dispatch_usecase import (
                Orchestrate as OrchestrateUseCase,
            )
            
            self.orchestrator = OrchestrateUseCase(
                config=self.config,
                councils=self.councils,
                architect=self.architect,
            )
            
            logger.info(f"Agent {agent_id} registered successfully to {role} council")
            logger.info(f"Orchestrator reinitialized with {len(self.councils)} councils")
            
            return orchestrator_pb2.RegisterAgentResponse(
                success=True,
                message=f"Agent {agent_id} registered successfully",
                agent_id=agent_id,
            )
            
        except Exception as e:
            logger.error(f"RegisterAgent error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to register agent: {str(e)}")
            return orchestrator_pb2.RegisterAgentResponse(
                success=False,
                message=str(e)
            )

    async def CreateCouncil(self, request, context):
        """Create a council for a role with configurable agents.
        
        Creates a council with the specified number of agents (mock or vLLM)
        based on the configuration provided.
        """
        try:
            role = request.role
            num_agents = request.num_agents if request.num_agents > 0 else 3
            config = request.config if request.HasField('config') else None
            
            logger.info(f"Creating council for role={role} with {num_agents} agents")
            
            # Check if council already exists
            if role in self.councils:
                context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                context.set_details(f"Council for role {role} already exists")
                return orchestrator_pb2.CreateCouncilResponse()
            
            # Determine agent type from config or environment
            # DEFAULT: RAY_VLLM for production (real vLLM agents)
            agent_type = "RAY_VLLM"  # Production default: real vLLM agents
            
            if config and config.custom_params:
                agent_type = config.custom_params.get("agent_type", agent_type)
            
            # Also check environment variable
            import os
            agent_type = os.getenv("AGENT_TYPE", agent_type)
            
            logger.info(f"Creating council with agent_type={agent_type}")
            
            # Create agents using AgentFactory
            from swe_ai_fleet.orchestrator.config_module.vllm_config import VLLMConfig
            from swe_ai_fleet.orchestrator.domain.agents.agent_factory import (
                AgentFactory,
                AgentType,
            )
            
            agents = []
            agent_ids = []
            
            # Determine agent type from config or use default
            # E2E tests should use RAY_VLLM (real agents), unit tests use MOCK
            requested_agent_type = config.agent_type if (config and config.agent_type) else "RAY_VLLM"
            
            # Map string to AgentType enum
            agent_type_map = {
                "MOCK": AgentType.MOCK,
                "VLLM": AgentType.VLLM,
                "RAY_VLLM": AgentType.VLLM,  # Both VLLM and RAY_VLLM use VLLM type
            }
            agent_type = agent_type_map.get(requested_agent_type, AgentType.VLLM)
            
            logger.info(f"Creating council with agent_type: {requested_agent_type} (mapped to {agent_type})")
            
            if agent_type == AgentType.VLLM:
                # Use vLLM agents
                vllm_config = VLLMConfig.from_env()
                
                for i in range(num_agents):
                    agent_id = f"agent-{role.lower()}-{i+1:03d}"
                    
                    # Create vLLM agent config
                    agent_config = vllm_config.to_agent_config(agent_id, role)
                    
                    # Override with custom params if provided
                    if config and config.custom_params:
                        if "vllm_url" in config.custom_params:
                            agent_config["vllm_url"] = config.custom_params["vllm_url"]
                        if "model" in config.custom_params:
                            agent_config["model"] = config.custom_params["model"]
                        if "temperature" in config.custom_params:
                            agent_config["temperature"] = float(config.custom_params["temperature"])
                    
                    agent = AgentFactory.create_agent(**agent_config)
                    agents.append(agent)
                    agent_ids.append(agent_id)
                    
            else:
                # PRODUCTION: Should NEVER reach here (default is RAY_VLLM)
                # Mock agents are ONLY for unit tests, not for production/E2E
                logger.error(
                    f"❌ CRITICAL: Attempted to create MOCK agents in production! "
                    f"agent_type={agent_type}. "
                    f"Production must use RAY_VLLM agents. "
                    f"Check AGENT_TYPE env var or config.agent_type."
                )
                context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
                context.set_details(
                    "Mock agents not allowed in production. "
                    "Set agent_type='RAY_VLLM' or AGENT_TYPE=vllm"
                )
                return orchestrator_pb2.CreateCouncilResponse()
            
            # Create Deliberate use case with these agents
            from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import (
                Deliberate,
            )
            
            council = Deliberate(
                agents=agents,
                tooling=self.scoring,
                rounds=1,
            )
            
            # Store council and its agents
            self.councils[role] = council
            self.council_agents[role] = agents
            
            # Initialize/reinitialize orchestrator with updated councils
            from swe_ai_fleet.orchestrator.usecases.dispatch_usecase import (
                Orchestrate as OrchestrateUseCase,
            )
            
            self.orchestrator = OrchestrateUseCase(
                config=self.config,
                councils=self.councils,
                architect=self.architect,
            )
            
            council_id = f"council-{role.lower()}"
            
            logger.info(f"Council {council_id} created successfully with {len(agents)} agents")
            logger.info(f"Orchestrator reinitialized with {len(self.councils)} councils")
            
            return orchestrator_pb2.CreateCouncilResponse(
                council_id=council_id,
                agents_created=len(agents),
                agent_ids=agent_ids,
            )
            
        except Exception as e:
            logger.error(f"CreateCouncil error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to create council: {str(e)}")
            return orchestrator_pb2.CreateCouncilResponse()

    async def ListCouncils(self, request, context):
        """List all active councils.
        
        Returns information about all registered councils including their agent details.
        """
        try:
            councils = []
            for role, _council in self.councils.items():
                # Get actual agents from council_agents
                agents = self.council_agents.get(role, [])
                num_agents = len(agents)
                
                # Get model from first agent (all agents in council use same model)
                model = "unknown"
                if agents and hasattr(agents[0], 'model'):
                    model = agents[0].model
                elif agents and hasattr(agents[0], 'vllm_url'):
                    # For VLLM agents, extract model from config or use default
                    model = os.getenv('VLLM_MODEL', 'Qwen/Qwen3-0.6B')
                
                # Create AgentInfo for each agent if requested
                agent_infos = []
                if request.include_agents:
                    for agent in agents:
                        agent_info = orchestrator_pb2.AgentInfo(
                            agent_id=agent.agent_id,
                            role=role,
                            status="ready",  # TODO: Track actual agent status
                        )
                        agent_infos.append(agent_info)
                
                council_info = orchestrator_pb2.CouncilInfo(
                    council_id=f"council-{role.lower()}",
                    role=role,
                    num_agents=num_agents,
                    agents=agent_infos,
                    status="active" if num_agents > 0 else "idle",
                    model=model
                )
                councils.append(council_info)
            
            return orchestrator_pb2.ListCouncilsResponse(councils=councils)
        except Exception as e:
            logger.error(f"ListCouncils error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return orchestrator_pb2.ListCouncilsResponse()

    async def DeleteCouncil(self, request, context):
        """Delete a council and all its agents.
        
        Removes all agents from the council and deletes the council itself.
        """
        try:
            role = request.role
            logger.info(f"Deleting council for role={role}")
            
            # Check if council exists
            if role not in self.councils:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Council for role {role} not found")
                return orchestrator_pb2.DeleteCouncilResponse(
                    success=False,
                    message=f"Council for role {role} not found",
                    agents_removed=0
                )
            
            # Get agents count before deletion
            agents = self.council_agents.get(role, [])
            agents_count = len(agents)
            
            # Remove all agents
            if role in self.council_agents:
                del self.council_agents[role]
            
            # Remove council
            del self.councils[role]
            
            logger.info(f"Successfully deleted council {role} with {agents_count} agents")
            
            return orchestrator_pb2.DeleteCouncilResponse(
                success=True,
                message=f"Council {role} deleted successfully",
                agents_removed=agents_count
            )
            
        except Exception as e:
            logger.error(f"DeleteCouncil error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error deleting council: {str(e)}")
            return orchestrator_pb2.DeleteCouncilResponse(
                success=False,
                message=f"Internal error: {str(e)}",
                agents_removed=0
            )

    async def UnregisterAgent(self, request, context):
        """Unregister an agent from a council.
        
        TODO: Implement agent unregistration.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Agent unregistration not yet implemented")
        return orchestrator_pb2.UnregisterAgentResponse(success=False, message="Not implemented")

    async def ProcessPlanningEvent(self, request, context):
        """Process a planning event from NATS.
        
        TODO: Implement event processing logic.
        This should be called internally by NATS consumer, not directly.
        """
        logger.info(f"Planning event: {request.event_type} for case {request.case_id}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Event processing not yet implemented - needs NATS integration")
        return orchestrator_pb2.PlanningEventResponse(processed=False)

    async def DeriveSubtasks(self, request, context):
        """Derive atomic subtasks from a case/plan.
        
        TODO: Implement task derivation logic.
        Requires integration with Planning and Context services.
        """
        logger.info(f"Derive subtasks: case={request.case_id}, roles={request.roles}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Subtask derivation not yet implemented")
        return orchestrator_pb2.DeriveSubtasksResponse(tasks=[], total_tasks=0)

    async def GetTaskContext(self, request, context):
        """Get hydrated context for a task.
        
        TODO: Implement Context Service integration.
        Should call Context Service at context:50054.
        """
        logger.info(f"Get context: task={request.task_id}, role={request.role}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Context integration not yet implemented")
        return orchestrator_pb2.GetTaskContextResponse(context_text="", token_count=0)

    async def GetMetrics(self, request, context):
        """Get detailed performance metrics.
        
        TODO: Implement detailed metrics collection and reporting.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Detailed metrics not yet implemented")
        return orchestrator_pb2.GetMetricsResponse()

    def _proto_to_constraints(self, proto_constraints) -> TaskConstraints:
        """Convert protobuf constraints to domain TaskConstraints."""
        # Convert proto constraints to domain format
        rubric_dict = {
            "description": proto_constraints.rubric,
            "requirements": list(proto_constraints.requirements),
        }
        
        architect_rubric_dict = {
            "k": 3,  # Top-k selection
            "criteria": proto_constraints.rubric
        }
        
        additional = {
            "max_iterations": proto_constraints.max_iterations or 10,
            "timeout_seconds": proto_constraints.timeout_seconds or 300,
        }
        if proto_constraints.metadata:
            additional["metadata"] = dict(proto_constraints.metadata)
        
        return TaskConstraints(
            rubric=rubric_dict,
            architect_rubric=architect_rubric_dict,
            cluster_spec=None,
            additional_constraints=additional
        )

    def _deliberation_results_to_proto(
        self, results, duration_ms: int, execution_id: str
    ) -> orchestrator_pb2.DeliberateResponse:
        """Convert deliberation results to protobuf response."""
        proto_results = []
        for rank, result in enumerate(results, 1):
            proto_result = orchestrator_pb2.DeliberationResult(
                proposal=orchestrator_pb2.Proposal(
                    author_id=result.proposal.author.agent_id,
                    author_role=result.proposal.author.role,  # role is a string
                    content=result.proposal.content,
                    created_at_ms=int(time.time() * 1000)
                ),
                checks=self._check_suite_to_proto(result.checks),
                score=result.score,
                rank=rank
            )
            proto_results.append(proto_result)
        
        winner_id = proto_results[0].proposal.author_id if proto_results else ""
        
        return orchestrator_pb2.DeliberateResponse(
            results=proto_results,
            winner_id=winner_id,
            duration_ms=duration_ms,
            metadata=orchestrator_pb2.OrchestratorMetadata(
                orchestrator_version="0.1.0",
                timestamp_ms=int(time.time() * 1000),
                execution_id=execution_id
            )
        )

    def _orchestration_result_to_proto(
        self, result, task_id: str, duration_ms: int
    ) -> orchestrator_pb2.OrchestrateResponse:
        """Convert orchestration result to protobuf response."""
        winner = result.get("winner")
        candidates = result.get("candidates", [])
        
        # Winner is a DeliberationResult object (not dict)
        proto_winner = orchestrator_pb2.DeliberationResult(
            proposal=orchestrator_pb2.Proposal(
                author_id=winner.proposal.author.agent_id,
                author_role=winner.proposal.author.role,  # role is a string
                content=winner.proposal.content,
                created_at_ms=int(time.time() * 1000)
            ),
            checks=self._check_suite_to_proto(winner.checks),
            score=winner.score,
            rank=1
        )
        
        # Candidates are already dict format (from to_dict())
        proto_candidates = [
            orchestrator_pb2.DeliberationResult(
                proposal=orchestrator_pb2.Proposal(
                    author_id=c["proposal"]["author"].agent_id,
                    author_role=c["proposal"]["author"].role,  # role is a string
                    content=c["proposal"]["content"],
                    created_at_ms=int(time.time() * 1000)
                ),
                checks=self._check_suite_to_proto(c["checks"]),
                score=c["score"],
                rank=idx + 2
            )
            for idx, c in enumerate(candidates)
        ]
        
        execution_id = self._generate_execution_id(task_id)
        
        return orchestrator_pb2.OrchestrateResponse(
            winner=proto_winner,
            candidates=proto_candidates,
            execution_id=execution_id,
            duration_ms=duration_ms,
            metadata=orchestrator_pb2.OrchestratorMetadata(
                orchestrator_version="0.1.0",
                timestamp_ms=int(time.time() * 1000),
                execution_id=execution_id
            )
        )

    def _check_suite_to_proto(self, check_suite) -> orchestrator_pb2.CheckSuite:
        """Convert CheckSuite to protobuf.
        
        Handles both object and dict formats (from to_dict()).
        """
        # Handle dict format (from to_dict())
        if isinstance(check_suite, dict):
            policy_data = check_suite.get("policy")
            lint_data = check_suite.get("lint")
            dryrun_data = check_suite.get("dryrun")
            
            policy = orchestrator_pb2.PolicyResult(
                passed=policy_data.get("ok", True) if policy_data else True,
                violations=list(policy_data.get("violations", [])) if policy_data else [],
                message="" 
            )
            
            lint_issues = lint_data.get("issues", []) if lint_data else []
            lint = orchestrator_pb2.LintResult(
                passed=lint_data.get("ok", True) if lint_data else True,
                error_count=len(lint_issues),
                warning_count=0,
                errors=list(lint_issues)
            )
            
            dryrun_errors = dryrun_data.get("errors", []) if dryrun_data else []
            dryrun = orchestrator_pb2.DryRunResult(
                passed=dryrun_data.get("ok", True) if dryrun_data else True,
                output="",
                exit_code=0 if dryrun_data.get("ok", True) else 1,
                message=dryrun_errors[0] if dryrun_errors else ""
            )
        else:
            # Handle object format (CheckSuiteResult)
            policy = orchestrator_pb2.PolicyResult(
                passed=check_suite.policy.ok if check_suite.policy else True,
                violations=list(check_suite.policy.violations) if check_suite.policy else [],
                message=""
            )
            
            lint_issues = check_suite.lint.issues if check_suite.lint else []
            lint = orchestrator_pb2.LintResult(
                passed=check_suite.lint.ok if check_suite.lint else True,
                error_count=len(lint_issues),
                warning_count=0,
                errors=list(lint_issues)
            )
            
            dryrun_errors = check_suite.dryrun.errors if check_suite.dryrun else []
            dryrun = orchestrator_pb2.DryRunResult(
                passed=check_suite.dryrun.ok if check_suite.dryrun else True,
                output="",
                exit_code=0 if (check_suite.dryrun and check_suite.dryrun.ok) else 1,
                message=dryrun_errors[0] if dryrun_errors else ""
            )
        
        all_passed = all([
            policy.passed,
            lint.passed,
            dryrun.passed
        ])
        
        return orchestrator_pb2.CheckSuite(
            policy=policy,
            lint=lint,
            dryrun=dryrun,
            all_passed=all_passed
        )

    def _generate_execution_id(self, task_desc: str) -> str:
        """Generate unique execution ID."""
        content = f"{task_desc}:{time.time()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


async def serve_async():
    """Start the gRPC server."""
    # Read configuration from environment
    port = os.getenv("GRPC_PORT", "50055")
    nats_url = os.getenv("NATS_URL", "nats://nats:4222")
    enable_nats = os.getenv("ENABLE_NATS", "true").lower() == "true"
    
    # Initialize config with default roles
    from swe_ai_fleet.orchestrator.config_module.role_config import RoleConfig
    
    roles = [
        RoleConfig(name="DEV", replicas=3, model_profile="default"),
        RoleConfig(name="QA", replicas=3, model_profile="default"),
        RoleConfig(name="ARCHITECT", replicas=3, model_profile="default"),
        RoleConfig(name="DEVOPS", replicas=3, model_profile="default"),
        RoleConfig(name="DATA", replicas=3, model_profile="default"),
    ]
    config = SystemConfig(roles=roles, require_human_approval=False)
    
    # Initialize NATS handler and consumers if enabled
    nats_handler = None
    planning_consumer = None
    context_consumer = None
    agent_response_consumer = None
    deliberation_collector = None
    
    if enable_nats:
        try:
            logger.info("Initializing NATS handler...")
            
            # Initialize DeliberationResultCollector first
            # TODO: Migrate to Pull Consumer (currently uses Push → causes "already bound" error)
            # deliberation_collector = DeliberationResultCollector(
            #     nats_url=nats_url,
            #     timeout_seconds=int(os.getenv("DELIBERATION_TIMEOUT", "300")),
            #     cleanup_after_seconds=int(os.getenv("DELIBERATION_CLEANUP", "3600")),
            # )
            deliberation_collector = None  # Disabled temporarily
            
            # Create servicer with result collector
            servicer_temp = OrchestratorServiceServicer(
                config=config,
                result_collector=deliberation_collector
            )
            
            # NOTE: Auto-initialization removed - use init_councils.py script instead
            # Councils are created via CreateCouncil RPC (called by init_councils.py Job)
            logger.info("⚠️  Councils must be initialized via CreateCouncil RPC (run init_councils.py)")
            
            # Initialize NATS handler
            nats_handler = OrchestratorNATSHandler(nats_url, servicer_temp)
            await nats_handler.connect()
            
            # Ensure streams exist
            logger.info("Ensuring NATS streams exist...")
            await ensure_streams(nats_handler.js)
            
            # Initialize consumers (AFTER councils are ready)
            logger.info("Initializing NATS consumers...")
            planning_consumer = OrchestratorPlanningConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                orchestrator_service=servicer_temp,
                nats_publisher=nats_handler.js,
            )
            await planning_consumer.start()
            
            context_consumer = OrchestratorContextConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                orchestrator_service=servicer_temp,
            )
            await context_consumer.start()
            
            agent_response_consumer = OrchestratorAgentResponseConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                orchestrator_service=servicer_temp,
                nats_publisher=nats_handler.js,
            )
            await agent_response_consumer.start()
            
            # Start DeliberationResultCollector
            # Disabled temporarily (needs Pull Consumer migration)
            # if deliberation_collector:
            #     await deliberation_collector.start()
            
            logger.info("✓ All NATS consumers started")
            
            # Use the servicer with NATS
            servicer = servicer_temp
            
        except Exception as e:
            logger.warning(f"NATS initialization failed: {e}. Continuing without NATS.")
            nats_handler = None
            planning_consumer = None
            context_consumer = None
            agent_response_consumer = None
            # Create servicer without NATS
            servicer = OrchestratorServiceServicer(config=config)
    else:
        # Create servicer without NATS
        servicer = OrchestratorServiceServicer(config=config)
        
        # Auto-initialize councils (same as NATS branch)
        auto_init_councils = os.getenv("AUTO_INIT_COUNCILS", "true").lower() == "true"
        
        if auto_init_councils:
            logger.info("🤖 Auto-initializing councils for all roles...")
            
            from swe_ai_fleet.orchestrator.config_module.vllm_config import VLLMConfig
            from swe_ai_fleet.orchestrator.domain.agents.agent_factory import AgentFactory
            from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate
            
            vllm_config = VLLMConfig.from_env()
            
            for role_config in config.roles:
                role_name = role_config.name
                num_agents = role_config.replicas
                
                try:
                    agents = []
                    for i in range(num_agents):
                        agent_id = f"agent-{role_name.lower()}-{i+1:03d}"
                        agent_config = vllm_config.to_agent_config(agent_id, role_name)
                        agent = AgentFactory.create_agent(**agent_config)
                        agents.append(agent)
                    
                    council = Deliberate(agents=agents, tooling=servicer.scoring, rounds=1)
                    servicer.councils[role_name] = council
                    servicer.council_agents[role_name] = agents
                    
                    logger.info(f"   ✅ Council {role_name}: {len(agents)} VLLM agents created")
                except Exception as e:
                    logger.error(f"   ❌ Failed to create council for {role_name}: {e}", exc_info=True)
            
            from swe_ai_fleet.orchestrator.usecases.dispatch_usecase import Orchestrate as OrchestrateUseCase
            servicer.orchestrator = OrchestrateUseCase(config=config, councils=servicer.councils, architect=servicer.architect)
            
            total_agents = sum(len(agents) for agents in servicer.council_agents.values())
            logger.info(f"✅ Auto-initialization complete: {total_agents} agents in {len(servicer.councils)} councils")
    
    # Create ASYNC gRPC server (supports background tasks)
    server = grpc.aio.server()
    
    # Add servicer
    orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(servicer, server)
    
    # Start server (async)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    
    logger.info(f"🚀 Orchestrator Service listening on port {port}")
    logger.info(f"   Active councils: {len(servicer.councils)}")
    if nats_handler:
        logger.info(f"   NATS: {nats_url} ✓")
    else:
        logger.info("   NATS: disabled")
    
    # Keep server running (event loop stays active for background tasks)
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator Service...")
        await server.stop(grace=5)
        
        # Stop consumers
        if planning_consumer:
            await planning_consumer.stop()
        if context_consumer:
            await context_consumer.stop()
        if agent_response_consumer:
            await agent_response_consumer.stop()
        if deliberation_collector:
            await deliberation_collector.stop()
        
        # Close NATS connection
        if nats_handler:
            await nats_handler.close()


def main():
    """Main entry point."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()

