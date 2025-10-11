"""Unit tests for DeliberateAsync use case."""
from unittest.mock import Mock, patch

import pytest

from swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase import DeliberateAsync


class TestDeliberateAsync:
    """Unit tests for DeliberateAsync."""
    
    @pytest.fixture
    def deliberate_async(self):
        """Create DeliberateAsync instance for testing."""
        return DeliberateAsync(
            ray_address=None,  # Don't actually connect
            vllm_url="http://vllm-test:8000",
            model="test-model",
            nats_url="nats://nats-test:4222",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
    
    def test_initialization(self, deliberate_async):
        """Test DeliberateAsync initialization."""
        assert deliberate_async.vllm_url == "http://vllm-test:8000"
        assert deliberate_async.model == "test-model"
        assert deliberate_async.nats_url == "nats://nats-test:4222"
        assert deliberate_async.temperature == 0.7
        assert deliberate_async.max_tokens == 1024
        assert deliberate_async.timeout == 30
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    def test_connect_ray_when_not_initialized(
        self, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test Ray connection when not already initialized."""
        deliberate_async.connect_ray()
        
        mock_is_initialized.assert_called_once()
        mock_ray_init.assert_called_once_with(ignore_reinit_error=True)
    
    @patch("ray.is_initialized", return_value=True)
    @patch("ray.init")
    def test_connect_ray_when_already_initialized(
        self, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test Ray connection when already initialized."""
        deliberate_async.connect_ray()
        
        mock_is_initialized.assert_called_once()
        # Should not call init if already initialized
        mock_ray_init.assert_not_called()
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    def test_connect_ray_with_address(
        self, mock_ray_init, mock_is_initialized
    ):
        """Test Ray connection with explicit address."""
        deliberate = DeliberateAsync(
            ray_address="ray://test-cluster:10001",
            vllm_url="http://test:8000",
            model="test",
            nats_url="nats://test:4222",
        )
        
        deliberate.connect_ray()
        
        mock_ray_init.assert_called_once_with(
            address="ray://test-cluster:10001",
            ignore_reinit_error=True
        )
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    @patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.VLLMAgentJob")
    def test_execute_basic(
        self, mock_agent_job_class, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test basic execution of deliberation."""
        # Mock Ray actor and job submission
        mock_actor = Mock()
        mock_job_ref = Mock()
        mock_actor.run.remote = Mock(return_value=mock_job_ref)
        mock_agent_job_class.remote = Mock(return_value=mock_actor)
        
        # Execute deliberation
        result = deliberate_async.execute(
            task_id="test-task-001",
            task_description="Write factorial function",
            role="DEV",
            num_agents=3,
            constraints={"rubric": "Clean code"},
            rounds=1,
        )
        
        # Verify Ray was initialized
        mock_is_initialized.assert_called()
        mock_ray_init.assert_called_once()
        
        # Verify result structure
        assert result["task_id"] == "test-task-001"
        assert result["num_agents"] == 3
        assert result["role"] == "DEV"
        assert result["status"] == "submitted"
        assert len(result["job_refs"]) == 3
        assert len(result["agent_ids"]) == 3
        
        # Verify agent IDs format
        assert result["agent_ids"][0] == "agent-dev-001"
        assert result["agent_ids"][1] == "agent-dev-002"
        assert result["agent_ids"][2] == "agent-dev-003"
        
        # Verify 3 agent actors were created
        assert mock_agent_job_class.remote.call_count == 3
        
        # Verify run.remote was called 3 times
        assert mock_actor.run.remote.call_count == 3
        
        # Verify first call has diversity=False, rest have diversity=True
        first_call = mock_actor.run.remote.call_args_list[0]
        assert first_call[1]["diversity"] is False
        
        second_call = mock_actor.run.remote.call_args_list[1]
        assert second_call[1]["diversity"] is True
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    @patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.VLLMAgentJob")
    def test_execute_generates_task_id_if_not_provided(
        self, mock_agent_job_class, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test that task_id is generated if not provided."""
        mock_actor = Mock()
        mock_actor.run.remote = Mock(return_value=Mock())
        mock_agent_job_class.remote = Mock(return_value=mock_actor)
        
        result = deliberate_async.execute(
            task_id=None,  # No task_id provided
            task_description="Test task",
            role="QA",
            num_agents=2,
        )
        
        # Verify task_id was generated
        assert result["task_id"] is not None
        assert result["task_id"].startswith("task-")
        assert len(result["task_id"]) > 5  # UUID format
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    @patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.VLLMAgentJob")
    def test_execute_with_different_roles(
        self, mock_agent_job_class, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test execution with different roles."""
        mock_actor = Mock()
        mock_actor.run.remote = Mock(return_value=Mock())
        mock_agent_job_class.remote = Mock(return_value=mock_actor)
        
        roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        
        for role in roles:
            result = deliberate_async.execute(
                task_id=f"test-{role.lower()}",
                task_description="Test task",
                role=role,
                num_agents=2,
            )
            
            assert result["role"] == role
            # Verify agent IDs match role
            assert all(
                aid.startswith(f"agent-{role.lower()}-")
                for aid in result["agent_ids"]
            )
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    @patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.VLLMAgentJob")
    def test_execute_handles_none_constraints(
        self, mock_agent_job_class, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test that None constraints are handled properly."""
        mock_actor = Mock()
        mock_actor.run.remote = Mock(return_value=Mock())
        mock_agent_job_class.remote = Mock(return_value=mock_actor)
        
        result = deliberate_async.execute(
            task_id="test-task",
            task_description="Test",
            role="DEV",
            num_agents=1,
            constraints=None,  # None constraints
        )
        
        # Should not raise error
        assert result["status"] == "submitted"
        
        # Verify run.remote was called with empty dict
        call_args = mock_actor.run.remote.call_args
        assert call_args[1]["constraints"] == {}
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.init")
    @patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.VLLMAgentJob")
    def test_execute_warns_on_multiple_rounds(
        self, mock_agent_job_class, mock_ray_init, mock_is_initialized, deliberate_async
    ):
        """Test warning when multiple rounds requested."""
        mock_actor = Mock()
        mock_actor.run.remote = Mock(return_value=Mock())
        mock_agent_job_class.remote = Mock(return_value=mock_actor)
        
        with patch("swe_ai_fleet.orchestrator.usecases.deliberate_async_usecase.logger") as mock_logger:
            result = deliberate_async.execute(
                task_id="test",
                task_description="Test",
                role="DEV",
                num_agents=1,
                rounds=3,  # Multiple rounds
            )
            
            # Should log warning
            mock_logger.warning.assert_called()
            
            # Should still execute with rounds=1
            assert result["rounds"] == 1
    
    @patch("ray.is_initialized", return_value=True)
    @patch("ray.wait")
    @patch("ray.get")
    def test_get_job_status_all_pending(
        self, mock_ray_get, mock_ray_wait, mock_is_initialized, deliberate_async
    ):
        """Test job status when all jobs are pending."""
        mock_refs = [Mock(), Mock(), Mock()]
        
        # Mock ray.wait to return empty ready list
        mock_ray_wait.return_value = ([], mock_refs)
        
        status = deliberate_async.get_job_status(mock_refs)
        
        assert status["total"] == 3
        assert status["pending"] == 3
        assert status["completed"] == 0
        assert status["failed"] == 0
        assert status["status"] == "in_progress"
    
    @patch("ray.is_initialized", return_value=True)
    @patch("ray.wait")
    @patch("ray.get")
    def test_get_job_status_all_completed(
        self, mock_ray_get, mock_ray_wait, mock_is_initialized, deliberate_async
    ):
        """Test job status when all jobs are completed."""
        mock_refs = [Mock(), Mock()]
        
        # Mock ray.wait to return all refs as ready
        mock_ray_wait.side_effect = [
            ([mock_refs[0]], []),
            ([mock_refs[1]], []),
        ]
        mock_ray_get.return_value = {"status": "completed"}
        
        status = deliberate_async.get_job_status(mock_refs)
        
        assert status["total"] == 2
        assert status["pending"] == 0
        assert status["completed"] == 2
        assert status["failed"] == 0
        assert status["status"] == "done"
    
    @patch("ray.is_initialized", return_value=True)
    @patch("ray.wait")
    @patch("ray.get")
    def test_get_job_status_some_failed(
        self, mock_ray_get, mock_ray_wait, mock_is_initialized, deliberate_async
    ):
        """Test job status when some jobs failed."""
        mock_refs = [Mock(), Mock(), Mock()]
        
        # Mock ray.wait to return all as ready
        mock_ray_wait.side_effect = [
            ([mock_refs[0]], []),
            ([mock_refs[1]], []),
            ([mock_refs[2]], []),
        ]
        
        # Mock ray.get to succeed for first, fail for second, succeed for third
        mock_ray_get.side_effect = [
            {"status": "completed"},  # First job succeeds
            Exception("Job failed"),  # Second job fails
            {"status": "completed"},  # Third job succeeds
        ]
        
        status = deliberate_async.get_job_status(mock_refs)
        
        assert status["total"] == 3
        assert status["pending"] == 0
        assert status["completed"] == 2
        assert status["failed"] == 1
        assert status["status"] == "done"
    
    @patch("ray.is_initialized", return_value=False)
    def test_get_job_status_ray_not_initialized(
        self, mock_is_initialized, deliberate_async
    ):
        """Test job status when Ray is not initialized."""
        status = deliberate_async.get_job_status([Mock()])
        
        assert status["status"] == "error"
        assert "not initialized" in status["message"]
    
    @patch("ray.is_initialized", return_value=True)
    @patch("ray.shutdown")
    def test_shutdown(
        self, mock_ray_shutdown, mock_is_initialized, deliberate_async
    ):
        """Test shutdown closes Ray connection."""
        deliberate_async.shutdown()
        
        mock_is_initialized.assert_called_once()
        mock_ray_shutdown.assert_called_once()
    
    @patch("ray.is_initialized", return_value=False)
    @patch("ray.shutdown")
    def test_shutdown_when_not_initialized(
        self, mock_ray_shutdown, mock_is_initialized, deliberate_async
    ):
        """Test shutdown does nothing if Ray not initialized."""
        deliberate_async.shutdown()
        
        mock_is_initialized.assert_called_once()
        # Should not call shutdown if not initialized
        mock_ray_shutdown.assert_not_called()

