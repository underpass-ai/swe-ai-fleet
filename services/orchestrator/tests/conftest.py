"""Pytest configuration and fixtures for orchestrator tests."""

import pytest

from services.orchestrator.domain.entities import (
    AgentCollection,
    AgentConfig,
    CouncilRegistry,
    OrchestratorStatistics,
)


@pytest.fixture
def mock_agent():
    """Create a mock agent."""
    class MockAgent:
        def __init__(self, agent_id="agent-001", role="Coder", model="gpt-4"):
            self.agent_id = agent_id
            self.role = role
            self.model = model
            self.vllm_url = "http://vllm:8000"
    
    return MockAgent


@pytest.fixture
def mock_council():
    """Create a mock council."""
    class MockCouncil:
        def __init__(self, role="Coder", agents=None):
            self.role = role
            self.agents = agents or []
            self.execute_called = False
            self.results = [{"proposal": {"content": "solution"}}]
        
        def execute(self, task_description, constraints):
            self.execute_called = True
            self.task_description = task_description
            self.constraints = constraints
            return self.results
    
    return MockCouncil


@pytest.fixture
def agent_collection():
    """Create an empty AgentCollection."""
    return AgentCollection()


@pytest.fixture
def council_registry():
    """Create an empty CouncilRegistry."""
    return CouncilRegistry()


@pytest.fixture
def orchestrator_statistics():
    """Create an OrchestratorStatistics entity."""
    return OrchestratorStatistics()


@pytest.fixture
def sample_agent_config():
    """Create a sample AgentConfig."""
    return AgentConfig(
        agent_id="agent-001",
        role="Coder",
        vllm_url="http://vllm:8000",
        model="Qwen/Qwen3-0.6B",
        temperature=0.7
    )

