"""Unit tests for Artifacts collection."""

from core.agents_and_tools.agents.domain.entities.collections.artifact import Artifact
from core.agents_and_tools.agents.domain.entities.collections.artifacts import Artifacts


class TestArtifactsCreation:
    """Test Artifacts collection creation."""

    def test_create_empty_artifacts(self):
        """Test creating empty artifacts collection."""
        artifacts = Artifacts()

        assert artifacts.items == {}
        assert artifacts.count() == 0

    def test_create_artifacts_with_items(self):
        """Test creating artifacts collection with initial items."""
        artifact1 = Artifact(name="commit_sha", value="abc123", artifact_type="commit")
        artifact2 = Artifact(name="files_changed", value=["file1.txt"], artifact_type="file_list")

        artifacts = Artifacts(items={"commit_sha": artifact1, "files_changed": artifact2})

        assert artifacts.count() == 2
        assert len(artifacts.items) == 2


class TestArtifactsAdd:
    """Test Artifacts.add() method."""

    def test_add_artifact_with_default_type(self):
        """Test adding artifact with default type."""
        artifacts = Artifacts()

        artifacts.add(name="test_artifact", value="test_value")

        assert artifacts.count() == 1
        assert "test_artifact" in artifacts.items
        artifact = artifacts.items["test_artifact"]
        assert artifact.value == "test_value"
        assert artifact.artifact_type == "generic"

    def test_add_artifact_with_custom_type(self):
        """Test adding artifact with custom type."""
        artifacts = Artifacts()

        artifacts.add(name="commit_sha", value="abc123", artifact_type="commit")

        artifact = artifacts.items["commit_sha"]
        assert artifact.artifact_type == "commit"

    def test_add_multiple_artifacts(self):
        """Test adding multiple artifacts."""
        artifacts = Artifacts()

        artifacts.add(name="artifact1", value="value1")
        artifacts.add(name="artifact2", value="value2")
        artifacts.add(name="artifact3", value="value3")

        assert artifacts.count() == 3

    def test_add_artifact_overwrites_existing(self):
        """Test adding artifact with same name overwrites existing."""
        artifacts = Artifacts()

        artifacts.add(name="test", value="value1")
        artifacts.add(name="test", value="value2")

        assert artifacts.count() == 1
        assert artifacts.items["test"].value == "value2"


class TestArtifactsGet:
    """Test Artifacts.get() method."""

    def test_get_existing_artifact(self):
        """Test getting existing artifact."""
        artifacts = Artifacts()
        artifacts.add(name="test", value="test_value")

        value = artifacts.get("test")

        assert value == "test_value"

    def test_get_nonexistent_artifact_returns_none(self):
        """Test getting nonexistent artifact returns None."""
        artifacts = Artifacts()

        value = artifacts.get("nonexistent")

        assert value is None


class TestArtifactsGetAll:
    """Test Artifacts.get_all() method."""

    def test_get_all_returns_all_artifacts(self):
        """Test get_all returns all artifacts."""
        artifacts = Artifacts()
        artifacts.add(name="artifact1", value="value1")
        artifacts.add(name="artifact2", value="value2")

        all_artifacts = artifacts.get_all()

        assert len(all_artifacts) == 2
        assert all_artifacts == artifacts.items


class TestArtifactsCount:
    """Test Artifacts.count() method."""

    def test_count_returns_zero_for_empty_collection(self):
        """Test count returns zero for empty collection."""
        artifacts = Artifacts()

        assert artifacts.count() == 0

    def test_count_returns_correct_number(self):
        """Test count returns correct number of artifacts."""
        artifacts = Artifacts()

        assert artifacts.count() == 0

        artifacts.add(name="artifact1", value="value1")
        assert artifacts.count() == 1

        artifacts.add(name="artifact2", value="value2")
        assert artifacts.count() == 2


class TestArtifactsUpdateFromDict:
    """Test Artifacts.update_from_dict() method."""

    def test_update_from_dict_with_simple_values(self):
        """Test update_from_dict with simple value mapping."""
        artifacts = Artifacts()
        from unittest.mock import MagicMock

        # Mock the mapper
        mock_mapper = MagicMock()
        mock_mapper.from_dict_entry.return_value = Artifact(
            name="test", value="value", artifact_type="generic"
        )

        artifacts.update_from_dict({"test": "value"}, mapper=mock_mapper)

        assert artifacts.count() == 1
        mock_mapper.from_dict_entry.assert_called_once()

