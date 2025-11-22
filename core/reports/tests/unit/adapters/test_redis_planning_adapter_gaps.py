"""Quick coverage for reports redis_planning_read_adapter gaps"""

from unittest.mock import MagicMock

from core.reports.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter
from core.reports.domain.report import Report


def test_save_report_success():
    """Test successful report save."""
    mock_client = MagicMock()
    mock_pipeline = MagicMock()
    mock_client.pipeline.return_value = mock_pipeline
    
    adapter = RedisPlanningReadAdapter(mock_client)
    report = Report(
        case_id="case-001",
        plan_id="plan-001",
        generated_at_ms=1000,
        markdown="# Test report",
    )
    
    adapter.save_report("case-001", report, ttl_seconds=3600)
    
    mock_client.pipeline.assert_called_once()
    mock_pipeline.execute.assert_called_once()


def test_get_llm_events_for_session_success():
    """Test successful LLM events retrieval."""
    mock_client = MagicMock()
    events_raw = [
        ("msg-2", {"role": "assistant", "content": "Hi there"}),
        ("msg-1", {"role": "user", "content": "Hello"}),
    ]
    mock_client.xrevrange.return_value = events_raw
    
    adapter = RedisPlanningReadAdapter(mock_client)
    result = adapter.get_llm_events_for_session("session-001", count=2)
    
    assert len(result) == 2
    # After reversed, msg-1 should be first
    assert result[0]["id"] == "msg-1"
    assert result[0]["role"] == "user"


def test_get_llm_events_for_session_empty():
    """Test LLM events retrieval when stream is empty."""
    mock_client = MagicMock()
    mock_client.xrevrange.return_value = []
    
    adapter = RedisPlanningReadAdapter(mock_client)
    result = adapter.get_llm_events_for_session("session-001")
    
    assert result == []


def test_get_llm_events_for_session_exception():
    """Test exception handling in get_llm_events_for_session."""
    mock_client = MagicMock()
    mock_client.xrevrange.side_effect = Exception("Stream error")
    
    adapter = RedisPlanningReadAdapter(mock_client)
    result = adapter.get_llm_events_for_session("session-001")
    
    assert result == []
