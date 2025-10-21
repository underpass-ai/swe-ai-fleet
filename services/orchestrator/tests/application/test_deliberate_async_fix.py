"""Unit test for async deliberation fix.

This test verifies that the Deliberate use case correctly handles async/await
and doesn't attempt to call asyncio.run() from within an event loop.
"""

import asyncio
import pytest

from swe_ai_fleet.orchestrator.domain.check_results.services import Scoring
from swe_ai_fleet.orchestrator.domain.tasks.task_constraints import TaskConstraints
from swe_ai_fleet.orchestrator.usecases.peer_deliberation_usecase import Deliberate


class MockAgent:
    """Mock agent for testing async deliberation."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    def generate(self, task: str, constraints, diversity: bool = False):
        """Generate a proposal (sync)."""
        return {"content": f"Proposal from {self.agent_id}: {task[:50]}"}
    
    def critique(self, content: str, rubric: str):
        """Critique a proposal (sync)."""
        return f"Feedback from {self.agent_id}"
    
    def revise(self, content: str, feedback: str):
        """Revise a proposal (sync)."""
        return f"Revised by {self.agent_id}: {content[:50]}"


class MockAsyncAgent:
    """Mock async agent for testing async deliberation."""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
    
    async def generate(self, task: str, constraints, diversity: bool = False):
        """Generate a proposal (async)."""
        await asyncio.sleep(0.001)  # Simulate async operation
        return {"content": f"Async proposal from {self.agent_id}: {task[:50]}"}
    
    async def critique(self, content: str, rubric: str):
        """Critique a proposal (async)."""
        await asyncio.sleep(0.001)
        return f"Async feedback from {self.agent_id}"
    
    async def revise(self, content: str, feedback: str):
        """Revise a proposal (async)."""
        await asyncio.sleep(0.001)
        return f"Async revised by {self.agent_id}: {content[:50]}"


class MockScoring(Scoring):
    """Mock scoring tool."""
    
    def run_check_suite(self, content: str):
        """Run checks on content."""
        return {"checks": ["syntax"], "passed": True}
    
    def score_checks(self, check_suite):
        """Score the check suite."""
        return 0.8


@pytest.fixture
def task_constraints():
    """Create mock task constraints."""
    return TaskConstraints(
        rubric="Quality code review",
        architect_rubric=None,
        cluster_spec=None
    )


@pytest.fixture
def mock_scoring():
    """Create mock scoring tool."""
    return MockScoring()


def test_deliberate_with_sync_agents(task_constraints, mock_scoring):
    """Test deliberation with synchronous agents."""
    agents = [MockAgent(f"agent-{i}") for i in range(3)]
    deliberate = Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    # Execute in async context (simulating gRPC server)
    async def run_test():
        results = await deliberate.execute(
            task="Review this authentication module",
            constraints=task_constraints
        )
        return results
    
    # This should NOT raise "asyncio.run() cannot be called from a running event loop"
    results = asyncio.run(run_test())
    
    assert len(results) == 3
    assert all(r.score > 0 for r in results)
    assert results[0].score >= results[1].score  # Sorted by score


def test_deliberate_with_async_agents(task_constraints, mock_scoring):
    """Test deliberation with asynchronous agents."""
    agents = [MockAsyncAgent(f"agent-{i}") for i in range(3)]
    deliberate = Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    # Execute in async context (simulating gRPC server)
    async def run_test():
        results = await deliberate.execute(
            task="Review this authentication module",
            constraints=task_constraints
        )
        return results
    
    # This should NOT raise "asyncio.run() cannot be called from a running event loop"
    results = asyncio.run(run_test())
    
    assert len(results) == 3
    assert all(r.score > 0 for r in results)
    assert results[0].score >= results[1].score  # Sorted by score


def test_deliberate_in_running_event_loop(task_constraints, mock_scoring):
    """Test that deliberation works when called from within a running event loop.
    
    This is the critical test that verifies the bug fix.
    Before the fix, this would raise:
    RuntimeError: asyncio.run() cannot be called from a running event loop
    """
    agents = [MockAgent(f"agent-{i}") for i in range(2)]
    deliberate = Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    # Simulate being called from a gRPC async server (event loop already running)
    async def grpc_handler_simulation():
        # This simulates what happens in server.py Deliberate() RPC handler
        results = await deliberate.execute(
            task="Review authentication code",
            constraints=task_constraints
        )
        return results
    
    # Execute the handler in an event loop (simulating gRPC server)
    results = asyncio.run(grpc_handler_simulation())
    
    # Verify results
    assert len(results) == 2
    assert all(r.proposal is not None for r in results)
    assert all(r.score > 0 for r in results)


@pytest.mark.asyncio
async def test_deliberate_with_pytest_asyncio(task_constraints, mock_scoring):
    """Test deliberation using pytest-asyncio.
    
    This verifies the fix works with pytest's async test support.
    """
    agents = [MockAsyncAgent(f"agent-{i}") for i in range(2)]
    deliberate = Deliberate(agents=agents, tooling=mock_scoring, rounds=1)
    
    # Call directly with await (already in async context)
    results = await deliberate.execute(
        task="Implement user authentication",
        constraints=task_constraints
    )
    
    assert len(results) == 2
    assert all("Async" in r.proposal.content for r in results)

