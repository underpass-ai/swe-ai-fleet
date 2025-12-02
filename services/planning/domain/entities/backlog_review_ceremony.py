"""Backlog Review Ceremony entity."""

from dataclasses import dataclass
from datetime import datetime

from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)


@dataclass(frozen=True)
class BacklogReviewCeremony:
    """
    Ceremonia de revisión del backlog.

    Coordina la revisión de historias por múltiples roles (Architect, QA, DevOps)
    con participación del PO (humano) como moderador.

    Domain Invariants:
    - ceremony_id must be unique
    - created_by must be PO user (valid UserName)
    - story_ids can be empty (PO puede iniciar sin historias)
    - status transitions must follow FSM rules
    - If status is IN_PROGRESS or later, started_at must be set
    - If status is COMPLETED, completed_at must be set

    Immutability: frozen=True ensures no mutation after creation.
    Use builder methods to create new instances with updated values.
    """

    ceremony_id: BacklogReviewCeremonyId
    created_by: UserName
    story_ids: tuple[StoryId, ...]
    status: BacklogReviewCeremonyStatus
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    review_results: tuple[StoryReviewResult, ...] = ()

    def __post_init__(self) -> None:
        """
        Fail-fast validation.

        Raises:
            ValueError: If any invariant is violated.
        """
        if not self.created_by.value.strip():
            raise ValueError("created_by cannot be empty")

        if self.created_at > self.updated_at:
            raise ValueError(
                f"created_at ({self.created_at}) cannot be after "
                f"updated_at ({self.updated_at})"
            )

        # Status-specific validations
        if self.status.is_in_progress() or self.status.is_reviewing():
            if not self.started_at:
                raise ValueError(
                    f"{self.status.to_string()} ceremony must have started_at"
                )

        if self.status.is_completed():
            if not self.completed_at:
                raise ValueError("COMPLETED ceremony must have completed_at")

    def add_story(
        self,
        story_id: StoryId,
        updated_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Add story to ceremony (creates new instance).

        Args:
            story_id: Story to add
            updated_at: Update timestamp

        Returns:
            New BacklogReviewCeremony with story added

        Raises:
            ValueError: If story already in ceremony or ceremony is completed/cancelled
        """
        if story_id in self.story_ids:
            raise ValueError(f"Story {story_id} already in ceremony")

        if self.status.is_completed() or self.status.is_cancelled():
            raise ValueError(
                f"Cannot add story to {self.status.to_string()} ceremony"
            )

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=(*self.story_ids, story_id),
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            review_results=self.review_results,
        )

    def remove_story(
        self,
        story_id: StoryId,
        updated_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Remove story from ceremony (creates new instance).

        Args:
            story_id: Story to remove
            updated_at: Update timestamp

        Returns:
            New BacklogReviewCeremony with story removed

        Raises:
            ValueError: If story not in ceremony or ceremony is completed/cancelled
        """
        if story_id not in self.story_ids:
            raise ValueError(f"Story {story_id} not in ceremony")

        if self.status.is_completed() or self.status.is_cancelled():
            raise ValueError(
                f"Cannot remove story from {self.status.to_string()} ceremony"
            )

        new_story_ids = tuple(sid for sid in self.story_ids if sid != story_id)

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=new_story_ids,
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            review_results=self.review_results,
        )

    def start(
        self,
        started_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Start ceremony (creates new instance).

        Args:
            started_at: Start timestamp

        Returns:
            New BacklogReviewCeremony with status=IN_PROGRESS

        Raises:
            ValueError: If ceremony is not in DRAFT status
        """
        if not self.status.is_draft():
            raise ValueError(
                f"Cannot start ceremony in status {self.status.to_string()}"
            )

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=self.story_ids,
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum.IN_PROGRESS
            ),
            created_at=self.created_at,
            updated_at=started_at,
            started_at=started_at,
            completed_at=None,
            review_results=self.review_results,
        )

    def mark_reviewing(
        self,
        review_results: tuple[StoryReviewResult, ...],
        updated_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Mark ceremony as reviewing (creates new instance).

        Called when all reviews are completed and awaiting PO approval.

        Args:
            review_results: Results of all story reviews
            updated_at: Update timestamp

        Returns:
            New BacklogReviewCeremony with status=REVIEWING

        Raises:
            ValueError: If ceremony is not in IN_PROGRESS status
        """
        if not self.status.is_in_progress():
            raise ValueError(
                f"Cannot mark reviewing in status {self.status.to_string()}"
            )

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=self.story_ids,
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum.REVIEWING
            ),
            created_at=self.created_at,
            updated_at=updated_at,
            started_at=self.started_at,
            completed_at=None,
            review_results=review_results,
        )

    def complete(
        self,
        completed_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Complete ceremony (creates new instance).

        Args:
            completed_at: Completion timestamp

        Returns:
            New BacklogReviewCeremony with status=COMPLETED

        Raises:
            ValueError: If ceremony is not in REVIEWING status
        """
        if not self.status.is_reviewing():
            raise ValueError(
                f"Cannot complete ceremony in status {self.status.to_string()}"
            )

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=self.story_ids,
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum.COMPLETED
            ),
            created_at=self.created_at,
            updated_at=completed_at,
            started_at=self.started_at,
            completed_at=completed_at,
            review_results=self.review_results,
        )

    def cancel(
        self,
        updated_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Cancel ceremony (creates new instance).

        Args:
            updated_at: Update timestamp

        Returns:
            New BacklogReviewCeremony with status=CANCELLED

        Raises:
            ValueError: If ceremony is already completed
        """
        if self.status.is_completed():
            raise ValueError("Cannot cancel completed ceremony")

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=self.story_ids,
            status=BacklogReviewCeremonyStatus(
                BacklogReviewCeremonyStatusEnum.CANCELLED
            ),
            created_at=self.created_at,
            updated_at=updated_at,
            started_at=self.started_at,
            completed_at=None,
            review_results=self.review_results,
        )

    def update_review_result(
        self,
        story_id: StoryId,
        review_result: StoryReviewResult,
        updated_at: datetime,
    ) -> "BacklogReviewCeremony":
        """
        Update review result for a story (creates new instance).

        Args:
            story_id: Story to update
            review_result: Updated review result
            updated_at: Update timestamp

        Returns:
            New BacklogReviewCeremony with updated review result

        Raises:
            ValueError: If story not in ceremony
        """
        if story_id not in self.story_ids:
            raise ValueError(f"Story {story_id} not in ceremony")

        # Replace existing result or add new one
        new_results = tuple(
            result if result.story_id != story_id else review_result
            for result in self.review_results
        )

        # If not found, add it
        if not any(result.story_id == story_id for result in new_results):
            new_results = (*new_results, review_result)

        return BacklogReviewCeremony(
            ceremony_id=self.ceremony_id,
            created_by=self.created_by,
            story_ids=self.story_ids,
            status=self.status,
            created_at=self.created_at,
            updated_at=updated_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            review_results=new_results,
        )


