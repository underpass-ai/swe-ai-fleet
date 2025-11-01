"""Unit tests for DockerResult entity."""

import pytest
from core.agents_and_tools.tools.domain.docker_operation_metadata import DockerOperationMetadata
from core.agents_and_tools.tools.domain.docker_result import DockerResult


# =============================================================================
# Test Helpers
# =============================================================================

def create_simple_metadata(operation: str = "run") -> DockerOperationMetadata:
    """Helper to create simple metadata for tests."""
    return DockerOperationMetadata(cmd=["podman", operation])


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestDockerResultConstructorValidation:
    """Test constructor fail-fast validation."""


    def test_rejects_empty_operation(self):
        """Should raise ValueError if operation is empty."""
        metadata = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=False, name=None)
        with pytest.raises(ValueError, match="operation is required and cannot be empty"):
            DockerResult(
                success=True,
                operation="",  # Empty operation
                stdout="",
                stderr="",
                exit_code=0,
                metadata=metadata,
            )

    def test_rejects_none_stdout(self):
        """Should raise ValueError if stdout is None."""
        metadata = DockerOperationMetadata.for_build(cmd=["podman", "build"], context=".", dockerfile="Dockerfile")
        with pytest.raises(ValueError, match="stdout is required"):
            DockerResult(
                success=True,
                operation="build",
                stdout=None,  # None instead of empty string
                stderr="",
                exit_code=0,
                metadata=metadata,
            )

    def test_rejects_none_stderr(self):
        """Should raise ValueError if stderr is None."""
        metadata = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=False, name=None)
        with pytest.raises(ValueError, match="stderr is required"):
            DockerResult(
                success=True,
                operation="run",
                stdout="",
                stderr=None,  # None instead of empty string
                exit_code=0,
                metadata=metadata,
            )


    def test_rejects_none_metadata(self):
        """Should raise ValueError if metadata is None."""
        with pytest.raises(ValueError, match="metadata is required"):
            DockerResult(
                success=True,
                operation="logs",
                stdout="",
                stderr="",
                exit_code=0,
                metadata=None,  # None instead of entity
            )

    def test_accepts_valid_entity(self):
        """Should create entity when all fields are valid."""
        metadata = DockerOperationMetadata.for_build(
            cmd=["podman", "build", "-t", "myapp:latest", "."],
            context=".",
            dockerfile="Dockerfile",
        )
        result = DockerResult(
            success=True,
            operation="build",
            stdout="Build successful",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.success is True
        assert result.operation == "build"
        assert result.stdout == "Build successful"
        assert result.stderr == ""
        assert result.exit_code == 0
        assert result.metadata is metadata
        assert isinstance(result.metadata, DockerOperationMetadata)


# =============================================================================
# Immutability Tests
# =============================================================================

class TestDockerResultImmutability:
    """Test that DockerResult is immutable (frozen=True)."""

    def test_cannot_modify_success(self):
        """Should prevent modification of success field."""
        metadata = DockerOperationMetadata(cmd=["podman", "run", "nginx"])
        result = DockerResult(
            success=True,
            operation="run",
            stdout="",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.success = False

    def test_cannot_modify_operation(self):
        """Should prevent modification of operation field."""
        metadata = DockerOperationMetadata(cmd=["podman", "build"])
        result = DockerResult(
            success=True,
            operation="build",
            stdout="",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            result.operation = "run"


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestDockerResultBusinessLogic:
    """Test domain logic methods."""

    def test_is_success_returns_true_when_success_and_exit_code_zero(self):
        """Should return True when both success=True and exit_code=0."""
        result = DockerResult(
            success=True,
            operation="build",
            stdout="Build successful",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("build"),
        )

        assert result.is_success() is True

    def test_is_success_returns_false_when_success_false(self):
        """Should return False when success=False."""
        result = DockerResult(
            success=False,
            operation="build",
            stdout="",
            stderr="Build failed",
            exit_code=1,
            metadata=create_simple_metadata("build"),
        )

        assert result.is_success() is False

    def test_is_success_returns_false_when_exit_code_nonzero(self):
        """Should return False when exit_code is not 0."""
        result = DockerResult(
            success=True,
            operation="run",
            stdout="",
            stderr="Container exited with error",
            exit_code=127,
            metadata=create_simple_metadata("run"),
        )

        assert result.is_success() is False

    def test_has_errors_returns_true_when_stderr_present(self):
        """Should return True when stderr has content."""
        result = DockerResult(
            success=False,
            operation="exec",
            stdout="",
            stderr="Command not found",
            exit_code=1,
            metadata=create_simple_metadata("exec"),
        )

        assert result.has_errors() is True

    def test_has_errors_returns_false_when_stderr_empty(self):
        """Should return False when stderr is empty."""
        result = DockerResult(
            success=True,
            operation="ps",
            stdout="CONTAINER ID   IMAGE",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("ps"),
        )

        assert result.has_errors() is False

    def test_has_errors_returns_false_when_stderr_whitespace_only(self):
        """Should return False when stderr contains only whitespace."""
        result = DockerResult(
            success=True,
            operation="logs",
            stdout="App running",
            stderr="   \n  ",
            exit_code=0,
            metadata=create_simple_metadata("logs"),
        )

        assert result.has_errors() is False

    def test_get_output_returns_combined_output(self):
        """Should return combined stdout and stderr."""
        result = DockerResult(
            success=True,
            operation="build",
            stdout="Step 1/3: Build image",
            stderr="Warning: deprecated flag",
            exit_code=0,
            metadata=create_simple_metadata("build"),
        )

        output = result.get_output()

        assert "STDOUT:" in output
        assert "Step 1/3: Build image" in output
        assert "STDERR:" in output
        assert "Warning: deprecated flag" in output

    def test_get_output_handles_stdout_only(self):
        """Should return only stdout when stderr is empty."""
        result = DockerResult(
            success=True,
            operation="ps",
            stdout="CONTAINER ID   IMAGE",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("ps"),
        )

        output = result.get_output()

        assert "STDOUT:" in output
        assert "CONTAINER ID   IMAGE" in output
        assert "STDERR:" not in output

    def test_get_output_handles_stderr_only(self):
        """Should return only stderr when stdout is empty."""
        result = DockerResult(
            success=False,
            operation="run",
            stdout="",
            stderr="Container failed to start",
            exit_code=1,
            metadata=create_simple_metadata("run"),
        )

        output = result.get_output()

        assert "STDERR:" in output
        assert "Container failed to start" in output
        assert "STDOUT:" not in output

    def test_get_output_handles_no_output(self):
        """Should return 'No output' when both stdout and stderr are empty."""
        result = DockerResult(
            success=True,
            operation="rm",
            stdout="",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("rm"),
        )

        output = result.get_output()

        assert output == "No output"


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestDockerResultEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_all_docker_operations(self):
        """Should accept all valid DockerOperation literals."""
        operations = ["build", "run", "exec", "ps", "logs", "stop", "rm"]

        for op in operations:
            result = DockerResult(
                success=True,
                operation=op,
                stdout="",
                stderr="",
                exit_code=0,
                metadata=create_simple_metadata(op),
            )
            assert result.operation == op

    def test_accepts_empty_strings_for_stdout_and_stderr(self):
        """Should accept empty strings for stdout and stderr."""
        result = DockerResult(
            success=True,
            operation="ps",
            stdout="",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("ps"),
        )

        assert result.stdout == ""
        assert result.stderr == ""

    def test_metadata_entity_provides_rich_information(self):
        """Should accept metadata entity with rich information."""
        metadata = DockerOperationMetadata.for_run(
            cmd=["podman", "run", "-d", "--name", "webserver", "nginx"],
            image="nginx:latest",
            detach=True,
            name="webserver",
        )

        result = DockerResult(
            success=True,
            operation="run",
            stdout="container_id_abc123",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.metadata is metadata
        assert result.metadata.image == "nginx:latest"
        assert result.metadata.detach is True
        assert result.metadata.name == "webserver"

    def test_handles_multiline_output(self):
        """Should handle multiline stdout and stderr."""
        result = DockerResult(
            success=True,
            operation="logs",
            stdout="Line 1\nLine 2\nLine 3",
            stderr="Warning 1\nWarning 2",
            exit_code=0,
            metadata=create_simple_metadata("logs"),
        )

        assert "Line 1" in result.stdout
        assert "Line 2" in result.stdout
        assert "Warning 1" in result.stderr

    def test_handles_negative_exit_codes(self):
        """Should accept negative exit codes (signal termination)."""
        result = DockerResult(
            success=False,
            operation="run",
            stdout="",
            stderr="Killed",
            exit_code=-9,  # SIGKILL
            metadata=create_simple_metadata("run"),
        )

        assert result.exit_code == -9
        assert result.is_success() is False


# =============================================================================
# Tell Don't Ask Pattern Tests - summarize()
# =============================================================================

class TestDockerResultSummarize:
    """Test summarize() method following Tell, Don't Ask principle."""

    def test_summarize_successful_build(self):
        """Should summarize successful build operation."""
        metadata = DockerOperationMetadata.for_build(cmd=["podman", "build"], context=".", dockerfile="Dockerfile")
        result = DockerResult(
            success=True,
            operation="build",
            stdout="Successfully built abc123",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.summarize() == "Docker image built successfully"

    def test_summarize_failed_build(self):
        """Should summarize failed build operation."""
        metadata = DockerOperationMetadata.for_error(cmd=["podman", "build"], error="Build failed")
        result = DockerResult(
            success=False,
            operation="build",
            stdout="",
            stderr="Error: Dockerfile not found",
            exit_code=1,
            metadata=metadata,
        )

        assert result.summarize() == "Docker image build failed"

    def test_summarize_successful_run_detached(self):
        """Should summarize successful detached run with container name."""
        metadata = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=True, name="webserver")
        result = DockerResult(
            success=True,
            operation="run",
            stdout="container_id_123",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.summarize() == "Container started in background: webserver"

    def test_summarize_successful_run_detached_unnamed(self):
        """Should summarize successful detached run without name."""
        metadata = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=True, name=None)
        result = DockerResult(
            success=True,
            operation="run",
            stdout="container_id_456",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.summarize() == "Container started in background: unnamed"

    def test_summarize_successful_run_interactive(self):
        """Should summarize successful interactive run."""
        metadata = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="python", detach=False, name=None)
        result = DockerResult(
            success=True,
            operation="run",
            stdout="Hello World",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.summarize() == "Container executed successfully"

    def test_summarize_successful_ps_with_containers(self):
        """Should summarize ps operation with container count."""
        metadata = DockerOperationMetadata(cmd=["podman", "ps"])
        result = DockerResult(
            success=True,
            operation="ps",
            stdout="CONTAINER ID\ncontainer1\ncontainer2\n",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        summary = result.summarize()
        assert "container(s)" in summary

    def test_summarize_successful_logs(self):
        """Should summarize successful logs operation."""
        metadata = DockerOperationMetadata(cmd=["podman", "logs"], container_id="webserver")
        result = DockerResult(
            success=True,
            operation="logs",
            stdout="App log line 1\nApp log line 2",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        assert result.summarize() == "Retrieved container logs"

    def test_summarize_encapsulates_decision_logic(self):
        """Should encapsulate all summarization logic within entity."""
        # This tests the "Tell, Don't Ask" principle:
        # - Client doesn't ask "what operation is this?" and decide how to summarize
        # - Client tells "summarize yourself"
        
        build_result = DockerResult(
            success=True,
            operation="build",
            stdout="Built",
            stderr="",
            exit_code=0,
            metadata=create_simple_metadata("build"),
        )
        
        run_result = DockerResult(
            success=True,
            operation="run",
            stdout="",
            stderr="",
            exit_code=0,
            metadata=DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=False, name=None),
        )
        
        # Both know how to summarize themselves
        assert "built" in build_result.summarize().lower()
        assert "executed" in run_result.summarize().lower()


# =============================================================================
# Tell Don't Ask Pattern Tests - collect_artifacts()
# =============================================================================

class TestDockerResultCollectArtifacts:
    """Test collect_artifacts() method following Tell, Don't Ask principle."""

    def test_collect_artifacts_from_successful_build(self):
        """Should collect artifacts from successful build."""
        metadata = DockerOperationMetadata.for_build(
            cmd=["podman", "build", "-t", "myapp:v1.0", "."],
            context=".",
            dockerfile="Dockerfile"
        )
        metadata = DockerOperationMetadata(
            cmd=metadata.cmd,
            image="myapp:v1.0",
            additional_data={"context": ".", "dockerfile": "Dockerfile"}
        )
        
        result = DockerResult(
            success=True,
            operation="build",
            stdout="Successfully built abc123",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        artifacts = result.collect_artifacts()

        assert artifacts["docker_image"] == "myapp:v1.0"
        assert artifacts["build_context"] == "."

    def test_collect_artifacts_from_successful_detached_run(self):
        """Should collect container ID from detached run."""
        metadata = DockerOperationMetadata.for_run(
            cmd=["podman", "run", "-d"], 
            image="nginx:latest",
            detach=True,
            name="webserver"
        )
        
        result = DockerResult(
            success=True,
            operation="run",
            stdout="container_abc123",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        artifacts = result.collect_artifacts()

        assert artifacts["container_id"] == "container_abc123"
        assert artifacts["image"] == "nginx:latest"
        assert artifacts["container_name"] == "webserver"

    def test_collect_artifacts_from_ps_operation(self):
        """Should collect container count from ps."""
        metadata = DockerOperationMetadata(cmd=["podman", "ps", "-a"])
        result = DockerResult(
            success=True,
            operation="ps",
            stdout="HEADER\ncontainer1\ncontainer2\ncontainer3\n",
            stderr="",
            exit_code=0,
            metadata=metadata,
        )

        artifacts = result.collect_artifacts()

        assert artifacts["containers_count"] == 4  # Including header

    def test_collect_artifacts_encapsulates_logic(self):
        """Should encapsulate all artifact collection logic within entity."""
        # This tests the "Tell, Don't Ask" principle:
        # - Client doesn't ask "what operation is this?" and decide what to collect
        # - Client tells "collect your artifacts"
        
        build_meta = DockerOperationMetadata(cmd=["podman", "build"], image="myapp:v1.0", additional_data={"context": "."})
        build_result = DockerResult(
            success=True,
            operation="build",
            stdout="Built",
            stderr="",
            exit_code=0,
            metadata=build_meta,
        )
        
        run_meta = DockerOperationMetadata.for_run(cmd=["podman", "run"], image="nginx", detach=True, name="web")
        run_result = DockerResult(
            success=True,
            operation="run",
            stdout="container_123",
            stderr="",
            exit_code=0,
            metadata=run_meta,
        )
        
        # Both know what artifacts are relevant for their operation type
        build_artifacts = build_result.collect_artifacts()
        run_artifacts = run_result.collect_artifacts()
        
        assert "docker_image" in build_artifacts
        assert "container_id" in run_artifacts

