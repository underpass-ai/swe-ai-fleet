"""Unit tests for Task Derivation Service server."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from core.shared.domain.value_objects.task_derivation.config.task_derivation_config import (
    TaskDerivationConfig,
)
from server import (
    ServerConfiguration,
    TaskDerivationServer,
)


@pytest.fixture
def mock_config_file(tmp_path: Path) -> Path:
    """Create a temporary config file for tests."""
    config_file = tmp_path / "task_derivation.yaml"
    config_content = {
        "prompt_template": "Template: {description}",
        "constraints": {"min_tasks": 3, "max_tasks": 8},
        "retry": {"max_retries": 3},
    }
    config_file.write_text(yaml.dump(config_content))
    return config_file


@pytest.fixture
def mock_nats_client():
    """Create a mock NATS client."""
    mock_client = AsyncMock()
    mock_jetstream = AsyncMock()
    mock_client.jetstream = MagicMock(return_value=mock_jetstream)
    return mock_client, mock_jetstream


class TestServerConfiguration:
    """Tests for ServerConfiguration DTO."""

    def test_valid_configuration(self) -> None:
        """Test valid configuration creation."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template: {description}",
            min_tasks=3,
            max_tasks=8,
            max_retries=3,
        )

        config = ServerConfiguration(
            nats_url="nats://localhost:4222",
            planning_service_address="planning:50054",
            context_service_address="context:50054",
            ray_executor_address="ray-executor:50056",
            vllm_url="http://localhost:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
            task_derivation_config=config_obj,
        )

        assert config.nats_url == "nats://localhost:4222"
        assert config.planning_service_address == "planning:50054"
        assert config.context_service_address == "context:50054"
        assert config.ray_executor_address == "ray-executor:50056"
        assert config.task_derivation_config == config_obj

    def test_configuration_rejects_empty_nats_url(self) -> None:
        """Test that empty nats_url raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="nats_url cannot be empty"):
            ServerConfiguration(
                nats_url="",
                planning_service_address="planning:50054",
                context_service_address="context:50054",
                ray_executor_address="ray-executor:50056",
                vllm_url="http://localhost:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
                task_derivation_config=config_obj,
            )

    def test_configuration_rejects_empty_planning_address(self) -> None:
        """Test that empty planning_service_address raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="planning_service_address cannot be empty"):
            ServerConfiguration(
                nats_url="nats://localhost:4222",
                planning_service_address="",
                context_service_address="context:50054",
                ray_executor_address="ray-executor:50056",
                vllm_url="http://localhost:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
                task_derivation_config=config_obj,
            )

    def test_configuration_rejects_empty_context_address(self) -> None:
        """Test that empty context_service_address raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="context_service_address cannot be empty"):
            ServerConfiguration(
                nats_url="nats://localhost:4222",
                planning_service_address="planning:50054",
                context_service_address="",
                ray_executor_address="ray-executor:50056",
                vllm_url="http://localhost:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
                task_derivation_config=config_obj,
            )

    def test_configuration_rejects_empty_ray_executor_address(self) -> None:
        """Test that empty ray_executor_address raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="ray_executor_address cannot be empty"):
            ServerConfiguration(
                nats_url="nats://localhost:4222",
                planning_service_address="planning:50054",
                context_service_address="context:50054",
                ray_executor_address="",
                vllm_url="http://localhost:8000",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
                task_derivation_config=config_obj,
            )

    def test_configuration_rejects_empty_vllm_url(self) -> None:
        """Test that empty vllm_url raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="vllm_url cannot be empty"):
            ServerConfiguration(
                nats_url="nats://localhost:4222",
                planning_service_address="planning:50054",
                context_service_address="context:50054",
                ray_executor_address="ray-executor:50056",
                vllm_url="",
                vllm_model="Qwen/Qwen2.5-7B-Instruct",
                task_derivation_config=config_obj,
            )

    def test_configuration_rejects_empty_vllm_model(self) -> None:
        """Test that empty vllm_model raises ValueError."""
        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )

        with pytest.raises(ValueError, match="vllm_model cannot be empty"):
            ServerConfiguration(
                nats_url="nats://localhost:4222",
                planning_service_address="planning:50054",
                context_service_address="context:50054",
                ray_executor_address="ray-executor:50056",
                vllm_url="http://localhost:8000",
                vllm_model="",
                task_derivation_config=config_obj,
            )


class TestTaskDerivationServer:
    """Tests for TaskDerivationServer."""

    def test_server_initialization(self) -> None:
        """Test server initializes correctly."""
        server = TaskDerivationServer()

        assert server._nats_client is None
        assert server._jetstream is None
        assert server._request_consumer is None
        assert server._result_consumer is None
        assert server._shutdown_event is not None

    @pytest.mark.asyncio
    async def test_load_configuration_success(self, mock_config_file, monkeypatch) -> None:
        """Test _load_configuration loads config from environment and YAML."""
        monkeypatch.setenv("NATS_URL", "nats://test:4222")
        monkeypatch.setenv("PLANNING_SERVICE_ADDRESS", "planning-test:50054")
        monkeypatch.setenv("CONTEXT_SERVICE_ADDRESS", "context-test:50054")
        monkeypatch.setenv("RAY_EXECUTOR_ADDRESS", "ray-test:50056")
        monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(mock_config_file))

        server = TaskDerivationServer()
        config = server._load_configuration()

        assert config.nats_url == "nats://test:4222"
        assert config.planning_service_address == "planning-test:50054"
        assert config.context_service_address == "context-test:50054"
        assert config.ray_executor_address == "ray-test:50056"
        assert config.task_derivation_config.prompt_template == "Template: {description}"
        assert config.task_derivation_config.min_tasks == 3
        assert config.task_derivation_config.max_tasks == 8

    @pytest.mark.asyncio
    async def test_load_configuration_uses_defaults(self, mock_config_file, monkeypatch) -> None:
        """Test _load_configuration uses default values when env vars not set."""
        # Clear env vars
        monkeypatch.delenv("NATS_URL", raising=False)
        monkeypatch.delenv("PLANNING_SERVICE_ADDRESS", raising=False)
        monkeypatch.delenv("CONTEXT_SERVICE_ADDRESS", raising=False)
        monkeypatch.delenv("RAY_EXECUTOR_ADDRESS", raising=False)
        monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(mock_config_file))

        server = TaskDerivationServer()
        config = server._load_configuration()

        assert "nats://" in config.nats_url
        assert "planning" in config.planning_service_address
        assert "context" in config.context_service_address
        assert "ray-executor" in config.ray_executor_address

    @pytest.mark.asyncio
    async def test_load_configuration_missing_config_file(self, monkeypatch) -> None:
        """Test _load_configuration raises FileNotFoundError for missing config file."""
        monkeypatch.setenv("TASK_DERIVATION_CONFIG", "/nonexistent/config.yaml")

        server = TaskDerivationServer()

        with pytest.raises(FileNotFoundError):
            server._load_configuration()

    @pytest.mark.asyncio
    async def test_load_configuration_missing_prompt_template(self, tmp_path, monkeypatch) -> None:
        """Test _load_configuration raises ValueError for missing prompt_template."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(yaml.dump({"constraints": {"min_tasks": 3}}))
        monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(config_file))

        server = TaskDerivationServer()

        with pytest.raises(ValueError, match="prompt_template"):
            server._load_configuration()

    @pytest.mark.asyncio
    async def test_initialize_infrastructure(self, mock_nats_client) -> None:
        """Test _initialize_infrastructure connects to NATS."""
        mock_client, mock_jetstream = mock_nats_client
        mock_client.jetstream = MagicMock(return_value=mock_jetstream)

        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )
        config = ServerConfiguration(
            nats_url="nats://localhost:4222",
            planning_service_address="planning:50054",
            context_service_address="context:50054",
            ray_executor_address="ray-executor:50056",
            vllm_url="http://localhost:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
            task_derivation_config=config_obj,
        )

        server = TaskDerivationServer()

        with patch("nats.connect", return_value=mock_client):
            await server._initialize_infrastructure(config)

        assert server._nats_client == mock_client
        assert server._jetstream == mock_jetstream

    @pytest.mark.asyncio
    async def test_build_dependencies(self, mock_nats_client, mock_config_file, monkeypatch) -> None:
        """Test _build_dependencies creates consumers with injected use cases."""
        mock_client, mock_jetstream = mock_nats_client
        monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(mock_config_file))

        config_obj = TaskDerivationConfig(
            prompt_template="Template", min_tasks=1, max_tasks=1, max_retries=0
        )
        config = ServerConfiguration(
            nats_url="nats://localhost:4222",
            planning_service_address="planning:50054",
            context_service_address="context:50054",
            ray_executor_address="ray-executor:50056",
            vllm_url="http://localhost:8000",
            vllm_model="Qwen/Qwen2.5-7B-Instruct",
            task_derivation_config=config_obj,
        )

        server = TaskDerivationServer()
        server._nats_client = mock_client
        server._jetstream = mock_jetstream

        request_consumer, result_consumer = server._build_dependencies(config)

        assert request_consumer is not None
        assert result_consumer is not None
        assert request_consumer._derive_tasks_usecase is not None
        assert result_consumer._process_usecase is not None

    @pytest.mark.asyncio
    async def test_start_initializes_and_starts_consumers(
        self, mock_nats_client, mock_config_file, monkeypatch
    ) -> None:
        """Test start() initializes infrastructure and starts consumers."""
        mock_client, mock_jetstream = mock_nats_client
        mock_request_subscription = AsyncMock()
        mock_result_subscription = AsyncMock()
        # Make fetch raise CancelledError immediately to exit polling loops
        mock_request_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
        mock_result_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
        mock_jetstream.pull_subscribe = AsyncMock(
            side_effect=[mock_request_subscription, mock_result_subscription]
        )

        monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(mock_config_file))

        server = TaskDerivationServer()

        with patch("nats.connect", return_value=mock_client):
            await server.start()

        assert server._nats_client == mock_client
        assert server._request_consumer is not None
        assert server._result_consumer is not None
        assert server._request_consumer._polling_task is not None
        assert server._result_consumer._polling_task is not None

        # Cleanup: stop server (will cancel polling tasks and re-raise CancelledError)
        with pytest.raises(asyncio.CancelledError):
            await server.stop()

    @pytest.mark.asyncio
    async def test_stop_gracefully_stops_consumers(self, mock_nats_client) -> None:
        """Test stop() gracefully stops all consumers."""
        mock_client, _ = mock_nats_client

        server = TaskDerivationServer()
        server._nats_client = mock_client

        # Create mock consumers
        mock_request_consumer = AsyncMock()
        mock_result_consumer = AsyncMock()
        server._request_consumer = mock_request_consumer
        server._result_consumer = mock_result_consumer

        await server.stop()

        mock_request_consumer.stop.assert_awaited_once()
        mock_result_consumer.stop.assert_awaited_once()
        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_handles_missing_consumers(self, mock_nats_client) -> None:
        """Test stop() handles case where consumers are None."""
        mock_client, _ = mock_nats_client

        server = TaskDerivationServer()
        server._nats_client = mock_client
        server._request_consumer = None
        server._result_consumer = None

        # Should not raise
        await server.stop()

        mock_client.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_wait_for_termination(self) -> None:
        """Test wait_for_termination waits for shutdown event."""
        server = TaskDerivationServer()

        # Set shutdown event after a short delay
        async def trigger_shutdown():
            await asyncio.sleep(0.1)
            server._shutdown_event.set()

        wait_task = asyncio.create_task(server.wait_for_termination())
        shutdown_task = asyncio.create_task(trigger_shutdown())

        await asyncio.wait([wait_task, shutdown_task], return_when=asyncio.ALL_COMPLETED)

        assert wait_task.done()


@pytest.mark.asyncio
async def test_serve_function_initializes_server(mock_config_file, mock_nats_client, monkeypatch) -> None:
    """Test serve() function initializes and starts server."""
    mock_client, mock_jetstream = mock_nats_client
    mock_request_subscription = AsyncMock()
    mock_result_subscription = AsyncMock()
    # Make fetch raise CancelledError immediately to exit polling loops
    mock_request_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    mock_result_subscription.fetch = AsyncMock(side_effect=asyncio.CancelledError())
    mock_jetstream.pull_subscribe = AsyncMock(
        side_effect=[mock_request_subscription, mock_result_subscription]
    )

    monkeypatch.setenv("TASK_DERIVATION_CONFIG", str(mock_config_file))

    # Mock signal handlers
    with patch("signal.signal"):
        with patch("nats.connect", return_value=mock_client):
            # Create server and start it
            server = TaskDerivationServer()
            await server.start()

            # Verify server started
            assert server._nats_client == mock_client
            assert server._request_consumer is not None
            assert server._result_consumer is not None

            # Trigger shutdown immediately
            server._shutdown_event.set()

            # Cleanup: stop will re-raise CancelledError (expected)
            with pytest.raises(asyncio.CancelledError):
                await server.stop()
