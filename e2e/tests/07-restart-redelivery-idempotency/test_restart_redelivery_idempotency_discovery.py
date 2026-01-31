"""Unit tests for E2E test 07 discovery logic (_find_test_data, _find_ceremony_containing_story, discover_story_and_ceremony).

These tests mock fleet.planning.v2 so they can run without generated protobuf stubs.
Run from repo root: pytest e2e/tests/07-restart-redelivery-idempotency/test_restart_redelivery_idempotency_discovery.py -v
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Mock fleet.planning.v2 before importing the E2E script (protobuf stubs not present when running pytest from repo root)
sys.modules["fleet"] = MagicMock()
sys.modules["fleet.planning"] = MagicMock()
sys.modules["fleet.planning.v2"] = MagicMock()
planning_pb2 = MagicMock()
sys.modules["fleet.planning.v2"].planning_pb2 = planning_pb2
sys.modules["fleet.planning.v2"].planning_pb2_grpc = MagicMock()

from test_restart_redelivery_idempotency import (
    CEREMONY_ID_PLACEHOLDER,
    STORY_ID_PLACEHOLDER,
    SYNTHETIC_CEREMONY_ID,
    RestartRedeliveryIdempotencyTest,
)


@pytest.fixture
def test_instance() -> RestartRedeliveryIdempotencyTest:
    """Create test instance with placeholder env (no overrides)."""
    for key in ("TEST_STORY_ID", "TEST_CEREMONY_ID", "TEST_PROJECT_NAME", "TEST_EPIC_TITLE"):
        os.environ.pop(key, None)
    return RestartRedeliveryIdempotencyTest()


@pytest.fixture
def planning_stub(test_instance: RestartRedeliveryIdempotencyTest) -> MagicMock:
    """Attach a mock planning stub to the instance (no real gRPC)."""
    stub = MagicMock()
    test_instance.planning_stub = stub
    return stub


@pytest.mark.asyncio
async def test_find_test_data_returns_first_story_id(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """_find_test_data returns first story_id when project/epic/stories exist."""
    from fleet.planning.v2 import planning_pb2  # type: ignore[import]

    project = MagicMock()
    project.name = "Test de swe fleet"
    project.project_id = "PROJ-123"
    epic = MagicMock()
    epic.title = "Autenticacion"
    epic.epic_id = "E-456"
    story = MagicMock()
    story.story_id = "s-789"
    story.title = "RBAC"

    planning_stub.ListProjects = AsyncMock(
        return_value=MagicMock(success=True, projects=[project])
    )
    planning_stub.ListEpics = AsyncMock(
        return_value=MagicMock(success=True, epics=[epic])
    )
    planning_stub.ListStories = AsyncMock(
        return_value=MagicMock(success=True, stories=[story])
    )

    result = await test_instance._find_test_data()

    assert result == "s-789"
    planning_stub.ListProjects.assert_awaited_once()
    planning_stub.ListEpics.assert_awaited_once()
    planning_stub.ListStories.assert_awaited_once()


@pytest.mark.asyncio
async def test_find_test_data_returns_none_when_no_stories(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """_find_test_data returns None when epic has no stories."""
    project = MagicMock()
    project.name = "Test de swe fleet"
    project.project_id = "PROJ-123"
    epic = MagicMock()
    epic.title = "Autenticacion"
    epic.epic_id = "E-456"

    planning_stub.ListProjects = AsyncMock(
        return_value=MagicMock(success=True, projects=[project])
    )
    planning_stub.ListEpics = AsyncMock(
        return_value=MagicMock(success=True, epics=[epic])
    )
    planning_stub.ListStories = AsyncMock(
        return_value=MagicMock(success=True, stories=[])
    )

    result = await test_instance._find_test_data()

    assert result is None


@pytest.mark.asyncio
async def test_find_test_data_returns_none_when_stub_missing(
    test_instance: RestartRedeliveryIdempotencyTest,
) -> None:
    """_find_test_data returns None when planning_stub is not set."""
    test_instance.planning_stub = None
    result = await test_instance._find_test_data()
    assert result is None


@pytest.mark.asyncio
async def test_find_ceremony_containing_story_returns_ceremony_id(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """_find_ceremony_containing_story returns ceremony_id when story is in ceremony."""
    ceremony = MagicMock()
    ceremony.ceremony_id = "BRC-abc"
    ceremony.story_ids = ["s-other", "s-789"]

    planning_stub.ListBacklogReviewCeremonies = AsyncMock(
        return_value=MagicMock(success=True, ceremonies=[ceremony])
    )

    result = await test_instance._find_ceremony_containing_story("s-789")

    assert result == "BRC-abc"


@pytest.mark.asyncio
async def test_find_ceremony_containing_story_returns_none_when_not_found(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """_find_ceremony_containing_story returns None when no ceremony contains the story."""
    ceremony = MagicMock()
    ceremony.ceremony_id = "BRC-abc"
    ceremony.story_ids = ["s-other"]

    planning_stub.ListBacklogReviewCeremonies = AsyncMock(
        return_value=MagicMock(success=True, ceremonies=[ceremony])
    )

    result = await test_instance._find_ceremony_containing_story("s-789")

    assert result is None


@pytest.mark.asyncio
async def test_discover_story_and_ceremony_when_placeholders_discovers_story(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """discover_story_and_ceremony discovers story and sets synthetic ceremony when placeholders."""
    assert test_instance.story_id == STORY_ID_PLACEHOLDER
    assert test_instance.ceremony_id == CEREMONY_ID_PLACEHOLDER

    project = MagicMock()
    project.name = "Test de swe fleet"
    project.project_id = "PROJ-123"
    epic = MagicMock()
    epic.title = "Autenticacion"
    epic.epic_id = "E-456"
    story = MagicMock()
    story.story_id = "s-789"
    story.title = "RBAC"

    planning_stub.ListProjects = AsyncMock(
        return_value=MagicMock(success=True, projects=[project])
    )
    planning_stub.ListEpics = AsyncMock(
        return_value=MagicMock(success=True, epics=[epic])
    )
    planning_stub.ListStories = AsyncMock(
        return_value=MagicMock(success=True, stories=[story])
    )
    planning_stub.ListBacklogReviewCeremonies = AsyncMock(
        return_value=MagicMock(success=True, ceremonies=[])
    )

    result = await test_instance.discover_story_and_ceremony()

    assert result is True
    assert test_instance.story_id == "s-789"
    assert test_instance.ceremony_id == SYNTHETIC_CEREMONY_ID


@pytest.mark.asyncio
async def test_discover_story_and_ceremony_when_placeholders_no_data_returns_false(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """discover_story_and_ceremony returns False when no stories found for project/epic."""
    project = MagicMock()
    project.name = "Test de swe fleet"
    project.project_id = "PROJ-123"
    epic = MagicMock()
    epic.title = "Autenticacion"
    epic.epic_id = "E-456"

    planning_stub.ListProjects = AsyncMock(
        return_value=MagicMock(success=True, projects=[project])
    )
    planning_stub.ListEpics = AsyncMock(
        return_value=MagicMock(success=True, epics=[epic])
    )
    planning_stub.ListStories = AsyncMock(
        return_value=MagicMock(success=True, stories=[])
    )

    result = await test_instance.discover_story_and_ceremony()

    assert result is False
    assert test_instance.story_id == STORY_ID_PLACEHOLDER


@pytest.mark.asyncio
async def test_discover_story_and_ceremony_when_explicit_story_keeps_it(
    test_instance: RestartRedeliveryIdempotencyTest,
    planning_stub: MagicMock,
) -> None:
    """When TEST_STORY_ID is set (not placeholder), discover keeps it and only resolves ceremony."""
    test_instance.story_id = "s-explicit"
    test_instance.ceremony_id = CEREMONY_ID_PLACEHOLDER

    ceremony = MagicMock()
    ceremony.ceremony_id = "BRC-real"
    ceremony.story_ids = ["s-explicit"]

    planning_stub.ListBacklogReviewCeremonies = AsyncMock(
        return_value=MagicMock(success=True, ceremonies=[ceremony])
    )

    result = await test_instance.discover_story_and_ceremony()

    assert result is True
    assert test_instance.story_id == "s-explicit"
    assert test_instance.ceremony_id == "BRC-real"
