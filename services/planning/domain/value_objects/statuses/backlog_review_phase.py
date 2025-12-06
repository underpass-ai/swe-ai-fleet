"""BacklogReviewPhase enum for Planning Service.

Defines work phases for backlog review ceremonies and context retrieval.
Aligned with Context Service phase values for consistency.
"""

from enum import Enum


class BacklogReviewPhase(str, Enum):
    """Work phases for backlog review ceremonies.

    Phases represent the stage of work in the story lifecycle during backlog review.
    Used for context retrieval when reviewing stories before planning.
    Aligned with Context Service phase values (DESIGN, BUILD, TEST, DOCS).

    Phase Flow:
    - DESIGN: Technical design and planning phase (used for backlog review)
    - BUILD: Implementation and development phase
    - TEST: QA testing and validation phase
    - DOCS: Documentation phase
    """

    DESIGN = "DESIGN"  # Technical design phase
    BUILD = "BUILD"    # Implementation phase
    TEST = "TEST"      # QA testing phase
    DOCS = "DOCS"      # Documentation phase

    def __str__(self) -> str:
        """Return string value.

        Returns:
            String representation
        """
        return self.value
