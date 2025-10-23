"""Task prompt value object."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class TaskPrompt:
    """
    Task prompt para un agente (Value Object).
    
    Encapsula la descripción de la tarea y metadata
    para generar el user prompt completo.
    """
    task: str
    metadata: dict[str, Any] = field(default_factory=dict)
    
    def render(self) -> str:
        """
        Renderizar el prompt completo.
        
        Returns:
            Task prompt como string
        """
        prompt = f"Task: {self.task}\n\n"
        prompt += "Please provide a detailed proposal for implementing this task.\n\n"
        prompt += "Your response should include:\n"
        prompt += "1. Analysis of the requirements\n"
        prompt += "2. Proposed solution approach\n"
        prompt += "3. Implementation details\n"
        prompt += "4. Potential challenges and how to address them\n"
        
        # Add metadata if present
        if self.metadata:
            prompt += "\n\nAdditional context:\n"
            for key, value in self.metadata.items():
                prompt += f"- {key}: {value}\n"
        
        return prompt

