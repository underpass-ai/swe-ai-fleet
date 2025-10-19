"""Tests for DeliberationResultData entity."""


from services.orchestrator.domain.entities import DeliberationResultData


class TestDeliberationResultData:
    """Test suite for DeliberationResultData entity."""
    
    def test_creation(self):
        """Test creating DeliberationResultData."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            duration_ms=1500
        )
        
        assert result.task_id == "task-123"
        assert result.status == "DELIBERATION_STATUS_COMPLETED"
        assert result.duration_ms == 1500
    
    def test_is_completed_true(self):
        """Test is_completed property."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED"
        )
        
        assert result.is_completed is True
    
    def test_is_completed_false(self):
        """Test is_completed returns False for other statuses."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_PENDING"
        )
        
        assert result.is_completed is False
    
    def test_is_failed_true(self):
        """Test is_failed property."""
        result_failed = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_FAILED"
        )
        result_timeout = DeliberationResultData(
            task_id="task-124",
            status="DELIBERATION_STATUS_TIMEOUT"
        )
        
        assert result_failed.is_failed is True
        assert result_timeout.is_failed is True
    
    def test_is_failed_false(self):
        """Test is_failed returns False for non-failure statuses."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED"
        )
        
        assert result.is_failed is False
    
    def test_has_results_true(self):
        """Test has_results when results present."""
        from services.orchestrator.domain.entities.deliberation_result_data import (
            AgentResultData,
            ProposalData,
        )
        
        proposal = ProposalData("agent-001", "Coder", "code")
        agent_result = AgentResultData("agent-001", proposal)
        
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            results=[agent_result]
        )
        
        assert result.has_results is True
    
    def test_has_results_false(self):
        """Test has_results when no results."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            results=[]
        )
        
        assert result.has_results is False
    
    def test_winner_agent_id(self):
        """Test winner_agent_id property."""
        from services.orchestrator.domain.entities.deliberation_result_data import (
            AgentResultData,
            ProposalData,
        )
        
        proposal = ProposalData("agent-001", "Coder", "code")
        agent_result = AgentResultData("agent-001", proposal)
        
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            results=[agent_result]
        )
        
        assert result.winner_agent_id == "agent-001"
    
    def test_winner_agent_id_none(self):
        """Test winner_agent_id is None when no results."""
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            results=[]
        )
        
        assert result.winner_agent_id is None
    
    def test_from_dict(self):
        """Test creating from dict."""
        data = {
            "task_id": "task-123",
            "status": "DELIBERATION_STATUS_COMPLETED",
            "duration_ms": 2000,
            "error_message": "",
            "results": [
                {
                    "agent_id": "agent-001",
                    "proposal": {
                        "author_id": "agent-001",
                        "author_role": "Coder",
                        "content": "solution"
                    }
                }
            ],
            "total_agents": 3,
            "received_count": 1,
            "failed_count": 2
        }
        
        result = DeliberationResultData.from_dict(data)
        
        assert result.task_id == "task-123"
        assert result.status == "DELIBERATION_STATUS_COMPLETED"
        assert result.duration_ms == 2000
        assert len(result.results) == 1
        assert result.results[0].agent_id == "agent-001"
    
    def test_to_dict(self):
        """Test converting to dict."""
        from services.orchestrator.domain.entities.deliberation_result_data import (
            AgentResultData,
            ProposalData,
        )
        
        proposal = ProposalData("agent-001", "Coder", "code")
        agent_result = AgentResultData("agent-001", proposal)
        
        result = DeliberationResultData(
            task_id="task-123",
            status="DELIBERATION_STATUS_COMPLETED",
            results=[agent_result],
            total_agents=3
        )
        
        data = result.to_dict()
        
        assert data["task_id"] == "task-123"
        assert data["status"] == "DELIBERATION_STATUS_COMPLETED"
        assert len(data["results"]) == 1
        assert data["total_agents"] == 3

