"""TaskDerivationConfig value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskDerivationConfig:
    """Configuration for task derivation process.

    Immutable configuration loaded from YAML.
    NO serialization methods (use mappers in infrastructure).

    Following DDD:
    - Value object (no identity)
    - Immutable
    - Fail-fast validation
    """

    prompt_template: str
    min_tasks: int
    max_tasks: int
    max_retries: int

    def __post_init__(self) -> None:
        """Validate configuration (fail-fast).

        Raises:
            ValueError: If configuration is invalid
        """
        if not self.prompt_template or not self.prompt_template.strip():
            raise ValueError("prompt_template cannot be empty")

        if self.min_tasks < 1:
            raise ValueError(f"min_tasks must be >= 1: {self.min_tasks}")

        if self.max_tasks < self.min_tasks:
            raise ValueError(
                f"max_tasks ({self.max_tasks}) must be >= min_tasks ({self.min_tasks})"
            )

        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0: {self.max_retries}")

    def build_prompt(
        self,
        description: str,
        acceptance_criteria: str = "",
        technical_notes: str = "",
    ) -> str:
        """Build LLM prompt from template.

        Tell, Don't Ask: Config knows how to build prompts.

        Args:
            description: Plan description
            acceptance_criteria: Plan acceptance criteria
            technical_notes: Technical notes from plan

        Returns:
            Formatted prompt ready for LLM
        """
        return self.prompt_template.format(
            description=description,
            acceptance_criteria=acceptance_criteria or "Not specified",
            technical_notes=technical_notes or "None",
            min_tasks=self.min_tasks,
            max_tasks=self.max_tasks,
        )

