"""Agent type entity."""

from __future__ import annotations

from enum import Enum


class AgentType(str, Enum):
    """Domain entity representing the type of agent implementation.
    
    Production-only agent types. No mocks allowed in production code.
    
    Attributes:
        VLLM: vLLM-based agent for production use
    """
    
    VLLM = "VLLM"
    
    @classmethod
    def from_string(cls, value: str) -> AgentType:
        """Create AgentType from string value.
        
        Production-only: Only VLLM agents allowed, no mocks.
        
        Args:
            value: String representation of agent type
            
        Returns:
            AgentType.VLLM (only option in production)
            
        Raises:
            ValueError: If value is MOCK or invalid
        """
        # Normalize input
        normalized = value.upper()
        
        # Reject MOCK explicitly
        if normalized == "MOCK":
            raise ValueError(
                "MOCK agents not allowed in production. "
                "Use VLLM or RAY_VLLM for real agents."
            )
        
        # Handle aliases (all map to VLLM in production)
        if normalized in ("VLLM", "RAY_VLLM"):
            return cls.VLLM
        
        raise ValueError(
            f"Invalid agent type: {value}. "
            f"Production only supports: VLLM, RAY_VLLM"
        )
    
    def is_vllm(self) -> bool:
        """Check if this is a vLLM agent type.
        
        In production, this is always True.
        
        Returns:
            True (always, since VLLM is the only option)
        """
        return True  # Only VLLM exists in production

