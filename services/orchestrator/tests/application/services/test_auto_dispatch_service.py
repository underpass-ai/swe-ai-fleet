from typing import Any

import pytest

from services.orchestrator.application.services.auto_dispatch_service import AutoDispatchService
from services.orchestrator.domain.entities import PlanApprovedEvent


class MockDeliberationResult:
    def __init__(self, results: list[Any], duration_ms: int) -> None:
        self.results = results
        self.duration_ms = duration_ms


class TestAutoDispatchService:
    @pytest.mark.asyncio
    async def test_dispatch_deliberations_for_plan_with_no_roles_returns_empty(self, mocker) -> None:
        mock_council_query = mocker.MagicMock()
        mock_registry = mocker.MagicMock()
        mock_stats = mocker.MagicMock()
        mock_messaging = mocker.MagicMock()

        service = AutoDispatchService(
            council_query=mock_council_query,
            council_registry=mock_registry,
            stats=mock_stats,
            messaging=mock_messaging,
        )

        event = PlanApprovedEvent(
            story_id="story-1",
            plan_id="plan-1",
            approved_by="user-1",
            roles=[],
            timestamp="2025-01-01T00:00:00Z",
        )

        result = await service.dispatch_deliberations_for_plan(event)

        assert result["total_roles"] == 0
        assert result["successful"] == 0
        assert result["failed"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_dispatch_deliberations_for_plan_dispatches_all_roles(self, mocker) -> None:
        mock_council_query = mocker.MagicMock()
        mock_council_query.has_council.return_value = True

        mock_registry = mocker.MagicMock()
        mock_council = mocker.MagicMock()
        mock_registry.get_council.return_value = mock_council

        mock_stats = mocker.MagicMock()
        mock_messaging = mocker.MagicMock()

        mock_deliberate_uc = mocker.AsyncMock()
        mock_deliberate_uc.execute.return_value = MockDeliberationResult(results=[1, 2, 3], duration_ms=1000)

        mocker.patch(
            "services.orchestrator.application.services.auto_dispatch_service.DeliberateUseCase",
            return_value=mock_deliberate_uc,
        )

        service = AutoDispatchService(
            council_query=mock_council_query,
            council_registry=mock_registry,
            stats=mock_stats,
            messaging=mock_messaging,
        )

        event = PlanApprovedEvent(
            story_id="story-1",
            plan_id="plan-1",
            approved_by="user-1",
            roles=["DEV", "QA"],
            timestamp="2025-01-01T00:00:00Z",
        )

        result = await service.dispatch_deliberations_for_plan(event)

        assert result["total_roles"] == 2
        assert result["successful"] == 2
        assert result["failed"] == 0
        assert len(result["results"]) == 2
        assert all(r["success"] for r in result["results"])

    @pytest.mark.asyncio
    async def test_dispatch_deliberations_for_plan_handles_missing_council(self, mocker) -> None:
        mock_council_query = mocker.MagicMock()
        mock_council_query.has_council.return_value = False

        mock_registry = mocker.MagicMock()
        mock_stats = mocker.MagicMock()
        mock_messaging = mocker.MagicMock()

        service = AutoDispatchService(
            council_query=mock_council_query,
            council_registry=mock_registry,
            stats=mock_stats,
            messaging=mock_messaging,
        )

        event = PlanApprovedEvent(
            story_id="story-1",
            plan_id="plan-1",
            approved_by="user-1",
            roles=["MISSING"],
            timestamp="2025-01-01T00:00:00Z",
        )

        result = await service.dispatch_deliberations_for_plan(event)

        assert result["total_roles"] == 1
        assert result["successful"] == 0
        assert result["failed"] == 1
        assert result["results"][0]["success"] is False
        assert "Council for role" in result["results"][0]["error"]

    @pytest.mark.asyncio
    async def test_dispatch_deliberations_for_plan_continues_on_error(self, mocker) -> None:
        mock_council_query = mocker.MagicMock()
        mock_council_query.has_council.side_effect = [True, False]

        mock_registry = mocker.MagicMock()
        mock_council = mocker.MagicMock()
        mock_registry.get_council.return_value = mock_council

        mock_stats = mocker.MagicMock()
        mock_messaging = mocker.MagicMock()

        mock_deliberate_uc = mocker.AsyncMock()
        mock_deliberate_uc.execute.return_value = MockDeliberationResult(results=[1], duration_ms=500)

        mocker.patch(
            "services.orchestrator.application.services.auto_dispatch_service.DeliberateUseCase",
            return_value=mock_deliberate_uc,
        )

        service = AutoDispatchService(
            council_query=mock_council_query,
            council_registry=mock_registry,
            stats=mock_stats,
            messaging=mock_messaging,
        )

        event = PlanApprovedEvent(
            story_id="story-1",
            plan_id="plan-1",
            approved_by="user-1",
            roles=["DEV", "MISSING"],
            timestamp="2025-01-01T00:00:00Z",
        )

        result = await service.dispatch_deliberations_for_plan(event)

        assert result["total_roles"] == 2
        assert result["successful"] == 1
        assert result["failed"] == 1
