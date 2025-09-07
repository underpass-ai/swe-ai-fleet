# tests/unit/test_context_domain_models_unit.py
from __future__ import annotations

import pytest

from swe_ai_fleet.context.domain.case import Case
from swe_ai_fleet.context.domain.decision import Decision
from swe_ai_fleet.context.domain.domain_event import DomainEvent
from swe_ai_fleet.context.domain.graph_relationship import GraphRelationship
from swe_ai_fleet.context.domain.plan_version import PlanVersion
from swe_ai_fleet.context.domain.subtask import Subtask


class TestCase:
    """Unit tests for Case domain model."""

    def test_from_payload_with_name(self):
        """Test creating Case from payload with name."""
        payload = {"case_id": "CASE-001", "name": "Test Case"}
        case = Case.from_payload(payload)
        
        assert case.case_id == "CASE-001"
        assert case.name == "Test Case"

    def test_from_payload_without_name(self):
        """Test creating Case from payload without name."""
        payload = {"case_id": "CASE-001"}
        case = Case.from_payload(payload)
        
        assert case.case_id == "CASE-001"
        assert case.name == ""

    def test_to_dict(self):
        """Test converting Case to dictionary."""
        case = Case(case_id="CASE-001", name="Test Case")
        result = case.to_dict()
        
        expected = {"case_id": "CASE-001", "name": "Test Case"}
        assert result == expected

    def test_to_graph_properties(self):
        """Test converting Case to graph properties."""
        case = Case(case_id="CASE-001", name="Test Case")
        result = case.to_graph_properties()
        
        expected = {"name": "Test Case"}
        assert result == expected

    def test_immutable(self):
        """Test that Case is immutable."""
        case = Case(case_id="CASE-001", name="Test Case")
        
        with pytest.raises(AttributeError):
            case.case_id = "NEW-ID"


class TestDecision:
    """Unit tests for Decision domain model."""

    def test_from_payload_with_all_fields(self):
        """Test creating Decision from payload with all fields."""
        payload = {
            "node_id": "DEC-001",
            "kind": "architecture",
            "summary": "Use microservices",
            "sub_id": "SUB-001"
        }
        decision = Decision.from_payload(payload)
        
        assert decision.node_id == "DEC-001"
        assert decision.kind == "architecture"
        assert decision.summary == "Use microservices"
        assert decision.sub_id == "SUB-001"

    def test_from_payload_without_optional_fields(self):
        """Test creating Decision from payload without optional fields."""
        payload = {"node_id": "DEC-001"}
        decision = Decision.from_payload(payload)
        
        assert decision.node_id == "DEC-001"
        assert decision.kind == ""
        assert decision.summary == ""
        assert decision.sub_id is None

    def test_to_dict(self):
        """Test converting Decision to dictionary."""
        decision = Decision(
            node_id="DEC-001",
            kind="design",
            summary="Use REST API",
            sub_id="SUB-001"
        )
        result = decision.to_dict()
        
        expected = {
            "node_id": "DEC-001",
            "kind": "design",
            "summary": "Use REST API",
            "sub_id": "SUB-001"
        }
        assert result == expected

    def test_to_graph_properties(self):
        """Test converting Decision to graph properties."""
        decision = Decision(
            node_id="DEC-001",
            kind="design",
            summary="Use REST API"
        )
        result = decision.to_graph_properties()
        
        expected = {
            "kind": "design",
            "summary": "Use REST API"
        }
        assert result == expected

    def test_affects_subtask_with_sub_id(self):
        """Test affects_subtask returns True when sub_id is present."""
        decision = Decision(
            node_id="DEC-001",
            kind="design",
            summary="Use REST API",
            sub_id="SUB-001"
        )
        assert decision.affects_subtask() is True

    def test_affects_subtask_without_sub_id(self):
        """Test affects_subtask returns False when sub_id is None."""
        decision = Decision(
            node_id="DEC-001",
            kind="design",
            summary="Use REST API"
        )
        assert decision.affects_subtask() is False


