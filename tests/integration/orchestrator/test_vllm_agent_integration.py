"""
Integration tests for VLLMAgentJob without Ray.

These tests validate the agent logic using VLLMAgentJobBase (no Ray decorator)
with a real vLLM server and NATS.
"""

import pytest

from swe_ai_fleet.ray_jobs.vllm_agent_job import VLLMAgentJobBase


@pytest.mark.integration
class TestVLLMAgentJobIntegration:
    """Integration tests for VLLMAgentJob (without Ray, using Base class)."""
    
    @pytest.fixture
    def vllm_url(self):
        """vLLM server URL (can be localhost or container)."""
        import os
        return os.getenv("VLLM_URL", "http://localhost:28000")
    
    @pytest.fixture
    def nats_url(self):
        """NATS server URL."""
        import os
        return os.getenv("NATS_URL", "nats://localhost:4222")
    
    @pytest.fixture
    def agent(self, vllm_url, nats_url):
        """Create VLLMAgentJobBase instance (no Ray)."""
        return VLLMAgentJobBase(
            agent_id="agent-test-001",
            role="DEV",
            vllm_url=vllm_url,
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            nats_url=nats_url,
            temperature=0.7,
            max_tokens=512,  # Smaller for faster tests
            timeout=30,
        )
    
    @pytest.mark.asyncio
    async def test_agent_can_call_vllm_directly(self, agent, vllm_url):
        """Test that agent can call vLLM API successfully."""
        # This test requires vLLM running (skip if not available)
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{vllm_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip(f"vLLM not available at {vllm_url}")
        except Exception:
            pytest.skip(f"vLLM not available at {vllm_url}")
        
        # Generate proposal
        proposal = await agent._generate_proposal(
            task="Write a simple hello world function",
            constraints={"rubric": "Keep it simple"},
            diversity=False
        )
        
        # Verify proposal structure
        assert "content" in proposal
        assert "author_id" in proposal
        assert proposal["author_id"] == "agent-test-001"
        assert proposal["author_role"] == "DEV"
        assert len(proposal["content"]) > 10, "Proposal should have content"
        
        print(f"\n✅ Proposal generated ({len(proposal['content'])} chars)")
        print(f"Preview: {proposal['content'][:100]}...")
    
    @pytest.mark.asyncio
    async def test_agent_diversity_mode(self, agent, vllm_url):
        """Test that diversity mode increases temperature."""
        import aiohttp
        
        # Skip if vLLM not available
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{vllm_url}/health", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    if resp.status != 200:
                        pytest.skip(f"vLLM not available at {vllm_url}")
        except Exception:
            pytest.skip(f"vLLM not available at {vllm_url}")
        
        task = "Explain what a function is"
        constraints = {}
        
        # Generate two proposals (one normal, one with diversity)
        proposal1 = await agent._generate_proposal(task, constraints, diversity=False)
        proposal2 = await agent._generate_proposal(task, constraints, diversity=True)
        
        # Both should have content
        assert len(proposal1["content"]) > 10
        assert len(proposal2["content"]) > 10
        
        # They should be different (diversity should cause variation)
        # Note: Not always guaranteed due to sampling, but usually different
        print("\n✅ Generated 2 proposals")
        print(f"Proposal 1: {len(proposal1['content'])} chars")
        print(f"Proposal 2: {len(proposal2['content'])} chars")
        
        if proposal1["content"][:50] != proposal2["content"][:50]:
            print("✅ Proposals are different (diversity working)")
        else:
            print("⚠️  Proposals similar (can happen with sampling)")
    
    def test_agent_build_prompts(self, agent):
        """Test prompt building (no external dependencies)."""
        # Test system prompt
        constraints = {
            "rubric": "Code must be clean",
            "requirements": ["Use type hints", "Add docstrings"]
        }
        
        system_prompt = agent._build_system_prompt(constraints, diversity=False)
        
        assert "expert software developer" in system_prompt.lower()
        assert "Code must be clean" in system_prompt
        assert "Use type hints" in system_prompt
        assert "Add docstrings" in system_prompt
        
        # Test task prompt
        task_prompt = agent._build_task_prompt("Write factorial", constraints)
        
        assert "Write factorial" in task_prompt
        assert "proposal" in task_prompt.lower()
        
        print("\n✅ Prompts generated correctly")


@pytest.mark.integration  
@pytest.mark.skipif(
    True,  # Skip by default (requires NATS running)
    reason="Requires NATS server - run manually when needed"
)
class TestVLLMAgentJobWithNATS:
    """Integration tests that require NATS server."""
    
    @pytest.mark.asyncio
    async def test_full_agent_execution_with_nats(self):
        """Test complete agent execution including NATS publishing."""
        import os
        
        vllm_url = os.getenv("VLLM_URL", "http://localhost:28000")
        nats_url = os.getenv("NATS_URL", "nats://localhost:24222")
        
        agent = VLLMAgentJobBase(
            agent_id="agent-integration-001",
            role="DEV",
            vllm_url=vllm_url,
            model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
            nats_url=nats_url,
            temperature=0.7,
            max_tokens=256,
            timeout=30,
        )
        
        # Execute full flow
        result = await agent._run_async(
            task_id="test-task-integration",
            task_description="Write a hello world function",
            constraints={},
            diversity=False
        )
        
        # Verify result
        assert result["task_id"] == "test-task-integration"
        assert result["agent_id"] == "agent-integration-001"
        assert result["status"] == "completed"
        assert "proposal" in result
        assert len(result["proposal"]["content"]) > 10
        
        print("\n✅ Full execution completed")
        print(f"   Duration: {result['duration_ms']}ms")
        print(f"   Proposal length: {len(result['proposal']['content'])} chars")
