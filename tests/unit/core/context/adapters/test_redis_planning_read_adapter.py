"""Unit tests for core.context.adapters.redis_planning_read_adapter

Tests RedisPlanningReadAdapter implementation with comprehensive coverage
of Redis operations, JSON parsing, error handling, and edge cases.
"""

import json
from unittest.mock import MagicMock, patch

from core.context.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter
from core.reports.dtos.dtos import (
    CaseSpecDTO,
    PlanVersionDTO,
)


class TestRedisPlanningReadAdapterKeyGeneration:
    """Test static key generation methods"""

    def test_key_spec(self):
        """Test _k_spec generates correct key."""
        key = RedisPlanningReadAdapter._k_spec("case-123")
        assert key == "swe:case:case-123:spec"

    def test_key_draft(self):
        """Test _k_draft generates correct key."""
        key = RedisPlanningReadAdapter._k_draft("case-123")
        assert key == "swe:case:case-123:planning:draft"

    def test_key_stream(self):
        """Test _k_stream generates correct key."""
        key = RedisPlanningReadAdapter._k_stream("case-123")
        assert key == "swe:case:case-123:planning:stream"

    def test_key_summary_last(self):
        """Test _k_summary_last generates correct key."""
        key = RedisPlanningReadAdapter._k_summary_last("case-123")
        assert key == "swe:case:case-123:summaries:last"

    def test_key_handoff(self):
        """Test _k_handoff generates correct key with timestamp."""
        key = RedisPlanningReadAdapter._k_handoff("case-123", 1234567890)
        assert key == "swe:case:case-123:handoff:1234567890"

    def test_key_generation_with_special_chars(self):
        """Test key generation with special characters in case_id."""
        key = RedisPlanningReadAdapter._k_spec("case-456-special")
        assert "case-456-special" in key
        assert key.startswith("swe:case:")


class TestRedisPlanningReadAdapterInitialization:
    """Test adapter initialization"""

    def test_initialization_with_client(self):
        """Test adapter initializes with persistence client."""
        mock_client = MagicMock()
        adapter = RedisPlanningReadAdapter(mock_client)
        
        assert adapter.r == mock_client

    def test_initialization_stores_client_reference(self):
        """Test client reference is stored correctly."""
        mock_client = MagicMock()
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Verify client is accessible
        assert adapter.r is not None
        assert adapter.r == mock_client

    def test_client_property_exposes_underlying_client(self):
        """Test client property exposes the underlying Redis client."""
        mock_client = MagicMock()
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Act - Access client property
        exposed_client = adapter.client
        
        # Assert - Should return the same client
        assert exposed_client is mock_client
        assert exposed_client is adapter.r

    def test_client_property_is_read_only(self):
        """Test client property is read-only (no setter)."""
        mock_client = MagicMock()
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Act & Assert - Should raise AttributeError on assignment
        try:
            adapter.client = MagicMock()  # type: ignore[misc]
            assert False, "client property should be read-only"
        except AttributeError:
            # Expected - property has no setter
            pass

    def test_client_property_allows_direct_redis_operations(self):
        """Test client property can be used for direct Redis operations."""
        mock_client = MagicMock()
        mock_client.hset = MagicMock(return_value=7)
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Act - Use client property for direct operation
        result = adapter.client.hset("story:US-001", mapping={"title": "Test"})
        
        # Assert - Should call the underlying client
        assert result == 7
        mock_client.hset.assert_called_once_with("story:US-001", mapping={"title": "Test"})