class TestPlanVersion:
    """Unit tests for PlanVersion domain model."""

    def test_from_payload_with_version(self):
        """Test creating PlanVersion from payload with version."""
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": 2
        }
        plan = PlanVersion.from_payload(payload)
        
        assert plan.plan_id == "PLAN-001"
        assert plan.version == 2
        assert plan.case_id == "CASE-001"

    def test_from_payload_with_string_version(self):
        """Test creating PlanVersion from payload with string version."""
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": "3"
        }
        plan = PlanVersion.from_payload(payload)
        
        assert plan.version == 3  # Should be converted to int

    def test_from_payload_without_version(self):
        """Test creating PlanVersion from payload without version."""
        payload = {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001"
        }
        plan = PlanVersion.from_payload(payload)
        
        assert plan.version == 1  # Default version

    def test_to_dict(self):
        """Test converting PlanVersion to dictionary."""
        plan = PlanVersion(
            plan_id="PLAN-001",
            version=2,
            case_id="CASE-001"
        )
        result = plan.to_dict()
        
        expected = {
            "plan_id": "PLAN-001",
            "version": 2,
            "case_id": "CASE-001"
        }
        assert result == expected

    def test_to_graph_properties(self):
        """Test converting PlanVersion to graph properties."""
        plan = PlanVersion(
            plan_id="PLAN-001",
            version=2,
            case_id="CASE-001"
        )
        result = plan.to_graph_properties()
        
        expected = {"version": 2}
        assert result == expected

    def test_get_relationship_to_case(self):
        """Test getting relationship details to case."""
        plan = PlanVersion(
            plan_id="PLAN-001",
            version=2,
            case_id="CASE-001"
        )
        relationship = plan.get_relationship_to_case()
        
        assert isinstance(relationship, GraphRelationship)
        assert relationship.src_id == "CASE-001"
        assert relationship.rel_type == "HAS_PLAN"
        assert relationship.dst_id == "PLAN-001"
        assert relationship.src_labels == ["Case"]
        assert relationship.dst_labels == ["PlanVersion"]


class TestSubtask:
    """Unit tests for Subtask domain model."""

    def test_from_payload_with_all_fields(self):
        """Test creating Subtask from payload with all fields."""
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001",
            "title": "Implement feature",
            "type": "development"
        }
        subtask = Subtask.from_payload(payload)
        
        assert subtask.sub_id == "SUB-001"
        assert subtask.title == "Implement feature"
        assert subtask.type == "development"
        assert subtask.plan_id == "PLAN-001"
        assert subtask.last_status is None

    def test_from_payload_with_defaults(self):
        """Test creating Subtask from payload with default values."""
        payload = {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001"
        }
        subtask = Subtask.from_payload(payload)
        
        assert subtask.sub_id == "SUB-001"
        assert subtask.title == ""
        assert subtask.type == "task"
        assert subtask.plan_id == "PLAN-001"

    def test_from_status_payload(self):
        """Test creating Subtask from status update payload."""
        payload = {
            "sub_id": "SUB-001",
            "status": "completed"
        }
        subtask = Subtask.from_status_payload(payload)
        
        assert subtask.sub_id == "SUB-001"
        assert subtask.title == ""
        assert subtask.type == "task"
        assert subtask.plan_id == ""
        assert subtask.last_status == "completed"

    def test_to_dict(self):
        """Test converting Subtask to dictionary."""
        subtask = Subtask(
            sub_id="SUB-001",
            title="Implement feature",
            type="development",
            plan_id="PLAN-001",
            last_status="completed"
        )
        result = subtask.to_dict()
        
        expected = {
            "sub_id": "SUB-001",
            "title": "Implement feature",
            "type": "development",
            "plan_id": "PLAN-001",
            "last_status": "completed"
        }
        assert result == expected

    def test_to_graph_properties_with_status(self):
        """Test converting Subtask to graph properties with status."""
        subtask = Subtask(
            sub_id="SUB-001",
            title="Implement feature",
            type="development",
            plan_id="PLAN-001",
            last_status="completed"
        )
        result = subtask.to_graph_properties()
        
        expected = {
            "title": "Implement feature",
            "type": "development",
            "last_status": "completed"
        }
        assert result == expected

    def test_to_graph_properties_without_status(self):
        """Test converting Subtask to graph properties without status."""
        subtask = Subtask(
            sub_id="SUB-001",
            title="Implement feature",
            type="development",
            plan_id="PLAN-001"
        )
        result = subtask.to_graph_properties()
        
        expected = {
            "title": "Implement feature",
            "type": "development"
        }
        assert result == expected

    def test_get_relationship_to_plan(self):
        """Test getting relationship details to plan."""
        subtask = Subtask(
            sub_id="SUB-001",
            title="Implement feature",
            type="development",
            plan_id="PLAN-001"
        )
        relationship = subtask.get_relationship_to_plan()
        
        assert isinstance(relationship, GraphRelationship)
        assert relationship.src_id == "PLAN-001"
        assert relationship.rel_type == "HAS_SUBTASK"
        assert relationship.dst_id == "SUB-001"
        assert relationship.src_labels == ["PlanVersion"]
        assert relationship.dst_labels == ["Subtask"]

    def test_update_status(self):
        """Test updating subtask status."""
        subtask = Subtask(
            sub_id="SUB-001",
            title="Implement feature",
            type="development",
            plan_id="PLAN-001"
        )
        
        updated_subtask = subtask.update_status("completed")
        
        assert updated_subtask.sub_id == subtask.sub_id
        assert updated_subtask.title == subtask.title
        assert updated_subtask.type == subtask.type
        assert updated_subtask.plan_id == subtask.plan_id
        assert updated_subtask.last_status == "completed"
        assert subtask.last_status is None  # Original unchanged


