"""Definition of Ready (DoR) Score value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DORScore:
    """
    Value Object: Definition of Ready score (0-100).
    
    DoR Criteria:
    - User story is clear and concise
    - Acceptance criteria defined
    - Dependencies identified
    - Effort estimated
    - Testable
    
    Score Ranges:
    - 0-49: Not ready (DRAFT)
    - 50-79: Partially ready (needs refinement)
    - 80-100: Ready for planning
    
    Domain Invariants:
    - Score must be between 0 and 100 (inclusive)
    - Score must be an integer
    
    Immutability: frozen=True ensures no mutation after creation.
    """
    
    value: int
    
    def __post_init__(self) -> None:
        """
        Fail-fast validation.
        
        Raises:
            ValueError: If score is not between 0 and 100.
            TypeError: If score is not an integer.
        """
        if not isinstance(self.value, int):
            raise TypeError(f"DoR score must be an integer, got {type(self.value)}")
        
        if self.value < 0 or self.value > 100:
            raise ValueError(
                f"DoR score must be between 0 and 100, got {self.value}"
            )
    
    def is_ready(self) -> bool:
        """
        Check if story is ready for planning.
        
        Business Rule: Score >= 80 means ready.
        
        Returns:
            True if score >= 80, False otherwise.
        """
        return self.value >= 80
    
    def is_partially_ready(self) -> bool:
        """
        Check if story is partially ready.
        
        Business Rule: 50 <= score < 80 means partially ready.
        
        Returns:
            True if 50 <= score < 80, False otherwise.
        """
        return 50 <= self.value < 80
    
    def is_not_ready(self) -> bool:
        """
        Check if story is not ready.
        
        Business Rule: score < 50 means not ready.
        
        Returns:
            True if score < 50, False otherwise.
        """
        return self.value < 50
    
    def __str__(self) -> str:
        """String representation for logging."""
        return f"{self.value}/100"

