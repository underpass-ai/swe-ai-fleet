"""Unit tests for ContainerRunConfig value object."""

import pytest
from core.agents_and_tools.tools.domain.container_run_config import ContainerRunConfig


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerRunConfigConstructorValidation:
    """Test constructor fail-fast validation."""

    def test_rejects_empty_image(self):
        """Should raise ValueError if image is empty."""
        with pytest.raises(ValueError, match="image is required and cannot be empty"):
            ContainerRunConfig(image="")

    def test_rejects_whitespace_only_image(self):
        """Should raise ValueError if image is whitespace only."""
        with pytest.raises(ValueError, match="image is required and cannot be empty"):
            ContainerRunConfig(image="   ")

    def test_rejects_non_boolean_detach(self):
        """Should raise ValueError if detach is not a boolean."""
        with pytest.raises(ValueError, match="detach must be a boolean"):
            ContainerRunConfig(image="nginx", detach="yes")  # String instead of bool

    def test_rejects_non_boolean_rm(self):
        """Should raise ValueError if rm is not a boolean."""
        with pytest.raises(ValueError, match="rm must be a boolean"):
            ContainerRunConfig(image="nginx", rm=1)  # Int instead of bool

    def test_rejects_non_integer_timeout(self):
        """Should raise ValueError if timeout is not an integer."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ContainerRunConfig(image="nginx", timeout="300")  # String instead of int

    def test_rejects_non_positive_timeout(self):
        """Should raise ValueError if timeout is not positive."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerRunConfig(image="nginx", timeout=0)

    def test_rejects_negative_timeout(self):
        """Should raise ValueError if timeout is negative."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerRunConfig(image="nginx", timeout=-10)

    def test_rejects_non_dict_env(self):
        """Should raise ValueError if env is not a dict or None."""
        with pytest.raises(ValueError, match="env must be a dictionary or None"):
            ContainerRunConfig(image="nginx", env=["VAR=value"])  # List instead of dict

    def test_rejects_non_dict_volumes(self):
        """Should raise ValueError if volumes is not a dict or None."""
        with pytest.raises(ValueError, match="volumes must be a dictionary or None"):
            ContainerRunConfig(image="nginx", volumes="/src:/dst")  # String instead of dict

    def test_rejects_non_dict_ports(self):
        """Should raise ValueError if ports is not a dict or None."""
        with pytest.raises(ValueError, match="ports must be a dictionary or None"):
            ContainerRunConfig(image="nginx", ports=8080)  # Int instead of dict

    def test_rejects_non_list_command(self):
        """Should raise ValueError if command is not a list or None."""
        with pytest.raises(ValueError, match="command must be a list or None"):
            ContainerRunConfig(image="nginx", command="sh -c echo test")  # String instead of list

    def test_accepts_valid_minimal_config(self):
        """Should create instance with just image (minimal config)."""
        config = ContainerRunConfig(image="nginx:latest")

        assert config.image == "nginx:latest"
        assert config.command is None
        assert config.env is None
        assert config.volumes is None
        assert config.ports is None
        assert config.detach is False
        assert config.rm is True
        assert config.name is None
        assert config.timeout == 300

    def test_accepts_valid_full_config(self):
        """Should create instance with all fields populated."""
        config = ContainerRunConfig(
            image="myapp:v1.0",
            command=["python", "app.py"],
            env={"ENV": "production", "DEBUG": "false"},
            volumes={"/host/data": "/container/data"},
            ports={"8080": "80"},
            detach=True,
            rm=False,
            name="my-container",
            timeout=600,
        )

        assert config.image == "myapp:v1.0"
        assert config.command == ["python", "app.py"]
        assert config.env == {"ENV": "production", "DEBUG": "false"}
        assert config.volumes == {"/host/data": "/container/data"}
        assert config.ports == {"8080": "80"}
        assert config.detach is True
        assert config.rm is False
        assert config.name == "my-container"
        assert config.timeout == 600


# =============================================================================
# Immutability Tests
# =============================================================================

class TestContainerRunConfigImmutability:
    """Test that ContainerRunConfig is immutable (frozen=True)."""

    def test_cannot_modify_image(self):
        """Should prevent modification of image field."""
        config = ContainerRunConfig(image="nginx")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.image = "apache"

    def test_cannot_modify_detach(self):
        """Should prevent modification of detach field."""
        config = ContainerRunConfig(image="nginx", detach=False)

        with pytest.raises(Exception):  # FrozenInstanceError
            config.detach = True


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestContainerRunConfigBusinessLogic:
    """Test domain logic methods."""

    def test_has_command_returns_true_when_command_provided(self):
        """Should return True when command is provided."""
        config = ContainerRunConfig(image="nginx", command=["sh", "-c", "echo test"])
        assert config.has_command() is True

    def test_has_command_returns_false_when_command_none(self):
        """Should return False when command is None."""
        config = ContainerRunConfig(image="nginx", command=None)
        assert config.has_command() is False

    def test_has_command_returns_false_when_command_empty_list(self):
        """Should return False when command is empty list."""
        config = ContainerRunConfig(image="nginx", command=[])
        assert config.has_command() is False

    def test_has_env_vars_returns_true_when_env_provided(self):
        """Should return True when env vars are provided."""
        config = ContainerRunConfig(image="nginx", env={"PATH": "/usr/bin"})
        assert config.has_env_vars() is True

    def test_has_env_vars_returns_false_when_env_none(self):
        """Should return False when env is None."""
        config = ContainerRunConfig(image="nginx", env=None)
        assert config.has_env_vars() is False

    def test_has_env_vars_returns_false_when_env_empty(self):
        """Should return False when env is empty dict."""
        config = ContainerRunConfig(image="nginx", env={})
        assert config.has_env_vars() is False

    def test_has_volumes_returns_true_when_volumes_provided(self):
        """Should return True when volumes are provided."""
        config = ContainerRunConfig(image="nginx", volumes={"/host": "/container"})
        assert config.has_volumes() is True

    def test_has_volumes_returns_false_when_volumes_none(self):
        """Should return False when volumes is None."""
        config = ContainerRunConfig(image="nginx", volumes=None)
        assert config.has_volumes() is False

    def test_has_ports_returns_true_when_ports_provided(self):
        """Should return True when ports are provided."""
        config = ContainerRunConfig(image="nginx", ports={"80": "8080"})
        assert config.has_ports() is True

    def test_has_ports_returns_false_when_ports_none(self):
        """Should return False when ports is None."""
        config = ContainerRunConfig(image="nginx", ports=None)
        assert config.has_ports() is False

    def test_is_detached_returns_true_when_detach_enabled(self):
        """Should return True when detach is True."""
        config = ContainerRunConfig(image="nginx", detach=True)
        assert config.is_detached() is True

    def test_is_detached_returns_false_when_detach_disabled(self):
        """Should return False when detach is False."""
        config = ContainerRunConfig(image="nginx", detach=False)
        assert config.is_detached() is False

    def test_should_auto_remove_returns_true_when_rm_enabled(self):
        """Should return True when rm is True."""
        config = ContainerRunConfig(image="nginx", rm=True)
        assert config.should_auto_remove() is True

    def test_should_auto_remove_returns_false_when_rm_disabled(self):
        """Should return False when rm is False."""
        config = ContainerRunConfig(image="nginx", rm=False)
        assert config.should_auto_remove() is False


# =============================================================================
# Factory Methods Tests
# =============================================================================

class TestContainerRunConfigFactoryMethods:
    """Test factory methods for creating ContainerRunConfig instances."""

    def test_simple_factory_creates_minimal_config(self):
        """Should create simple config with just image."""
        config = ContainerRunConfig.simple("nginx:latest")

        assert config.image == "nginx:latest"
        assert config.command is None
        assert config.env is None
        assert config.volumes is None
        assert config.ports is None
        assert config.detach is False
        assert config.rm is True
        assert config.name is None
        assert config.timeout == 300

    def test_interactive_factory_creates_interactive_config(self):
        """Should create interactive config (not detached, auto-remove)."""
        config = ContainerRunConfig.interactive("python:3.11", ["python", "script.py"])

        assert config.image == "python:3.11"
        assert config.command == ["python", "script.py"]
        assert config.detach is False
        assert config.rm is True
        assert config.has_command() is True

    def test_daemon_factory_creates_daemon_config(self):
        """Should create daemon config (detached, no auto-remove, named)."""
        config = ContainerRunConfig.daemon("nginx:latest", "webserver")

        assert config.image == "nginx:latest"
        assert config.name == "webserver"
        assert config.detach is True
        assert config.rm is False
        assert config.is_detached() is True
        assert config.should_auto_remove() is False


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestContainerRunConfigEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_empty_dicts_for_optional_fields(self):
        """Should accept empty dicts for env, volumes, ports."""
        config = ContainerRunConfig(
            image="nginx",
            env={},
            volumes={},
            ports={},
        )

        assert config.env == {}
        assert config.volumes == {}
        assert config.ports == {}
        assert config.has_env_vars() is False
        assert config.has_volumes() is False
        assert config.has_ports() is False

    def test_accepts_complex_command(self):
        """Should accept complex multi-part commands."""
        config = ContainerRunConfig(
            image="alpine",
            command=["sh", "-c", "cd /app && python -m pytest --cov"],
        )

        assert len(config.command) == 3
        assert config.command[2] == "cd /app && python -m pytest --cov"

    def test_accepts_multiple_env_vars(self):
        """Should accept multiple environment variables."""
        config = ContainerRunConfig(
            image="myapp",
            env={
                "DATABASE_URL": "postgres://localhost/db",
                "REDIS_URL": "redis://localhost:6379",
                "ENV": "production",
                "DEBUG": "false",
            },
        )

        assert len(config.env) == 4
        assert config.env["DATABASE_URL"] == "postgres://localhost/db"

    def test_accepts_multiple_volume_mounts(self):
        """Should accept multiple volume mounts."""
        config = ContainerRunConfig(
            image="myapp",
            volumes={
                "/host/data": "/container/data",
                "/host/config": "/container/config",
                "/host/logs": "/container/logs",
            },
        )

        assert len(config.volumes) == 3

    def test_accepts_multiple_port_mappings(self):
        """Should accept multiple port mappings."""
        config = ContainerRunConfig(
            image="webapp",
            ports={
                "8080": "80",
                "8443": "443",
                "3000": "3000",
            },
        )

        assert len(config.ports) == 3

    def test_accepts_large_timeout(self):
        """Should accept large timeout values."""
        config = ContainerRunConfig(image="nginx", timeout=86400)  # 24 hours
        assert config.timeout == 86400

    def test_equality_of_identical_configs(self):
        """Should be equal when all fields are the same."""
        config1 = ContainerRunConfig(image="nginx", timeout=600)
        config2 = ContainerRunConfig(image="nginx", timeout=600)

        assert config1 == config2

    def test_inequality_when_fields_differ(self):
        """Should not be equal when fields differ."""
        config1 = ContainerRunConfig(image="nginx")
        config2 = ContainerRunConfig(image="apache")

        assert config1 != config2

