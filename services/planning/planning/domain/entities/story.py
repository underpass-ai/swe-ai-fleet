"""Story entity - Aggregate Root."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects import StoryId, StoryState, StoryStateEnum, DORScore


@dataclass(frozen=True)
class Story:
    """
    Aggregate Root: User Story in the planning system.
    
    Responsibilities:
    - Manage story lifecycle (FSM transitions)
    - Validate state transitions
    - Calculate DoR score
    - Maintain story metadata
    
    Domain Invariants:
    - Story ID must be unique
    - Title cannot be empty
    - Brief cannot be empty
    - State transitions must follow FSM rules
    - DoR score must be 0-100
    - Created timestamp must be set
    
    Immutability: frozen=True ensures no mutation after creation.
    Use builder methods to create new instances with updated values.
    """
    
    story_id: StoryId
    title: str
    brief: str
    state: StoryState
    dor_score: DORScore
    created_by: str
    created_at: datetime
    updated_at: datetime
    
    def __post_init__(self) -> None:
        """
        Fail-fast validation.
        
        Raises:
            ValueError: If any invariant is violated.
        """
        if not self.title:
            raise ValueError("Story title cannot be empty")
        
        if not self.title.strip():
            raise ValueError("Story title cannot be whitespace")
        
        if not self.brief:
            raise ValueError("Story brief cannot be empty")
        
        if not self.brief.strip():
            raise ValueError("Story brief cannot be whitespace")
        
        if not self.created_by:
            raise ValueError("created_by cannot be empty")
        
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
        
        update_time = updated_at or datetime.utcnow()
        
        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )
        
        # Return new instance (immutable)
        return Story(
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
        update_time = updated_at or datetime.utcnow()
        
        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )
        
        return Story(
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
        title: str | None = None,
        brief: str | None = None,
        updated_at: datetime | None = None,
    ) -> "Story":
        """
        Update story content (title and/or brief).
        
        Business Rule: Content can be updated while in DRAFT or PO_REVIEW states.
        
        Args:
            title: New title (optional, keeps current if None).
            brief: New brief (optional, keeps current if None).
            updated_at: Timestamp of update (defaults to now).
        
        Returns:
            New Story instance with updated content.
        
        Raises:
            ValueError: If updated_at is invalid or content is empty.
        """
        new_title = title if title is not None else self.title
        new_brief = brief if brief is not None else self.brief
        
        if not new_title or not new_title.strip():
            raise ValueError("Title cannot be empty or whitespace")
        
        if not new_brief or not new_brief.strip():
            raise ValueError("Brief cannot be empty or whitespace")
        
        update_time = updated_at or datetime.utcnow()
        
        if update_time < self.created_at:
            raise ValueError(
                f"updated_at ({update_time}) cannot be before "
                f"created_at ({self.created_at})"
            )
        
        return Story(
            story_id=self.story_id,
            title=new_title,
            brief=new_brief,
            state=self.state,
            dor_score=self.dor_score,
            created_by=self.created_by,
            created_at=self.created_at,
            updated_at=update_time,
        )
    
    def is_ready_for_planning(self) -> bool:
        """
        Check if story is ready for planning.
        
        Business Rules:
        - DoR score >= 80
        - State is READY_FOR_PLANNING or later
        
        Returns:
            True if ready for planning, False otherwise.
        """
        ready_states = {
            StoryStateEnum.READY_FOR_PLANNING,
            StoryStateEnum.IN_PROGRESS,
            StoryStateEnum.CODE_REVIEW,
            StoryStateEnum.TESTING,
            StoryStateEnum.DONE,
            StoryStateEnum.ARCHIVED,
        }
        
        return (
            self.dor_score.is_ready()
            and self.state.value in ready_states
        )
    
    def __str__(self) -> str:
        """String representation for logging."""
        return (
            f"Story({self.story_id}, "
            f"title='{self.title[:30]}...', "
            f"state={self.state}, "
            f"dor={self.dor_score})"
        )

