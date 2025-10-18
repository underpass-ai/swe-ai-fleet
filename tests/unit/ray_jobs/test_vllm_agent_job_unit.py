"""Unit tests for VLLMAgentJob."""
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from swe_ai_fleet.ray_jobs import (
    RayAgentExecutor,
    RayAgentFactory,
)
from swe_ai_fleet.ray_jobs.domain import ExecutionRequest


class TestVLLMAgentJob:
    """Unit tests for VLLMAgentJob."""
    
    @pytest.fixture
    def agent_job(self):
        """Create a RayAgentExecutor instance for testing (not Ray actor)."""
        return RayAgentFactory.create(
            agent_id="agent-dev-001",
            role="DEV",
            vllm_url="http://vllm-test:8000",
            model="test-model",
            nats_url="nats://nats-test:4222",
            temperature=0.7,
            max_tokens=1024,
            timeout=30,
            enable_tools=False,
        )
    
    def test_initialization(self, agent_job):
        """Test agent job initialization."""
        assert agent_job.config.agent_id == "agent-dev-001"
        assert agent_job.config.role.value == "DEV"
        assert agent_job.config.vllm_url == "http://vllm-test:8000"
        assert agent_job.config.model == "test-model"
        assert agent_job.config.nats_url == "nats://nats-test:4222"
        assert agent_job.config.temperature == 0.7
        assert agent_job.config.max_tokens == 1024
        assert agent_job.config.timeout == 30
    
    def test_get_info(self, agent_job):
        """Test get_info method."""
        info = agent_job.get_info()
        
        assert info["agent_id"] == "agent-dev-001"
        assert info["role"] == "DEV"
        assert info["model"] == "test-model"
        assert info["vllm_url"] == "http://vllm-test:8000"
        assert info["temperature"] == 0.7
        assert info["max_tokens"] == 1024
    
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
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
    
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
    def test_build_system_prompt_with_diversity(self, agent_job):
        """Test system prompt building with diversity flag."""
        constraints = {"rubric": "Test coverage"}
        
        prompt = agent_job._build_system_prompt(constraints, diversity=True)
        
        assert "creative and diverse" in prompt
        assert "alternative perspectives" in prompt
    
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
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
            agent = RayAgentFactory.create(
                agent_id=f"agent-{role.lower()}-001",
                role=role,
                vllm_url="http://test:8000",
                model="test-model",
                nats_url="nats://test:4222",
            )
            prompt = agent._build_system_prompt({}, diversity=False)
            assert keyword.lower() in prompt.lower()
    
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
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
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
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
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
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
    @pytest.mark.skip(reason="Moved to GenerateProposal use case")
    async def test_generate_proposal_api_error(self, agent_job):
        """Test proposal generation with vLLM API error."""
        import aiohttp
        
        # Patch the session.post call directly to raise an error
        with patch("aiohttp.ClientSession.post") as mock_post:
            mock_post.side_effect = aiohttp.ClientError("API Error")
            
            with pytest.raises(RuntimeError, match="Failed to call vLLM API"):
                await agent_job._generate_proposal("Test task", {}, False)
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Moved to ExecuteAgentTask use case")
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
                # Create execution request
                request = ExecutionRequest.create(
                    task_id="task-123",
                    task_description="Test task",
                    constraints={},
                    diversity=False,
                )
                result = await agent_job._run_async(request)
                
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
    @pytest.mark.skip(reason="Moved to ExecuteAgentTask use case")
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
                # Create execution request
                request = ExecutionRequest.create(
                    task_id="task-456",
                    task_description="Test task",
                    constraints={},
                    diversity=False,
                )
                with pytest.raises(RuntimeError, match="vLLM failed"):
                    await agent_job._run_async(request)
                
                # Verify error was published to NATS
                mock_js.publish.assert_called_once()
                call_args = mock_js.publish.call_args
                assert call_args[1]["subject"] == "agent.response.failed"
                
                # Verify error payload
                payload = json.loads(call_args[1]["payload"].decode())
                assert payload["task_id"] == "task-456"
                assert payload["status"] == "failed"
                assert "vLLM failed" in payload["error"]


class TestRayAgentExecutorIntegrationWithRay:
    """Integration tests for RayAgentExecutor with Ray."""
    
    @pytest.mark.skip(reason="VLLMAgentJob removed - use RayAgentExecutor directly with ray.remote")
    def test_ray_remote_decorator(self):
        """Test that RayAgentExecutor can be used with @ray.remote decorator."""
        pass
    
    @pytest.mark.skip(reason="VLLMAgentJob removed - use RayAgentExecutor with ray.remote")
    def test_get_info_via_ray(self):
        """Test calling get_info through Ray (without NATS/vLLM dependencies)."""
        pass

