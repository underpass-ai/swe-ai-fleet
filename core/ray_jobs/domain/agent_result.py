"""Domain model for agent execution results."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class AgentResult:
    """
    Resultado de la ejecución de un agente (Value Object).
    
    Representa el resultado inmutable de una tarea ejecutada por un agente,
    ya sea exitosa o fallida.
    """
    task_id: str
    agent_id: str
    role: str
    status: str  # "completed" | "failed"
    duration_ms: int
    timestamp: str
    
    # Campos opcionales (dependen de success/failure)
    proposal: dict[str, Any] | None = None
    operations: list | None = None
    artifacts: dict | None = None
    audit_trail: list | None = None
    error: str | None = None
    error_type: str | None = None
    success: bool | None = None
    
    # Metadata adicional
    model: str | None = None
    enable_tools: bool | None = None
    diversity: bool | None = None
    
    @classmethod
    def success_result(
        cls,
        task_id: str,
        agent_id: str,
        role: str,
        duration_ms: int,
        proposal: dict[str, Any] | None = None,
        operations: list | None = None,
        artifacts: dict | None = None,
        audit_trail: list | None = None,
        model: str | None = None,
        enable_tools: bool = False,
        diversity: bool = False,
    ) -> "AgentResult":
        """Factory method para resultados exitosos."""
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            role=role,
            status="completed",
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC).isoformat(),
            proposal=proposal,
            operations=operations or [],
            artifacts=artifacts or {},
            audit_trail=audit_trail or [],
            success=True,
            model=model,
            enable_tools=enable_tools,
            diversity=diversity,
        )
    
    @classmethod
    def failure_result(
        cls,
        task_id: str,
        agent_id: str,
        role: str,
        duration_ms: int,
        error: Exception,
        model: str | None = None,
    ) -> "AgentResult":
        """Factory method para resultados fallidos."""
        return cls(
            task_id=task_id,
            agent_id=agent_id,
            role=role,
            status="failed",
            duration_ms=duration_ms,
            timestamp=datetime.now(UTC).isoformat(),
            error=str(error),
            error_type=type(error).__name__,
            success=False,
            model=model,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convertir a diccionario para serialización."""
        result = {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }
        
        # Agregar campos opcionales solo si existen
        if self.proposal is not None:
            result["proposal"] = self.proposal
        if self.operations is not None:
            result["operations"] = self.operations
        if self.artifacts is not None:
            result["artifacts"] = self.artifacts
        if self.audit_trail is not None:
            result["audit_trail"] = self.audit_trail
        if self.error is not None:
            result["error"] = self.error
        if self.error_type is not None:
            result["error_type"] = self.error_type
        if self.success is not None:
            result["success"] = self.success
        if self.model is not None:
            result["model"] = self.model
        if self.enable_tools is not None:
            result["enable_tools"] = self.enable_tools
        if self.diversity is not None:
            result["diversity"] = self.diversity
            
        return result
    
    @property
    def is_success(self) -> bool:
        """Check si el resultado fue exitoso."""
        return self.status == "completed"
    
    @property
    def is_failure(self) -> bool:
        """Check si el resultado falló."""
        return self.status == "failed"

