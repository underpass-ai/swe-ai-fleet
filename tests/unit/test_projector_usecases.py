# tests/unit/test_projector_usecases.py
"""Integration tests for ProjectorCoordinator using a fake writer implementation."""

import pytest
from core.context.usecases.projector_coordinator import ProjectorCoordinator


class _FakeWriter:
    """Fake implementation of GraphCommandPort for testing."""

    def __init__(self):
        self.ops = []

    def init_constraints(self, labels):
        self.ops.append(("constraints", tuple(labels)))

    def upsert_entity(self, label, id, props=None):
        self.ops.append(("upsert", label, id, props or {}))

    def upsert_entity_multi(self, labels, id, props=None):
        self.ops.append(("upsert_multi", tuple(labels), id, props or {}))

    def relate(self, src, rel, dst, **kw):
        self.ops.append(("rel", src, rel, dst, kw))


class TestProjectorCoordinatorIntegration:
    """Integration tests for ProjectorCoordinator using fake writer."""

    def test_routing_and_side_effects(self):
        """Test that all event types are properly routed and produce expected side effects."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        # Test all supported event types
        assert c.handle("case.created", {"case_id": "C1", "name": "Demo"})
        assert c.handle("plan.versioned", {"case_id": "C1", "plan_id": "P1", "version": 1})
        assert c.handle("subtask.created", {"plan_id": "P1", "sub_id": "T1", "title": "Fix tests"})
        assert c.handle("subtask.status_changed", {"sub_id": "T1", "status": "in_progress"})
        assert c.handle(
            "decision.made", {"node_id": "D1", "kind": "dev.change", "summary": "Patch", "sub_id": "T1"}
        )

        # Test unknown event type
        assert not c.handle("unknown.event", {})

        # Verify expected operations were performed
        assert any(op[0] == "upsert" and op[1] == "Case" and op[2] == "C1" for op in w.ops)
        assert any(op[0] == "rel" and op[1] == "C1" and op[2] == "HAS_PLAN" and op[3] == "P1" for op in w.ops)
        assert any(
            op[0] == "rel" and op[1] == "P1" and op[2] == "HAS_SUBTASK" and op[3] == "T1" for op in w.ops
        )
        assert any(
            op[0] == "upsert"
            and op[1] == "Subtask"
            and op[2] == "T1"
            and op[3].get("last_status") == "in_progress"
            for op in w.ops
        )
        assert any(op[0] == "rel" and op[1] == "D1" and op[2] == "AFFECTS" and op[3] == "T1" for op in w.ops)

    def test_case_created_with_minimal_payload(self):
        """Test case.created event with minimal required payload."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        result = c.handle("case.created", {"case_id": "C1"})

        assert result is True
        assert len(w.ops) == 1
        op = w.ops[0]
        assert op[0] == "upsert"
        assert op[1] == "Case"
        assert op[2] == "C1"
        assert op[3] == {"case_id": "C1", "name": ""}

    def test_plan_versioned_with_string_version(self):
        """Test plan.versioned event with string version (should be converted to int)."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        result = c.handle("plan.versioned", {"case_id": "C1", "plan_id": "P1", "version": "2"})

        assert result is True
        assert len(w.ops) == 2  # upsert + relate

        # Check upsert operation
        upsert_op = next(op for op in w.ops if op[0] == "upsert")
        assert upsert_op[1] == "PlanVersion"
        assert upsert_op[2] == "P1"
        assert upsert_op[3] == {"plan_id": "P1", "version": 2, "case_id": "C1"}  # Should be converted to int

        # Check relate operation
        relate_op = next(op for op in w.ops if op[0] == "rel")
        assert relate_op[1] == "C1"
        assert relate_op[2] == "HAS_PLAN"
        assert relate_op[3] == "P1"

    def test_subtask_created_with_defaults(self):
        """Test subtask.created event with default values."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        result = c.handle("subtask.created", {"plan_id": "P1", "sub_id": "T1"})

        assert result is True
        assert len(w.ops) == 2  # upsert + relate

        # Check upsert operation with defaults
        upsert_op = next(op for op in w.ops if op[0] == "upsert")
        assert upsert_op[1] == "Subtask"
        assert upsert_op[2] == "T1"
        assert upsert_op[3] == {"sub_id": "T1", "title": "", "type": "task", "plan_id": "P1"}

    def test_decision_made_without_sub_id(self):
        """Test decision.made event without sub_id (no relationship created)."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        result = c.handle("decision.made", {"node_id": "D1", "kind": "design", "summary": "Use REST"})

        assert result is True
        assert len(w.ops) == 1  # Only upsert, no relate

        op = w.ops[0]
        assert op[0] == "upsert"
        assert op[1] == "Decision"
        assert op[2] == "D1"
        assert op[3] == {"kind": "design", "summary": "Use REST"}

    def test_subtask_status_changed_with_none_status(self):
        """Test subtask.status_changed event with None status."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        result = c.handle("subtask.status_changed", {"sub_id": "T1", "status": None})

        assert result is True
        assert len(w.ops) == 1

        op = w.ops[0]
        assert op[0] == "upsert"
        assert op[1] == "Subtask"
        assert op[2] == "T1"
        assert op[3] == {"sub_id": "T1", "last_status": None}

    def test_error_handling_missing_required_field(self):
        """Test that missing required fields raise appropriate errors."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        # Missing case_id should raise KeyError
        with pytest.raises(KeyError):
            c.handle("case.created", {"name": "Test"})

        # Missing plan_id should raise KeyError
        with pytest.raises(KeyError):
            c.handle("subtask.created", {"sub_id": "T1"})

        # Missing node_id should raise KeyError
        with pytest.raises(KeyError):
            c.handle("decision.made", {"kind": "design"})

    def test_all_event_types_registered(self):
        """Test that all expected event types are registered."""
        w = _FakeWriter()
        c = ProjectorCoordinator(w)

        expected_events = {
            "case.created",
            "plan.versioned",
            "subtask.created",
            "subtask.status_changed",
            "decision.made",
        }

        assert set(c.handlers.keys()) == expected_events

        # All handlers should be callable
        for handler in c.handlers.values():
            assert callable(handler)
