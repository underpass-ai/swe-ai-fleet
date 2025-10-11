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
from concurrent import futures

import grpc

# Add project root to path to import swe_ai_fleet modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.context.streams_init import ensure_streams
from services.orchestrator.consumers import (
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class OrchestratorServiceServicer(orchestrator_pb2_grpc.OrchestratorServiceServicer):
    """gRPC servicer for Orchestrator Service."""

    def __init__(self, config: SystemConfig):
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
        
        # Initialize architect selector with default architect
        from swe_ai_fleet.orchestrator.domain.agents.architect_agent import ArchitectAgent
        self.architect = ArchitectSelectorService(architect=ArchitectAgent())
        
        # Orchestrator will be initialized lazily when councils are available
        self.orchestrator = None
        
        logger.info("Orchestrator Service initialized successfully")
        logger.warning("No agents configured - councils are empty. Agents must be registered separately.")

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

    def Deliberate(self, request, context):
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

    def Orchestrate(self, request, context):
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

    def GetStatus(self, request, context):
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
    
    def StreamDeliberation(self, request, context):
        """Stream deliberation progress.
        
        TODO: Implement streaming updates during deliberation.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Streaming deliberation not yet implemented")
        # Return empty stream (proper generator pattern)
        return iter(())  # Empty generator

    def RegisterAgent(self, request, context):
        """Register an agent in a council.
        
        TODO: Implement agent registration via AgentFactory or external registry.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Agent registration not yet implemented")
        return orchestrator_pb2.RegisterAgentResponse(success=False, message="Not implemented")

    def CreateCouncil(self, request, context):
        """Create a council for a role.
        
        TODO: Implement dynamic council creation.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Council creation not yet implemented")
        return orchestrator_pb2.CreateCouncilResponse()

    def ListCouncils(self, request, context):
        """List all active councils.
        
        This RPC is functional - returns current council state.
        """
        try:
            councils = []
            for role, _council in self.councils.items():
                council_info = orchestrator_pb2.CouncilInfo(
                    council_id=f"council-{role.lower()}",
                    role=role,
                    num_agents=0,
                    status="idle"
                )
                councils.append(council_info)
            
            return orchestrator_pb2.ListCouncilsResponse(councils=councils)
        except Exception as e:
            logger.error(f"ListCouncils error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            return orchestrator_pb2.ListCouncilsResponse()

    def UnregisterAgent(self, request, context):
        """Unregister an agent from a council.
        
        TODO: Implement agent unregistration.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Agent unregistration not yet implemented")
        return orchestrator_pb2.UnregisterAgentResponse(success=False, message="Not implemented")

    def ProcessPlanningEvent(self, request, context):
        """Process a planning event from NATS.
        
        TODO: Implement event processing logic.
        This should be called internally by NATS consumer, not directly.
        """
        logger.info(f"Planning event: {request.event_type} for case {request.case_id}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Event processing not yet implemented - needs NATS integration")
        return orchestrator_pb2.PlanningEventResponse(processed=False)

    def DeriveSubtasks(self, request, context):
        """Derive atomic subtasks from a case/plan.
        
        TODO: Implement task derivation logic.
        Requires integration with Planning and Context services.
        """
        logger.info(f"Derive subtasks: case={request.case_id}, roles={request.roles}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Subtask derivation not yet implemented")
        return orchestrator_pb2.DeriveSubtasksResponse(tasks=[], total_tasks=0)

    def GetTaskContext(self, request, context):
        """Get hydrated context for a task.
        
        TODO: Implement Context Service integration.
        Should call Context Service at context:50054.
        """
        logger.info(f"Get context: task={request.task_id}, role={request.role}")
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("Context integration not yet implemented")
        return orchestrator_pb2.GetTaskContextResponse(context_text="", token_count=0)

    def GetMetrics(self, request, context):
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
                    author_role=result.proposal.author.role.name,
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
        
        proto_winner = orchestrator_pb2.DeliberationResult(
            proposal=orchestrator_pb2.Proposal(
                author_id=winner.proposal.author.agent_id,
                author_role=winner.proposal.author.role.name,
                content=winner.proposal.content,
                created_at_ms=int(time.time() * 1000)
            ),
            checks=self._check_suite_to_proto(winner.checks),
            score=winner.score,
            rank=1
        )
        
        proto_candidates = [
            orchestrator_pb2.DeliberationResult(
                proposal=orchestrator_pb2.Proposal(
                    author_id=c.proposal.author.agent_id,
                    author_role=c.proposal.author.role.name,
                    content=c.proposal.content,
                    created_at_ms=int(time.time() * 1000)
                ),
                checks=self._check_suite_to_proto(c.checks),
                score=c.score,
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
        """Convert CheckSuite to protobuf."""
        policy = orchestrator_pb2.PolicyResult(
            passed=check_suite.policy.passed if check_suite.policy else True,
            violations=list(check_suite.policy.violations) if check_suite.policy else [],
            message=check_suite.policy.message if check_suite.policy else ""
        )
        
        lint = orchestrator_pb2.LintResult(
            passed=check_suite.lint.passed if check_suite.lint else True,
            error_count=check_suite.lint.error_count if check_suite.lint else 0,
            warning_count=check_suite.lint.warning_count if check_suite.lint else 0,
            errors=list(check_suite.lint.errors) if check_suite.lint else []
        )
        
        dryrun = orchestrator_pb2.DryRunResult(
            passed=check_suite.dryrun.passed if check_suite.dryrun else True,
            output=check_suite.dryrun.output if check_suite.dryrun else "",
            exit_code=check_suite.dryrun.exit_code if check_suite.dryrun else 0,
            message=check_suite.dryrun.message if check_suite.dryrun else ""
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
    
    if enable_nats:
        try:
            logger.info("Initializing NATS handler...")
            # Create servicer first (needed by consumers)
            servicer_temp = OrchestratorServiceServicer(config=config)
            
            # Initialize NATS handler
            nats_handler = OrchestratorNATSHandler(nats_url, servicer_temp)
            await nats_handler.connect()
            
            # Ensure streams exist
            logger.info("Ensuring NATS streams exist...")
            await ensure_streams(nats_handler.js)
            
            # Initialize consumers
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
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add servicer
    orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(servicer, server)
    
    # Start server
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    
    logger.info(f"🚀 Orchestrator Service listening on port {port}")
    logger.info(f"   Active councils: {len(servicer.councils)}")
    if nats_handler:
        logger.info(f"   NATS: {nats_url} ✓")
    else:
        logger.info("   NATS: disabled")
    
    # Keep server running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator Service...")
        server.stop(grace=5)
        
        # Stop consumers
        if planning_consumer:
            await planning_consumer.stop()
        if context_consumer:
            await context_consumer.stop()
        if agent_response_consumer:
            await agent_response_consumer.stop()
        
        # Close NATS connection
        if nats_handler:
            await nats_handler.close()


def main():
    """Main entry point."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()

