"""Tests for RehydrationStatsDTO."""

import pytest

from core.context.infrastructure.dtos.rehydration_stats_dto import (
    RehydrationStatsDTO,
)


class TestRehydrationStatsDTO:
    """Test RehydrationStatsDTO."""

    def test_create_stats_dto_success(self) -> None:
        """Test creating stats DTO with valid data."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV", "QA"],
        )

        assert stats.decisions == 5
        assert stats.decision_edges == 10
        assert stats.impacts == 3
        assert stats.events == 2
        assert stats.roles == ["DEV", "QA"]

    def test_create_stats_dto_with_empty_roles(self) -> None:
        """Test creating stats DTO with empty roles list."""
        stats = RehydrationStatsDTO(
            decisions=0,
            decision_edges=0,
            impacts=0,
            events=0,
            roles=[],
        )

        assert stats.roles == []

    def test_stats_dto_is_immutable(self) -> None:
        """Test that stats DTO is immutable (frozen dataclass)."""
        stats = RehydrationStatsDTO(
            decisions=5,
            decision_edges=10,
            impacts=3,
            events=2,
            roles=["DEV"],
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            stats.decisions = 10  # type: ignore

    def test_stats_dto_equality(self) -> None:
        """Test stats DTO equality comparison."""
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

        assert stats1 == stats2

    def test_stats_dto_inequality(self) -> None:
        """Test stats DTO inequality comparison."""
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

        assert stats1 != stats2

