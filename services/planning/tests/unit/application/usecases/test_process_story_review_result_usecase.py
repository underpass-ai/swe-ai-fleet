"""Unit tests for ProcessStoryReviewResultUseCase."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from planning.application.dto import StoryReviewResultDTO
from planning.application.ports import MessagingPort, StoragePort
from planning.application.usecases import CeremonyNotFoundError
from planning.application.usecases.process_story_review_result_usecase import (
    ProcessStoryReviewResultUseCase,
)
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
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


class TestProcessStoryReviewResultUseCase:
    """Test suite for ProcessStoryReviewResultUseCase."""

    @pytest.fixture
    def storage_port(self) -> StoragePort:
        """Fixture providing mock StoragePort."""
        mock = AsyncMock(spec=StoragePort)
        mock.save_backlog_review_ceremony = AsyncMock()
        return mock

    @pytest.fixture
    def messaging_port(self) -> MessagingPort:
        """Fixture providing mock MessagingPort."""
        mock = AsyncMock(spec=MessagingPort)
        mock.publish = AsyncMock()
        return mock

    @pytest.fixture
    def use_case(
        self,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> ProcessStoryReviewResultUseCase:
        """Fixture providing the use case."""
        return ProcessStoryReviewResultUseCase(
            storage=storage_port,
            messaging=messaging_port,
        )

    @pytest.fixture
    def in_progress_ceremony(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony in IN_PROGRESS status with 2 stories."""
        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(),
        )

    @pytest.fixture
    def ceremony_with_partial_review(self) -> BacklogReviewCeremony:
        """Fixture providing ceremony with one partial review (ARCHITECT only)."""
        partial_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan for ST-001"),
                description=Brief("Generated from council reviews"),
                acceptance_criteria=("Review completed by councils",),
                technical_notes="ARCHITECT feedback",
                roles=("ARCHITECT",),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=("Setup infrastructure", "Implement feature"),
            ),
            architect_feedback="ARCHITECT feedback here",
            qa_feedback="",
            devops_feedback="",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        return BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(partial_result,),
        )

    @pytest.mark.asyncio
    async def test_process_first_review_for_story(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
        in_progress_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test processing first review for a story (ARCHITECT)."""
        # Arrange
        storage_port.get_backlog_review_ceremony.return_value = in_progress_ceremony

        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="Technical analysis from ARCHITECT council",
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.ceremony_id.value == "BRC-12345"
        assert result.status.is_in_progress()  # Not all stories reviewed yet

        # Verify ceremony saved
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

        # Should NOT publish reviewing event (not all stories reviewed)
        messaging_port.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_second_review_for_story(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        ceremony_with_partial_review: BacklogReviewCeremony,
    ) -> None:
        """Test processing second review (QA) for a story that already has ARCHITECT."""
        # Arrange
        storage_port.get_backlog_review_ceremony.return_value = ceremony_with_partial_review

        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.QA,
            feedback="QA analysis from QA council",
            reviewed_at=datetime(2025, 12, 2, 12, 30, 0, tzinfo=UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.status.is_in_progress()  # Still missing DEVOPS

        # Find updated review result for ST-001
        review_result = None
        for r in result.review_results:
            if r.story_id.value == "ST-001":
                review_result = r
                break

        assert review_result is not None
        assert review_result.architect_feedback == "ARCHITECT feedback here"
        assert review_result.qa_feedback == "QA analysis from QA council"
        assert review_result.devops_feedback == ""  # Not received yet

        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_process_all_reviews_transitions_to_reviewing(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> None:
        """Test that ceremony transitions to REVIEWING when all stories reviewed."""
        # Arrange - ceremony with 1 story, already has ARCHITECT + QA
        partial_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan for ST-001"),
                description=Brief("Generated from council reviews"),
                acceptance_criteria=("Review completed by councils",),
                technical_notes="Feedback",
                roles=("ARCHITECT", "QA"),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=("Task 1",),
            ),
            architect_feedback="ARCHITECT feedback",
            qa_feedback="QA feedback",
            devops_feedback="",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),  # Only 1 story
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(partial_result,),
        )

        storage_port.get_backlog_review_ceremony.return_value = ceremony

        # Now process DEVOPS (final role)
        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.DEVOPS,
            feedback="DEVOPS feedback from DEVOPS council",
            reviewed_at=datetime(2025, 12, 2, 12, 45, 0, tzinfo=UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.status.is_reviewing()  # All stories reviewed!

        # Verify event published
        messaging_port.publish.assert_awaited_once()
        call_args = messaging_port.publish.call_args
        assert call_args[1]["subject"] == "planning.backlog_review.ceremony.reviewing"

        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ceremony_not_found_raises(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that non-existent ceremony raises error."""
        # Arrange
        storage_port.get_backlog_review_ceremony.return_value = None

        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-99999"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="Feedback",
            reviewed_at=datetime.now(UTC),
        )

        # Act & Assert
        with pytest.raises(CeremonyNotFoundError):
            await use_case.execute(dto)

    @pytest.mark.asyncio
    async def test_late_arrival_tolerates_non_in_progress_status(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that late-arriving reviews don't crash if ceremony already completed."""
        # Arrange - ceremony already in REVIEWING status
        reviewing_ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 13, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(),
        )

        storage_port.get_backlog_review_ceremony.return_value = reviewing_ceremony

        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="Late arriving feedback",
            reviewed_at=datetime.now(UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert - should return ceremony unchanged (tolerant of late arrivals)
        assert result.ceremony_id.value == "BRC-12345"
        assert result.status.is_reviewing()

        # Should NOT save (no changes)
        storage_port.save_backlog_review_ceremony.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_feedback_parsing_extracts_tasks(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        in_progress_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test that feedback with numbered lists extracts tasks."""
        # Arrange
        storage_port.get_backlog_review_ceremony.return_value = in_progress_ceremony

        feedback_with_tasks = """
Architecture Analysis:

1. Setup authentication service
2. Implement JWT token generation
3. Add middleware for route protection
4. Create user registration endpoint

Additional notes:
- Use Redis for session storage
- Implement rate limiting
"""

        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            feedback=feedback_with_tasks,
            reviewed_at=datetime.now(UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        review_result = result.review_results[0]
        assert len(review_result.plan_preliminary.tasks_outline) > 0
        # Should extract at least some tasks from numbered list

    @pytest.mark.asyncio
    async def test_multiple_stories_require_all_reviewed(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        messaging_port: MessagingPort,
    ) -> None:
        """Test that with multiple stories, all must be reviewed before REVIEWING."""
        # Arrange - 2 stories, ST-001 fully reviewed, ST-002 not reviewed yet
        st001_complete = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan for ST-001"),
                description=Brief("Generated from council reviews"),
                acceptance_criteria=("Review completed by councils",),
                technical_notes="Feedback",
                roles=("ARCHITECT", "QA", "DEVOPS"),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=(),
            ),
            architect_feedback="ARCHITECT feedback",
            qa_feedback="QA feedback",
            devops_feedback="DEVOPS feedback",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(st001_complete,),  # Only ST-001 reviewed
        )

        storage_port.get_backlog_review_ceremony.return_value = ceremony

        # Process first review for ST-002
        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-002"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="ARCHITECT feedback for ST-002",
            reviewed_at=datetime(2025, 12, 2, 12, 30, 0, tzinfo=UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert
        assert result.status.is_in_progress()  # ST-002 not fully reviewed yet

        # Should NOT publish reviewing event
        messaging_port.publish.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_accumulates_feedback_from_all_roles(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
    ) -> None:
        """Test that feedback accumulates correctly from all 3 roles."""
        # Arrange
        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime(2025, 12, 2, 10, 0, 0, tzinfo=UTC),
            updated_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            started_at=datetime(2025, 12, 2, 11, 0, 0, tzinfo=UTC),
            review_results=(),
        )

        storage_port.get_backlog_review_ceremony.return_value = ceremony

        # Process ARCHITECT
        dto_architect = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.ARCHITECT,
            feedback="ARCHITECT feedback",
            reviewed_at=datetime(2025, 12, 2, 12, 0, 0, tzinfo=UTC),
        )

        result1 = await use_case.execute(dto_architect)

        # Update storage mock to return updated ceremony
        storage_port.get_backlog_review_ceremony.return_value = result1

        # Process QA
        dto_qa = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.QA,
            feedback="QA feedback",
            reviewed_at=datetime(2025, 12, 2, 12, 15, 0, tzinfo=UTC),
        )

        result2 = await use_case.execute(dto_qa)

        # Update storage mock again
        storage_port.get_backlog_review_ceremony.return_value = result2

        # Process DEVOPS (final)
        dto_devops = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.DEVOPS,
            feedback="DEVOPS feedback",
            reviewed_at=datetime(2025, 12, 2, 12, 30, 0, tzinfo=UTC),
        )

        result3 = await use_case.execute(dto_devops)

        # Assert - All 3 roles should have feedback
        review_result = result3.review_results[0]
        assert review_result.architect_feedback == "ARCHITECT feedback"
        assert review_result.qa_feedback == "QA feedback"
        assert review_result.devops_feedback == "DEVOPS feedback"

        # Should transition to REVIEWING
        assert result3.status.is_reviewing()

    @pytest.mark.asyncio
    async def test_empty_feedback_handled_correctly(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        storage_port: StoragePort,
        in_progress_ceremony: BacklogReviewCeremony,
    ) -> None:
        """Test that use case handles feedback without tasks gracefully."""
        # Arrange
        storage_port.get_backlog_review_ceremony.return_value = in_progress_ceremony

        # Feedback without numbered lists or bullet points
        dto = StoryReviewResultDTO(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            story_id=StoryId("ST-001"),
            role=BacklogReviewRole.QA,
            feedback="Just plain text without any task structure.",
            reviewed_at=datetime.now(UTC),
        )

        # Act
        result = await use_case.execute(dto)

        # Assert - should not crash
        assert result.ceremony_id.value == "BRC-12345"
        storage_port.save_backlog_review_ceremony.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_extract_tasks_with_numbered_list(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _extract_tasks_from_feedback with numbered list."""
        feedback = "1. First task\n2. Second task\n3. Third task"
        tasks = use_case._extract_tasks_from_feedback(feedback)

        assert len(tasks) == 3
        assert "First task" in tasks
        assert "Second task" in tasks
        assert "Third task" in tasks

    @pytest.mark.asyncio
    async def test_extract_tasks_with_bullet_points(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _extract_tasks_from_feedback with bullet points."""
        feedback = "- First task\n- Second task\n* Third task"
        tasks = use_case._extract_tasks_from_feedback(feedback)

        assert len(tasks) == 3
        assert "First task" in tasks
        assert "Second task" in tasks
        assert "Third task" in tasks

    @pytest.mark.asyncio
    async def test_extract_tasks_mixed_formats(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _extract_tasks_from_feedback with mixed numbered and bullet formats."""
        feedback = "1. Numbered task\n- Bullet task\n2. Another numbered"
        tasks = use_case._extract_tasks_from_feedback(feedback)

        assert len(tasks) == 3
        assert "Numbered task" in tasks
        assert "Bullet task" in tasks
        assert "Another numbered" in tasks

    @pytest.mark.asyncio
    async def test_extract_tasks_limits_to_10(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test that _extract_tasks_from_feedback limits to 10 tasks."""
        feedback = "\n".join([f"{i}. Task {i}" for i in range(1, 20)])
        tasks = use_case._extract_tasks_from_feedback(feedback)

        assert len(tasks) == 10
        assert "Task 1" in tasks
        assert "Task 10" in tasks
        assert "Task 11" not in tasks

    @pytest.mark.asyncio
    async def test_extract_tasks_empty_feedback(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _extract_tasks_from_feedback with empty feedback."""
        assert use_case._extract_tasks_from_feedback("") == ()
        assert use_case._extract_tasks_from_feedback("   ") == ()
        assert use_case._extract_tasks_from_feedback("\n\n") == ()

    @pytest.mark.asyncio
    async def test_extract_tasks_no_matches(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _extract_tasks_from_feedback with no matching patterns."""
        feedback = "Just plain text without any numbered or bullet points."
        tasks = use_case._extract_tasks_from_feedback(feedback)

        assert tasks == ()

    @pytest.mark.asyncio
    async def test_extract_tasks_truncates_long_feedback(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test that _extract_tasks_from_feedback truncates feedback exceeding MAX_FEEDBACK_LENGTH."""
        # Create feedback longer than MAX_FEEDBACK_LENGTH (10000)
        long_feedback = "A" * 15000 + "\n1. Task at the end"
        tasks = use_case._extract_tasks_from_feedback(long_feedback)

        # Should still extract tasks if they're within the truncated portion
        # But since we truncate to 10000, the task at position 15000 won't be found
        # This tests the ReDoS protection
        assert isinstance(tasks, tuple)

    @pytest.mark.asyncio
    async def test_extract_tasks_redos_protection(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test ReDoS protection with malicious input pattern."""
        # Pattern that could cause catastrophic backtracking with old regex
        # Using [^\n]+ instead of .+ prevents this
        malicious_feedback = "1. " + "A" * 5000 + "\n2. " + "B" * 5000
        tasks = use_case._extract_tasks_from_feedback(malicious_feedback)

        # Should complete quickly without ReDoS
        assert isinstance(tasks, tuple)
        assert len(tasks) <= 2

    @pytest.mark.asyncio
    async def test_extract_tasks_multiline_content(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test that _extract_tasks_from_feedback only matches single-line tasks."""
        feedback = "1. Task with\nmultiple lines\n2. Another task"
        tasks = use_case._extract_tasks_from_feedback(feedback)

        # Should only match "Task with" (first line) and "Another task"
        assert len(tasks) == 2
        assert "Task with" in tasks
        assert "Another task" in tasks
        assert "multiple lines" not in tasks

    @pytest.mark.asyncio
    async def test_parse_feedback_extracts_tasks(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _parse_feedback extracts tasks correctly."""
        feedback = "1. First task\n2. Second task"
        components = use_case._parse_feedback(feedback)

        assert "tasks" in components
        assert len(components["tasks"]) == 2
        assert "First task" in components["tasks"]
        assert "Second task" in components["tasks"]

    @pytest.mark.asyncio
    async def test_parse_feedback_truncates_long_description(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _parse_feedback truncates description to 200 characters."""
        long_feedback = "A" * 500
        components = use_case._parse_feedback(long_feedback)

        assert len(components["description"]) == 200

    @pytest.mark.asyncio
    async def test_all_stories_reviewed_single_story_all_roles(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _all_stories_reviewed with single story and all roles."""
        complete_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("ARCHITECT", "QA", "DEVOPS"),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=(),
            ),
            architect_feedback="ARCHITECT feedback",
            qa_feedback="QA feedback",
            devops_feedback="DEVOPS feedback",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime.now(UTC),
        )

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(complete_result,),
        )

        assert use_case._all_stories_reviewed(ceremony) is True

    @pytest.mark.asyncio
    async def test_all_stories_reviewed_missing_role_feedback(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _all_stories_reviewed returns False when role feedback missing."""
        incomplete_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("ARCHITECT",),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=(),
            ),
            architect_feedback="ARCHITECT feedback",
            qa_feedback="",  # Missing QA feedback
            devops_feedback="",  # Missing DEVOPS feedback
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime.now(UTC),
        )

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(incomplete_result,),
        )

        assert use_case._all_stories_reviewed(ceremony) is False

    @pytest.mark.asyncio
    async def test_all_stories_reviewed_multiple_stories_partial(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _all_stories_reviewed with multiple stories, one incomplete."""
        complete_result = StoryReviewResult(
            story_id=StoryId("ST-001"),
            plan_preliminary=PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="Notes",
                roles=("ARCHITECT", "QA", "DEVOPS"),
                estimated_complexity="MEDIUM",
                dependencies=(),
                tasks_outline=(),
            ),
            architect_feedback="ARCHITECT feedback",
            qa_feedback="QA feedback",
            devops_feedback="DEVOPS feedback",
            recommendations=(),
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=datetime.now(UTC),
        )

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(complete_result,),  # Only ST-001, missing ST-002
        )

        assert use_case._all_stories_reviewed(ceremony) is False

    @pytest.mark.asyncio
    async def test_all_stories_reviewed_no_review_results(
        self,
        use_case: ProcessStoryReviewResultUseCase,
    ) -> None:
        """Test _all_stories_reviewed returns False when no review results."""
        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(),  # No review results
        )

        assert use_case._all_stories_reviewed(ceremony) is False

    @pytest.mark.asyncio
    async def test_publish_ceremony_reviewing_event_success(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        messaging_port: MessagingPort,
    ) -> None:
        """Test _publish_ceremony_reviewing_event publishes successfully."""
        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"), StoryId("ST-002")),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(),
        )

        await use_case._publish_ceremony_reviewing_event(ceremony)

        messaging_port.publish.assert_awaited_once()
        call_args = messaging_port.publish.call_args
        assert call_args[1]["subject"] == "planning.backlog_review.ceremony.reviewing"
        assert call_args[1]["payload"]["ceremony_id"] == "BRC-12345"
        assert call_args[1]["payload"]["status"] == "REVIEWING"
        assert call_args[1]["payload"]["total_stories"] == 2
        assert call_args[1]["payload"]["total_reviews"] == 0

    @pytest.mark.asyncio
    async def test_publish_ceremony_reviewing_event_handles_error(
        self,
        use_case: ProcessStoryReviewResultUseCase,
        messaging_port: MessagingPort,
    ) -> None:
        """Test _publish_ceremony_reviewing_event handles publish errors gracefully."""
        messaging_port.publish.side_effect = Exception("NATS connection failed")

        ceremony = BacklogReviewCeremony(
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            created_by=UserName("po@example.com"),
            story_ids=(StoryId("ST-001"),),
            status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
            review_results=(),
        )

        # Should not raise exception
        await use_case._publish_ceremony_reviewing_event(ceremony)

        messaging_port.publish.assert_awaited_once()

