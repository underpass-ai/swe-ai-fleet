"""Domain model for agent configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .agent_role import AgentRole


@dataclass(frozen=True)
class AgentConfig:
    """
    Configuración de un agente (Value Object).
    
    Encapsula toda la configuración necesaria para ejecutar un agente,
    incluyendo identificación, modelo, URLs y parámetros de generación.
    """
    agent_id: str
    role: AgentRole | str
    model: str
    vllm_url: str
    nats_url: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    workspace_path: Optional[Path] = None
    enable_tools: bool = False
    
    @classmethod
    def create(
        cls,
        agent_id: str,
        role: str,
        model: str,
        vllm_url: str,
        nats_url: str,
        workspace_path: str | Path | None = None,
        enable_tools: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        timeout: int = 60,
    ) -> "AgentConfig":
        """
        Factory method para crear configuración de agente.
        
        Args:
            agent_id: Unique identifier for this agent
            role: Agent role (DEV, QA, etc.)
            model: Model name to use
            vllm_url: URL of vLLM server
            nats_url: URL of NATS server
            workspace_path: Path to workspace (required if enable_tools=True)
            enable_tools: Whether to enable tool execution
            temperature: Sampling temperature for LLM
            max_tokens: Maximum tokens to generate
            timeout: Timeout in seconds for vLLM API calls
            
        Returns:
            AgentConfig instance
            
        Raises:
            ValueError: If enable_tools=True but workspace_path is None
        """
        # Validate configuration
        if enable_tools and not workspace_path:
            raise ValueError("workspace_path required when enable_tools=True")
        
        # Convert role to enum if possible
        try:
            role_enum = AgentRole(role)
        except ValueError:
            role_enum = role  # Custom role
        
        # Convert workspace_path to Path if provided
        workspace = Path(workspace_path) if workspace_path else None
        
        return cls(
            agent_id=agent_id,
            role=role_enum,
            model=model,
            vllm_url=vllm_url,
            nats_url=nats_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            workspace_path=workspace,
            enable_tools=enable_tools,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """
        Convertir a diccionario para serialización.
        
        Returns:
            Dictionary with agent configuration
        """
        return {
            "agent_id": self.agent_id,
            "role": self.role.value if isinstance(self.role, AgentRole) else self.role,
            "model": self.model,
            "vllm_url": self.vllm_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
    
    def validate(self) -> None:
        """
        Validar configuración.
        
        Raises:
            ValueError: Si la configuración es inválida
        """
        if self.enable_tools and not self.workspace_path:
            raise ValueError("workspace_path required when enable_tools=True")
        
        if self.temperature < 0 or self.temperature > 2:
            raise ValueError(f"temperature must be between 0 and 2, got {self.temperature}")
        
        if self.max_tokens < 1:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
    
    @property
    def mode_description(self) -> str:
        """Descripción del modo de operación."""
        return "with tools" if self.enable_tools else "text-only"