class TestGraphRelationship:
    """Unit tests for GraphRelationship domain model."""

    def test_affects_relationship(self):
        """Test creating AFFECTS relationship."""
        rel = GraphRelationship.affects_relationship("DEC-001", "SUB-001")
        
        assert rel.src_id == "DEC-001"
        assert rel.rel_type == "AFFECTS"
        assert rel.dst_id == "SUB-001"
        assert rel.src_labels == ["Decision"]
        assert rel.dst_labels == ["Subtask"]

    def test_has_plan_relationship(self):
        """Test creating HAS_PLAN relationship."""
        rel = GraphRelationship.has_plan_relationship("CASE-001", "PLAN-001")
        
        assert rel.src_id == "CASE-001"
        assert rel.rel_type == "HAS_PLAN"
        assert rel.dst_id == "PLAN-001"
        assert rel.src_labels == ["Case"]
        assert rel.dst_labels == ["PlanVersion"]

    def test_has_subtask_relationship(self):
        """Test creating HAS_SUBTASK relationship."""
        rel = GraphRelationship.has_subtask_relationship("PLAN-001", "SUB-001")
        
        assert rel.src_id == "PLAN-001"
        assert rel.rel_type == "HAS_SUBTASK"
        assert rel.dst_id == "SUB-001"
        assert rel.src_labels == ["PlanVersion"]
        assert rel.dst_labels == ["Subtask"]

    def test_to_dict(self):
        """Test converting GraphRelationship to dictionary."""
        rel = GraphRelationship(
            src_id="CASE-001",
            rel_type="HAS_PLAN",
            dst_id="PLAN-001",
            src_labels=["Case"],
            dst_labels=["PlanVersion"],
            properties={"created_at": "2024-01-01"}
        )
        result = rel.to_dict()
        
        expected = {
            "src_id": "CASE-001",
            "rel_type": "HAS_PLAN",
            "dst_id": "PLAN-001",
            "src_labels": ["Case"],
            "dst_labels": ["PlanVersion"],
            "properties": {"created_at": "2024-01-01"}
        }
        assert result == expected

    def test_get_cypher_pattern_with_labels(self):
        """Test generating Cypher pattern with labels."""
        rel = GraphRelationship(
            src_id="CASE-001",
            rel_type="HAS_PLAN",
            dst_id="PLAN-001",
            src_labels=["Case"],
            dst_labels=["PlanVersion"]
        )
        pattern = rel.get_cypher_pattern()
        
        expected = (
            "MATCH (a:Case {id:$src}), (b:PlanVersion {id:$dst}) "
            "MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props"
        )
        assert pattern == expected

    def test_get_cypher_pattern_without_labels(self):
        """Test generating Cypher pattern without labels."""
        rel = GraphRelationship(
            src_id="CASE-001",
            rel_type="HAS_PLAN",
            dst_id="PLAN-001"
        )
        pattern = rel.get_cypher_pattern()
        
        expected = (
            "MATCH (a {id:$src}), (b {id:$dst}) "
            "MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props"
        )
        assert pattern == expected

    def test_get_cypher_pattern_with_multiple_labels(self):
        """Test generating Cypher pattern with multiple labels."""
        rel = GraphRelationship(
            src_id="CASE-001",
            rel_type="HAS_PLAN",
            dst_id="PLAN-001",
            src_labels=["Case", "Project"],
            dst_labels=["PlanVersion", "Version"]
        )
        pattern = rel.get_cypher_pattern()
        
        # Labels should be sorted
        expected = (
            "MATCH (a:Case:Project {id:$src}), (b:PlanVersion:Version {id:$dst}) "
            "MERGE (a)-[r:HAS_PLAN]->(b) SET r += $props"
        )
        assert pattern == expected


