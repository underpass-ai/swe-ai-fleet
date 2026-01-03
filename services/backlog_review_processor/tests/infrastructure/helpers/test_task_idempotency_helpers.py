"""Unit tests for task idempotency helper functions."""

import pytest

from backlog_review_processor.domain.entities.extracted_task import ExtractedTask
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.infrastructure.helpers.task_idempotency_helpers import (
    generate_request_id_from_extracted_task,
    generate_task_fingerprint,
    generate_task_request_id,
)


class TestGenerateTaskFingerprint:
    """Tests for generate_task_fingerprint function."""

    def test_generate_fingerprint_deterministic(self):
        """Test that fingerprint is deterministic for same input."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        assert fingerprint1 == fingerprint2
        assert len(fingerprint1) == 16  # First 16 chars of SHA-256

    def test_generate_fingerprint_different_for_different_titles(self):
        """Test that different titles produce different fingerprints."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title 1",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title 2",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        assert fingerprint1 != fingerprint2

    def test_generate_fingerprint_different_for_different_descriptions(self):
        """Test that different descriptions produce different fingerprints."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title",
            description="Description 1",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title",
            description="Description 2",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        assert fingerprint1 != fingerprint2

    def test_generate_fingerprint_different_for_different_hours(self):
        """Test that different estimated_hours produce different fingerprints."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=16,
            deliberation_indices=[0, 1],
        )

        assert fingerprint1 != fingerprint2

    def test_generate_fingerprint_different_for_different_indices(self):
        """Test that different deliberation_indices produce different fingerprints."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[2, 3],
        )

        assert fingerprint1 != fingerprint2

    def test_generate_fingerprint_sorts_indices(self):
        """Test that deliberation_indices are sorted for deterministic hash."""
        fingerprint1 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[1, 0],  # Unsorted
        )
        fingerprint2 = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],  # Sorted
        )

        assert fingerprint1 == fingerprint2

    def test_generate_fingerprint_normalizes_strings(self):
        """Test that strings are normalized (trimmed and lowercased)."""
        fingerprint1 = generate_task_fingerprint(
            title="  Task Title  ",
            description="  Task Description  ",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        fingerprint2 = generate_task_fingerprint(
            title="task title",
            description="task description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        assert fingerprint1 == fingerprint2

    def test_generate_fingerprint_empty_indices(self):
        """Test fingerprint generation with empty deliberation_indices."""
        fingerprint = generate_task_fingerprint(
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[],
        )

        assert len(fingerprint) == 16
        assert isinstance(fingerprint, str)


class TestGenerateTaskRequestId:
    """Tests for generate_task_request_id function."""

    def test_generate_request_id_format(self):
        """Test that request_id follows expected format."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")
        fingerprint = "abc123def4567890"

        request_id = generate_task_request_id(ceremony_id, story_id, fingerprint)

        assert request_id == "planning:create_task:BRC-12345:ST-001:abc123def4567890"

    def test_generate_request_id_deterministic(self):
        """Test that request_id is deterministic for same input."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")
        fingerprint = "abc123def4567890"

        request_id1 = generate_task_request_id(ceremony_id, story_id, fingerprint)
        request_id2 = generate_task_request_id(ceremony_id, story_id, fingerprint)

        assert request_id1 == request_id2

    def test_generate_request_id_different_for_different_ceremonies(self):
        """Test that different ceremony_ids produce different request_ids."""
        story_id = StoryId("ST-001")
        fingerprint = "abc123def4567890"

        request_id1 = generate_task_request_id(
            BacklogReviewCeremonyId("BRC-12345"), story_id, fingerprint
        )
        request_id2 = generate_task_request_id(
            BacklogReviewCeremonyId("BRC-67890"), story_id, fingerprint
        )

        assert request_id1 != request_id2

    def test_generate_request_id_different_for_different_stories(self):
        """Test that different story_ids produce different request_ids."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        fingerprint = "abc123def4567890"

        request_id1 = generate_task_request_id(
            ceremony_id, StoryId("ST-001"), fingerprint
        )
        request_id2 = generate_task_request_id(
            ceremony_id, StoryId("ST-002"), fingerprint
        )

        assert request_id1 != request_id2

    def test_generate_request_id_different_for_different_fingerprints(self):
        """Test that different fingerprints produce different request_ids."""
        ceremony_id = BacklogReviewCeremonyId("BRC-12345")
        story_id = StoryId("ST-001")

        request_id1 = generate_task_request_id(
            ceremony_id, story_id, "abc123def4567890"
        )
        request_id2 = generate_task_request_id(
            ceremony_id, story_id, "xyz789abc1234567"
        )

        assert request_id1 != request_id2


class TestGenerateRequestIdFromExtractedTask:
    """Tests for generate_request_id_from_extracted_task function."""

    def test_generate_from_extracted_task(self):
        """Test request_id generation from ExtractedTask."""
        extracted_task = ExtractedTask(
            story_id=StoryId("ST-001"),
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        request_id = generate_request_id_from_extracted_task(extracted_task)

        assert request_id.startswith("planning:create_task:BRC-12345:ST-001:")
        assert len(request_id) > len("planning:create_task:BRC-12345:ST-001:")

    def test_generate_from_extracted_task_deterministic(self):
        """Test that same ExtractedTask produces same request_id."""
        extracted_task = ExtractedTask(
            story_id=StoryId("ST-001"),
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            title="Task Title",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        request_id1 = generate_request_id_from_extracted_task(extracted_task)
        request_id2 = generate_request_id_from_extracted_task(extracted_task)

        assert request_id1 == request_id2

    def test_generate_from_extracted_task_different_tasks(self):
        """Test that different ExtractedTasks produce different request_ids."""
        task1 = ExtractedTask(
            story_id=StoryId("ST-001"),
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            title="Task Title 1",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )
        task2 = ExtractedTask(
            story_id=StoryId("ST-001"),
            ceremony_id=BacklogReviewCeremonyId("BRC-12345"),
            title="Task Title 2",
            description="Task Description",
            estimated_hours=8,
            deliberation_indices=[0, 1],
        )

        request_id1 = generate_request_id_from_extracted_task(task1)
        request_id2 = generate_request_id_from_extracted_task(task2)

        assert request_id1 != request_id2
