"""Port for publishing agent results."""

from abc import ABC, abstractmethod

from ..agent_result import AgentResult


class IResultPublisher(ABC):
    """
    Puerto para publicar resultados de agentes.
    
    Define el contrato que debe cumplir cualquier
    implementación de publicación de resultados (NATS, Kafka, etc.).
    """
    
    @abstractmethod
    async def publish_success(self, result: AgentResult) -> None:
        """
        Publicar resultado exitoso.
        
        Args:
            result: Resultado del agente
        """
        pass
    
    @abstractmethod
    async def publish_failure(self, result: AgentResult) -> None:
        """
        Publicar resultado fallido.
        
        Args:
            result: Resultado del agente con error
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

