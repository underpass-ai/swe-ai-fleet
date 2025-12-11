"""Port for publishing agent results."""

from abc import ABC, abstractmethod
from typing import Any

from ..agent_result import AgentResult


class IResultPublisher(ABC):
    """
    Puerto para publicar resultados de agentes.

    Define el contrato que debe cumplir cualquier
    implementación de publicación de resultados (NATS, Kafka, etc.).
    """

    @abstractmethod
    async def publish_success(self, result: AgentResult, num_agents: int | None = None, original_task_id: str | None = None, constraints: dict[str, Any] | None = None) -> None:
        """
        Publicar resultado exitoso.

        Args:
            result: Resultado del agente
            num_agents: Número total de agentes en la deliberación (opcional)
            original_task_id: Task ID original desde planning (formato: "ceremony-{id}:story-{id}:role-{role}") (opcional)
            constraints: Constraints del request original (incluye metadata con story_id, ceremony_id, etc.) (opcional)
        """
        pass

    @abstractmethod
    async def publish_failure(self, result: AgentResult, num_agents: int | None = None, original_task_id: str | None = None) -> None:
        """
        Publicar resultado fallido.

        Args:
            result: Resultado del agente con error
            num_agents: Número total de agentes en la deliberación (opcional)
            original_task_id: Task ID original desde planning (formato: "ceremony-{id}:story-{id}:role-{role}") (opcional)
        """
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Conectar al sistema de mensajería."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Cerrar conexión."""
        pass