class TestDomainEvent:
    """Unit tests for DomainEvent domain model."""

    def test_case_created(self):
        """Test creating case.created domain event."""
        event = DomainEvent.case_created("CASE-001", "Test Case")
        
        assert event.event_type == "case.created"
        assert event.payload == {"case_id": "CASE-001", "name": "Test Case"}

    def test_case_created_without_name(self):
        """Test creating case.created domain event without name."""
        event = DomainEvent.case_created("CASE-001")
        
        assert event.event_type == "case.created"
        assert event.payload == {"case_id": "CASE-001", "name": ""}

    def test_plan_versioned(self):
        """Test creating plan.versioned domain event."""
        event = DomainEvent.plan_versioned("CASE-001", "PLAN-001", 2)
        
        assert event.event_type == "plan.versioned"
        assert event.payload == {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": 2
        }

    def test_plan_versioned_with_default_version(self):
        """Test creating plan.versioned domain event with default version."""
        event = DomainEvent.plan_versioned("CASE-001", "PLAN-001")
        
        assert event.event_type == "plan.versioned"
        assert event.payload == {
            "case_id": "CASE-001",
            "plan_id": "PLAN-001",
            "version": 1
        }

    def test_subtask_created(self):
        """Test creating subtask.created domain event."""
        event = DomainEvent.subtask_created("PLAN-001", "SUB-001", "Fix tests", "testing")
        
        assert event.event_type == "subtask.created"
        assert event.payload == {
            "plan_id": "PLAN-001",
            "sub_id": "SUB-001",
            "title": "Fix tests",
            "type": "testing"
        }

    def test_subtask_status_changed(self):
        """Test creating subtask.status_changed domain event."""
        event = DomainEvent.subtask_status_changed("SUB-001", "completed")
        
        assert event.event_type == "subtask.status_changed"
        assert event.payload == {"sub_id": "SUB-001", "status": "completed"}

    def test_subtask_status_changed_with_none(self):
        """Test creating subtask.status_changed domain event with None status."""
        event = DomainEvent.subtask_status_changed("SUB-001", None)
        
        assert event.event_type == "subtask.status_changed"
        assert event.payload == {"sub_id": "SUB-001", "status": None}

    def test_decision_made_with_sub_id(self):
        """Test creating decision.made domain event with sub_id."""
        event = DomainEvent.decision_made("DEC-001", "design", "Use REST", "SUB-001")
        
        assert event.event_type == "decision.made"
        assert event.payload == {
            "node_id": "DEC-001",
            "kind": "design",
            "summary": "Use REST",
            "sub_id": "SUB-001"
        }

    def test_decision_made_without_sub_id(self):
        """Test creating decision.made domain event without sub_id."""
        event = DomainEvent.decision_made("DEC-001", "design", "Use REST")
        
        assert event.event_type == "decision.made"
        assert event.payload == {
            "node_id": "DEC-001",
            "kind": "design",
            "summary": "Use REST"
        }

    def test_to_dict(self):
        """Test converting DomainEvent to dictionary."""
        event = DomainEvent.case_created("CASE-001", "Test Case")
        result = event.to_dict()
        
        expected = {
            "event_type": "case.created",
            "payload": {"case_id": "CASE-001", "name": "Test Case"}
        }
        assert result == expected

    def test_get_entity_id_case(self):
        """Test extracting entity ID from case event."""
        event = DomainEvent.case_created("CASE-001", "Test Case")
        assert event.get_entity_id() == "CASE-001"

    def test_get_entity_id_plan(self):
        """Test extracting entity ID from plan event."""
        event = DomainEvent.plan_versioned("CASE-001", "PLAN-001")
        assert event.get_entity_id() == "PLAN-001"

    def test_get_entity_id_subtask(self):
        """Test extracting entity ID from subtask event."""
        event = DomainEvent.subtask_created("PLAN-001", "SUB-001")
        assert event.get_entity_id() == "SUB-001"

    def test_get_entity_id_decision(self):
        """Test extracting entity ID from decision event."""
        event = DomainEvent.decision_made("DEC-001")
        assert event.get_entity_id() == "DEC-001"

    def test_get_entity_id_unknown(self):
        """Test extracting entity ID from unknown event."""
        event = DomainEvent("unknown.event", {"some_field": "value"})
        assert event.get_entity_id() is None
