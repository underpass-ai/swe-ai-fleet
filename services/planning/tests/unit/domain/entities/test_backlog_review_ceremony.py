"""Unit tests for BacklogReviewCeremony entity."""

from datetime import UTC, datetime

import pytest
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


class TestBacklogReviewCeremony:
    """Test suite for BacklogReviewCeremony entity."""

    @pytest.fixture
    def ceremony_id(self) -> BacklogReviewCeremonyId:
        """Fixture providing a ceremony ID."""
        return BacklogReviewCeremonyId("BRC-12345")

    @pytest.fixture
    def created_by(self) -> UserName:
        """Fixture providing a PO username."""
        return UserName("po@example.com")

    @pytest.fixture
    def created_at(self) -> datetime:
        """Fixture providing a creation timestamp."""
        return datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC)

    @pytest.fixture
    def draft_ceremony(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> BacklogReviewCeremony:
        """Fixture providing a ceremony in DRAFT status."""
        return BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=created_at,
            updated_at=created_at,
        )

    def test_create_ceremony_success(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test creating a valid ceremony."""
        ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=created_at,
            updated_at=created_at,
        )

        assert ceremony.ceremony_id == ceremony_id
        assert ceremony.created_by == created_by
        assert ceremony.story_ids == ()
        assert ceremony.status.is_draft()
        assert ceremony.started_at is None
        assert ceremony.completed_at is None
        assert ceremony.review_results == ()

    def test_create_ceremony_with_stories(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test creating ceremony with pre-selected stories."""
        story_ids = (StoryId("ST-001"), StoryId("ST-002"))

        ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=story_ids,
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=created_at,
            updated_at=created_at,
        )

        assert len(ceremony.story_ids) == 2
        assert StoryId("ST-001") in ceremony.story_ids

    def test_post_init_created_by_empty_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_at: datetime,
    ) -> None:
        """Test that empty created_by raises ValueError (from UserName validation)."""
        # UserName itself validates in __post_init__, so error comes from there
        with pytest.raises(ValueError, match="UserName cannot be empty"):
            BacklogReviewCeremony(
                ceremony_id=ceremony_id,
                created_by=UserName("   "),  # Fails in UserName.__post_init__
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
                created_at=created_at,
                updated_at=created_at,
            )

    def test_post_init_created_at_after_updated_at_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
    ) -> None:
        """Test that created_at > updated_at raises ValueError."""
        created_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)
        updated_at = datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC)  # Earlier!

        with pytest.raises(ValueError, match="created_at .* cannot be after updated_at"):
            BacklogReviewCeremony(
                ceremony_id=ceremony_id,
                created_by=created_by,
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
                created_at=created_at,
                updated_at=updated_at,
            )

    def test_post_init_in_progress_requires_started_at(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that IN_PROGRESS status requires started_at."""
        with pytest.raises(ValueError, match="IN_PROGRESS ceremony must have started_at"):
            BacklogReviewCeremony(
                ceremony_id=ceremony_id,
                created_by=created_by,
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
                created_at=created_at,
                updated_at=created_at,
                started_at=None,  # Missing!
            )

    def test_post_init_reviewing_requires_started_at(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that REVIEWING status requires started_at."""
        with pytest.raises(ValueError, match="REVIEWING ceremony must have started_at"):
            BacklogReviewCeremony(
                ceremony_id=ceremony_id,
                created_by=created_by,
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
                created_at=created_at,
                updated_at=created_at,
                started_at=None,  # Missing!
            )

    def test_post_init_completed_requires_completed_at(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that COMPLETED status requires completed_at."""
        with pytest.raises(ValueError, match="COMPLETED ceremony must have completed_at"):
            BacklogReviewCeremony(
                ceremony_id=ceremony_id,
                created_by=created_by,
                story_ids=(),
                status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
                created_at=created_at,
                updated_at=created_at,
                started_at=created_at,
                completed_at=None,  # Missing!
            )

    def test_add_story_success(self, draft_ceremony: BacklogReviewCeremony) -> None:
        """Test successfully adding a story to ceremony."""
        story_id = StoryId("ST-001")
        updated_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_ceremony = draft_ceremony.add_story(story_id, updated_at)

        assert len(updated_ceremony.story_ids) == 1
        assert StoryId("ST-001") in updated_ceremony.story_ids
        assert updated_ceremony.updated_at == updated_at

    def test_add_story_creates_new_instance(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that add_story creates a new instance (immutability)."""
        story_id = StoryId("ST-001")
        updated_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_ceremony = draft_ceremony.add_story(story_id, updated_at)

        # Original unchanged
        assert len(draft_ceremony.story_ids) == 0
        # New instance created
        assert len(updated_ceremony.story_ids) == 1

    def test_add_story_duplicate_raises_value_error(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that adding duplicate story raises ValueError."""
        story_id = StoryId("ST-001")
        updated_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        updated_ceremony = draft_ceremony.add_story(story_id, updated_at)

        with pytest.raises(ValueError, match="Story .* already in ceremony"):
            updated_ceremony.add_story(story_id, updated_at)

    def test_add_story_to_completed_ceremony_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that adding story to completed ceremony raises ValueError."""
        completed_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
            completed_at=created_at,
        )

        with pytest.raises(ValueError, match="Cannot add story to COMPLETED ceremony"):
            completed_ceremony.add_story(StoryId("ST-001"), created_at)

    def test_add_story_to_cancelled_ceremony_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that adding story to cancelled ceremony raises ValueError."""
        cancelled_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.CANCELLED),
            created_at=created_at,
            updated_at=created_at,
        )

        with pytest.raises(ValueError, match="Cannot add story to CANCELLED ceremony"):
            cancelled_ceremony.add_story(StoryId("ST-001"), created_at)

    def test_remove_story_success(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test successfully removing a story from ceremony."""
        story_ids = (StoryId("ST-001"), StoryId("ST-002"))
        ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=story_ids,
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.DRAFT),
            created_at=created_at,
            updated_at=created_at,
        )

        updated_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)
        updated_ceremony = ceremony.remove_story(StoryId("ST-001"), updated_at)

        assert len(updated_ceremony.story_ids) == 1
        assert StoryId("ST-002") in updated_ceremony.story_ids
        assert StoryId("ST-001") not in updated_ceremony.story_ids

    def test_remove_story_not_in_ceremony_raises_value_error(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that removing non-existent story raises ValueError."""
        with pytest.raises(ValueError, match="Story .* not in ceremony"):
            draft_ceremony.remove_story(
                StoryId("ST-999"),
                datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            )

    def test_remove_story_from_completed_ceremony_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that removing story from completed ceremony raises ValueError."""
        completed_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
            completed_at=created_at,
        )

        with pytest.raises(ValueError, match="Cannot remove story from COMPLETED ceremony"):
            completed_ceremony.remove_story(StoryId("ST-001"), created_at)

    def test_start_ceremony_success(self, draft_ceremony: BacklogReviewCeremony) -> None:
        """Test successfully starting a ceremony."""
        started_at = datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC)

        started_ceremony = draft_ceremony.start(started_at)

        assert started_ceremony.status.is_in_progress()
        assert started_ceremony.started_at == started_at
        assert started_ceremony.updated_at == started_at

    def test_start_ceremony_wrong_status_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that starting non-draft ceremony raises ValueError."""
        in_progress_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
        )

        with pytest.raises(ValueError, match="Cannot start ceremony in status"):
            in_progress_ceremony.start(datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC))

    def test_mark_reviewing_success(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test successfully marking ceremony as reviewing."""
        in_progress_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
        )

        review_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("DEVELOPER",),
                estimated_complexity="LOW",
                dependencies=(),
            ),
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=created_at,
        )

        updated_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)
        reviewing_ceremony = in_progress_ceremony.mark_reviewing((review_result,), updated_at)

        assert reviewing_ceremony.status.is_reviewing()
        assert len(reviewing_ceremony.review_results) == 1

    def test_mark_reviewing_wrong_status_raises_value_error(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that marking draft as reviewing raises ValueError."""
        with pytest.raises(ValueError, match="Cannot mark reviewing in status"):
            draft_ceremony.mark_reviewing((), datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC))

    def test_complete_ceremony_success(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test successfully completing a ceremony."""
        reviewing_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
        )

        completed_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)
        completed_ceremony = reviewing_ceremony.complete(completed_at)

        assert completed_ceremony.status.is_completed()
        assert completed_ceremony.completed_at == completed_at

    def test_complete_ceremony_wrong_status_raises_value_error(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that completing non-reviewing ceremony raises ValueError."""
        with pytest.raises(ValueError, match="Cannot complete ceremony in status"):
            draft_ceremony.complete(datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC))

    def test_cancel_ceremony_success(self, draft_ceremony: BacklogReviewCeremony) -> None:
        """Test successfully cancelling a ceremony."""
        updated_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)

        cancelled_ceremony = draft_ceremony.cancel(updated_at)

        assert cancelled_ceremony.status.is_cancelled()
        assert cancelled_ceremony.updated_at == updated_at

    def test_cancel_completed_ceremony_raises_value_error(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test that cancelling completed ceremony raises ValueError."""
        completed_ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
            completed_at=created_at,
        )

        with pytest.raises(ValueError, match="Cannot cancel completed ceremony"):
            completed_ceremony.cancel(datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC))

    def test_update_review_result_success(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        created_by: UserName,
        created_at: datetime,
    ) -> None:
        """Test successfully updating review result."""
        ceremony = BacklogReviewCeremony(
            ceremony_id=ceremony_id,
            created_by=created_by,
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=created_at,
            updated_at=created_at,
            started_at=created_at,
        )

        review_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=None,
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=created_at,
        )

        updated_at = datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC)
        updated_ceremony = ceremony.update_review_result(
            StoryId("ST-001"), review_result, updated_at
        )

        assert len(updated_ceremony.review_results) == 1
        assert updated_ceremony.review_results[0].story_id == StoryId("ST-001")

    def test_update_review_result_story_not_in_ceremony_raises_value_error(
        self, draft_ceremony: BacklogReviewCeremony
    ) -> None:
        """Test that updating result for non-existent story raises ValueError."""
        review_result = StoryReviewResult(
            story_id=StoryId("ST-999"),
            plan_preliminary=None,
            architect_feedback="Good",
            qa_feedback="Good",
            devops_feedback="Good",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
        )

        with pytest.raises(ValueError, match="Story .* not in ceremony"):
            draft_ceremony.update_review_result(
                StoryId("ST-999"),
                review_result,
                datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            )

    def test_immutability(self, draft_ceremony: BacklogReviewCeremony) -> None:
        """Test that ceremony is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            draft_ceremony.status = BacklogReviewCeremonyStatus(  # type: ignore
                BacklogReviewCeremonyStatusEnum.COMPLETED
            )

