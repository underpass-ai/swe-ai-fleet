"""Unit tests for Neo4jCommandStore Project persistence."""

from unittest.mock import Mock, MagicMock, patch

import pytest

from core.context.adapters.neo4j_command_store import Neo4jCommandStore
from core.context.domain.entity_ids.epic_id import EpicId
from core.context.domain.entity_ids.project_id import ProjectId
from core.context.domain.epic import Epic
from core.context.domain.epic_status import EpicStatus
from core.context.domain.graph_label import GraphLabel
from core.context.domain.neo4j_config import Neo4jConfig
from core.context.domain.project import Project
from core.context.domain.project_status import ProjectStatus
from core.context.infrastructure.mappers.project_mapper import ProjectMapper


@pytest.fixture
def neo4j_config() -> Neo4jConfig:
    """Create test Neo4j config."""
    return Neo4jConfig(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="testpassword",
        database="neo4j",
    )


@pytest.fixture
def mock_driver():
    """Create mock Neo4j driver with context manager support."""
    with patch("core.context.adapters.neo4j_command_store.GraphDatabase") as mock_gdb:
        mock_driver_instance = Mock()
        mock_session = MagicMock()  # MagicMock supports __enter__/__exit__
        mock_driver_instance.session.return_value = mock_session
        mock_gdb.driver.return_value = mock_driver_instance
        yield mock_driver_instance


class TestNeo4jCommandStoreProject:
    """Test suite for Project persistence in Neo4jCommandStore."""

    def test_save_project_happy_path(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test saving a valid Project to Neo4j."""
        store = Neo4jCommandStore(config=neo4j_config)

        project = Project(
            project_id=ProjectId("PROJ-SAVE-001"),
            name="Test Project",
            description="Test description",
            status=ProjectStatus.ACTIVE,
            owner="test_owner",
            created_at_ms=1699564800000,
        )

        # Execute save
        store.save_project(project)

        # Verify upsert_entity was called with correct parameters
        # This would normally call into Neo4j driver, but we're mocking it
        # The important part is that the method executes without errors

    def test_save_project_with_minimal_fields(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test saving Project with minimal required fields."""
        store = Neo4jCommandStore(config=neo4j_config)

        project = Project(
            project_id=ProjectId("PROJ-MIN"),
            name="Minimal Project",
            # description, owner use defaults
        )

        # Should save without errors
        store.save_project(project)

    def test_save_epic_with_project_id(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test saving Epic with valid project_id."""
        store = Neo4jCommandStore(config=neo4j_config)

        epic = Epic(
            epic_id=EpicId("E-SAVE-001"),
            project_id=ProjectId("PROJ-001"),  # Valid parent reference
            title="Test Epic",
            description="Test description",
            status=EpicStatus.ACTIVE,
        )

        # Execute save
        store.save_epic(epic)

        # Should complete without errors

    def test_save_epic_domain_invariant_enforced(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test that Epic without project_id cannot be created (domain invariant).

        Note: This test verifies that domain validation prevents invalid data
        from reaching the adapter layer.
        """
        # Cannot create Epic without project_id - domain layer prevents this
        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            Epic(
                epic_id=EpicId("E-ORPHAN"),
                project_id=ProjectId(""),  # Empty violates invariant
                title="Orphan Epic",
            )

    def test_save_project_calls_upsert_entity(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test that save_project calls upsert_entity with correct label."""
        store = Neo4jCommandStore(config=neo4j_config)

        project = Project(
            project_id=ProjectId("PROJ-UPSERT"),
            name="Upsert Test",
        )

        # Mock upsert_entity method
        with patch.object(store, "upsert_entity") as mock_upsert:
            store.save_project(project)

            # Verify upsert was called with PROJECT label
            mock_upsert.assert_called_once()
            call_kwargs = mock_upsert.call_args
            assert call_kwargs.kwargs["label"] == GraphLabel.PROJECT.value
            assert call_kwargs.kwargs["id"] == "PROJ-UPSERT"

    def test_save_epic_calls_upsert_entity(self, neo4j_config: Neo4jConfig, mock_driver: Mock) -> None:
        """Test that save_epic calls upsert_entity with correct label."""
        store = Neo4jCommandStore(config=neo4j_config)

        epic = Epic(
            epic_id=EpicId("E-UPSERT"),
            project_id=ProjectId("PROJ-001"),
            title="Upsert Test Epic",
        )

        # Mock upsert_entity method
        with patch.object(store, "upsert_entity") as mock_upsert:
            store.save_epic(epic)

            # Verify upsert was called with EPIC label
            mock_upsert.assert_called_once()
            call_kwargs = mock_upsert.call_args
            assert call_kwargs.kwargs["label"] == GraphLabel.EPIC.value
            assert call_kwargs.kwargs["id"] == "E-UPSERT"


class TestProjectMapperEdgeCases:
    """Test edge cases for ProjectMapper."""

    def test_from_neo4j_node_missing_project_id(self) -> None:
        """Test that missing project_id raises KeyError."""
        node = {
            "name": "No ID Project",
        }

        with pytest.raises(KeyError):
            ProjectMapper.from_neo4j_node(node)

    def test_from_neo4j_node_missing_name(self) -> None:
        """Test that missing name raises KeyError."""
        node = {
            "project_id": "PROJ-001",
        }

        with pytest.raises(KeyError):
            ProjectMapper.from_neo4j_node(node)

    def test_from_dict_empty_project_id_raises_error(self) -> None:
        """Test that empty project_id raises ValueError from ProjectId validation."""
        data = {
            "project_id": "",  # Empty
            "name": "Test",
        }

        with pytest.raises(ValueError, match="ProjectId cannot be empty"):
            ProjectMapper.from_dict(data)

    def test_from_dict_empty_name_raises_error(self) -> None:
        """Test that empty name raises ValueError from Project validation."""
        data = {
            "project_id": "PROJ-001",
            "name": "",  # Empty
        }

        with pytest.raises(ValueError, match="Project name cannot be empty"):
            ProjectMapper.from_dict(data)

