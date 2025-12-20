"""NATS adapter for publishing agent results."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

import nats
from nats.js import JetStreamContext

from ...domain import AgentResult
from ...domain.ports import IResultPublisher

logger = logging.getLogger(__name__)


class NATSResultPublisher(IResultPublisher):
    """
    Implementación de IResultPublisher usando NATS JetStream.

    Publica resultados de agentes a streams de NATS para
    procesamiento asíncrono por otros servicios.
    """

    def __init__(self, nats_url: str | None):
        """
        Initialize NATS publisher.

        Args:
            nats_url: URL del servidor NATS (None to disable NATS publishing)
        """
        self.nats_url = nats_url
        self._client = None
        self._js: JetStreamContext | None = None

    async def connect(self) -> None:
        """Conectar a NATS."""
        if not self.nats_url:
            logger.debug("NATS URL not provided, skipping connection")
            return
        if not self._client:
            self._client = await nats.connect(self.nats_url)
            self._js = self._client.jetstream()
            logger.info(f"✅ Connected to NATS: {self.nats_url}")

    async def close(self) -> None:
        """Cerrar conexión a NATS."""
        if self._client:
            await self._client.close()
            self._client = None
            self._js = None
            logger.debug("✅ NATS connection closed")

    async def _ensure_connected(self) -> bool:
        """Ensure NATS is connected, attempting connection if needed.

        Returns:
            True if connected, False otherwise
        """
        if not self.nats_url:
            logger.warning("⚠️ [NATSResultPublisher] NATS URL not provided, skipping publish_success")
            return False
        if not self._js:
            logger.warning("⚠️ [NATSResultPublisher] NATS not connected, attempting to connect...")
            try:
                await self.connect()
            except Exception:
                logger.error("❌ [NATSResultPublisher] Failed to connect to NATS, skipping publish_success")
                return False
            if not self._js:
                logger.error("❌ [NATSResultPublisher] Connection completed but _js is None, skipping publish_success")
                return False
        return True

    def _log_llm_response(self, result: AgentResult) -> None:
        """Log LLM response content if available."""
        if not result.proposal:
            return

        proposal_data = result.proposal
        llm_content = None
        if isinstance(proposal_data, dict):
            llm_content = proposal_data.get('content', '')
        elif isinstance(proposal_data, str):
            llm_content = proposal_data

        if llm_content:
            logger.info(
                f"\n{'='*80}\n"
                f"💡 LLM RESPONSE (NATS) - Agent: {result.agent_id} ({result.role})\n"
                f"{'='*80}\n"
                f"{llm_content}\n"
                f"{'='*80}\n"
            )

    def _determine_subject(self, task_id: str | None) -> str:
        """Determine NATS subject based on task_id format.

        Args:
            task_id: Task ID to analyze

        Returns:
            NATS subject string
        """
        if not task_id:
            return "agent.response.completed"

        if task_id.endswith(":task-extraction"):
            return "agent.response.completed.task-extraction"

        if ":role-" in task_id and task_id.startswith("ceremony-"):
            return "agent.response.completed.backlog-review.role"

        return "agent.response.completed"

    def _build_result_dict(
        self,
        result: AgentResult,
        num_agents: int | None,
        original_task_id: str | None,
        constraints: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str]:
        """Build result dictionary and determine task_id to use.

        Args:
            result: Agent result to convert
            num_agents: Optional number of agents
            original_task_id: Optional original task ID
            constraints: Optional constraints dictionary

        Returns:
            Tuple of (result_dict, task_id_to_use)
        """
        result_dict = result.to_dict()

        if num_agents is not None:
            result_dict['num_agents'] = num_agents

        if constraints:
            result_dict['constraints'] = constraints

        task_id_to_use = result.task_id
        if original_task_id:
            task_id_to_use = original_task_id
            result_dict["task_id"] = original_task_id
            logger.info(
                f"✅ Using original_task_id as main task_id: {original_task_id} "
                f"(replacing Ray task_id: {result.task_id})"
            )

        return result_dict, task_id_to_use
    
    def _is_task_extraction(
        self,
        original_task_id: str | None,
        constraints: dict[str, Any] | None,
    ) -> bool:
        """Detectar si es task extraction por task_id o metadata.
        
        Args:
            original_task_id: Original task ID
            constraints: Constraints dictionary with metadata
            
        Returns:
            True si es task extraction, False en caso contrario
        """
        # Detect by task_id
        if original_task_id and ":task-extraction" in original_task_id:
            return True
        
        # Detect by metadata
        if constraints and isinstance(constraints, dict):
            metadata = constraints.get("metadata", {})
            task_type = metadata.get("task_type")
            if task_type == "TASK_EXTRACTION":
                return True
        
        return False
    
    def _build_canonical_task_extraction_event(
        self,
        result: AgentResult,
        original_task_id: str | None,
        constraints: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Construir evento canónico para task extraction.
        
        Args:
            result: Agent result with proposal
            original_task_id: Original task ID
            constraints: Constraints dictionary with metadata
            
        Returns:
            Canonical event dictionary with tasks already parsed
        """
        # Parse tasks from proposal
        proposal = result.proposal or {}
        content = proposal.get("content", "")
        
        tasks = []
        try:
            tasks_data = json.loads(content)
            tasks = tasks_data.get("tasks", [])
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.error(
                f"Failed to parse tasks from proposal for {original_task_id or result.task_id}: {e}\n"
                f"Content preview: {content[:200]}"
            )
            tasks = []
        
        # Extract metadata
        metadata = {}
        if constraints and isinstance(constraints, dict):
            metadata = constraints.get("metadata", {})
        
        return {
            "task_id": original_task_id or result.task_id,
            "story_id": metadata.get("story_id"),
            "ceremony_id": metadata.get("ceremony_id"),
            "tasks": tasks,  # Already parsed and validated
            "model": result.model,
            "timestamp": result.timestamp,
            "duration_ms": result.duration_ms,
            "validated_at": datetime.now(UTC).isoformat(),
            # Do NOT include raw_content (or truncate it)
        }

    async def publish_success(self, result: AgentResult, num_agents: int | None = None, original_task_id: str | None = None, constraints: dict[str, Any] | None = None) -> None:
        """
        Publicar resultado exitoso.

        Args:
            result: Resultado exitoso del agente
            num_agents: Número total de agentes en la deliberación (opcional)
            original_task_id: Task ID original desde planning (opcional)
            constraints: Constraints del request original (incluye metadata con story_id, ceremony_id, etc.)
        """
        logger.info(
            f"🔍 [NATSResultPublisher.publish_success] Entry: "
            f"task_id={result.task_id}, "
            f"agent_id={result.agent_id}, "
            f"role={result.role}, "
            f"nats_url={self.nats_url}, "
            f"_js={self._js is not None}, "
            f"num_agents={num_agents}, "
            f"original_task_id={original_task_id}, "
            f"has_constraints={constraints is not None}"
        )

        if not await self._ensure_connected():
            return

        self._log_llm_response(result)

        try:
            # Detect if this is task extraction
            is_task_extraction = self._is_task_extraction(original_task_id, constraints)
            
            if is_task_extraction:
                # Publish canonical event with tasks already parsed
                canonical_event = self._build_canonical_task_extraction_event(
                    result, original_task_id, constraints
                )
                subject = "agent.response.completed.task-extraction"
                payload = json.dumps(canonical_event).encode()
                
                logger.info(
                    f"📤 [NATSResultPublisher] Publishing canonical event: "
                    f"subject={subject}, task_id={original_task_id or result.task_id}, "
                    f"tasks_count={len(canonical_event.get('tasks', []))}"
                )
                
                ack = await self._js.publish(subject=subject, payload=payload)
                
                logger.info(
                    f"✅ [NATSResultPublisher] Successfully published canonical event: "
                    f"task_id={original_task_id or result.task_id}, "
                    f"stream={ack.stream if hasattr(ack, 'stream') else 'N/A'}, "
                    f"seq={ack.seq if hasattr(ack, 'seq') else 'N/A'}"
                )
                return
            
            # Standard event for non-task-extraction
            result_dict, task_id_to_use = self._build_result_dict(
                result, num_agents, original_task_id, constraints
            )
            subject = self._determine_subject(task_id_to_use)

            logger.info(
                f"🔍 [NATSResultPublisher] About to publish: "
                f"subject={subject}, "
                f"task_id_to_use={task_id_to_use}, "
                f"payload_size={len(result_dict)} keys, "
                f"has_constraints_in_payload={'constraints' in result_dict}"
            )

            payload = json.dumps(result_dict).encode()
            logger.info(
                f"📤 [NATSResultPublisher] Publishing to NATS: "
                f"subject={subject}, "
                f"payload_bytes={len(payload)}, "
                f"task_id={task_id_to_use}"
            )
            ack = await self._js.publish(
                subject=subject,
                payload=payload,
            )
            logger.info(
                f"✅ [NATSResultPublisher] Successfully published {subject}: "
                f"task_id={task_id_to_use}, "
                f"agent_id={result.agent_id}, "
                f"role={result.role}, "
                f"stream={ack.stream if hasattr(ack, 'stream') else 'N/A'}, "
                f"seq={ack.seq if hasattr(ack, 'seq') else 'N/A'}"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to publish agent.response.completed: task_id={result.task_id}, "
                f"agent_id={result.agent_id}, error={e}",
                exc_info=True
            )
            raise

    async def publish_failure(self, result: AgentResult, num_agents: int | None = None, original_task_id: str | None = None) -> None:
        """
        Publicar resultado fallido.

        Args:
            result: Resultado fallido del agente
            num_agents: Número total de agentes en la deliberación (opcional)
            original_task_id: Task ID original desde planning (opcional)
        """
        if not self.nats_url:
            logger.debug("NATS URL not provided, skipping publish_failure")
            return
        if not self._js:
            logger.warning("NATS not connected, attempting to connect...")
            await self.connect()
            if not self._js:
                logger.warning("Failed to connect to NATS, skipping publish_failure")
                return

        try:
            result_dict = result.to_dict()
            # Add num_agents to payload if provided (needed by DeliberationResultCollector)
            if num_agents is not None:
                result_dict['num_agents'] = num_agents
            # Add original_task_id to payload if provided (needed to detect backlog review ceremonies)
            if original_task_id:
                # Store in error metadata or as separate field
                if "metadata" not in result_dict:
                    result_dict["metadata"] = {}
                result_dict["metadata"]["task_id"] = original_task_id

            payload = json.dumps(result_dict).encode()
            ack = await self._js.publish(
                subject="agent.response.failed",
                payload=payload,
            )
            logger.info(
                f"📤 Published agent.response.failed: task_id={result.task_id}, "
                f"agent_id={result.agent_id}, error={result.error}, "
                f"stream={ack.stream if hasattr(ack, 'stream') else 'N/A'}, "
                f"seq={ack.seq if hasattr(ack, 'seq') else 'N/A'}"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to publish agent.response.failed: task_id={result.task_id}, "
                f"agent_id={result.agent_id}, error={e}",
                exc_info=True
            )
            raise

