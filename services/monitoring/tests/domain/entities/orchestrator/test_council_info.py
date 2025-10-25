"""Tests for CouncilInfo value object."""

import pytest
from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
from services.monitoring.domain.entities.orchestrator.council_info import CouncilInfo


class TestCouncilInfo:
    """Test cases for CouncilInfo value object."""
    
    def test_create_valid_council_info(self):
        """Test creating CouncilInfo with valid data."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        assert council.council_id == "council-dev-001"
        assert council.role == "DEV"
        assert council.emoji == "🧑‍💻"
        assert council.status == "active"
        assert council.model == "llama-3.1-8b"
        assert council.total_agents == 2
        assert council.agents.count() == 2
    
    def test_council_info_is_immutable(self):
        """Test that CouncilInfo is immutable (frozen dataclass)."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        
        with pytest.raises(AttributeError):
            council.council_id = "new-id"
    
    def test_empty_council_id_raises_error(self):
        """Test that empty council ID raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Council ID cannot be empty"):
            CouncilInfo(
                council_id="",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_empty_role_raises_error(self):
        """Test that empty role raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Council role cannot be empty"):
            CouncilInfo(
                council_id="council-dev-001",
                role="",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_empty_emoji_raises_error(self):
        """Test that empty emoji raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Council emoji cannot be empty"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_empty_status_raises_error(self):
        """Test that empty status raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Council status cannot be empty"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_empty_model_raises_error(self):
        """Test that empty model raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Council model cannot be empty"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="",
                total_agents=1,
                agents=agents
            )
    
    def test_negative_total_agents_raises_error(self):
        """Test that negative total agents raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Total agents cannot be negative"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=-1,
                agents=agents
            )
    
    def test_invalid_role_raises_error(self):
        """Test that invalid role raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Invalid agent role"):
            CouncilInfo(
                council_id="council-dev-001",
                role="INVALID_ROLE",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_invalid_status_raises_error(self):
        """Test that invalid status raises ValueError."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        with pytest.raises(ValueError, match="Invalid council status"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="invalid_status",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
    
    def test_valid_roles(self):
        """Test all valid roles."""
        valid_roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        
        for role in valid_roles:
            agents = [AgentInfo(agent_id=f"agent-{role.lower()}-001", role=role, status="ready")]
            
            council = CouncilInfo(
                council_id=f"council-{role.lower()}-001",
                role=role,
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
            assert council.role == role
    
    def test_valid_statuses(self):
        """Test all valid statuses."""
        valid_statuses = ["active", "idle", "inactive", "error", "offline"]
        
        for status in valid_statuses:
            agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
            
            council = CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status=status,
                model="llama-3.1-8b",
                total_agents=1,
                agents=agents
            )
            assert council.status == status
    
    def test_agents_count_mismatch_raises_error(self):
        """Test that agents count mismatch raises ValueError."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        with pytest.raises(ValueError, match="Total agents.*does not match"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=1,  # Mismatch: 2 agents but total_agents=1
                agents=agents
            )
    
    def test_agent_role_mismatch_raises_error(self):
        """Test that agent role mismatch raises ValueError."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-qa-001", role="QA", status="ready")  # Wrong role
        ]
        
        with pytest.raises(ValueError, match="Agent.*has role.*but expected role is"):
            CouncilInfo(
                council_id="council-dev-001",
                role="DEV",
                emoji="🧑‍💻",
                status="active",
                model="llama-3.1-8b",
                total_agents=2,
                agents=agents
            )
    
    def test_is_active(self):
        """Test is_active method (Tell, Don't Ask pattern)."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        active_council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert active_council.is_active() is True
        
        idle_council = CouncilInfo(
            council_id="council-dev-002",
            role="DEV",
            emoji="🧑‍💻",
            status="idle",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert idle_council.is_active() is False
    
    def test_is_idle(self):
        """Test is_idle method (Tell, Don't Ask pattern)."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        idle_council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="idle",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert idle_council.is_idle() is True
        
        active_council = CouncilInfo(
            council_id="council-dev-002",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert active_council.is_idle() is False
    
    def test_is_offline(self):
        """Test is_offline method (Tell, Don't Ask pattern)."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        offline_council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="offline",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert offline_council.is_offline() is True
        
        active_council = CouncilInfo(
            council_id="council-dev-002",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert active_council.is_offline() is False
    
    def test_has_agents(self):
        """Test has_agents method (Tell, Don't Ask pattern)."""
        agents = [AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready")]
        
        council_with_agents = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=1,
            agents=agents
        )
        assert council_with_agents.has_agents() is True
        
        empty_council = CouncilInfo(
            council_id="council-dev-002",
            role="DEV",
            emoji="🧑‍💻",
            status="inactive",
            model="llama-3.1-8b",
            total_agents=0,
            agents=[]
        )
        assert empty_council.has_agents() is False
    
    def test_get_ready_agents(self):
        """Test get_ready_agents method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle"),
            AgentInfo(agent_id="agent-dev-003", role="DEV", status="ready")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=3,
            agents=agents
        )
        
        ready_agents = council.get_ready_agents()
        assert len(ready_agents) == 2
        assert all(agent.is_ready() for agent in ready_agents)
    
    def test_get_busy_agents(self):
        """Test get_busy_agents method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="busy"),
            AgentInfo(agent_id="agent-dev-003", role="DEV", status="busy")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=3,
            agents=agents
        )
        
        busy_agents = council.get_busy_agents()
        assert len(busy_agents) == 2
        assert all(agent.is_busy() for agent in busy_agents)
    
    def test_get_offline_agents(self):
        """Test get_offline_agents method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="offline"),
            AgentInfo(agent_id="agent-dev-003", role="DEV", status="offline")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=3,
            agents=agents
        )
        
        offline_agents = council.get_offline_agents()
        assert len(offline_agents) == 2
        assert all(agent.is_offline() for agent in offline_agents)
    
    def test_get_agent_by_id(self):
        """Test get_agent_by_id method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        agent = council.get_agent_by_id("agent-dev-001")
        assert agent is not None
        assert agent.agent_id == "agent-dev-001"
        
        not_found = council.get_agent_by_id("agent-dev-999")
        assert not_found is None
    
    def test_has_agent(self):
        """Test has_agent method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        assert council.has_agent("agent-dev-001") is True
        assert council.has_agent("agent-dev-002") is True
        assert council.has_agent("agent-dev-999") is False
    
    def test_get_display_name(self):
        """Test get_display_name method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        expected = "DEV Council (2 agents)"
        assert council.get_display_name() == expected
    
    def test_get_agent_summary(self):
        """Test get_agent_summary method (Tell, Don't Ask pattern)."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-003", role="DEV", status="busy"),
            AgentInfo(agent_id="agent-dev-004", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=4,
            agents=agents
        )
        
        from services.monitoring.domain.entities.orchestrator.agent_summary import AgentSummary
        
        summary = council.get_agent_summary(AgentSummary)
        summary_dict = summary.to_dict()
        expected = {"ready": 2, "busy": 1, "idle": 1}
        
        # Only check the expected statuses
        for status, count in expected.items():
            assert summary_dict[status] == count
    
    def test_to_dict(self):
        """Test to_dict method for serialization."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        result = council.to_dict()
        
        assert result["council_id"] == "council-dev-001"
        assert result["role"] == "DEV"
        assert result["emoji"] == "🧑‍💻"
        assert result["status"] == "active"
        assert result["model"] == "llama-3.1-8b"
        assert result["total_agents"] == 2
        assert len(result["agents"]) == 2
        assert result["display_name"] == "DEV Council (2 agents)"
        # agent_summary removed because it requires dependency injection
    
    def test_from_dict(self):
        """Test from_dict factory method."""
        data = {
            "council_id": "council-dev-001",
            "role": "DEV",
            "emoji": "🧑‍💻",
            "status": "active",
            "model": "llama-3.1-8b",
            "total_agents": 2,
            "agents": [
                {"agent_id": "agent-dev-001", "role": "DEV", "status": "ready"},
                {"agent_id": "agent-dev-002", "role": "DEV", "status": "idle"}
            ]
        }
        
        from services.monitoring.domain.entities.orchestrator.agent_info import AgentInfo
        
        council = CouncilInfo.from_dict(data, AgentInfo)
        
        assert council.council_id == "council-dev-001"
        assert council.role == "DEV"
        assert council.emoji == "🧑‍💻"
        assert council.status == "active"
        assert council.model == "llama-3.1-8b"
        assert council.total_agents == 2
        assert council.agents.count() == 2
        agents_list = council.agents.to_list()
        assert agents_list[0].agent_id == "agent-dev-001"
        assert agents_list[1].agent_id == "agent-dev-002"
    
    def test_from_dict_missing_fields(self):
        """Test from_dict with missing required fields."""
        data = {
            "council_id": "council-dev-001",
            "role": "DEV",
            "emoji": "🧑‍💻",
            "status": "active"
            # Missing "model" and "total_agents"
        }
        
        with pytest.raises(ValueError, match="Missing required fields"):
            CouncilInfo.from_dict(data, AgentInfo)
    
    def test_create_empty_council(self):
        """Test create_empty_council factory method."""
        council = CouncilInfo.create_empty_council(
            council_id="council-dev-001",
            role="DEV",
            model="llama-3.1-8b"
        )
        
        assert council.council_id == "council-dev-001"
        assert council.role == "DEV"
        assert council.emoji == "🧑‍💻"
        assert council.status == "inactive"
        assert council.model == "llama-3.1-8b"
        assert council.total_agents == 0
        assert council.agents.count() == 0
    
    def test_create_empty_council_all_roles(self):
        """Test create_empty_council with all valid roles."""
        test_cases = [
            ("DEV", "🧑‍💻"),
            ("QA", "🧪"),
            ("ARCHITECT", "🏗️"),
            ("DEVOPS", "⚙️"),
            ("DATA", "📊")
        ]
        
        for role, expected_emoji in test_cases:
            council = CouncilInfo.create_empty_council(
                council_id=f"council-{role.lower()}-001",
                role=role,
                model="llama-3.1-8b"
            )
            
            assert council.role == role
            assert council.emoji == expected_emoji
    
    def test_equality(self):
        """Test that CouncilInfo instances with same data are equal."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council1 = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        council2 = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        assert council1 == council2
    
    def test_inequality(self):
        """Test that CouncilInfo instances with different data are not equal."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council1 = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        council2 = CouncilInfo(
            council_id="council-dev-002",  # Different ID
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        assert council1 != council2
    
    def test_hash(self):
        """Test that CouncilInfo instances are not hashable due to mutable fields."""
        agents = [
            AgentInfo(agent_id="agent-dev-001", role="DEV", status="ready"),
            AgentInfo(agent_id="agent-dev-002", role="DEV", status="idle")
        ]
        
        council = CouncilInfo(
            council_id="council-dev-001",
            role="DEV",
            emoji="🧑‍💻",
            status="active",
            model="llama-3.1-8b",
            total_agents=2,
            agents=agents
        )
        
        # Should raise TypeError because CouncilInfo contains mutable fields (list)
        with pytest.raises(TypeError, match="unhashable type"):
            hash(council)
