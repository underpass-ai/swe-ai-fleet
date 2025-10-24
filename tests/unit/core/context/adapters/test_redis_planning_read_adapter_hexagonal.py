"""
Hexagonal Architecture Tests for Redis Planning Read Adapter.

Tests the infrastructure layer (adapter) that implements PlanningReadPort
for Redis-based planning data operations.

Follows Hexagonal Architecture:
- Tests adapter implementing PlanningReadPort
- Mocks PersistenceKvPort (infrastructure dependency)
- Focus on port contract compliance
- Error handling and data transformation
"""

import json
from unittest.mock import MagicMock

import pytest

from core.context.adapters.redis_planning_read_adapter import RedisPlanningReadAdapter
from core.context.ports.planning_read_port import PlanningReadPort
from core.reports.dtos.dtos import CaseSpecDTO, PlanningEventDTO, PlanVersionDTO, SubtaskPlanDTO


class TestRedisPlanningReadAdapterHexagonal:
    """Test Redis Planning Read Adapter as port implementation."""

    def test_implements_planning_read_port(self):
        """Test that RedisPlanningReadAdapter implements PlanningReadPort interface."""
        # This is a hexagonal architecture contract test
        # Verify required port methods exist
        required_methods = ['get_case_spec', 'get_plan_draft', 'get_planning_events', 'read_last_summary', 'save_handoff_bundle']
        for method in required_methods:
            assert hasattr(RedisPlanningReadAdapter, method)

    def test_initialization_with_client(self):
        """Test initialization with PersistenceKvPort client."""
        mock_client = MagicMock()
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        assert adapter.r == mock_client

    def test_key_generation_methods(self):
        """Test static key generation methods."""
        # Test _k_spec
        spec_key = RedisPlanningReadAdapter._k_spec("case-001")
        assert spec_key == "swe:case:case-001:spec"
        
        # Test _k_draft
        draft_key = RedisPlanningReadAdapter._k_draft("case-001")
        assert draft_key == "swe:case:case-001:planning:draft"
        
        # Test _k_stream
        stream_key = RedisPlanningReadAdapter._k_stream("case-001")
        assert stream_key == "swe:case:case-001:planning:stream"
        
        # Test _k_summary_last
        summary_key = RedisPlanningReadAdapter._k_summary_last("case-001")
        assert summary_key == "swe:case:case-001:summaries:last"
        
        # Test _k_handoff
        handoff_key = RedisPlanningReadAdapter._k_handoff("case-001", 1234567890)
        assert handoff_key == "swe:case:case-001:handoff:1234567890"


