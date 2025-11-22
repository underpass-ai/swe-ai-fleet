"""Unit tests for Artifact domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.collections.artifact import Artifact


class TestArtifactCreation:
    """Test Artifact entity creation."""

    def test_create_artifact_with_required_fields(self):
        """Test creating artifact with required fields."""
        artifact = Artifact(name="commit_sha", value="abc123", artifact_type="commit")

        assert artifact.name == "commit_sha"
        assert artifact.value == "abc123"
        assert artifact.artifact_type == "commit"

    def test_create_artifact_with_string_value(self):
        """Test creating artifact with string value."""
        artifact = Artifact(name="file_path", value="/path/to/file.txt", artifact_type="file")

        assert artifact.value == "/path/to/file.txt"
        assert isinstance(artifact.value, str)

    def test_create_artifact_with_list_value(self):
        """Test creating artifact with list value."""
        files = ["file1.txt", "file2.txt"]
        artifact = Artifact(name="files_changed", value=files, artifact_type="file_list")

        assert artifact.value == files
        assert isinstance(artifact.value, list)

    def test_create_artifact_with_dict_value(self):
        """Test creating artifact with dict value."""
        metadata = {"author": "test", "timestamp": "2024-01-01"}
        artifact = Artifact(name="metadata", value=metadata, artifact_type="metadata")

        assert artifact.value == metadata
        assert isinstance(artifact.value, dict)


class TestArtifactImmutability:
    """Test Artifact immutability."""

    def test_artifact_is_immutable(self):
        """Test artifact is frozen (immutable)."""
        artifact = Artifact(name="test", value="value", artifact_type="generic")

        with pytest.raises(AttributeError):
            artifact.name = "new_name"  # type: ignore

        with pytest.raises(AttributeError):
            artifact.value = "new_value"  # type: ignore


class TestArtifactEquality:
    """Test Artifact equality and comparison."""

    def test_artifacts_with_same_values_are_equal(self):
        """Test artifacts with identical values are equal."""
        artifact1 = Artifact(name="test", value="value", artifact_type="generic")
        artifact2 = Artifact(name="test", value="value", artifact_type="generic")

        assert artifact1 == artifact2

    def test_artifacts_with_different_names_are_not_equal(self):
        """Test artifacts with different names are not equal."""
        artifact1 = Artifact(name="test1", value="value", artifact_type="generic")
        artifact2 = Artifact(name="test2", value="value", artifact_type="generic")

        assert artifact1 != artifact2

    def test_artifacts_with_different_values_are_not_equal(self):
        """Test artifacts with different values are not equal."""
        artifact1 = Artifact(name="test", value="value1", artifact_type="generic")
        artifact2 = Artifact(name="test", value="value2", artifact_type="generic")

        assert artifact1 != artifact2

