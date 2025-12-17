"""TokenBudget enum for Planning Service.

Defines standard token budget values for context retrieval.
Used to specify how many tokens should be allocated for context requests.
"""

from enum import IntEnum


class TokenBudget(IntEnum):
    """Standard token budget values for context retrieval.

    Token budgets represent the maximum number of tokens to include
    in context responses from Context Service. Different use cases
    may require different token budgets based on complexity.

    Values:
    - STANDARD: Default budget for most use cases (2000 tokens)
    - LARGE: For complex stories requiring more context (4000 tokens)
    - SMALL: For simple stories with minimal context (1000 tokens)
    """

    STANDARD = 2000  # Default budget for backlog review
    LARGE = 4000      # For complex stories
    SMALL = 1000      # For simple stories

    def __str__(self) -> str:
        """Return string representation.

        Returns:
            String representation of token budget value
        """
        return str(self.value)