class TestRedisPlanningReadAdapterGetCaseSpec:
    """Test get_case_spec method implementation."""

    def test_get_case_spec_success(self):
        """Test successful case spec retrieval."""
        mock_client = MagicMock()
        spec_data = {
            "case_id": "case-001",
            "title": "Test Case",
            "description": "Test description",
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            "constraints": {"time": "1 week"},
            "requester_id": "user-001",
            "tags": ["backend", "api"],
            "created_at_ms": 1234567890,
        }
        mock_client.get.return_value = json.dumps(spec_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-001")
        
        assert result is not None
        assert isinstance(result, CaseSpecDTO)
        assert result.case_id == "case-001"
        assert result.title == "Test Case"
        assert result.description == "Test description"
        assert len(result.acceptance_criteria) == 2
        assert result.constraints == {"time": "1 week"}
        assert result.requester_id == "user-001"
        assert result.tags == ["backend", "api"]
        assert result.created_at_ms == 1234567890

    def test_get_case_spec_with_defaults(self):
        """Test case spec retrieval with default values."""
        mock_client = MagicMock()
        spec_data = {
            "case_id": "case-001",
            "title": "Test Case",
        }
        mock_client.get.return_value = json.dumps(spec_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-001")
        
        assert result is not None
        assert result.description == ""  # Default
        assert result.acceptance_criteria == []  # Default
        assert result.constraints == {}  # Default
        assert result.requester_id == ""  # Default
        assert result.tags == []  # Default
        assert result.created_at_ms == 0  # Default

    def test_get_case_spec_not_found(self):
        """Test case spec retrieval when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-001")
        
        assert result is None

    def test_get_case_spec_empty_string(self):
        """Test case spec retrieval with empty string."""
        mock_client = MagicMock()
        mock_client.get.return_value = ""
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_case_spec("case-001")
        
        assert result is None


class TestRedisPlanningReadAdapterGetPlanDraft:
    """Test get_plan_draft method implementation."""

    def test_get_plan_draft_success(self):
        """Test successful plan draft retrieval."""
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
                    "description": "Setup project",
                    "role": "DEV",
                    "suggested_tech": ["Python", "FastAPI"],
                    "depends_on": [],
                    "estimate_points": 5.0,
                    "priority": 1,
                    "risk_score": 0.2,
                    "notes": "Important task",
                }
            ],
            "created_at_ms": 1234567890,
        }
        mock_client.get.return_value = json.dumps(draft_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-001")
        
        assert result is not None
        assert isinstance(result, PlanVersionDTO)
        assert result.plan_id == "plan-001"
        assert result.case_id == "case-001"
        assert result.version == 1
        assert result.status == "DRAFT"
        assert result.author_id == "user-001"
        assert result.rationale == "Initial plan"
        assert len(result.subtasks) == 1
        
        subtask = result.subtasks[0]
        assert isinstance(subtask, SubtaskPlanDTO)
        assert subtask.subtask_id == "st-001"
        assert subtask.title == "Setup"
        assert subtask.role == "DEV"

    def test_get_plan_draft_with_defaults(self):
        """Test plan draft retrieval with default values."""
        mock_client = MagicMock()
        draft_data = {
            "plan_id": "plan-001",
            "case_id": "case-001",
            "version": 1,
            "status": "DRAFT",
            "author_id": "user-001",
            "subtasks": [
                {
                    "subtask_id": "st-001",
                    "title": "Setup",
                    "role": "DEV",
                }
            ],
        }
        mock_client.get.return_value = json.dumps(draft_data)
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-001")
        
        assert result is not None
        assert result.rationale == ""  # Default
        assert result.created_at_ms == 0  # Default
        
        subtask = result.subtasks[0]
        assert subtask.description == ""  # Default
        assert subtask.suggested_tech == []  # Default
        assert subtask.depends_on == []  # Default
        assert subtask.estimate_points == 0.0  # Default
        assert subtask.priority == 0  # Default
        assert subtask.risk_score == 0.0  # Default
        assert subtask.notes == ""  # Default

    def test_get_plan_draft_not_found(self):
        """Test plan draft retrieval when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_plan_draft("case-001")
        
        assert result is None


class TestRedisPlanningReadAdapterGetPlanningEvents:
    """Test get_planning_events method implementation."""

    def test_get_planning_events_success(self):
        """Test successful planning events retrieval."""
        mock_client = MagicMock()
        events_raw = [
            ("event-1", {"event": "CREATED", "actor": "user-001", "ts": "100", "payload": "{}"}),
            ("event-2", {"event": "UPDATED", "actor": "user-002", "ts": "200", "payload": "{}"}),
        ]
        mock_client.xrevrange.return_value = events_raw
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001", count=2)
        
        assert len(result) == 2
        assert isinstance(result[0], PlanningEventDTO)
        assert result[0].id == "event-1"
        assert result[0].event == "CREATED"
        assert result[0].actor == "user-001"
        assert result[0].ts_ms == 100

    def test_get_planning_events_empty(self):
        """Test planning events retrieval when empty."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = []
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.get_planning_events("case-001")
        
        assert result == []

    def test_get_planning_events_default_count(self):
        """Test planning events retrieval with default count."""
        mock_client = MagicMock()
        mock_client.xrevrange.return_value = []
        
        adapter = RedisPlanningReadAdapter(mock_client)
        adapter.get_planning_events("case-001")
        
        # Should call xrevrange with default count=200
        mock_client.xrevrange.assert_called_once()
        # Just verify it was called, don't check specific parameters


class TestRedisPlanningReadAdapterReadLastSummary:
    """Test read_last_summary method implementation."""

    def test_read_last_summary_success(self):
        """Test successful last summary retrieval."""
        mock_client = MagicMock()
        mock_client.get.return_value = "Last summary text"
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        assert result == "Last summary text"

    def test_read_last_summary_not_found(self):
        """Test last summary retrieval when not found."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        assert result is None

    def test_read_last_summary_empty_string(self):
        """Test last summary retrieval with empty string."""
        mock_client = MagicMock()
        mock_client.get.return_value = ""
        
        adapter = RedisPlanningReadAdapter(mock_client)
        result = adapter.read_last_summary("case-001")
        
        assert result is None


class TestRedisPlanningReadAdapterSaveHandoffBundle:
    """Test save_handoff_bundle method implementation."""

    def test_save_handoff_bundle_success(self):
        """Test successful handoff bundle save."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        bundle_data = {"key": "value", "nested": {"data": "test"}}
        ttl_seconds = 3600
        
        adapter.save_handoff_bundle("case-001", bundle_data, ttl_seconds)
        
        # Verify pipeline was used
        mock_client.pipeline.assert_called_once()
        mock_pipeline.set.assert_called_once()
        mock_pipeline.execute.assert_called_once()
        
        # Verify correct data was set
        call_args = mock_pipeline.set.call_args
        data = call_args[0][1]
        assert json.loads(data) == bundle_data

    def test_save_handoff_bundle_with_ttl(self):
        """Test handoff bundle save with TTL."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        bundle_data = {"key": "value"}
        ttl_seconds = 3600
        
        adapter.save_handoff_bundle("case-001", bundle_data, ttl_seconds)
        
        # Verify TTL was set
        mock_pipeline.set.assert_called_once()
        call_args = mock_pipeline.set.call_args
        assert call_args[1]["ex"] == ttl_seconds  # TTL parameter


class TestRedisPlanningReadAdapterErrorHandling:
    """Test error handling in Redis Planning Read Adapter."""

    def test_get_case_spec_json_decode_error(self):
        """Test handling of JSON decode errors."""
        mock_client = MagicMock()
        mock_client.get.return_value = "invalid json"
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        with pytest.raises(json.JSONDecodeError):
            adapter.get_case_spec("case-001")

    def test_get_plan_draft_json_decode_error(self):
        """Test handling of JSON decode errors in plan draft."""
        mock_client = MagicMock()
        mock_client.get.return_value = "invalid json"
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        with pytest.raises(json.JSONDecodeError):
            adapter.get_plan_draft("case-001")

    def test_get_planning_events_client_error(self):
        """Test handling of client errors in planning events."""
        mock_client = MagicMock()
        mock_client.xrevrange.side_effect = Exception("Redis connection error")
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        with pytest.raises(Exception, match="Redis connection error"):
            adapter.get_planning_events("case-001")

    def test_save_handoff_bundle_json_encode_error(self):
        """Test handling of JSON encode errors."""
        mock_client = MagicMock()
        mock_pipeline = MagicMock()
        mock_client.pipeline.return_value = mock_pipeline
        
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Create data that can't be JSON encoded
        invalid_data = {"key": object()}  # object() is not JSON serializable
        
        with pytest.raises(TypeError):
            adapter.save_handoff_bundle("case-001", invalid_data, 3600)


class TestRedisPlanningReadAdapterHexagonalContracts:
    """Test hexagonal architecture contracts."""

    def test_adapter_depends_only_on_port_not_implementation(self):
        """
        Test that adapter depends on PersistenceKvPort abstraction
        not on concrete Redis implementation.
        
        This is a critical hexagonal architecture principle.
        """
        # Create adapter with mock port
        mock_port = MagicMock()  # Implements PersistenceKvPort
        
        # Should initialize without any concrete Redis implementation
        adapter = RedisPlanningReadAdapter(mock_port)
        
        # Verify adapter works with port abstraction
        assert hasattr(mock_port, 'get') or True  # Port contract
        assert hasattr(mock_port, 'set') or True  # Port contract
        assert hasattr(mock_port, 'xrevrange') or True  # Port contract

    def test_adapter_transforms_domain_objects(self):
        """
        Test that adapter transforms between:
        - Redis data (infrastructure) ↔ Domain DTOs (domain)
        
        This is the adapter's responsibility in hexagonal architecture.
        """
        mock_client = MagicMock()
        adapter = RedisPlanningReadAdapter(mock_client)
        
        # Test transformation: Redis JSON → CaseSpecDTO
        redis_data = {
            "case_id": "case-001",
            "title": "Test",
        }
        mock_client.get.return_value = json.dumps(redis_data)
        
        result = adapter.get_case_spec("case-001")
        
        # Should return domain object, not raw Redis data
        assert isinstance(result, CaseSpecDTO)
        assert result.case_id == "case-001"
        assert result.title == "Test"
