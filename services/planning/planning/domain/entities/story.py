"""Story entity - Aggregate Root."""

from dataclasses import dataclass
from datetime import UTC, datetime

from planning.domain.value_objects import (
    Brief,
    DORScore,
    StoryId,
    StoryState,
    StoryStateEnum,
    Title,
    UserName,
)
from planning.domain.value_objects.identifiers.epic_id import EpicId


@dataclass(frozen=True)
class Story:
    """
    Aggregate Root: User Story in the planning system.

    Responsibilities:
    - Manage story lifecycle (FSM transitions)
    - Validate state transitions
    - Calculate DoR score
    - Maintain story metadata

    Hierarchy: Project → Epic → Story → Task

    Domain Invariants:
    - Story ID must be unique
    - Story MUST belong to an Epic (epic_id is REQUIRED)
    - Title cannot be empty
    - Brief cannot be empty
    - State transitions must follow FSM rules
    - DoR score must be 0-100
    - Created timestamp must be set

    Immutability: frozen=True ensures no mutation after creation.
    Use builder methods to create new instances with updated values.
    """

    story_id: StoryId
    epic_id: EpicId  # REQUIRED - parent epic (domain invariant)
    title: Title  # Value Object - encapsulates validation
    brief: Brief  # Value Object - encapsulates validation
    state: StoryState
    dor_score: DORScore
    created_by: UserName  # Value Object - encapsulates validation
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If any invariant is violated.
        """
        # Title, Brief, and UserName validation is delegated to Value Objects
        # This follows DDD: ubiquitous language and validation in Value Objects

        if self.created_at > self.updated_at:
            raise ValueError(
                f"created_at ({self.created_at}) cannot be after "
                f"updated_at ({self.updated_at})"
            )

    def transition_to(
        self,
        target_state: StoryState,
        updated_at: datetime | None = None,
    ) -> "Story":
        """
        Transition story to a new state.

        Business Rules:
        - Transition must be valid according to FSM rules
        - updated_at must be after created_at
        - DoR score may need to be updated based on state

        Args:
            target_state: Target state to transition to.
            updated_at: Timestamp of update (defaults to now).

        Returns:
            New Story instance with updated state.

        Raises:
            ValueError: If transition is invalid.
        """
        if not self.state.can_transition_to(target_state):
            raise ValueError(
                f"Invalid state transition: {self.state} → {target_state}"
            )

        update_time = updated_at or datetime.now(UTC)

        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )

        # Return new instance (immutable)
        return Story(
            epic_id=self.epic_id,  # REQUIRED - preserve parent reference
            story_id=self.story_id,
            title=self.title,
            brief=self.brief,
            state=target_state,
            dor_score=self.dor_score,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=update_time,
        )

    def update_dor_score(
        self,
        new_score: DORScore,
        updated_at: datetime | None = None,
    ) -> "Story":
        """
        Update DoR score.

        Business Rule: DoR score may change as story is refined.

        Args:
            new_score: New DoR score.
            updated_at: Timestamp of update (defaults to now).

        Returns:
            New Story instance with updated DoR score.

        Raises:
            ValueError: If updated_at is invalid.
        """
        update_time = updated_at or datetime.now(UTC)

        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )

        return Story(
            epic_id=self.epic_id,  # REQUIRED - preserve parent reference
            story_id=self.story_id,
            title=self.title,
            brief=self.brief,
            state=self.state,
            dor_score=new_score,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=update_time,
        )

    def update_content(
        self,
        title: Title | None = None,
        brief: Brief | None = None,
        updated_at: datetime | None = None,
    ) -> "Story":
        """
        Update story content (title and/or brief).

        Business Rule: Content can be updated while in DRAFT or PO_REVIEW states.

        Args:
            title: New Title value object (optional, keeps current if None).
            brief: New Brief value object (optional, keeps current if None).
            updated_at: Timestamp of update (defaults to now).

        Returns:
            New Story instance with updated content.

        Raises:
            ValueError: If updated_at is invalid.
        """
        new_title = self._value_or_current(title, self.title)
        new_brief = self._value_or_current(brief, self.brief)

        update_time = updated_at or datetime.now(UTC)

        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )

        return Story(
            epic_id=self.epic_id,  # REQUIRED - preserve parent reference
            story_id=self.story_id,
            title=new_title,
            brief=new_brief,
            state=self.state,
            dor_score=self.dor_score,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=update_time,
        )

    @staticmethod
    def _value_or_current(new_value, current_value):
        """
        Helper: Return new value if provided, otherwise keep current.

        Args:
            new_value: New value (or None to keep current).
            current_value: Current value to fall back to.

        Returns:
            new_value if not None, else current_value.
        """
        return new_value if new_value is not None else current_value

    def meets_dor_threshold(self) -> bool:
        """
        Check if DoR score meets minimum threshold.

        Business Rule: Score >= 80 means ready.

        Returns:
            True if DoR score >= 80, False otherwise.
        """
        return self.dor_score.is_ready()

    def can_be_planned(self) -> bool:
        """
        Check if story can be planned now.

        Business Rules:
        - DoR score >= 80
        - State is READY_FOR_PLANNING

        Returns:
            True if ready to derive tasks, False otherwise.
        """
        return (
            self.meets_dor_threshold()
            and self.state.is_state(StoryStateEnum.READY_FOR_PLANNING)  # Tell, Don't Ask
        )

    def is_planned_or_beyond(self) -> bool:
        """
        Check if story has been planned already.

        Business Rule: Story has passed through planning phase.

        Returns:
            True if state is PLANNED or later, False otherwise.
        """
        planned_states = {
            StoryStateEnum.PLANNED,
            StoryStateEnum.READY_FOR_EXECUTION,
            StoryStateEnum.IN_PROGRESS,
            StoryStateEnum.CODE_REVIEW,
            StoryStateEnum.TESTING,
            StoryStateEnum.READY_TO_REVIEW,
            StoryStateEnum.ACCEPTED,
            StoryStateEnum.CARRY_OVER,
            StoryStateEnum.DONE,
            StoryStateEnum.ARCHIVED,
        }
        return self.state.is_one_of(planned_states)  # Tell, Don't Ask

    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Story({self.story_id}, "
            f"title='{self.title.value[:30]}...', "
            f"state={self.state}, "
            f"dor={self.dor_score})"
        )

