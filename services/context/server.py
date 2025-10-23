"""
Context Service - gRPC Server with NATS support
Provides hydrated prompts based on role/phase using DDD bounded context.
"""

import asyncio
import hashlib
import json
import logging
import os
import sys
import time

import grpc
import yaml

# Add project root to path to import swe_ai_fleet modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.context.consumers import OrchestrationEventsConsumer, PlanningEventsConsumer
from services.context.gen import context_pb2, context_pb2_grpc
from services.context.nats_handler import ContextNATSHandler
from services.context.streams_init import ensure_streams
from core.context.adapters.neo4j_command_store import Neo4jCommandStore
from core.context.adapters.neo4j_command_store import Neo4jConfig as Neo4jConfigCommand
from core.context.adapters.neo4j_query_store import Neo4jConfig as Neo4jConfigQuery
from core.context.adapters.neo4j_query_store import Neo4jQueryStore
from core.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from core.context.context_assembler import build_prompt_blocks
from core.context.domain.scopes.prompt_scope_policy import PromptScopePolicy
from core.context.session_rehydration import (
    RehydrationRequest,
    SessionRehydrationUseCase,
)
from core.context.usecases.project_case import ProjectCaseUseCase
from core.context.usecases.project_plan_version import ProjectPlanVersionUseCase
from core.context.usecases.project_subtask import ProjectSubtaskUseCase
from core.memory.adapters.redis_store import RedisStoreImpl
from core.reports.adapters.neo4j_decision_graph_read_adapter import Neo4jDecisionGraphReadAdapter

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

        # Initialize adapters with proper configs
        neo4j_config_query = Neo4jConfigQuery(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        neo4j_config_command = Neo4jConfigCommand(uri=neo4j_uri, user=neo4j_user, password=neo4j_password)
        
        # Create Neo4j query store
        neo4j_query_store = Neo4jQueryStore(config=neo4j_config_query)
        # Wrap with adapter that provides DecisionGraphReadPort methods
        self.graph_query = Neo4jDecisionGraphReadAdapter(store=neo4j_query_store)
        self.graph_command = Neo4jCommandStore(cfg=neo4j_config_command)
        
        # Redis adapter needs a PersistenceKvPort implementation
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        redis_store = RedisStoreImpl(url=redis_url)
        # The RedisPlanningReadAdapter expects the underlying redis.Redis client
        self.planning_read = RedisPlanningReadAdapter(client=redis_store.client)

        # Initialize use cases
        self.rehydrator = SessionRehydrationUseCase(
            planning_store=self.planning_read,
            graph_store=self.graph_query,
        )

        # Initialize scope policy with configuration
        scopes_cfg = load_scopes_config()
        self.policy = PromptScopePolicy(scopes_cfg)

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

            # Process each context change (run in thread pool)
            for change in request.changes:
                logger.info(
                    f"Processing change: {change.operation} "
                    f"{change.entity_type}/{change.entity_id}"
                )

                try:
                    await asyncio.to_thread(
                        self._process_context_change, change, request.story_id
                    )
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
    
    async def InitializeProjectContext(self, request, context):
        """Initialize a new project case in Neo4j."""
        try:
            logger.info(f"InitializeProjectContext: story_id={request.story_id}, title={request.title}")
            
            from datetime import datetime, timezone
            from core.context.usecases.project_case import ProjectCaseUseCase
            
            # Create case in Neo4j
            case_use_case = ProjectCaseUseCase(writer=self.graph_command)
            
            now_iso = datetime.now(timezone.utc).isoformat()
            case_use_case.execute({
                "case_id": request.story_id,
                "title": request.title,
                "description": request.description,
                "status": "ACTIVE",
                "current_phase": request.initial_phase or "DESIGN",
                "created_at": now_iso,
                "updated_at": now_iso
            })
            
            logger.info(f"✓ Created ProjectCase: {request.story_id}")
            
            return context_pb2.InitializeProjectContextResponse(
                context_id=f"ctx-{request.story_id}",
                story_id=request.story_id,
                current_phase=request.initial_phase or "DESIGN"
            )
            
        except Exception as e:
            logger.error(f"InitializeProjectContext error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return context_pb2.InitializeProjectContextResponse()
    
    async def AddProjectDecision(self, request, context):
        """Add a project decision to Neo4j."""
        try:
            logger.info(f"AddProjectDecision: story={request.story_id}, type={request.decision_type}")
            
            from datetime import datetime, timezone
            import uuid
            from core.context.usecases.project_decision import ProjectDecisionUseCase
            
            # Generate decision ID
            decision_id = f"DEC-{request.decision_type[:4]}-{uuid.uuid4().hex[:6].upper()}"
            
            # Extract metadata
            made_by_role = request.metadata.get("role", "UNKNOWN") if request.metadata else "UNKNOWN"
            made_by_agent = request.metadata.get("winner", "UNKNOWN") if request.metadata else "UNKNOWN"
            
            # Create decision in Neo4j
            decision_use_case = ProjectDecisionUseCase(writer=self.graph_command)
            
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
                "created_at": datetime.now(timezone.utc).isoformat()
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
            
            from datetime import datetime, timezone
            
            # Create phase transition in Neo4j
            query = """
            MATCH (s:ProjectCase {story_id: $story_id})
            CREATE (p:PhaseTransition {
                from_phase: $from_phase,
                to_phase: $to_phase,
                rationale: $rationale,
                transitioned_at: $transitioned_at
            })
            CREATE (s)-[:HAS_PHASE]->(p)
            SET s.current_phase = $to_phase,
                s.updated_at = $transitioned_at
            RETURN p.transitioned_at as when
            """
            
            now_iso = datetime.now(timezone.utc).isoformat()
            
            result = self.graph_command.execute_write(query, {
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
        scopes = []
        
        # Analyze content to determine which scopes were applied
        content = prompt_blocks.context
        
        if content:
            # Check for case header elements
            if "Case:" in content or "Status:" in content:
                scopes.append("CASE_HEADER")
            
            # Check for plan header elements  
            if "Plan:" in content or "Total Subtasks:" in content:
                scopes.append("PLAN_HEADER")
            
            # Check for subtasks section
            if "Subtasks:" in content or "Your Subtasks:" in content:
                if "No subtasks" not in content:
                    scopes.append("SUBTASKS_ROLE")
            
            # Check for decisions section
            if "Decisions:" in content or "Recent Decisions:" in content:
                if "No relevant decisions" not in content:
                    scopes.append("DECISIONS_RELEVANT_ROLE")
            
            # Check for dependencies
            if "Dependencies:" in content or "Decision Dependencies:" in content:
                scopes.append("DEPS_RELEVANT")
            
            # Check for milestones
            if "Milestones:" in content or "Recent Milestones:" in content:
                if "No recent milestones" not in content:
                    scopes.append("MILESTONES")
        
        return scopes

    def _generate_version_hash(self, content: str) -> str:
        """Generate a version hash for the context."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _handle_nats_publish_error(self, task):
        """Handle errors from async NATS publish tasks."""
        try:
            task.result()  # This will raise if the task failed
        except Exception as e:
            logger.error(f"NATS publish failed: {e}", exc_info=True)

    def _process_context_change(self, change, story_id: str):
        """Process a single context change and persist to graph store."""
        # Validate required fields
        if not change.operation or not change.entity_type or not change.entity_id:
            raise ValueError("Missing required fields in context change")
        
        logger.info(
            f"Processing context change: story={story_id}, "
            f"operation={change.operation}, entity={change.entity_type}/{change.entity_id}"
        )
        
        # Parse payload if provided
        payload_data = {}
        if change.payload:
            try:
                payload_data = json.loads(change.payload)
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON payload in context change: {e}")
        
        # Persist to graph command store based on entity type
        try:
            if change.entity_type == "DECISION":
                self._persist_decision_change(story_id, change, payload_data)
            elif change.entity_type == "SUBTASK":
                self._persist_subtask_change(story_id, change, payload_data)
            elif change.entity_type == "MILESTONE":
                self._persist_milestone_change(story_id, change, payload_data)
            elif change.entity_type == "CASE":
                self._persist_case_change(story_id, change, payload_data)
            elif change.entity_type == "PLAN":
                self._persist_plan_change(story_id, change, payload_data)
            else:
                logger.warning(f"Unknown entity type: {change.entity_type}")
        except Exception as e:
            # Log but don't fail - changes are recorded in NATS events
            logger.error(f"Failed to persist context change: {e}", exc_info=True)
    
    def _persist_decision_change(self, story_id: str, change, payload: dict):
        """Persist decision changes to Neo4j using generic command store methods."""
        properties = {
            "id": change.entity_id,
            "case_id": story_id,
            **payload
        }
        
        if change.operation == "CREATE":
            # Use generic upsert to create decision node
            self.graph_command.upsert_entity(
                label="Decision",
                id=change.entity_id,
                properties=properties
            )
        elif change.operation == "UPDATE":
            # Update existing decision using upsert
            self.graph_command.upsert_entity(
                label="Decision",
                id=change.entity_id,
                properties=properties
            )
        elif change.operation == "DELETE":
            # Mark decision as deleted/superseded
            properties["status"] = "DELETED"
            self.graph_command.upsert_entity(
                label="Decision",
                id=change.entity_id,
                properties=properties
            )
    
    def _persist_subtask_change(self, story_id: str, change, payload: dict):
        """Persist subtask changes using ProjectSubtaskUseCase."""
        logger.info(f"Persisting SUBTASK change: {change.operation} {change.entity_id}")
        
        if change.operation == "CREATE":
            # Use ProjectSubtaskUseCase for creating subtasks with relationships
            subtask_use_case = ProjectSubtaskUseCase(writer=self.graph_command)
            
            use_case_payload = {
                "sub_id": change.entity_id,
                "plan_id": story_id,  # Link subtask to plan/case
                **payload
            }
            
            subtask_use_case.execute(use_case_payload)
            logger.info(f"SUBTASK {change.entity_id} created successfully")
            
        elif change.operation == "UPDATE":
            # Update subtask using generic upsert (for status updates, etc.)
            properties = {
                "id": change.entity_id,
                **payload
            }
            self.graph_command.upsert_entity(
                label="Subtask",
                id=change.entity_id,
                properties=properties
            )
            logger.info(f"SUBTASK {change.entity_id} updated successfully")
    
    def _persist_milestone_change(self, story_id: str, change, payload: dict):
        """Persist milestone/event changes to graph using generic command store."""
        properties = {
            "id": change.entity_id,
            "case_id": story_id,
            "event_type": payload.get("event_type", "milestone"),
            "description": payload.get("description", ""),
            "timestamp_ms": int(time.time() * 1000)
        }
        
        if change.operation == "CREATE":
            # Create milestone event node
            self.graph_command.upsert_entity(
                label="Event",
                id=change.entity_id,
                properties=properties
            )
    
    def _persist_case_change(self, story_id: str, change, payload: dict):
        """Persist case changes using ProjectCaseUseCase."""
        logger.info(f"Persisting CASE change: {change.operation} {change.entity_id}")
        
        # Use ProjectCaseUseCase for domain logic
        case_use_case = ProjectCaseUseCase(writer=self.graph_command)
        
        # Build payload for use case
        use_case_payload = {
            "case_id": change.entity_id,
            **payload  # Include all payload fields (title, description, status, etc.)
        }
        
        case_use_case.execute(use_case_payload)
        logger.info(f"CASE {change.entity_id} projected successfully")
    
    def _persist_plan_change(self, story_id: str, change, payload: dict):
        """Persist plan version changes using ProjectPlanVersionUseCase."""
        logger.info(f"Persisting PLAN change: {change.operation} {change.entity_id}")
        
        # Use ProjectPlanVersionUseCase for domain logic
        plan_use_case = ProjectPlanVersionUseCase(writer=self.graph_command)
        
        # Build payload for use case
        use_case_payload = {
            "case_id": story_id,  # Link plan to case
            "plan_id": change.entity_id,
            **payload  # Include version, status, etc.
        }
        
        plan_use_case.execute(use_case_payload)
        logger.info(f"PLAN {change.entity_id} projected successfully")

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
        """Convert RehydrationBundle to protobuf response."""
        packs = {}
        for role, pack in bundle.packs.items():
            # Map only fields that exist in the proto CaseHeader
            case_header = pack.case_header
            packs[role] = context_pb2.RoleContextPack(
                role=pack.role,
                case_header=context_pb2.CaseHeader(
                    case_id=case_header.get("case_id", ""),
                    title=case_header.get("title", ""),
                    description=case_header.get("description", ""),
                    status="DRAFT",  # Default status, not in domain model
                    created_at=case_header.get("created_at", ""),
                    created_by=case_header.get("requester_id", ""),
                ),
                # Map only fields that exist in the proto PlanHeader
                plan_header=context_pb2.PlanHeader(
                    plan_id=pack.plan_header.get("plan_id", ""),
                    version=pack.plan_header.get("version", 0),
                    status=pack.plan_header.get("status", ""),
                    total_subtasks=pack.plan_header.get("total_subtasks", 0),
                    completed_subtasks=pack.plan_header.get("completed_subtasks", 0),
                ),
                subtasks=[
                    context_pb2.Subtask(
                        subtask_id=st.get("subtask_id", ""),
                        title=st.get("title", ""),
                        description=st.get("description", ""),
                        role=st.get("role", ""),
                        status=st.get("status", ""),
                        dependencies=st.get("dependencies", []),
                        priority=st.get("priority", 0),
                    )
                    for st in pack.role_subtasks
                ],
                decisions=[
                    context_pb2.Decision(
                        id=d.get("id", ""),
                        title=d.get("title", ""),
                        rationale=d.get("rationale", ""),
                        status=d.get("status", ""),
                        decided_by=d.get("decided_by", ""),
                        decided_at=d.get("decided_at", ""),
                    )
                    for d in pack.decisions_relevant
                ],
                decision_deps=[
                    context_pb2.DecisionRelation(
                        src_id=dr.get("src_id", ""),
                        dst_id=dr.get("dst_id", ""),
                        relation_type=dr.get("relation_type", ""),
                    )
                    for dr in pack.decision_dependencies
                ],
                impacted=[
                    context_pb2.ImpactedSubtask(
                        decision_id=imp.get("decision_id", ""),
                        subtask_id=imp.get("subtask_id", ""),
                        title=imp.get("title", ""),
                    )
                    for imp in pack.impacted_subtasks
                ],
                milestones=[
                    context_pb2.Milestone(
                        event_type=m.get("event_type", ""),
                        description=m.get("description", ""),
                        ts_ms=m.get("ts_ms", 0),
                        actor=m.get("actor", ""),
                    )
                    for m in pack.recent_milestones
                ],
                last_summary=pack.last_summary or "",
                token_budget_hint=pack.token_budget_hint,
            )

        return context_pb2.RehydrateSessionResponse(
            case_id=bundle.case_id,
            generated_at_ms=bundle.generated_at_ms,
            packs=packs,
            stats=context_pb2.RehydrationStats(
                decisions=bundle.stats.get("decisions", 0),
                decision_edges=bundle.stats.get("decision_edges", 0),
                impacts=bundle.stats.get("impacts", 0),
                events=bundle.stats.get("events", 0),
                roles=bundle.stats.get("roles", []),
            ),
        )

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
    planning_consumer = None
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
            
            neo4j_config_command = Neo4jConfigCommand(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password
            )
            graph_command = Neo4jCommandStore(cfg=neo4j_config_command)
            
            # Initialize consumers
            logger.info("Initializing NATS consumers...")
            planning_consumer = PlanningEventsConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                cache_service=redis_store.client,
                graph_command=graph_command,
            )
            await planning_consumer.start()
            
            orchestration_consumer = OrchestrationEventsConsumer(
                nc=nats_handler.nc,
                js=nats_handler.js,
                graph_command=graph_command,
                nats_publisher=nats_handler,
            )
            await orchestration_consumer.start()
            
            logger.info("✓ All NATS consumers started")
            
        except Exception as e:
            logger.warning(f"NATS initialization failed: {e}. Continuing without NATS.")
            nats_handler = None
            planning_consumer = None
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
        if planning_consumer:
            await planning_consumer.stop()
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

