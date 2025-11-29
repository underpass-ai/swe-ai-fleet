import pytest
from datetime import datetime
from unittest.mock import Mock

from planning.domain.entities.epic import Epic
from planning.domain.value_objects.identifiers.epic_id import EpicId
from planning.domain.value_objects.identifiers.project_id import ProjectId
from planning.domain.value_objects.statuses.epic_status import EpicStatus
from planning.infrastructure.mappers.epic_neo4j_mapper import EpicNeo4jMapper

class TestEpicNeo4jMapper:
    """Test suite for EpicNeo4jMapper."""

    @pytest.fixture
    def valid_epic(self) -> Epic:
        return Epic(
            epic_id=EpicId("epic-123"),
            project_id=ProjectId("proj-456"),
            title="Test Epic",
            description="Epic Description",
            status=EpicStatus.ACTIVE,
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            updated_at=datetime(2023, 1, 2, 12, 0, 0),
        )

    def test_to_graph_properties(self, valid_epic):
        """Test converting domain Epic to graph properties."""
        props = EpicNeo4jMapper.to_graph_properties(valid_epic)

        assert props["id"] == "epic-123"
        assert props["epic_id"] == "epic-123"
        assert props["project_id"] == "proj-456"
        assert props["name"] == "Test Epic"
        assert props["status"] == "active"
        assert props["created_at"] == "2023-01-01T12:00:00"
        assert props["updated_at"] == "2023-01-02T12:00:00"

    def test_from_node_data_success(self):
        """Test creating Epic from valid node data."""
        node_data = {
            "properties": {
                "id": "epic-123",
                "epic_id": "epic-123",
                "project_id": "proj-456",
                "name": "Test Epic",
                "description": "Epic Description",
                "status": "active",
                "created_at": "2023-01-01T12:00:00+00:00",
                "updated_at": "2023-01-02T12:00:00+00:00",
            }
        }

        epic = EpicNeo4jMapper.from_node_data(node_data)

        assert isinstance(epic, Epic)
        assert epic.epic_id.value == "epic-123"
        assert epic.project_id.value == "proj-456"
        assert epic.title == "Test Epic"
        assert epic.description == "Epic Description"
        assert epic.status == EpicStatus.ACTIVE
        assert epic.created_at.year == 2023
        assert epic.updated_at.year == 2023

    def test_from_node_data_flat_dict(self):
        """Test creating Epic from flat dictionary (no 'properties' key)."""
        node_data = {
            "id": "epic-123",
            "epic_id": "epic-123",
            "project_id": "proj-456",
            "name": "Test Epic",
            "description": "Epic Description",
            "status": "active",
            "created_at": "2023-01-01T12:00:00+00:00",
            "updated_at": "2023-01-02T12:00:00+00:00",
        }

        epic = EpicNeo4jMapper.from_node_data(node_data)

        assert epic.epic_id.value == "epic-123"
        assert epic.title == "Test Epic"
        assert epic.status == EpicStatus.ACTIVE

    def test_from_node_data_missing_required_fields(self):
        """Test validation failures."""
        with pytest.raises(ValueError, match="Cannot create Epic from empty"):
            EpicNeo4jMapper.from_node_data({})

        with pytest.raises(ValueError, match="Missing required field: epic_id"):
            EpicNeo4jMapper.from_node_data({"id": ""})

        with pytest.raises(ValueError, match="Missing required field: name"):
            EpicNeo4jMapper.from_node_data({"id": "e-1", "project_id": "p-1"})
            
        with pytest.raises(ValueError, match="Missing required timestamps"):
            EpicNeo4jMapper.from_node_data({
                "id": "e-1", 
                "project_id": "p-1",
                "name": "Epic"
            })

        with pytest.raises(ValueError, match="Missing required field: status"):
            EpicNeo4jMapper.from_node_data({
                "id": "e-1",
                "project_id": "p-1",
                "name": "Epic",
                "created_at": "2023-01-01T12:00:00+00:00",
                "updated_at": "2023-01-01T12:00:00+00:00"
            })
