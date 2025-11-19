"""
Context Service - gRPC Server with NATS support
Provides hydrated prompts based on role/phase using DDD bounded context.
"""

import asyncio
import hashlib
import logging
import os
import sys
import time

import grpc
import yaml

# Add project root to path to import swe_ai_fleet modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from datetime import UTC

from core.context.adapters.neo4j_command_store import Neo4jCommandStore
from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from core.context.application.session_rehydration_service import SessionRehydrationApplicationService
from core.context.context_assembler import build_prompt_blocks
from core.context.domain.neo4j_config import Neo4jConfig
from core.context.domain.rehydration_request import RehydrationRequest
from core.context.domain.scopes.prompt_scope_policy import PromptScopePolicy
from core.context.domain.services import (
    DataIndexer,
    DecisionSelector,
    ImpactCalculator,
    TokenBudgetCalculator,
)
from core.context.usecases.project_decision import ProjectDecisionUseCase
from core.context.usecases.project_plan_version import ProjectPlanVersionUseCase
from core.context.usecases.project_story import ProjectStoryUseCase
from core.context.usecases.project_task import ProjectTaskUseCase
from core.memory.adapters.redis_store import RedisStoreImpl
from core.reports.adapters.neo4j_decision_graph_read_adapter import Neo4jDecisionGraphReadAdapter

from services.context.consumers import OrchestrationEventsConsumer
from services.context.consumers.planning import (
    EpicCreatedConsumer,
    PlanApprovedConsumer,
    ProjectCreatedConsumer,
    StoryCreatedConsumer,
    StoryTransitionedConsumer,
    TaskCreatedConsumer,
)
from services.context.utils import detect_scopes
from services.context.gen import context_pb2, context_pb2_grpc
from services.context.infrastructure.mappers.rehydration_protobuf_mapper import (
    RehydrationProtobufMapper,
)
from services.context.nats_handler import ContextNATSHandler
from services.context.streams_init import ensure_streams

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def load_scopes_config(config_path: str | None = None) -> dict[str, dict[str, list[str]]]:
    """Load prompt scopes configuration from YAML file."""
    if config_path is None:
        # Default path relative to project root
        config_path = os.path.join(os.path.dirname(__file__), "../../config/prompt_scopes.yaml")

    try:
        with open(config_path) as f:
            data = yaml.safe_load(f)
            return data.get("phases", {})
    except FileNotFoundError:
        logger.warning(f"Scopes config not found at {config_path}, using empty config")
        return {}
    except Exception as e:
        logger.error(f"Error loading scopes config: {e}, using empty config")
        return {}


