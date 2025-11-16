"""LLMPrompt value object for LLM generation requests."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMPrompt:
    """Value Object for LLM prompt text.
    
    Domain Invariant: Prompt cannot be empty.
    Following DDD: No primitives - everything is a value object.
    """

    value: str

    def __post_init__(self) -> None:
        """Validate LLMPrompt (fail-fast).
        
        Raises:
            ValueError: If prompt is empty or whitespace
        """
        if not self.value or not self.value.strip():
            raise ValueError("LLMPrompt cannot be empty")

    def __str__(self) -> str:
        """String representation.
        
        Returns:
            String value
        """
        return self.value

    def token_count_estimate(self) -> int:
        """Estimate token count (rough approximation).
        
        Tell, Don't Ask: Prompt knows how to estimate itself.
        
        Returns:
            Estimated number of tokens (words / 0.75)
        """
        words = len(self.value.split())
        return int(words / 0.75)  # Rough GPT tokenization estimate