class TestGetCaseSpec:
    """Test get_case_spec method"""

    def test_get_case_spec_success(self):
        """Test successful retrieval of case spec."""
        mock_client = MagicMock()
        spec_data = {
            "case_id": "case-001",
            "title": "Implement API",
            "description": "REST API implementation",
            "acceptance_criteria": ["Must be RESTful", "Must have auth"],
            "constraints": {"max_time": "2 weeks"},
            "requester_id": "user-001",
            "tags": ["backend", "api"],
            "created_at_ms": 1234567890,
        }
        mock_client.get.return_value = json.dumps(spec_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-001")
        
        assert isinstance(result, CaseSpecDTO)
        assert result.case_id == "case-001"
        assert result.title == "Implement API"
        assert result.description == "REST API implementation"
        assert result.acceptance_criteria == ["Must be RESTful", "Must have auth"]
        assert result.constraints == {"max_time": "2 weeks"}
        assert result.requester_id == "user-001"
        assert result.tags == ["backend", "api"]
        assert result.created_at_ms == 1234567890

    def test_get_case_spec_not_found(self):
        """Test get_case_spec returns None when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("nonexistent-case")
        
        assert result is None

    def test_get_case_spec_with_defaults(self):
        """Test get_case_spec uses default values for optional fields."""
        mock_client = MagicMock()
        spec_data = {
            "case_id": "case-002",
            "title": "Minimal spec",
        }
        mock_client.get.return_value = json.dumps(spec_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-002")
        
        assert result.case_id == "case-002"
        assert result.title == "Minimal spec"
        assert result.description == ""
        assert result.acceptance_criteria == []
        assert result.constraints == {}
        assert result.requester_id == ""
        assert result.tags == []
        assert result.created_at_ms == 0

    def test_get_case_spec_calls_correct_key(self):
        """Test get_case_spec uses correct Redis key."""
        mock_client = MagicMock()
        mock_client.get.return_value = json.dumps({
            "case_id": "case-001",
            "title": "Test",
        })
        
        adapter = RedisPlanningReadAdapter(mock_client)
        adapter.get_case_spec("case-001")
        
        mock_client.get.assert_called_once_with("swe:case:case-001:spec")


class TestGetPlanDraft:
    """Test get_plan_draft method"""

    def test_get_plan_draft_success(self):
        """Test successful retrieval of plan draft."""
        mock_client = MagicMock()
        draft_data = {
            "plan_id": "plan-001",
            "case_id": "case-001",
            "version": 1,
            "status": "DRAFT",
            "author_id": "user-001",
            "rationale": "Initial plan",
            "subtasks": [
                {
                    "subtask_id": "st-001",
                    "title": "Setup",
                    "description": "Project setup",
                    "role": "DEV",
                    "suggested_tech": ["Node.js", "Express"],
                    "depends_on": [],
                    "estimate_points": 5.0,
                    "priority": 1,
                    "risk_score": 0.2,
                    "notes": "Low risk",
                }
            ],
            "created_at_ms": 1234567890,
        }
        mock_client.get.return_value = json.dumps(draft_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-001")
        
        assert isinstance(result, PlanVersionDTO)
        assert result.plan_id == "plan-001"
        assert result.case_id == "case-001"
        assert result.version == 1
        assert result.status == "DRAFT"
        assert result.author_id == "user-001"
        assert result.rationale == "Initial plan"
        assert len(result.subtasks) == 1
        
        # Check subtask
        st = result.subtasks[0]
        assert st.subtask_id == "st-001"
        assert st.title == "Setup"
        assert st.role == "DEV"
        assert st.suggested_tech == ["Node.js", "Express"]

    def test_get_plan_draft_not_found(self):
        """Test get_plan_draft returns None when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("nonexistent-case")
        
        assert result is None

    def test_get_plan_draft_with_no_subtasks(self):
        """Test get_plan_draft handles empty subtasks list."""
        mock_client = MagicMock()
        draft_data = {
            "plan_id": "plan-002",
            "case_id": "case-002",
            "version": 1,
            "status": "DRAFT",
            "author_id": "user-001",
            "subtasks": [],
        }
        mock_client.get.return_value = json.dumps(draft_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-002")
        
        assert result.subtasks == []

    def test_get_plan_draft_with_subtask_defaults(self):
        """Test get_plan_draft uses defaults for optional subtask fields."""
        mock_client = MagicMock()
        draft_data = {
            "plan_id": "plan-003",
            "case_id": "case-003",
            "version": 1,
            "status": "DRAFT",
            "author_id": "user-001",
            "subtasks": [
                {
                    "subtask_id": "st-001",
                    "title": "Minimal subtask",
                    "role": "QA",
                }
            ],
        }
        mock_client.get.return_value = json.dumps(draft_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-003")
        
        st = result.subtasks[0]
        assert st.description == ""
        assert st.suggested_tech == []
        assert st.depends_on == []
        assert st.estimate_points == 0.0
        assert st.priority == 0
        assert st.risk_score == 0.0
        assert st.notes == ""


class TestGetPlanningEvents:
    """Test get_planning_events method"""

    def test_get_planning_events_success(self):
        """Test successful retrieval of planning events."""
        mock_client = MagicMock()
        events_raw = [
            ("event-1", {"event": "CREATED", "actor": "user-001", "ts": "100", "payload": '{"type":"initial"}'}),
            ("event-2", {"event": "UPDATED", "actor": "user-002", "ts": "200", "payload": '{"type":"revised"}'}),
        ]
        mock_client.xrevrange.return_value = events_raw
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001", count=200)
        
        assert len(result) == 2
        assert result[0].id == "event-1"
        assert result[0].event == "CREATED"
        assert result[0].actor == "user-001"
        assert result[0].payload == {"type": "initial"}
        assert result[0].ts_ms == 100

    def test_get_planning_events_chronological_sort(self):
        """Test events are sorted chronologically."""
        mock_client = MagicMock()
        # Return events in reverse chronological order
        events_raw = [
            ("event-3", {"event": "FINAL", "actor": "user", "ts": "300", "payload": "{}"}),
            ("event-1", {"event": "CREATED", "actor": "user", "ts": "100", "payload": "{}"}),
            ("event-2", {"event": "UPDATED", "actor": "user", "ts": "200", "payload": "{}"}),
        ]
        mock_client.xrevrange.return_value = events_raw
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001")
        
        # Should be sorted chronologically
        assert result[0].ts_ms == 100
        assert result[1].ts_ms == 200
        assert result[2].ts_ms == 300

    def test_get_planning_events_invalid_payload_json(self):
        """Test get_planning_events handles invalid JSON payloads."""
        mock_client = MagicMock()
        events_raw = [
            ("event-1", {"event": "ERROR", "actor": "user", "ts": "100", "payload": "invalid json{"}),
        ]
        mock_client.xrevrange.return_value = events_raw
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001")
        
        assert len(result) == 1
        assert result[0].payload == {"raw": "invalid json{"}

    def test_get_planning_events_missing_payload(self):
        """Test get_planning_events handles missing payload."""
        mock_client = MagicMock()
        events_raw = [
            ("event-1", {"event": "CREATED", "actor": "user", "ts": "100"}),
        ]
        mock_client.xrevrange.return_value = events_raw
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001")
        
        assert result[0].payload == {}

    def test_get_planning_events_empty(self):
        """Test get_planning_events with no events."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = []
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001")
        
        assert result == []

    def test_get_planning_events_custom_count(self):
        """Test get_planning_events respects count parameter."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = []
        
        adapter = RedisPlanningReadAdapter(mock_client)
        adapter.get_planning_events("case-001", count=50)
        
        mock_client.xrevrange.assert_called_once()
        call_args = mock_client.xrevrange.call_args
        assert call_args[1]["count"] == 50


class TestReadLastSummary:
    """Test read_last_summary method"""

    def test_read_last_summary_success(self):
        """Test successful retrieval of last summary."""
        mock_client = MagicMock()
        summary_text = "Summary: Project approved for development"
        mock_client.get.return_value = summary_text
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        assert result == summary_text

    def test_read_last_summary_not_found(self):
        """Test read_last_summary returns None when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        assert result is None

    def test_read_last_summary_empty_string(self):
        """Test read_last_summary with empty string returns None."""
        mock_client = MagicMock()
        mock_client.get.return_value = ""
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        # Empty string is treated as falsy and converted to None
        assert result is None

    def test_read_last_summary_calls_correct_key(self):
        """Test read_last_summary uses correct Redis key."""
        mock_client = MagicMock()
        mock_client.get.return_value = "summary"
        
        adapter = RedisPlanningReadAdapter(mock_client)
        adapter.read_last_summary("case-001")
        
        mock_client.get.assert_called_once_with("swe:case:case-001:summaries:last")


class TestSaveHandoffBundle:
    """Test save_handoff_bundle method"""

    def test_save_handoff_bundle_success(self):
        """Test successful save of handoff bundle."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        bundle = {"task": "completed", "results": ["test1", "test2"]}
        
        with patch("time.time", return_value=1234.567):
            adapter.save_handoff_bundle("case-001", bundle, ttl_seconds=3600)
        
        # Verify pipeline was created
        mock_client.pipeline.assert_called_once()
        
        # Verify set was called with correct parameters
        mock_pipeline.set.assert_called_once()
        call_args = mock_pipeline.set.call_args
        
        # Check key contains handoff and timestamp
        key = call_args[0][0]
        assert "handoff" in key
        assert "1234567" in key  # Timestamp in milliseconds
        
        # Check value is JSON
        value = call_args[0][1]
        assert json.loads(value) == bundle
        
        # Check TTL
        assert call_args[1]["ex"] == 3600
        
        # Verify execute was called
        mock_pipeline.execute.assert_called_once()

    def test_save_handoff_bundle_different_ttls(self):
        """Test save_handoff_bundle with different TTL values."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        bundle = {"test": "data"}
        
        with patch("time.time", return_value=1000):
            adapter.save_handoff_bundle("case-001", bundle, ttl_seconds=7200)
        
        call_args = mock_pipeline.set.call_args
        assert call_args[1]["ex"] == 7200

    def test_save_handoff_bundle_complex_data(self):
        """Test save_handoff_bundle with complex nested data."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        bundle = {
            "status": "completed",
            "subtasks": [
                {"id": "st-1", "result": "pass"},
                {"id": "st-2", "result": "fail"},
            ],
            "metadata": {
                "duration": 3600,
                "nodes": ["a", "b", "c"],
            }
        }
        
        with patch("time.time", return_value=1000):
            adapter.save_handoff_bundle("case-001", bundle, ttl_seconds=1800)
        
        call_args = mock_pipeline.set.call_args
        saved_value = json.loads(call_args[0][1])
        assert saved_value == bundle

    def test_save_handoff_bundle_empty_bundle(self):
        """Test save_handoff_bundle with empty bundle."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        with patch("time.time", return_value=1000):
            adapter.save_handoff_bundle("case-001", {}, ttl_seconds=100)
        
        call_args = mock_pipeline.set.call_args
        saved_value = json.loads(call_args[0][1])
        assert saved_value == {}
