"""Tests for ListCouncilsUseCase."""


from services.orchestrator.application import ListCouncilsUseCase
from services.orchestrator.domain.entities import CouncilRegistry
from services.orchestrator.domain.ports.council_query_port import CouncilInfo


class MockCouncilQueryPort:
    """Mock council query port for testing."""
    
    def __init__(self, councils=None):
        self.councils = councils or []
        self.list_councils_called = False
    
    def list_councils(self, council_registry, include_agents=False):
        """Mock list_councils method."""
        self.list_councils_called = True
        self.include_agents = include_agents
        return self.councils


class TestListCouncilsUseCase:
    """Test suite for ListCouncilsUseCase."""
    
    def test_execute_success(self):
        """Test successful council listing."""
        council_info = CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=3,
            status="active",
            model="gpt-4"
        )
        council_info.agent_infos = []  # Assigned as attribute
        council_infos = [council_info]
        council_query = MockCouncilQueryPort(councils=council_infos)
        registry = CouncilRegistry()
        
        use_case = ListCouncilsUseCase(council_query=council_query)
        result = use_case.execute(council_registry=registry, include_agents=True)
        
        assert len(result) == 1
        assert result[0].role == "Coder"
        assert council_query.list_councils_called is True
        assert council_query.include_agents is True
    
    def test_execute_without_agents(self):
        """Test listing councils without agent details.
        
        Note: The validation for include_agents=True is in the adapter,
        not the use case. This test verifies the use case works with mocks.
        """
        council_info = CouncilInfo(
            council_id="council-coder",
            role="Coder",
            num_agents=3,
            status="active",
            model="gpt-4"
        )
        council_info.agent_infos = []  # Assigned as attribute
        council_infos = [council_info]
        council_query = MockCouncilQueryPort(councils=council_infos)
        registry = CouncilRegistry()
        
        use_case = ListCouncilsUseCase(council_query=council_query)
        result = use_case.execute(council_registry=registry, include_agents=False)
        
        # Use case should succeed with mock (real adapter validates)
        assert len(result) == 1
        assert result[0].role == "Coder"
    
    def test_execute_empty_registry(self):
        """Test listing councils from empty registry."""
        council_query = MockCouncilQueryPort(councils=[])
        registry = CouncilRegistry()
        
        use_case = ListCouncilsUseCase(council_query=council_query)
        result = use_case.execute(council_registry=registry, include_agents=True)
        
        assert len(result) == 0

