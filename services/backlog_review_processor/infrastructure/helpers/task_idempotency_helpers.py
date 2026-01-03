"""Helper functions for task idempotency in Backlog Review Processor.

Provides deterministic request_id generation for task creation commands.
"""

import hashlib
from typing import Any

from backlog_review_processor.domain.entities.extracted_task import ExtractedTask
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId


def generate_task_fingerprint(
    title: str,
    description: str,
    estimated_hours: int,
    deliberation_indices: list[int],
) -> str:
    """Generate deterministic fingerprint for a task.

    The fingerprint is a SHA-256 hash of task content fields that uniquely
    identify a task within a story/ceremony context.

    Args:
        title: Task title
        description: Task description
        estimated_hours: Estimated hours
        deliberation_indices: List of deliberation indices

    Returns:
        Deterministic task fingerprint (SHA-256 hex digest, first 16 chars)
    """
    # Sort deliberation_indices for deterministic hash
    sorted_indices = sorted(deliberation_indices)

    # Build components for hash (normalize strings)
    components = [
        title.strip().lower(),
        description.strip().lower(),
        str(estimated_hours),
        ",".join(str(idx) for idx in sorted_indices),
    ]

    # Create deterministic hash
    content = "|".join(components)
    fingerprint = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    return fingerprint


def generate_task_request_id(
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    task_fingerprint: str,
) -> str:
    """Generate deterministic request_id for task creation command.

    Format: planning:create_task:{ceremony_id}:{story_id}:{task_fingerprint}

    This ensures that the same task (same content) extracted from the same
    ceremony/story will have the same request_id, making the CreateTask
    command idempotent.

    Args:
        ceremony_id: Ceremony identifier
        story_id: Story identifier
        task_fingerprint: Task fingerprint (from generate_task_fingerprint)

    Returns:
        Deterministic request_id for CreateTask command
    """
    return f"planning:create_task:{ceremony_id.value}:{story_id.value}:{task_fingerprint}"


def generate_request_id_from_extracted_task(
    extracted_task: ExtractedTask,
) -> str:
    """Generate request_id from ExtractedTask domain entity.

    Convenience function that combines fingerprint generation and request_id
    generation from an ExtractedTask.

    Args:
        extracted_task: ExtractedTask domain entity

    Returns:
        Deterministic request_id for CreateTask command
    """
    fingerprint = generate_task_fingerprint(
        title=extracted_task.title,
        description=extracted_task.description,
        estimated_hours=extracted_task.estimated_hours,
        deliberation_indices=extracted_task.deliberation_indices,
    )

    return generate_task_request_id(
        ceremony_id=extracted_task.ceremony_id,
        story_id=extracted_task.story_id,
        task_fingerprint=fingerprint,
    )
