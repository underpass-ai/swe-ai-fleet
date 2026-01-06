"""Unit tests for Neo4jStorageAdapter."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.review.agent_deliberation import (
    AgentDeliberation,
)
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from backlog_review_processor.infrastructure.adapters.neo4j_adapter import (
    Neo4jStorageAdapter,
)
from backlog_review_processor.infrastructure.adapters.neo4j_config import Neo4jConfig


@pytest.fixture
def mock_neo4j_config():
    """Create mock Neo4j config."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="test-password",
        database="neo4j",
    )


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver."""
    driver = MagicMock()
    driver.session = MagicMock(return_value=MagicMock())
    driver.close = MagicMock()
    return driver


@pytest.fixture
def adapter(mock_neo4j_config, mock_driver):
    """Create adapter with mocked driver."""
    with patch("backlog_review_processor.infrastructure.adapters.neo4j_adapter.GraphDatabase") as mock_graph:
        mock_graph.driver = MagicMock(return_value=mock_driver)
        adapter = Neo4jStorageAdapter(config=mock_neo4j_config)
        adapter.driver = mock_driver
        return adapter


class TestGetAgentDeliberations:
    """Tests for get_agent_deliberations method."""

    @pytest.mark.asyncio
    async def test_get_agent_deliberations_returns_empty_list_when_none_found(
        self, adapter, mock_driver
    ):
        """Test that get_agent_deliberations returns empty list when no deliberations found."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        deliberations = await adapter.get_agent_deliberations(ceremony_id, story_id)

        # Assert
        assert deliberations == []
        mock_session.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_agent_deliberations_returns_deliberations(
        self, adapter, mock_driver
    ):
        """Test that get_agent_deliberations returns list of AgentDeliberation."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_record1 = MagicMock()
        mock_record1.__getitem__ = Mock(side_effect=lambda k: {
            "agent_id": "agent-architect-001",
            "role": "ARCHITECT",
            "proposal": '{"content": "Proposal 1"}',
            "deliberated_at": "2025-01-01T10:00:00+00:00",
        }[k])

        mock_record2 = MagicMock()
        mock_record2.__getitem__ = Mock(side_effect=lambda k: {
            "agent_id": "agent-qa-001",
            "role": "QA",
            "proposal": "Simple string proposal",
            "deliberated_at": "2025-01-01T11:00:00+00:00",
        }[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record1, mock_record2]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        deliberations = await adapter.get_agent_deliberations(ceremony_id, story_id)

        # Assert
        assert len(deliberations) == 2
        assert deliberations[0].agent_id == "agent-architect-001"
        assert deliberations[0].role == BacklogReviewRole.ARCHITECT
        assert deliberations[1].agent_id == "agent-qa-001"
        assert deliberations[1].role == BacklogReviewRole.QA

    @pytest.mark.asyncio
    async def test_get_agent_deliberations_handles_json_proposal(
        self, adapter, mock_driver
    ):
        """Test that get_agent_deliberations parses JSON proposal correctly."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        import json

        proposal_dict = {"content": "Proposal content", "metadata": {"key": "value"}}
        proposal_json = json.dumps(proposal_dict)

        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = Mock(side_effect=lambda k: {
            "agent_id": "agent-architect-001",
            "role": "ARCHITECT",
            "proposal": proposal_json,
            "deliberated_at": "2025-01-01T10:00:00+00:00",
        }[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        deliberations = await adapter.get_agent_deliberations(ceremony_id, story_id)

        # Assert
        assert len(deliberations) == 1
        assert isinstance(deliberations[0].proposal, dict)
        assert deliberations[0].proposal == proposal_dict

    @pytest.mark.asyncio
    async def test_get_agent_deliberations_handles_string_proposal(
        self, adapter, mock_driver
    ):
        """Test that get_agent_deliberations handles string proposal correctly."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        proposal_str = "Simple string proposal"

        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = Mock(side_effect=lambda k: {
            "agent_id": "agent-qa-001",
            "role": "QA",
            "proposal": proposal_str,
            "deliberated_at": "2025-01-01T10:00:00+00:00",
        }[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        deliberations = await adapter.get_agent_deliberations(ceremony_id, story_id)

        # Assert
        assert len(deliberations) == 1
        assert deliberations[0].proposal == proposal_str

    @pytest.mark.asyncio
    async def test_get_agent_deliberations_raises_on_error(self, adapter, mock_driver):
        """Test that get_agent_deliberations raises RuntimeError on query failure."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.run = MagicMock(side_effect=Exception("Neo4j connection error"))
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to get agent deliberations"):
            await adapter.get_agent_deliberations(ceremony_id, story_id)


class TestHasAllRoleDeliberations:
    """Tests for has_all_role_deliberations method."""

    @pytest.mark.asyncio
    async def test_has_all_role_deliberations_returns_false_when_no_deliberations(
        self, adapter, mock_driver
    ):
        """Test that has_all_role_deliberations returns False when no deliberations found."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        has_all = await adapter.has_all_role_deliberations(ceremony_id, story_id)

        # Assert
        assert has_all is False

    @pytest.mark.asyncio
    async def test_has_all_role_deliberations_returns_false_when_missing_roles(
        self, adapter, mock_driver
    ):
        """Test that has_all_role_deliberations returns False when not all roles present."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_record1 = MagicMock()
        mock_record1.__getitem__ = Mock(side_effect=lambda k: {"role": "ARCHITECT"}[k])
        mock_record2 = MagicMock()
        mock_record2.__getitem__ = Mock(side_effect=lambda k: {"role": "QA"}[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(return_value=iter([mock_record1, mock_record2]))
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        has_all = await adapter.has_all_role_deliberations(ceremony_id, story_id)

        # Assert
        assert has_all is False  # Missing DEVOPS

    @pytest.mark.asyncio
    async def test_has_all_role_deliberations_returns_true_when_all_roles_present(
        self, adapter, mock_driver
    ):
        """Test that has_all_role_deliberations returns True when all 3 roles present."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_record1 = MagicMock()
        mock_record1.__getitem__ = Mock(side_effect=lambda k: {"role": "ARCHITECT"}[k])
        mock_record2 = MagicMock()
        mock_record2.__getitem__ = Mock(side_effect=lambda k: {"role": "QA"}[k])
        mock_record3 = MagicMock()
        mock_record3.__getitem__ = Mock(side_effect=lambda k: {"role": "DEVOPS"}[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter([mock_record1, mock_record2, mock_record3])
        )
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        has_all = await adapter.has_all_role_deliberations(ceremony_id, story_id)

        # Assert
        assert has_all is True

    @pytest.mark.asyncio
    async def test_has_all_role_deliberations_returns_true_with_multiple_agents_same_role(
        self, adapter, mock_driver
    ):
        """Test that has_all_role_deliberations returns True even with multiple agents per role."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        # 2 ARCHITECTs, 1 QA, 1 DEVOPS
        mock_record1 = MagicMock()
        mock_record1.__getitem__ = Mock(side_effect=lambda k: {"role": "ARCHITECT"}[k])
        mock_record2 = MagicMock()
        mock_record2.__getitem__ = Mock(side_effect=lambda k: {"role": "ARCHITECT"}[k])
        mock_record3 = MagicMock()
        mock_record3.__getitem__ = Mock(side_effect=lambda k: {"role": "QA"}[k])
        mock_record4 = MagicMock()
        mock_record4.__getitem__ = Mock(side_effect=lambda k: {"role": "DEVOPS"}[k])

        mock_result = MagicMock()
        mock_result.__iter__ = Mock(
            return_value=iter([mock_record1, mock_record2, mock_record3, mock_record4])
        )
        mock_session.run = MagicMock(return_value=mock_result)
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act
        has_all = await adapter.has_all_role_deliberations(ceremony_id, story_id)

        # Assert
        assert has_all is True

    @pytest.mark.asyncio
    async def test_has_all_role_deliberations_raises_on_error(self, adapter, mock_driver):
        """Test that has_all_role_deliberations raises RuntimeError on query failure."""
        # Arrange
        ceremony_id = BacklogReviewCeremonyId("ceremony-123")
        story_id = StoryId("ST-456")

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_session.run = MagicMock(side_effect=Exception("Neo4j connection error"))
        mock_driver.session = MagicMock(return_value=mock_session)

        # Act & Assert
        with pytest.raises(RuntimeError, match="Failed to check role deliberations"):
            await adapter.has_all_role_deliberations(ceremony_id, story_id)
