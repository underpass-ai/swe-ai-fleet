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

from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
from swe_ai_fleet.orchestrator.config_module.system_config import SystemConfig
from swe_ai_fleet.orchestrator.domain.agents.agent import Agent
from swe_ai_fleet.orchestrator.domain.agents.role import Role
from swe_ai_fleet.orchestrator.domain.check_results.services.scoring import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate
from swe_ai_fleet.orchestrator.usecases.dispatch_usecase import Orchestrate
from swe_ai_fleet.orchestrator.domain.agents.services.architect_selector_service import ArchitectSelectorService

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
        
        # Initialize councils for each role
        self.councils = {}
        for role_name in ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]:
            agents = self._create_agents_for_role(role_name, num_agents=3)
            self.councils[role_name] = Deliberate(
                agents=agents,
                tooling=self.scoring,
                rounds=1
            )
        
        # Initialize architect selector
        self.architect = ArchitectSelectorService()
        
        # Initialize orchestrator
        self.orchestrator = Orchestrate(
            config=self.config,
            councils=self.councils,
            architect=self.architect
        )
        
        logger.info("Orchestrator Service initialized successfully")

    def _create_agents_for_role(self, role_name: str, num_agents: int = 3) -> list[Agent]:
        """Create agents for a specific role."""
        agents = []
        for i in range(num_agents):
            agent = Agent(
                agent_id=f"{role_name}-agent-{i}",
                role=Role(role_name),
                config=self.config
            )
            agents.append(agent)
        return agents

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
            
            # Get or create council for role
            council = self.councils.get(request.role)
            if not council:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unknown role: {request.role}")
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

    def _proto_to_constraints(self, proto_constraints) -> TaskConstraints:
        """Convert protobuf constraints to domain TaskConstraints."""
        return TaskConstraints(
            rubric=proto_constraints.rubric,
            requirements=list(proto_constraints.requirements),
            max_iterations=proto_constraints.max_iterations or 10,
            timeout_seconds=proto_constraints.timeout_seconds or 300
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
    
    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    
    # Add servicer
    servicer = OrchestratorServiceServicer(config=config)
    orchestrator_pb2_grpc.add_OrchestratorServiceServicer_to_server(servicer, server)
    
    # Start server
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    
    logger.info(f"🚀 Orchestrator Service listening on port {port}")
    logger.info(f"   Active councils: {len(servicer.councils)}")
    
    # Keep server running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down Orchestrator Service...")
        server.stop(grace=5)


def main():
    """Main entry point."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    main()

