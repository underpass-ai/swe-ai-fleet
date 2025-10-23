"""NATS adapter for publishing agent results."""

import json
import logging

import nats
from nats.js import JetStreamContext

from ...domain.ports import IResultPublisher
from ...domain import AgentResult

logger = logging.getLogger(__name__)


class NATSResultPublisher(IResultPublisher):
    """
    Implementación de IResultPublisher usando NATS JetStream.
    
    Publica resultados de agentes a streams de NATS para
    procesamiento asíncrono por otros servicios.
    """
    
    def __init__(self, nats_url: str):
        """
        Initialize NATS publisher.
        
        Args:
            nats_url: URL del servidor NATS
        """
        self.nats_url = nats_url
        self._client = None
        self._js: JetStreamContext | None = None
    
    async def connect(self) -> None:
        """Conectar a NATS."""
        if not self._client:
            self._client = await nats.connect(self.nats_url)
            self._js = self._client.jetstream()
            logger.debug(f"✅ Connected to NATS: {self.nats_url}")
    
    async def close(self) -> None:
        """Cerrar conexión a NATS."""
        if self._client:
            await self._client.close()
            self._client = None
            self._js = None
            logger.debug("✅ NATS connection closed")
    
    async def publish_success(self, result: AgentResult) -> None:
        """
        Publicar resultado exitoso.
        
        Args:
            result: Resultado exitoso del agente
        """
        if not self._js:
            raise RuntimeError("NATS not connected. Call connect() first.")
        
        await self._js.publish(
            subject="agent.response.completed",
            payload=json.dumps(result.to_dict()).encode(),
        )
        logger.debug(f"📤 Published success: {result.task_id}")
    
    async def publish_failure(self, result: AgentResult) -> None:
        """
        Publicar resultado fallido.
        
        Args:
            result: Resultado fallido del agente
        """
        if not self._js:
            raise RuntimeError("NATS not connected. Call connect() first.")
        
        await self._js.publish(
            subject="agent.response.failed",
            payload=json.dumps(result.to_dict()).encode(),
        )
        logger.debug(f"📤 Published failure: {result.task_id}")

