"""Domain entities for Task Extraction Service."""

from backlog_review_processor.domain.entities.backlog_review_result import (
    BacklogReviewResult,
)
from backlog_review_processor.domain.entities.extracted_task import ExtractedTask

__all__ = [
    "BacklogReviewResult",
    "ExtractedTask",
]

