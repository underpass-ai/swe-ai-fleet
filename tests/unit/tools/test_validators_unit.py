"""Unit tests for tools validators."""

import pytest

from swe_ai_fleet.tools.validators import (
    sanitize_log_output,
    validate_command_args,
    validate_container_image,
    validate_database_connection_string,
    validate_env_vars,
    validate_git_url,
    validate_path,
    validate_url,
)


class TestValidatePath:
    """Test path validation."""

    def test_valid_relative_path(self, tmp_path):
        """Test valid relative path."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Valid relative path
        assert validate_path("src/main.py", workspace) is True

    def test_valid_absolute_path(self, tmp_path):
        """Test valid absolute path within workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        (workspace / "src").mkdir()

        # Valid absolute path
        target = workspace / "src" / "main.py"
        assert validate_path(target, workspace) is True

    def test_path_traversal_attack(self, tmp_path):
        """Test path traversal prevention."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Path traversal attempt
        with pytest.raises(ValueError, match="Path outside workspace"):
            validate_path("../../etc/passwd", workspace)

    def test_absolute_path_outside_workspace(self, tmp_path):
        """Test absolute path outside workspace."""
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Absolute path outside workspace
        with pytest.raises(ValueError, match="Path outside workspace"):
            validate_path("/etc/passwd", workspace)


class TestValidateUrl:
    """Test URL validation."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        assert validate_url("https://api.example.com/users") is True

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        assert validate_url("http://api.example.com/users") is True

    def test_localhost_not_allowed_by_default(self):
        """Test localhost is blocked by default."""
        with pytest.raises(ValueError, match="not allowed"):
            validate_url("http://localhost:8080")

    def test_localhost_allowed_when_enabled(self):
        """Test localhost is allowed when enabled."""
        assert validate_url("http://localhost:8080", allow_localhost=True) is True

    def test_invalid_scheme(self):
        """Test invalid URL scheme."""
        with pytest.raises(ValueError, match="Only http:// and https://"):
            validate_url("file:///etc/passwd")

    def test_missing_scheme(self):
        """Test URL without scheme."""
        with pytest.raises(ValueError, match="must have scheme"):
            validate_url("example.com")


class TestValidateGitUrl:
    """Test Git URL validation."""

    def test_valid_https_git_url(self):
        """Test valid HTTPS Git URL."""
        assert validate_git_url("https://github.com/user/repo.git") is True

    def test_valid_ssh_git_url(self):
        """Test valid SSH Git URL."""
        assert validate_git_url("git@github.com:user/repo.git") is True

    def test_invalid_file_protocol(self):
        """Test file:// protocol is rejected."""
        with pytest.raises(ValueError, match="Only https:// and git@"):
            validate_git_url("file:///tmp/repo")

    def test_invalid_git_url_format(self):
        """Test invalid Git URL format."""
        with pytest.raises(ValueError, match="Invalid Git"):
            validate_git_url("https://github.com")  # No repo path


class TestValidateCommandArgs:
    """Test command argument validation."""

    def test_valid_simple_args(self):
        """Test valid simple arguments."""
        assert validate_command_args(["ls", "-la", "/tmp"]) is True

    def test_command_injection_semicolon(self):
        """Test semicolon command injection."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_command_args(["ls", "; rm -rf /"])

    def test_command_injection_pipe(self):
        """Test pipe command injection."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_command_args(["cat", "file.txt", "| bash"])

    def test_command_injection_and(self):
        """Test AND command injection."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_command_args(["true", "&&", "rm -rf /"])

    def test_command_substitution(self):
        """Test command substitution."""
        with pytest.raises(ValueError, match="Dangerous pattern"):
            validate_command_args(["echo", "$(whoami)"])


class TestValidateEnvVars:
    """Test environment variable validation."""

    def test_valid_env_vars(self):
        """Test valid environment variables."""
        assert validate_env_vars({"VAR1": "value1", "VAR2": "value2"}) is True

    def test_ld_preload_blocked(self):
        """Test LD_PRELOAD is blocked."""
        with pytest.raises(ValueError, match="LD_PRELOAD not allowed"):
            validate_env_vars({"LD_PRELOAD": "/tmp/malicious.so"})

    def test_path_with_parent_directory(self):
        """Test PATH with .. is blocked."""
        with pytest.raises(ValueError, match="PATH cannot contain"):
            validate_env_vars({"PATH": "/usr/bin:../../../tmp"})

    def test_ld_library_path_suspicious(self):
        """Test suspicious LD_LIBRARY_PATH."""
        with pytest.raises(ValueError, match="suspicious path"):
            validate_env_vars({"LD_LIBRARY_PATH": "/tmp/malicious"})


class TestValidateContainerImage:
    """Test container image validation."""

    def test_valid_simple_image(self):
        """Test simple image name."""
        assert validate_container_image("python:3.13") is True

    def test_valid_registry_image(self):
        """Test image with registry."""
        assert validate_container_image("docker.io/library/python:3.13") is True

    def test_valid_custom_registry(self):
        """Test custom registry image."""
        assert validate_container_image("registry.example.com/myapp:v1.0") is True

    def test_invalid_image_format(self):
        """Test invalid image format."""
        with pytest.raises(ValueError, match="Invalid container image format"):
            validate_container_image("invalid image name with spaces")


class TestValidateDatabaseConnectionString:
    """Test database connection string validation."""

    def test_valid_postgresql_url(self):
        """Test valid PostgreSQL connection string."""
        assert validate_database_connection_string(
            "postgresql://user:pass@localhost:5432/db",
            "postgresql"
        ) is True

    def test_valid_redis_url(self):
        """Test valid Redis connection string."""
        assert validate_database_connection_string(
            "redis://localhost:6379/0",
            "redis"
        ) is True

    def test_valid_neo4j_url(self):
        """Test valid Neo4j connection string."""
        assert validate_database_connection_string(
            "bolt://localhost:7687",
            "neo4j"
        ) is True

    def test_invalid_postgresql_scheme(self):
        """Test invalid PostgreSQL scheme."""
        with pytest.raises(ValueError, match="must start with postgresql://"):
            validate_database_connection_string(
                "mysql://localhost:3306/db",
                "postgresql"
            )

    def test_unknown_database_type(self):
        """Test unknown database type."""
        with pytest.raises(ValueError, match="Unknown database type"):
            validate_database_connection_string(
                "mongodb://localhost:27017",
                "mongodb"
            )


class TestSanitizeLogOutput:
    """Test log output sanitization."""

    def test_sanitize_long_output(self):
        """Test truncation of long output."""
        long_output = "A" * 20000
        result = sanitize_log_output(long_output, max_length=10000)

        assert len(result) <= 10100  # 10000 + "... (truncated)"
        assert "truncated" in result

    def test_remove_ansi_colors(self):
        """Test ANSI color code removal."""
        colored = "\x1b[31mRed text\x1b[0m"
        result = sanitize_log_output(colored)

        assert "\x1b" not in result
        assert "Red text" in result

    def test_short_output_unchanged(self):
        """Test short output is not modified."""
        short = "Normal output"
        result = sanitize_log_output(short)

        assert result == short

