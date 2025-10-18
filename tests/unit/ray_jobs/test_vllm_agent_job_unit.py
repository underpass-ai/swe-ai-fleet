"""Unit tests for VLLMAgentJob."""
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from swe_ai_fleet.ray_jobs.vllm_agent_job import (
    VLLMAgentJob,
    VLLMAgentJobBase,
)


class TestVLLMAgentJob:
    """Unit tests for VLLMAgentJob."""
    
    @pytest.fixture
    def agent_job(self):
        """Create a VLLMAgentJobBase instance for testing (not Ray actor)."""
        return VLLMAgentJobBase(
            agent_id="agent-dev-001",
            role="DEV",
            vllm_url="http://vllm-test:8000",
            model="test-model",
            nats_url="nats://nats-test:4222",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
        )
    
    def test_initialization(self, agent_job):
        """Test agent job initialization."""
        assert agent_job.agent_id == "agent-dev-001"
        assert agent_job.role == "DEV"
        assert agent_job.vllm_url == "http://vllm-test:8000"
        assert agent_job.model == "test-model"
        assert agent_job.nats_url == "nats://nats-test:4222"
        assert agent_job.temperature == 0.7
        assert agent_job.max_tokens == 1024
        assert agent_job.timeout == 30
    
    def test_get_info(self, agent_job):
        """Test get_info method."""
        info = agent_job.get_info()
        
        assert info["agent_id"] == "agent-dev-001"
        assert info["role"] == "DEV"
        assert info["model"] == "test-model"
        assert info["vllm_url"] == "http://vllm-test:8000"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 1024
    
    def test_build_system_prompt_basic(self, agent_job):
        """Test system prompt building with basic constraints."""
        constraints = {
            "rubric": "Code must be clean",
            "requirements": ["Use type hints", "Add docstrings"],
        }
        
        prompt = agent_job._build_system_prompt(constraints, diversity=False)
        
        assert "expert software developer" in prompt
        assert "Code must be clean" in prompt
        assert "Use type hints" in prompt
        assert "Add docstrings" in prompt
        assert "creative and diverse" not in prompt
    
    def test_build_system_prompt_with_diversity(self, agent_job):
        """Test system prompt building with diversity flag."""
        constraints = {"rubric": "Test coverage"}
        
        prompt = agent_job._build_system_prompt(constraints, diversity=True)
        
        assert "creative and diverse" in prompt
        assert "alternative perspectives" in prompt
    
    def test_build_system_prompt_different_roles(self):
        """Test system prompts for different roles."""
        roles_and_keywords = [
            ("DEV", "software developer"),
            ("QA", "quality assurance"),
            ("ARCHITECT", "software architect"),
            ("DEVOPS", "DevOps engineer"),
            ("DATA", "data engineer"),
        ]
        
        for role, keyword in roles_and_keywords:
            agent = VLLMAgentJobBase(
                agent_id=f"agent-{role.lower()}-001",
                role=role,
                vllm_url="http://test:8000",
                model="test-model",
                nats_url="nats://test:4222",
            )
            prompt = agent._build_system_prompt({}, diversity=False)
            assert keyword.lower() in prompt.lower()
    
    def test_build_task_prompt(self, agent_job):
        """Test task prompt building."""
        task = "Implement factorial function"
        constraints = {
            "metadata": {
                "language": "Python",
                "framework": "pytest",
            }
        }
        
        prompt = agent_job._build_task_prompt(task, constraints)
        
        assert "Implement factorial function" in prompt
        assert "Analysis of the requirements" in prompt
        assert "Proposed solution approach" in prompt
        assert "Implementation details" in prompt
        assert "Python" in prompt
        assert "pytest" in prompt
    
    @pytest.mark.asyncio
    async def test_generate_proposal_success(self, agent_job):
        """Test successful proposal generation."""
        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "Here is my proposal for the factorial function..."
                    }
                }
            ],
            "usage": {
                "total_tokens": 150
            }
        }
        
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status = Mock()
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(return_value=mock_response_obj)
            mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_response_obj.__aexit__ = AsyncMock()
            
            mock_session_class.return_value = mock_session
            
            constraints = {"rubric": "Test rubric"}
            proposal = await agent_job._generate_proposal(
                "Test task", constraints, diversity=False
            )
            
            assert proposal["content"] == "Here is my proposal for the factorial function..."
            assert proposal["author_id"] == "agent-dev-001"
            assert proposal["author_role"] == "DEV"
            assert proposal["model"] == "test-model"
            assert proposal["tokens"] == 150
            
            # Verify vLLM API was called
            mock_session.post.assert_called_once()
            call_args = mock_session.post.call_args
            assert "http://vllm-test:8000/v1/chat/completions" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_generate_proposal_with_diversity(self, agent_job):
        """Test proposal generation with diversity flag."""
        mock_response = {
            "choices": [
                {"message": {"content": "Diverse proposal"}}
            ],
            "usage": {"total_tokens": 100}
        }
        
        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = AsyncMock()
            mock_response_obj = AsyncMock()
            mock_response_obj.raise_for_status = Mock()
            mock_response_obj.json = AsyncMock(return_value=mock_response)
            
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session.post = MagicMock(return_value=mock_response_obj)
            mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
            mock_response_obj.__aexit__ = AsyncMock()
            
            mock_session_class.return_value = mock_session
            
            _ = await agent_job._generate_proposal(
                "Test task", {}, diversity=True
            )
            
            # Verify temperature was increased for diversity
            call_args = mock_session.post.call_args
            payload = call_args[1]["json"]
            # Temperature should be 0.7 * 1.3 = 0.91
            assert payload["temperature"] > 0.7
    
    @pytest.mark.asyncio
    async def test_generate_proposal_api_error(self, agent_job):
        """Test proposal generation with vLLM API error."""
        import aiohttp
        
        # Patch the session.post call directly to raise an error
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = aiohttp.ClientError("API Error")
            
            with pytest.raises(RuntimeError, match="Failed to call vLLM API"):
                await agent_job._generate_proposal("Test task", {}, False)
    
    @pytest.mark.asyncio
    async def test_run_async_success(self, agent_job):
        """Test successful async job execution."""
        mock_proposal = {
            "content": "Test proposal",
            "author_id": "agent-dev-001",
            "author_role": "DEV",
            "model": "test-model",
            "tokens": 100,
        }
        
        # Mock NATS
        mock_nats = AsyncMock()
        mock_js = AsyncMock()
        mock_nats.jetstream = MagicMock(return_value=mock_js)
        mock_js.publish = AsyncMock()
        
        with patch("nats.connect", AsyncMock(return_value=mock_nats)):
            with patch.object(
                agent_job, "_generate_proposal", AsyncMock(return_value=mock_proposal)
            ):
                result = await agent_job._run_async(
                    task_id="task-123",
                    task_description="Test task",
                    constraints={},
                    diversity=False,
                )
                
                assert result["task_id"] == "task-123"
                assert result["agent_id"] == "agent-dev-001"
                assert result["role"] == "DEV"
                assert result["status"] == "completed"
                assert result["proposal"] == mock_proposal
                assert "duration_ms" in result
                assert "timestamp" in result
                
                # Verify NATS publish was called
                mock_js.publish.assert_called_once()
                call_args = mock_js.publish.call_args
                assert call_args[1]["subject"] == "agent.response.completed"
                
                # Verify payload
                payload = json.loads(call_args[1]["payload"].decode())
                assert payload["task_id"] == "task-123"
                assert payload["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_run_async_failure(self, agent_job):
        """Test async job execution with failure."""
        # Mock NATS
        mock_nats = AsyncMock()
        mock_js = AsyncMock()
        mock_nats.jetstream = MagicMock(return_value=mock_js)
        mock_js.publish = AsyncMock()
        
        with patch("nats.connect", AsyncMock(return_value=mock_nats)):
            with patch.object(
                agent_job,
                "_generate_proposal",
                AsyncMock(side_effect=RuntimeError("vLLM failed"))
            ):
                with pytest.raises(RuntimeError, match="vLLM failed"):
                    await agent_job._run_async(
                        task_id="task-456",
                        task_description="Test task",
                        constraints={},
                        diversity=False,
                    )
                
                # Verify error was published to NATS
                mock_js.publish.assert_called_once()
                call_args = mock_js.publish.call_args
                assert call_args[1]["subject"] == "agent.response.failed"
                
                # Verify error payload
                payload = json.loads(call_args[1]["payload"].decode())
                assert payload["task_id"] == "task-456"
                assert payload["status"] == "failed"
                assert "vLLM failed" in payload["error"]


class TestVLLMAgentJobIntegrationWithRay:
    """Integration tests for VLLMAgentJob with Ray."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("ray", minversion="2.0"),
        reason="Ray not available"
    )
    def test_ray_remote_decorator(self):
        """Test that VLLMAgentJob is properly decorated with @ray.remote."""
        # Verify the class has Ray remote attributes
        assert hasattr(VLLMAgentJob, "remote")
        assert hasattr(VLLMAgentJob, "options")
    
    @pytest.mark.skipif(
        True,
        reason="Ray local mode not supported for async actors - test in real cluster"
    )
    def test_get_info_via_ray(self):
        """Test calling get_info through Ray (without NATS/vLLM dependencies)."""
        import ray
        
        if not ray.is_initialized():
            ray.init(local_mode=True, ignore_reinit_error=True)
        
        try:
            # Create remote actor
            agent_ref = VLLMAgentJob.remote(
                agent_id="test-agent",
                role="DEV",
                vllm_url="http://test:8000",
                model="test-model",
                nats_url="nats://test:4222",
            )
            
            # Call get_info (doesn't require external dependencies)
            info_ref = agent_ref.get_info.remote()
            info = ray.get(info_ref)
            
            assert info["agent_id"] == "test-agent"
            assert info["role"] == "DEV"
            
        finally:
            ray.shutdown()

