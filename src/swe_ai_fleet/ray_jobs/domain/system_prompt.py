"""System prompt value object."""

from dataclasses import dataclass

from .agent_role import AgentRole, get_role_context


@dataclass(frozen=True)
class SystemPrompt:
    """
    System prompt para un agente (Value Object).
    
    Encapsula el contexto base, rubrica, requerimientos y 
    configuración de diversidad para generar el prompt completo.
    """
    role: AgentRole | str
    rubric: str = ""
    requirements: tuple[str, ...] = ()
    diversity: bool = False
    
    @classmethod
    def for_role(
        cls,
        role: str,
        rubric: str = "",
        requirements: list[str] | None = None,
        diversity: bool = False,
    ) -> "SystemPrompt":
        """
        Factory method para crear prompt desde role string.
        
        Args:
            role: Role del agente
            rubric: Evaluation rubric
            requirements: Lista de requerimientos
            diversity: Enable diversity mode
            
        Returns:
            SystemPrompt instance
        """
        try:
            role_enum = AgentRole(role)
        except ValueError:
            role_enum = role  # Custom role
        
        return cls(
            role=role_enum,
            rubric=rubric,
            requirements=tuple(requirements or []),
            diversity=diversity,
        )
    
    def render(self) -> str:
        """
        Renderizar el prompt completo.
        
        Returns:
            System prompt como string
        """
        # Base context
        base_prompt = get_role_context(self.role)
        
        # Add rubric if present
        if self.rubric:
            base_prompt += f"\n\nEvaluation rubric:\n{self.rubric}"
        
        # Add requirements if present
        if self.requirements:
            req_text = "\n".join(f"- {req}" for req in self.requirements)
            base_prompt += f"\n\nRequirements:\n{req_text}"
        
        # Add diversity instruction
        if self.diversity:
            base_prompt += (
                "\n\nIMPORTANT: Provide a creative and diverse approach. "
                "Think outside the box and offer alternative perspectives."
            )
        
        return base_prompt
    
    def with_diversity(self) -> "SystemPrompt":
        """Crear nueva instancia con diversity enabled (immutable)."""
        return SystemPrompt(
            role=self.role,
            rubric=self.rubric,
            requirements=self.requirements,
            diversity=True,
        )
    
    def with_rubric(self, rubric: str) -> "SystemPrompt":
        """Crear nueva instancia con rubric diferente (immutable)."""
        return SystemPrompt(
            role=self.role,
            rubric=rubric,
            requirements=self.requirements,
            diversity=self.diversity,
        )

