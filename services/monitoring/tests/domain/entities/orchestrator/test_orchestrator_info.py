"""Tests for OrchestratorInfo aggregate root."""

import pytest
from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
from services.monitoring.domain.entities.orchestrator.orchestrator_connection_status import (
    OrchestratorConnectionStatus,
)
from services.monitoring.domain.entities.orchestrator.orchestrator_info import OrchestratorInfo


class TestOrchestratorInfo:
    """Test cases for OrchestratorInfo aggregate root."""
    
    def create_test_councils(self) -> list[CouncilInfo]:
        """Create test councils for testing."""
        dev_agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="busy")
        ]
        
        qa_agents = [
            AgentInfo(agent_id="agent-qa-001", role="QA", status="ready"),
            AgentInfo(agent_id="agent-qa-002", role="QA", status="idle")
        ]
        
        return [
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=2,
                agents=dev_agents
            ),
            CouncilInfo(
                council_id="council-qa-001",
                role="QA",
                emoji="🧪",
                status="idle",
                model="llama-3.1-8b",
                total_agents=2,
                agents=qa_agents
            )
        ]
    
    def test_create_valid_orchestrator_info(self):
        """Test creating OrchestratorInfo with valid data."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator.connection_status == connection_status
        assert len(orchestrator.councils) == 2
        assert orchestrator.total_councils == 2
        assert orchestrator.total_agents == 4
    
    def test_orchestrator_info_is_immutable(self):
        """Test that OrchestratorInfo is immutable (frozen dataclass)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        with pytest.raises(AttributeError):
            orchestrator.connection_status = None
    
    def test_councils_count_mismatch_raises_error(self):
        """Test that councils count mismatch raises ValueError."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=3,  # Mismatch: 3 expected but 2 councils provided
            total_agents=4
        )
        
        with pytest.raises(ValueError, match="Councils count mismatch"):
            OrchestratorInfo(
                connection_status=connection_status,
                councils=councils
            )
    
    def test_agents_count_mismatch_raises_error(self):
        """Test that agents count mismatch raises ValueError."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=6  # Mismatch: 6 expected but 4 agents provided
        )
        
        with pytest.raises(ValueError, match="Agents count mismatch"):
            OrchestratorInfo(
                connection_status=connection_status,
                councils=councils
            )
    
    def test_total_councils_property(self):
        """Test total_councils property (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator.total_councils == 2
    
    def test_total_agents_property(self):
        """Test total_agents property (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator.total_agents == 4
    
    def test_is_connected(self):
        """Test is_connected method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        
        # Connected orchestrator
        connected_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        connected_orchestrator = OrchestratorInfo(
            connection_status=connected_status,
            councils=councils
        )
        assert connected_orchestrator.is_connected() is True
        
        # Disconnected orchestrator
        disconnected_status = OrchestratorConnectionStatus.create_disconnected_status(
            error="Connection failed"
        )
        disconnected_orchestrator = OrchestratorInfo(
            connection_status=disconnected_status,
            councils=[]
        )
        assert disconnected_orchestrator.is_connected() is False
    
    def test_is_healthy(self):
        """Test is_healthy method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        
        # Healthy orchestrator
        healthy_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        healthy_orchestrator = OrchestratorInfo(
            connection_status=healthy_status,
            councils=councils
        )
        assert healthy_orchestrator.is_healthy() is True
        
        # Unhealthy orchestrator (disconnected)
        unhealthy_status = OrchestratorConnectionStatus.create_disconnected_status(
            error="Connection failed"
        )
        unhealthy_orchestrator = OrchestratorInfo(
            connection_status=unhealthy_status,
            councils=[]
        )
        assert unhealthy_orchestrator.is_healthy() is False
    
    def test_has_councils(self):
        """Test has_councils method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator_with_councils = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        assert orchestrator_with_councils.has_councils() is True
        
        empty_orchestrator = OrchestratorInfo.create_empty_orchestrator()
        assert empty_orchestrator.has_councils() is False
    
    def test_has_agents(self):
        """Test has_agents method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator_with_agents = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        assert orchestrator_with_agents.has_agents() is True
        
        empty_orchestrator = OrchestratorInfo.create_empty_orchestrator()
        assert empty_orchestrator.has_agents() is False
    
    def test_get_council_by_role(self):
        """Test get_council_by_role method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        dev_council = orchestrator.get_council_by_role("DEV")
        assert dev_council is not None
        assert dev_council.role == "DEV"
        
        qa_council = orchestrator.get_council_by_role("QA")
        assert qa_council is not None
        assert qa_council.role == "QA"
        
        arch_council = orchestrator.get_council_by_role("ARCHITECT")
        assert arch_council is None
    
    def test_has_council(self):
        """Test has_council method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator.has_council("DEV") is True
        assert orchestrator.has_council("QA") is True
        assert orchestrator.has_council("ARCHITECT") is False
    
    def test_get_councils_by_status(self):
        """Test get_councils_by_status method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        active_councils = orchestrator.get_councils_by_status("active")
        assert len(active_councils) == 1
        assert active_councils[0].role == "DEV"
        
        idle_councils = orchestrator.get_councils_by_status("idle")
        assert len(idle_councils) == 1
        assert idle_councils[0].role == "QA"
    
    def test_get_active_councils(self):
        """Test get_active_councils method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        active_councils = orchestrator.get_active_councils()
        assert len(active_councils) == 1
        assert active_councils[0].role == "DEV"
    
    def test_get_idle_councils(self):
        """Test get_idle_councils method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        idle_councils = orchestrator.get_idle_councils()
        assert len(idle_councils) == 1
        assert idle_councils[0].role == "QA"
    
    def test_get_all_agents(self):
        """Test get_all_agents method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        all_agents = orchestrator.get_all_agents()
        assert len(all_agents) == 4
        assert all(isinstance(agent, AgentInfo) for agent in all_agents)
    
    def test_get_agents_by_role(self):
        """Test get_agents_by_role method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        dev_agents = orchestrator.get_agents_by_role("DEV")
        assert len(dev_agents) == 2
        assert all(agent.role == "DEV" for agent in dev_agents)
        
        qa_agents = orchestrator.get_agents_by_role("QA")
        assert len(qa_agents) == 2
        assert all(agent.role == "QA" for agent in qa_agents)
    
    def test_get_agents_by_status(self):
        """Test get_agents_by_status method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        ready_agents = orchestrator.get_agents_by_status("ready")
        assert len(ready_agents) == 2
        assert all(agent.status == "ready" for agent in ready_agents)
        
        busy_agents = orchestrator.get_agents_by_status("busy")
        assert len(busy_agents) == 1
        assert all(agent.status == "busy" for agent in busy_agents)
    
    def test_get_ready_agents(self):
        """Test get_ready_agents method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        ready_agents = orchestrator.get_ready_agents()
        assert len(ready_agents) == 2
        assert all(agent.is_ready() for agent in ready_agents)
    
    def test_get_busy_agents(self):
        """Test get_busy_agents method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        busy_agents = orchestrator.get_busy_agents()
        assert len(busy_agents) == 1
        assert all(agent.is_busy() for agent in busy_agents)
    
    def test_get_agent_by_id(self):
        """Test get_agent_by_id method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        agent = orchestrator.get_agent_by_id("agent-dev-001")
        assert agent is not None
        assert agent.agent_id == "agent-dev-001"
        assert agent.role == "DEV"
        
        not_found = orchestrator.get_agent_by_id("agent-nonexistent")
        assert not_found is None
    
    def test_has_agent(self):
        """Test has_agent method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator.has_agent("agent-dev-001") is True
        assert orchestrator.has_agent("agent-qa-001") is True
        assert orchestrator.has_agent("agent-nonexistent") is False
    
    def test_get_council_summary(self):
        """Test get_council_summary method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        summary = orchestrator.get_council_summary()
        expected = {"active": 1, "idle": 1}
        assert summary == expected
    
    def test_get_agent_summary(self):
        """Test get_agent_summary method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        summary = orchestrator.get_agent_summary()
        expected = {"ready": 2, "busy": 1, "idle": 1}
        assert summary == expected
    
    def test_get_role_summary(self):
        """Test get_role_summary method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        summary = orchestrator.get_role_summary()
        expected = {"DEV": 1, "QA": 1}
        assert summary == expected
    
    def test_get_health_summary(self):
        """Test get_health_summary method (Tell, Don't Ask pattern)."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        summary = orchestrator.get_health_summary()
        
        assert summary["is_connected"] is True
        assert summary["is_healthy"] is True
        assert summary["total_councils"] == 2
        assert summary["total_agents"] == 4
        assert summary["active_councils"] == 1
        assert summary["ready_agents"] == 2
        assert summary["busy_agents"] == 1
        assert summary["offline_agents"] == 0
        assert "council_summary" in summary
        assert "agent_summary" in summary
        assert "role_summary" in summary
    
    def test_to_dict(self):
        """Test to_dict method for serialization."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        result = orchestrator.to_dict()
        
        assert "connection_status" in result
        assert "councils" in result
        assert result["total_councils"] == 2
        assert result["total_agents"] == 4
        assert result["is_connected"] is True
        assert result["is_healthy"] is True
        assert "health_summary" in result
        assert len(result["councils"]) == 2
    
    def test_from_dict(self):
        """Test from_dict factory method."""
        from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
        from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
        from services.monitoring.domain.entities.orchestrator.orchestrator_connection_status import (
            OrchestratorConnectionStatus,
        )
        
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        original = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        data = original.to_dict()
        restored = OrchestratorInfo.from_dict(data, CouncilInfo, OrchestratorConnectionStatus, AgentInfo)
        
        assert restored.total_councils == original.total_councils
        assert restored.total_agents == original.total_agents
        assert restored.is_connected() == original.is_connected()
        assert restored.is_healthy() == original.is_healthy()
        assert len(restored.councils) == len(original.councils)
    
    def test_from_dict_missing_fields(self):
        """Test from_dict with missing required fields."""
        from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
        from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo
        from services.monitoring.domain.entities.orchestrator.orchestrator_connection_status import (
            OrchestratorConnectionStatus,
        )
        
        data = {
            "connection_status": {"connected": True, "error": None, "total_councils": 0, "total_agents": 0}
            # Missing "councils"
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            OrchestratorInfo.from_dict(data, CouncilInfo, OrchestratorConnectionStatus, AgentInfo)
    
    def test_create_empty_orchestrator(self):
        """Test create_empty_orchestrator factory method."""
        orchestrator = OrchestratorInfo.create_empty_orchestrator()
        
        assert orchestrator.is_connected() is False
        assert orchestrator.is_healthy() is False
        assert orchestrator.has_councils() is False
        assert orchestrator.has_agents() is False
        assert orchestrator.total_councils == 0
        assert orchestrator.total_agents == 0
    
    def test_create_connected_orchestrator(self):
        """Test create_connected_orchestrator factory method."""
        councils = self.create_test_councils()
        
        orchestrator = OrchestratorInfo.create_connected_orchestrator(councils)
        
        assert orchestrator.is_connected() is True
        assert orchestrator.is_healthy() is True
        assert orchestrator.has_councils() is True
        assert orchestrator.has_agents() is True
        assert orchestrator.total_councils == 2
        assert orchestrator.total_agents == 4
        assert len(orchestrator.councils) == 2
    
    def test_create_disconnected_orchestrator(self):
        """Test create_disconnected_orchestrator factory method."""
        councils = self.create_test_councils()
        
        orchestrator = OrchestratorInfo.create_disconnected_orchestrator(
            error="Connection failed",
            councils=councils
        )
        
        assert orchestrator.is_connected() is False
        assert orchestrator.is_healthy() is False
        assert orchestrator.has_councils() is True
        assert orchestrator.has_agents() is True
        assert orchestrator.total_councils == 2
        assert orchestrator.total_agents == 4
        assert len(orchestrator.councils) == 2
    
    def test_create_disconnected_orchestrator_no_councils(self):
        """Test create_disconnected_orchestrator without councils."""
        orchestrator = OrchestratorInfo.create_disconnected_orchestrator(
            error="Connection failed"
        )
        
        assert orchestrator.is_connected() is False
        assert orchestrator.is_healthy() is False
        assert orchestrator.has_councils() is False
        assert orchestrator.has_agents() is False
        assert orchestrator.total_councils == 0
        assert orchestrator.total_agents == 0
        assert len(orchestrator.councils) == 0
    
    def test_equality(self):
        """Test that OrchestratorInfo instances with same data are equal."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator1 = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        orchestrator2 = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        assert orchestrator1 == orchestrator2
    
    def test_inequality(self):
        """Test that OrchestratorInfo instances with different data are not equal."""
        councils = self.create_test_councils()
        
        connected_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        disconnected_status = OrchestratorConnectionStatus.create_disconnected_status(
            error="Connection failed"
        )
        
        orchestrator1 = OrchestratorInfo(
            connection_status=connected_status,
            councils=councils
        )
        
        orchestrator2 = OrchestratorInfo(
            connection_status=disconnected_status,
            councils=[]
        )
        
        assert orchestrator1 != orchestrator2
    
    def test_hash(self):
        """Test that OrchestratorInfo instances are not hashable due to mutable fields."""
        councils = self.create_test_councils()
        connection_status = OrchestratorConnectionStatus.create_connected_status(
            total_councils=2,
            total_agents=4
        )
        
        orchestrator = OrchestratorInfo(
            connection_status=connection_status,
            councils=councils
        )
        
        # Should raise TypeError because OrchestratorInfo contains mutable fields (list)
        with pytest.raises(TypeError, match="unhashable type"):
            hash(orchestrator)
