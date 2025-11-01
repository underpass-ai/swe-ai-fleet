"""Unit tests for DockerOperationMetadata value object."""

import pytest

from core.agents_and_tools.tools.domain.docker_operation_metadata import DockerOperationMetadata


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestDockerOperationMetadataValidation:
    """Test fail-fast validation in DockerOperationMetadata."""

    def test_rejects_empty_cmd_list(self):
        """Should reject empty cmd list (fail-fast)."""
        with pytest.raises(ValueError, match="cmd is required and must be a non-empty list"):
            DockerOperationMetadata(cmd=[])

    def test_rejects_non_list_cmd(self):
        """Should reject non-list cmd (fail-fast)."""
        with pytest.raises(ValueError, match="cmd is required and must be a non-empty list"):
            DockerOperationMetadata(cmd="podman build")  # type: ignore

    def test_rejects_none_cmd(self):
        """Should reject None cmd (fail-fast)."""
        with pytest.raises(ValueError, match="cmd is required and must be a non-empty list"):
            DockerOperationMetadata(cmd=None)  # type: ignore


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestDockerOperationMetadataHappyPath:
    """Test valid DockerOperationMetadata creation."""

    def test_creates_with_minimal_data(self):
        """Should create with just cmd."""
        metadata = DockerOperationMetadata(cmd=["podman", "ps"])

        assert metadata.cmd == ["podman", "ps"]
        assert metadata.image is None
        assert metadata.additional_data == {}

    def test_creates_with_all_fields(self):
        """Should create with all fields."""
        metadata = DockerOperationMetadata(
            cmd=["podman", "run", "-d", "nginx"],
            image="nginx:latest",
            container_id="abc123",
            detach=True,
            name="webserver",
            timeout=300,
            error=None,
            additional_data={"custom": "value"},
        )

        assert metadata.cmd == ["podman", "run", "-d", "nginx"]
        assert metadata.image == "nginx:latest"
        assert metadata.container_id == "abc123"
        assert metadata.detach is True
        assert metadata.name == "webserver"

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        metadata = DockerOperationMetadata(cmd=["podman", "ps"])

        with pytest.raises(Exception):  # FrozenInstanceError
            metadata.cmd = ["docker", "ps"]  # type: ignore


# =============================================================================
# Factory Method Tests
# =============================================================================

class TestDockerOperationMetadataFactoryMethods:
    """Test factory methods for DockerOperationMetadata."""

    def test_for_build_creates_build_metadata(self):
        """Should create metadata for build operation."""
        metadata = DockerOperationMetadata.for_build(
            cmd=["podman", "build", "-t", "myapp:v1", "."],
            context=".",
            dockerfile="Dockerfile",
        )

        assert metadata.cmd == ["podman", "build", "-t", "myapp:v1", "."]
        assert metadata.additional_data["context"] == "."
        assert metadata.additional_data["dockerfile"] == "Dockerfile"

    def test_for_build_stores_in_additional_data(self):
        """Should store context and dockerfile in additional_data."""
        metadata = DockerOperationMetadata.for_build(
            cmd=["podman", "build"],
            context=".",
            dockerfile="Dockerfile",
        )

        assert metadata.additional_data["context"] == "."
        assert metadata.additional_data["dockerfile"] == "Dockerfile"
        assert metadata.image is None

    def test_for_run_creates_run_metadata(self):
        """Should create metadata for run operation."""
        metadata = DockerOperationMetadata.for_run(
            cmd=["podman", "run", "-d", "nginx"],
            image="nginx:latest",
            detach=True,
            name="webserver",
        )

        assert metadata.image == "nginx:latest"
        assert metadata.detach is True
        assert metadata.name == "webserver"

    def test_for_run_without_name(self):
        """Should create run metadata without name."""
        metadata = DockerOperationMetadata.for_run(
            cmd=["podman", "run", "nginx"],
            image="nginx",
            detach=False,
        )

        assert metadata.image == "nginx"
        assert metadata.detach is False
        assert metadata.name is None

    def test_for_error_creates_error_metadata(self):
        """Should create metadata for error cases."""
        metadata = DockerOperationMetadata.for_error(
            cmd=["podman", "build"],
            error="Build failed",
            timeout=600,
        )

        assert metadata.error == "Build failed"
        assert metadata.timeout == 600

    def test_for_error_without_timeout(self):
        """Should create error metadata without timeout."""
        metadata = DockerOperationMetadata.for_error(
            cmd=["podman", "run"],
            error="Container failed",
        )

        assert metadata.error == "Container failed"
        assert metadata.timeout is None


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestDockerOperationMetadataEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_empty_additional_data(self):
        """Should accept empty additional_data dict."""
        metadata = DockerOperationMetadata(cmd=["test"], additional_data={})

        assert metadata.additional_data == {}

    def test_accepts_none_for_all_optional_fields(self):
        """Should accept None for all optional fields."""
        metadata = DockerOperationMetadata(
            cmd=["test"],
            image=None,
            container_id=None,
            detach=None,
            name=None,
            timeout=None,
            error=None,
        )

        assert metadata.image is None
        assert metadata.container_id is None
        assert metadata.detach is None
        assert metadata.timeout is None

    def test_accepts_long_command(self):
        """Should accept very long command lists."""
        long_cmd = ["podman", "run"] + [f"--env VAR{i}=val{i}" for i in range(50)]
        metadata = DockerOperationMetadata(cmd=long_cmd)

        assert len(metadata.cmd) == 52

    def test_accepts_complex_additional_data(self):
        """Should accept complex additional_data."""
        metadata = DockerOperationMetadata(
            cmd=["test"],
            additional_data={
                "nested": {"data": "value"},
                "list": [1, 2, 3],
                "string": "test",
            }
        )

        assert metadata.additional_data["nested"]["data"] == "value"
        assert metadata.additional_data["list"] == [1, 2, 3]

