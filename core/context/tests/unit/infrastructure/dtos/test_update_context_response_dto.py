"""Tests for UpdateContextResponseDTO."""

import pytest

from core.context.infrastructure.dtos.update_context_response_dto import (
    UpdateContextResponseDTO,
)


class TestUpdateContextResponseDTO:
    """Test UpdateContextResponseDTO."""

    def test_create_dto_success(self) -> None:
        """Test creating DTO with valid data."""
        dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=["warning1", "warning2"],
        )

        assert dto.story_id == "story-1"
        assert dto.status == "success"
        assert dto.version == 1
        assert dto.hash == "abc123"
        assert dto.warnings == ["warning1", "warning2"]

    def test_create_dto_with_empty_warnings(self) -> None:
        """Test creating DTO with empty warnings list."""
        dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=0,
            hash="abc123",
            warnings=[],
        )

        assert dto.warnings == []

    def test_dto_is_immutable(self) -> None:
        """Test that DTO is immutable (frozen dataclass)."""
        dto = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            dto.story_id = "story-2"  # type: ignore

    def test_dto_equality(self) -> None:
        """Test DTO equality comparison."""
        dto1 = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        dto2 = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        assert dto1 == dto2

    def test_dto_inequality(self) -> None:
        """Test DTO inequality comparison."""
        dto1 = UpdateContextResponseDTO(
            story_id="story-1",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        dto2 = UpdateContextResponseDTO(
            story_id="story-2",
            status="success",
            version=1,
            hash="abc123",
            warnings=[],
        )

        assert dto1 != dto2

