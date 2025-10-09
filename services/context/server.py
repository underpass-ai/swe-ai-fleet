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
from concurrent import futures

import grpc

# Add project root to path to import swe_ai_fleet modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from services.context.gen import context_pb2, context_pb2_grpc
from services.context.nats_handler import ContextNATSHandler
from swe_ai_fleet.context.adapters.neo4j_command_store import Neo4jCommandStore as Neo4jGraphCommandStore
from swe_ai_fleet.context.adapters.neo4j_query_store import Neo4jQueryStore as Neo4jGraphQueryStore
from swe_ai_fleet.context.adapters.redis_planning_read_adapter import (
    RedisPlanningReadAdapter,
)
from swe_ai_fleet.context.context_assembler import build_prompt_blocks
from swe_ai_fleet.context.domain.scopes.prompt_scope_policy import PromptScopePolicy
from swe_ai_fleet.context.session_rehydration import (
    RehydrationRequest,
    SessionRehydrationUseCase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


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

        # Initialize adapters
        self.graph_query = Neo4jGraphQueryStore(neo4j_uri, neo4j_user, neo4j_password)
        self.graph_command = Neo4jGraphCommandStore(
            neo4j_uri, neo4j_user, neo4j_password
        )
        self.planning_read = RedisPlanningReadAdapter(redis_host, redis_port)

        # Initialize use cases
        self.rehydrator = SessionRehydrationUseCase(
            planning_store=self.planning_read,
            graph_store=self.graph_query,
        )

        # Initialize scope policy
        self.policy = PromptScopePolicy()

        # NATS handler for async events
        self.nats_handler = nats_handler

        logger.info("Context Service initialized successfully")

    def GetContext(self, request, context):
        """
        Get hydrated context for a specific story, role, and phase.
        Returns prompt blocks ready for agent consumption.
        """
        try:
            logger.info(
                f"GetContext request: story_id={request.story_id}, "
                f"role={request.role}, phase={request.phase}"
            )

            # Build prompt blocks using the context assembler
            prompt_blocks = build_prompt_blocks(
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

    def UpdateContext(self, request, context):
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

            # Process each context change
            for change in request.changes:
                logger.info(
                    f"Processing change: {change.operation} "
                    f"{change.entity_type}/{change.entity_id}"
                )

                try:
                    self._process_context_change(change, request.story_id)
                except Exception as e:
                    warning = f"Failed to process {change.entity_id}: {str(e)}"
                    warnings.append(warning)
                    logger.warning(warning)

            # Generate new version
            version = self._generate_new_version(request.story_id)
            hash_value = self._generate_context_hash(request.story_id, version)

            # Publish async event if NATS is available
            if self.nats_handler:
                task = asyncio.create_task(
                    self.nats_handler.publish_context_updated(
                        request.story_id, version
                    )
                )
                # Add error callback to handle task exceptions
                task.add_done_callback(self._handle_nats_publish_error)

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

    def RehydrateSession(self, request, context):
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

    def ValidateScope(self, request, context):
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
        """Detect which scopes are present in the prompt blocks."""
        # This would analyze the prompt_blocks content
        # For now, return empty list
        return []

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
        """Process a single context change."""
        # Log the change for now
        # Future: Route to appropriate domain aggregates and persist to Neo4j
        logger.info(
            f"Context change recorded: story={story_id}, "
            f"operation={change.operation}, entity={change.entity_type}/{change.entity_id}"
        )
        
        # Validate required fields
        if not change.operation or not change.entity_type or not change.entity_id:
            raise ValueError("Missing required fields in context change")
        
        # Future implementation would persist to graph_command store
        # For now, changes are acknowledged but not persisted

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
            packs[role] = context_pb2.RoleContextPack(
                role=pack.role,
                case_header=context_pb2.CaseHeader(**pack.case_header),
                plan_header=context_pb2.PlanHeader(**pack.plan_header),
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

    # Initialize NATS handler if enabled
    nats_handler = None
    if enable_nats:
        try:
            logger.info("Initializing NATS handler...")
            # We'll create servicer first, then pass it to NATS handler
            nats_handler = ContextNATSHandler(nats_url, None)
            await nats_handler.connect()
            await nats_handler.subscribe()
        except Exception as e:
            logger.warning(f"NATS initialization failed: {e}. Continuing without NATS.")
            nats_handler = None

    # Create gRPC server
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

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

    # Start server
    server.add_insecure_port(f"[::]:{port}")
    server.start()

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
        server.stop(grace=5)
        if nats_handler:
            await nats_handler.close()


def serve():
    """Entry point for the server."""
    asyncio.run(serve_async())


if __name__ == "__main__":
    serve()

