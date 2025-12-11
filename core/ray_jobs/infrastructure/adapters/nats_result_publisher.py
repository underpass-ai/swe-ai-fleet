"""NATS adapter for publishing agent results."""

import json
import logging
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

        if not self.nats_url:
            logger.warning("⚠️ [NATSResultPublisher] NATS URL not provided, skipping publish_success")
            return
        if not self._js:
            logger.warning("⚠️ [NATSResultPublisher] NATS not connected, attempting to connect...")
            await self.connect()
            if not self._js:
                logger.error("❌ [NATSResultPublisher] Failed to connect to NATS, skipping publish_success")
                return

        # Log LLM response when publishing to NATS
        if result.proposal:
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

        try:
            result_dict = result.to_dict()
            # Add num_agents to payload if provided (needed by DeliberationResultCollector)
            if num_agents is not None:
                result_dict['num_agents'] = num_agents

            # Preserve constraints (including metadata with story_id, ceremony_id, etc.)
            # This is essential for task-extraction events that need metadata
            if constraints:
                result_dict['constraints'] = constraints

            # Use original_task_id as the main task_id if provided (preserve original event identifier)
            # This ensures the task_id travels through the entire circuit without being reinvented
            task_id_to_use = result.task_id
            if original_task_id:
                task_id_to_use = original_task_id
                result_dict["task_id"] = original_task_id
                logger.info(
                    f"✅ Using original_task_id as main task_id: {original_task_id} "
                    f"(replacing Ray task_id: {result.task_id})"
                )

            # Determine subject based on task_id format for efficient filtering
            # Format: "ceremony-{id}:story-{id}:role-{role}" -> backlog-review.role
            # Format: "ceremony-{id}:story-{id}:task-extraction" -> task-extraction
            # Otherwise: generic subject (backward compatibility)
            subject = "agent.response.completed"
            if task_id_to_use:
                if task_id_to_use.endswith(":task-extraction"):
                    subject = "agent.response.completed.task-extraction"
                elif ":role-" in task_id_to_use and task_id_to_use.startswith("ceremony-"):
                    subject = "agent.response.completed.backlog-review.role"

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

