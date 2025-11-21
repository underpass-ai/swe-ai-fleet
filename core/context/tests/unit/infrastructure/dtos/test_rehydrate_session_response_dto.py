"""Tests for RehydrateSessionResponseDTO."""

import pytest

from core.context.infrastructure.dtos.rehydrate_session_response_dto import (
    RehydrateSessionResponseDTO,
)
from core.context.infrastructure.dtos.rehydration_stats_dto import (
    RehydrationStatsDTO,
)


class TestRehydrateSessionResponseDTO:
    """Test RehydrateSessionResponseDTO."""

    def test_create_response_dto_success(self) -> None:
        """Test creating response DTO with valid data."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        assert dto.case_id == "case-1"
        assert dto.status == "success"
        assert dto.generated_at_ms == 1000
        assert dto.packs_count == 2
        assert dto.stats is stats

    def test_create_response_dto_with_different_status(self) -> None:
        """Test creating response DTO with different status values."""
        stats = RehydrationStatsDTO(
            decisions=0,
            decision_edges=0,
            impacts=0,
            events=0,
            roles=[],
        )

        dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="error",
            generated_at_ms=0,
            packs_count=0,
            stats=stats,
        )

        assert dto.status == "error"
        assert dto.packs_count == 0

    def test_response_dto_is_immutable(self) -> None:
        """Test that response DTO is immutable (frozen dataclass)."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            dto.case_id = "case-2"  # type: ignore

    def test_response_dto_equality(self) -> None:
        """Test response DTO equality comparison."""
        stats1 = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        stats2 = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto1 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats1,
        )

        dto2 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats2,
        )

        assert dto1 == dto2

    def test_response_dto_inequality_different_case_id(self) -> None:
        """Test response DTO inequality with different case_id."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto1 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        dto2 = RehydrateSessionResponseDTO(
            case_id="case-2",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        assert dto1 != dto2

    def test_response_dto_inequality_different_stats(self) -> None:
        """Test response DTO inequality with different stats."""
        stats1 = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        stats2 = RehydrationStatsDTO(
            decisions=10,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto1 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats1,
        )

        dto2 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats2,
        )

        assert dto1 != dto2

    def test_response_dto_inequality_different_packs_count(self) -> None:
        """Test response DTO inequality with different packs_count."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        dto1 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=2,
            stats=stats,
        )

        dto2 = RehydrateSessionResponseDTO(
            case_id="case-1",
            status="success",
            generated_at_ms=1000,
            packs_count=3,
            stats=stats,
        )

        assert dto1 != dto2