class ContextServiceServicer(context_pb2_grpc.ContextServiceServicer):
    """gRPC servicer for Context Service."""

    def __init__(
        self,
        neo4j_uri: str,
        neo4j_user: str,
        neo4j_password: str,
        redis_host: str,
        redis_port: int,
        nats_handler: ContextNATSHandler | None = None,
    ):
        """Initialize Context Service with dependencies."""
        logger.info("Initializing Context Service...")

        # Initialize adapters with injected configuration
        # Use same config for both query and command stores
        neo4j_config = Neo4jConfig(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database="neo4j",  # Default database
            max_retries=3,
            base_backoff_s=0.25,
        )

        # Create Neo4j query store
        neo4j_query_store = Neo4jQueryStore(config=neo4j_config)
        # Wrap with adapter that provides DecisionGraphReadPort methods
        self.graph_query = Neo4jDecisionGraphReadAdapter(store=neo4j_query_store)

        # Create Neo4j command store
        self.graph_command = Neo4jCommandStore(config=neo4j_config)

        # Redis adapter needs a PersistenceKvPort implementation
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        redis_store = RedisStoreImpl(url=redis_url)
        # The RedisPlanningReadAdapter expects the underlying redis.Redis client
        self.planning_read = RedisPlanningReadAdapter(client=redis_store.client)

        # Initialize domain services (pure logic, stateless)
        token_calculator = TokenBudgetCalculator()
        decision_selector = DecisionSelector()
        impact_calculator = ImpactCalculator()
        data_indexer = DataIndexer()

        # Initialize Application Service (orchestrator)
        self.rehydrator = SessionRehydrationApplicationService(
            planning_store=self.planning_read,
            graph_store=self.graph_query,
            token_calculator=token_calculator,
            decision_selector=decision_selector,
            impact_calculator=impact_calculator,
            data_indexer=data_indexer,
        )

        # Initialize scope policy with configuration
        scopes_cfg = load_scopes_config()
        self.policy = PromptScopePolicy(scopes_cfg)

        # Initialize use cases (application layer) with DI
        from core.context.application.usecases.process_context_change import (
            ProcessContextChangeUseCase,
        )
        from core.context.application.usecases.record_milestone import RecordMilestoneUseCase

        self.project_story_uc = ProjectStoryUseCase(writer=self.graph_command)
        self.project_task_uc = ProjectTaskUseCase(writer=self.graph_command)
        self.project_plan_version_uc = ProjectPlanVersionUseCase(writer=self.graph_command)
        self.project_decision_uc = ProjectDecisionUseCase(writer=self.graph_command)
        self.record_milestone_uc = RecordMilestoneUseCase(graph_command=self.graph_command)

        # Unified command handler for UpdateContext (CQRS pattern)
        self.process_context_change_uc = ProcessContextChangeUseCase(
            decision_uc=self.project_decision_uc,
            task_uc=self.project_task_uc,
            story_uc=self.project_story_uc,
            plan_uc=self.project_plan_version_uc,
            milestone_uc=self.record_milestone_uc,
        )

        logger.info("✓ Use cases initialized with DI (hexagonal architecture)")

        # NATS handler for async events
        self.nats_handler = nats_handler

        logger.info("Context Service initialized successfully")

    async def GetContext(self, request, context):
        """
        Get hydrated context for a specific story, role, and phase.
        Returns prompt blocks ready for agent consumption.
        """
        try:
            logger.info(
                f"GetContext request: story_id={request.story_id}, "
                f"role={request.role}, phase={request.phase}"
            )

            # Build prompt blocks using the context assembler (run in thread to avoid blocking)
            prompt_blocks = await asyncio.to_thread(
                build_prompt_blocks,
                rehydrator=self.rehydrator,
                policy=self.policy,
                case_id=request.story_id,
                role=request.role,
                phase=request.phase,
                current_subtask_id=request.subtask_id if request.subtask_id else None,
            )

            # Serialize prompt blocks to context string
            context_str = self._serialize_prompt_blocks(prompt_blocks)

            # Calculate token count (simple word count for now)
            token_count = len(context_str.split())

            # Detect applied scopes
            scopes = self._detect_scopes(prompt_blocks)

            # Generate version hash
            version = self._generate_version_hash(context_str)

            logger.info(
                f"GetContext response: story_id={request.story_id}, "
                f"tokens={token_count}, scopes={len(scopes)}"
            )

            return context_pb2.GetContextResponse(
                context=context_str,
                token_count=token_count,
                scopes=scopes,
                version=version,
                blocks=context_pb2.PromptBlocks(
                    system=prompt_blocks.system,
                    context=prompt_blocks.context,
                    tools=prompt_blocks.tools,
                ),
            )

        except Exception as e:
            logger.error(f"GetContext error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get context: {str(e)}")
            return context_pb2.GetContextResponse()

    async def UpdateContext(self, request, context):
        """
        Update context with changes from agent execution.
        Records context changes and returns versioning info.
        """
        try:
            logger.info(
                f"UpdateContext request: story_id={request.story_id}, "
                f"task_id={request.task_id}, changes={len(request.changes)}"
            )

            warnings = []

            # Process each context change via unified use case (hexagonal architecture)
            for change in request.changes:
                logger.info(
                    f"Processing change: {change.operation} "
                    f"{change.entity_type}/{change.entity_id}"
                )

                try:
                    # Use injected command handler (application layer)
                    await self.process_context_change_uc.execute(change, request.story_id)
                except Exception as e:
                    warning = f"Failed to process {change.entity_id}: {str(e)}"
                    warnings.append(warning)
                    logger.warning(warning)

            # Generate new version
            version = self._generate_new_version(request.story_id)
            hash_value = self._generate_context_hash(request.story_id, version)

            # Publish async event if NATS is available
            if self.nats_handler:
                await self.nats_handler.publish_context_updated(
                    request.story_id, version
                )

            logger.info(
                f"UpdateContext response: story_id={request.story_id}, "
                f"version={version}, warnings={len(warnings)}"
            )

            return context_pb2.UpdateContextResponse(
                version=version,
                hash=hash_value,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"UpdateContext error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to update context: {str(e)}")
            return context_pb2.UpdateContextResponse()

    async def RehydrateSession(self, request, context):
        """
        Rehydrate session context from persistent storage.
        Builds complete context packs for specified roles.
        """
        try:
            logger.info(
                f"RehydrateSession request: case_id={request.case_id}, "
                f"roles={request.roles}"
            )

            # Build rehydration request
            rehydration_req = RehydrationRequest(
                case_id=request.case_id,
                roles=list(request.roles),
                include_timeline=request.include_timeline,
                include_summaries=request.include_summaries,
                timeline_events=request.timeline_events if request.timeline_events > 0 else 50,
                persist_handoff_bundle=request.persist_bundle,
                ttl_seconds=request.ttl_seconds if request.ttl_seconds > 0 else 3600,
            )

            # Execute rehydration
            bundle = self.rehydrator.build(rehydration_req)

            # Convert to protobuf response
            response = self._bundle_to_proto(bundle)

            logger.info(
                f"RehydrateSession response: case_id={request.case_id}, "
                f"roles={len(bundle.packs)}"
            )

            return response

        except Exception as e:
            logger.error(f"RehydrateSession error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to rehydrate session: {str(e)}")
            return context_pb2.RehydrateSessionResponse()

    async def ValidateScope(self, request, context):
        """
        Validate if provided scopes are allowed for the given role and phase.
        """
        try:
            logger.info(
                f"ValidateScope request: role={request.role}, "
                f"phase={request.phase}, scopes={len(request.provided_scopes)}"
            )

            # Check scopes using policy
            scope_check = self.policy.check(
                phase=request.phase,
                role=request.role,
                provided_scopes=set(request.provided_scopes),
            )

            response = context_pb2.ValidateScopeResponse(
                allowed=scope_check.allowed,
                missing=list(scope_check.missing),
                extra=list(scope_check.extra),
                reason=self._format_scope_reason(scope_check),
            )

            logger.info(
                f"ValidateScope response: allowed={scope_check.allowed}"
            )

            return response

        except Exception as e:
            logger.error(f"ValidateScope error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to validate scope: {str(e)}")
            return context_pb2.ValidateScopeResponse(allowed=False, reason=str(e))

    async def CreateStory(self, request, context):
        """Create a new user story in Neo4j and Valkey."""
        try:
            logger.info(f"CreateStory: story_id={request.story_id}, title={request.title}")

            from datetime import datetime

            now_iso = datetime.now(UTC).isoformat()
            initial_phase = request.initial_phase or "DESIGN"

            # Create ProjectCase node in Neo4j with story_id property
            # This runs in thread to avoid blocking async event loop
            await asyncio.to_thread(
                self.graph_command.upsert_entity,
                "ProjectCase",
                request.story_id,
                {
                    "story_id": request.story_id,
                    "title": request.title,
                    "description": request.description,
                    "status": "ACTIVE",
                    "current_phase": initial_phase,
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
            )

            logger.info(f"✓ Created ProjectCase node in Neo4j: {request.story_id}")

            # Store story context in Valkey/Redis for fast access
            story_key = f"story:{request.story_id}"
            story_data = {
                "story_id": request.story_id,
                "title": request.title,
                "description": request.description,
                "current_phase": initial_phase,
                "status": "ACTIVE",
                "created_at": now_iso,
                "updated_at": now_iso
            }

            await asyncio.to_thread(
                self.planning_read.client.hset,
                story_key,
                mapping=story_data
            )

            logger.info(f"✓ Stored story context in Valkey: {story_key}")

            return context_pb2.CreateStoryResponse(
                context_id=f"ctx-{request.story_id}",
                story_id=request.story_id,
                current_phase=initial_phase
            )

        except Exception as e:
            logger.error(f"CreateStory error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return context_pb2.CreateStoryResponse()

    async def CreateTask(self, request, context):
        """Create a new task/subtask for a story in Neo4j and Valkey."""
        try:
            logger.info(
                f"CreateTask: task_id={request.task_id}, "
                f"story={request.story_id}, role={request.role}"
            )

            from datetime import datetime

            now_iso = datetime.now(UTC).isoformat()

            # Create Task node in Neo4j
            await asyncio.to_thread(
                self.graph_command.upsert_entity,
                "Task",
                request.task_id,
                {
                    "task_id": request.task_id,
                    "story_id": request.story_id,
                    "title": request.title,
                    "description": request.description,
                    "role": request.role,
                    "priority": request.priority,
                    "estimated_hours": request.estimated_hours,
                    "status": "PENDING",
                    "created_at": now_iso,
                    "updated_at": now_iso
                }
            )

            # Create BELONGS_TO relationship: Task -> Story
            await asyncio.to_thread(
                self.graph_command.relate,
                src_id=request.task_id,
                rel_type="BELONGS_TO",
                dst_id=request.story_id,
                src_labels=["Task"],
                dst_labels=["ProjectCase"],
                properties={"created_at": now_iso}
            )

            # Create DEPENDS_ON relationships if dependencies exist
            for dep_task_id in request.dependencies:
                await asyncio.to_thread(
                    self.graph_command.relate,
                    src_id=request.task_id,
                    rel_type="DEPENDS_ON",
                    dst_id=dep_task_id,
                    src_labels=["Task"],
                    dst_labels=["Task"],
                    properties={"created_at": now_iso}
                )

            logger.info(f"✓ Created Task node in Neo4j: {request.task_id}")

            # Store task context in Valkey for fast access
            task_key = f"task:{request.task_id}"
            task_data = {
                "task_id": request.task_id,
                "story_id": request.story_id,
                "title": request.title,
                "description": request.description,
                "role": request.role,
                "priority": str(request.priority),
                "estimated_hours": str(request.estimated_hours),
                "status": "PENDING",
                "dependencies": ",".join(request.dependencies) if request.dependencies else "",
                "created_at": now_iso,
                "updated_at": now_iso
            }

            await asyncio.to_thread(
                self.planning_read.client.hset,
                task_key,
                mapping=task_data
            )

            logger.info(f"✓ Stored task context in Valkey: {task_key}")

            return context_pb2.CreateTaskResponse(
                task_id=request.task_id,
                story_id=request.story_id,
                status="PENDING"
            )

        except Exception as e:
            logger.error(f"CreateTask error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return context_pb2.CreateTaskResponse()

    async def AddProjectDecision(self, request, context):
        """Add a project decision to Neo4j."""
        try:
            logger.info(f"AddProjectDecision: story={request.story_id}, type={request.decision_type}")

            import uuid
            from datetime import datetime

            # Generate decision ID
            decision_id = f"DEC-{request.decision_type[:4]}-{uuid.uuid4().hex[:6].upper()}"

            # Extract metadata
            made_by_role = request.metadata.get("role", "UNKNOWN") if request.metadata else "UNKNOWN"
            made_by_agent = request.metadata.get("winner", "UNKNOWN") if request.metadata else "UNKNOWN"

            # Use injected use case (DI - hexagonal architecture)
            decision_use_case = self.project_decision_uc

            decision_use_case.execute({
                "decision_id": decision_id,
                "case_id": request.story_id,
                "decision_type": request.decision_type,
                "title": request.title,
                "rationale": request.rationale,
                "made_by_role": made_by_role,
                "made_by_agent": made_by_agent,
                "content": request.rationale,
                "alternatives_considered": request.alternatives_considered,
                "created_at": datetime.now(UTC).isoformat()
            })

            logger.info(f"✓ Created ProjectDecision: {decision_id}")

            return context_pb2.AddProjectDecisionResponse(
                decision_id=decision_id
            )

        except Exception as e:
            logger.error(f"AddProjectDecision error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return context_pb2.AddProjectDecisionResponse()

    async def TransitionPhase(self, request, context):
        """Record a phase transition in Neo4j."""
        try:
            logger.info(f"TransitionPhase: story={request.story_id}, {request.from_phase}→{request.to_phase}")

            from datetime import datetime

            # Create phase transition in Neo4j
            query = """
            MATCH (s:ProjectCase {story_id: $story_id})
            CREATE (p:PhaseTransition {
                story_id: $story_id,
                from_phase: $from_phase,
                to_phase: $to_phase,
                rationale: $rationale,
                timestamp: $transitioned_at,
                transitioned_at: $transitioned_at
            })
            CREATE (s)-[:HAS_PHASE]->(p)
            SET s.current_phase = $to_phase,
                s.updated_at = $transitioned_at
            RETURN p.transitioned_at as when
            """

            now_iso = datetime.now(UTC).isoformat()

            self.graph_command.execute_write(query, {
                "story_id": request.story_id,
                "from_phase": request.from_phase,
                "to_phase": request.to_phase,
                "rationale": request.rationale,
                "transitioned_at": now_iso
            })

            logger.info(f"✓ Phase transition: {request.from_phase} → {request.to_phase}")

            return context_pb2.TransitionPhaseResponse(
                story_id=request.story_id,
                current_phase=request.to_phase,
                transitioned_at=now_iso
            )

        except Exception as e:
            logger.error(f"TransitionPhase error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return context_pb2.TransitionPhaseResponse()

    # Helper methods

    def _serialize_prompt_blocks(self, prompt_blocks) -> str:
        """Serialize PromptBlocks to a single context string."""
        sections = []

        if prompt_blocks.system:
            sections.append(f"# System\n\n{prompt_blocks.system}")

        if prompt_blocks.context:
            sections.append(f"# Context\n\n{prompt_blocks.context}")

        if prompt_blocks.tools:
            sections.append(f"# Tools\n\n{prompt_blocks.tools}")

        return "\n\n---\n\n".join(sections)

    def _detect_scopes(self, prompt_blocks) -> list[str]:
        """Detect which scopes are present in the prompt blocks based on content sections."""
        return detect_scopes(prompt_blocks)

    def _generate_version_hash(self, content: str) -> str:
        """Generate a version hash for the context."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _handle_nats_publish_error(self, task):
        """Handle errors from async NATS publish tasks."""
        try:
            task.result()  # This will raise if the task failed
        except Exception as e:
            logger.error(f"NATS publish failed: {e}", exc_info=True)

    def _generate_new_version(self, story_id: str) -> int:
        """Generate new version number for context."""
        # Use timestamp-based versioning until proper version tracking is implemented
        # This ensures monotonically increasing versions
        return int(time.time())

    def _generate_context_hash(self, story_id: str, version: int) -> str:
        """Generate hash for context verification."""
        content = f"{story_id}:{version}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _bundle_to_proto(self, bundle) -> context_pb2.RehydrateSessionResponse:
        """Convert RehydrationBundle to protobuf response.

        Delegates to mapper (infrastructure layer).
        """
        return RehydrationProtobufMapper.bundle_to_response(bundle)

    def _format_scope_reason(self, scope_check) -> str:
        """Format scope check result into human-readable reason."""
        if scope_check.allowed:
            return "All scopes are allowed"

        parts = []
        if scope_check.missing:
            parts.append(f"Missing required scopes: {', '.join(scope_check.missing)}")
        if scope_check.extra:
            parts.append(f"Extra scopes not allowed: {', '.join(scope_check.extra)}")

        return "; ".join(parts)


async def serve_async():
    """Start the gRPC server with async NATS support."""
    # Read configuration from environment
    port = os.getenv("GRPC_PORT", "50054")
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
        raise ValueError("NEO4J_PASSWORD environment variable must be set")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    nats_url = os.getenv("NATS_URL", "nats://nats:4222")
    enable_nats = os.getenv("ENABLE_NATS", "true").lower() == "true"

    # Initialize NATS handler and consumers if enabled
    nats_handler = None
    planning_consumers = []  # List of planning consumers
    orchestration_consumer = None
    redis_store = None
    graph_command = None

    if enable_nats:
        try:
            logger.info("Initializing NATS handler...")
            # We'll create servicer first, then pass it to NATS handler
            nats_handler = ContextNATSHandler(nats_url, None)
            await nats_handler.connect()

            # Ensure streams exist
            logger.info("Ensuring NATS streams exist...")
            await ensure_streams(nats_handler.js)

            # Subscribe to context service RPCs
            await nats_handler.subscribe()

            # Initialize dependencies for consumers
            logger.info("Initializing consumer dependencies...")
            redis_url = f"redis://{redis_host}:{redis_port}/0"
            redis_store = RedisStoreImpl(url=redis_url)

            neo4j_config_command = Neo4jConfig(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
                database="neo4j",
                max_retries=3,
                base_backoff_s=0.25,
            )
            graph_command = Neo4jCommandStore(config=neo4j_config_command)

            # Initialize planning consumers with HEXAGONAL + DDD architecture
            logger.info("Initializing Planning event consumers...")

            # Create use cases (application layer) with Port injection
            from core.context.application.usecases import (
                HandleStoryPhaseTransitionUseCase,
                RecordPlanApprovalUseCase,
                SynchronizeEpicFromPlanningUseCase,
                SynchronizeProjectFromPlanningUseCase,
                SynchronizeStoryFromPlanningUseCase,
                SynchronizeTaskFromPlanningUseCase,
            )

            project_sync_uc = SynchronizeProjectFromPlanningUseCase(graph_command=graph_command)
            epic_sync_uc = SynchronizeEpicFromPlanningUseCase(graph_command=graph_command)
            story_sync_uc = SynchronizeStoryFromPlanningUseCase(graph_command=graph_command)
            task_sync_uc = SynchronizeTaskFromPlanningUseCase(graph_command=graph_command)
            plan_approval_uc = RecordPlanApprovalUseCase(graph_command=graph_command)
            story_transition_uc = HandleStoryPhaseTransitionUseCase(
                graph_command=graph_command,
                cache_service=redis_store.client,  # ✅ Use case needs cache for invalidation
            )

            logger.info("✓ Use cases initialized (hexagonal architecture)")

            # Consumer 1: Story transitions (hexagonal - use case injection with cache)
            story_transitioned = StoryTransitionedConsumer(
                js=nats_handler.js,
                use_case=story_transition_uc,  # ✅ Use case DI (hexagonal)
            )
            await story_transitioned.start()
            planning_consumers.append(story_transitioned)

            # Consumer 2: Plan approvals (hexagonal - use case injection)
            plan_approved = PlanApprovedConsumer(
                js=nats_handler.js,
                use_case=plan_approval_uc,  # ✅ Use case DI (hexagonal)
            )
            await plan_approved.start()
            planning_consumers.append(plan_approved)

            # Consumer 3: Project creation (hexagonal - use case injection)
            project_created = ProjectCreatedConsumer(
                js=nats_handler.js,
                use_case=project_sync_uc,  # ✅ Use case DI (hexagonal)
            )
            await project_created.start()
            planning_consumers.append(project_created)

            # Consumer 4: Epic creation (hexagonal - use case injection)
            epic_created = EpicCreatedConsumer(
                js=nats_handler.js,
                use_case=epic_sync_uc,  # ✅ Use case DI (hexagonal)
            )
            await epic_created.start()
            planning_consumers.append(epic_created)

            # Consumer 5: Story creation (hexagonal - use case injection)
            story_created = StoryCreatedConsumer(
                js=nats_handler.js,
                use_case=story_sync_uc,  # ✅ Use case DI (hexagonal)
            )
            await story_created.start()
            planning_consumers.append(story_created)

            # Consumer 6: Task creation (hexagonal - use case injection)
            task_created = TaskCreatedConsumer(
                js=nats_handler.js,
                use_case=task_sync_uc,  # ✅ Use case DI (hexagonal)
            )
            await task_created.start()
            planning_consumers.append(task_created)

            logger.info(f"✓ {len(planning_consumers)} Planning consumers started (hexagonal + DDD)")

            # Initialize orchestration consumer
            orchestration_consumer = OrchestrationEventsConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                graph_command=graph_command,
                nats_publisher=nats_handler,
            )
            await orchestration_consumer.start()

            logger.info("✓ All NATS consumers started successfully")

        except Exception as e:
            logger.warning(f"NATS initialization failed: {e}. Continuing without NATS.")
            nats_handler = None
            planning_consumers = []
            orchestration_consumer = None

    # Create ASYNC gRPC server (supports background tasks)
    server = grpc.aio.server()

    # Add servicer
    servicer = ContextServiceServicer(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        redis_host=redis_host,
        redis_port=redis_port,
        nats_handler=nats_handler,
    )

    # Update NATS handler with servicer reference
    if nats_handler:
        nats_handler.context_service = servicer

    context_pb2_grpc.add_ContextServiceServicer_to_server(servicer, server)

    # Start server (async)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()

    logger.info(f"🚀 Context Service listening on port {port}")
    logger.info(f"   Neo4j URI: {neo4j_uri}")
    logger.info(f"   Redis: {redis_host}:{redis_port}")
    if nats_handler:
        logger.info(f"   NATS: {nats_url} ✓")
    else:
        logger.info("   NATS: disabled")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down Context Service...")
        await server.stop(grace=5)

        # Stop consumers
        for consumer in planning_consumers:
            await consumer.stop()
        if orchestration_consumer:
            await orchestration_consumer.stop()

        # Close NATS connection
        if nats_handler:
            await nats_handler.close()


def serve():
    """Entry point for the server."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    serve()

