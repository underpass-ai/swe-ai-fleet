"""Integration tests for Context Service persistence layer.

Tests verify that context changes are correctly persisted to Neo4j.
These tests require Neo4j and Redis to be running.
"""

import time

import pytest
from core.context.adapters.neo4j_command_store import Neo4jCommandStore

pytestmark = pytest.mark.integration


class TestDecisionPersistence:
    """Integration tests for decision persistence."""
    
    @pytest.fixture
    def command_store(self, neo4j_connection):
        """Create Neo4j command store for testing."""
        from unittest.mock import Mock
        config = Mock()
        store = Neo4jCommandStore(cfg=config, driver=neo4j_connection)
        return store
    
    def test_create_decision(self, command_store, clean_test_case):
        """Test creating a new decision in Neo4j."""
        case_id = clean_test_case
        decision_id = f"{case_id}-DEC-001"
        
        properties = {
            "id": decision_id,
            "case_id": case_id,
            "title": "Use PostgreSQL for database",
            "rationale": "Better performance and ACID compliance",
            "status": "PROPOSED",
            "decided_by": "architect"
        }
        
        # Create decision
        command_store.upsert_entity(
            label="Decision",
            id=decision_id,
            properties=properties
        )
        
        # Verify decision was created
        with command_store._session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.id as id, d.title as title, d.status as status
            """, decision_id=decision_id)
            
            record = result.single()
            assert record is not None
            assert record["id"] == decision_id
            assert record["title"] == "Use PostgreSQL for database"
            assert record["status"] == "PROPOSED"
    
    def test_update_decision(self, command_store, clean_test_case):
        """Test updating an existing decision."""
        case_id = clean_test_case
        decision_id = f"{case_id}-DEC-002"
        
        # Create initial decision
        properties = {
            "id": decision_id,
            "case_id": case_id,
            "title": "Initial Title",
            "status": "PROPOSED"
        }
        command_store.upsert_entity("Decision", decision_id, properties)
        
        # Update decision
        updated_properties = {
            "id": decision_id,
            "case_id": case_id,
            "title": "Updated Title",
            "status": "APPROVED",
            "rationale": "Added rationale"
        }
        command_store.upsert_entity("Decision", decision_id, updated_properties)
        
        # Verify update
        with command_store._session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.title as title, d.status as status, d.rationale as rationale
            """, decision_id=decision_id)
            
            record = result.single()
            assert record["title"] == "Updated Title"
            assert record["status"] == "APPROVED"
            assert record["rationale"] == "Added rationale"
    
    def test_delete_decision(self, command_store, clean_test_case):
        """Test soft delete of a decision."""
        case_id = clean_test_case
        decision_id = f"{case_id}-DEC-003"
        
        # Create decision
        properties = {
            "id": decision_id,
            "case_id": case_id,
            "title": "To Be Deleted",
            "status": "PROPOSED"
        }
        command_store.upsert_entity("Decision", decision_id, properties)
        
        # Soft delete (mark as DELETED)
        deleted_properties = {
            "id": decision_id,
            "case_id": case_id,
            "title": "To Be Deleted",
            "status": "DELETED"
        }
        command_store.upsert_entity("Decision", decision_id, deleted_properties)
        
        # Verify decision still exists but is marked DELETED
        with command_store._session() as session:
            result = session.run("""
                MATCH (d:Decision {id: $decision_id})
                RETURN d.id as id, d.status as status
            """, decision_id=decision_id)
            
            record = result.single()
            assert record is not None
            assert record["status"] == "DELETED"


class TestSubtaskPersistence:
    """Integration tests for subtask persistence."""
    
    @pytest.fixture
    def command_store(self, neo4j_connection):
        """Create Neo4j command store for testing."""
        from unittest.mock import Mock
        config = Mock()
        store = Neo4jCommandStore(cfg=config, driver=neo4j_connection)
        return store
    
    def test_update_subtask(self, command_store, clean_test_case, neo4j_connection):
        """Test updating a subtask."""
        case_id = clean_test_case
        subtask_id = f"{case_id}-TASK-001"
        
        # Create subtask first
        with neo4j_connection.session() as session:
            session.run("""
                MATCH (p:PlanVersion {case_id: $case_id})
                CREATE (s:Subtask {
                    id: $subtask_id,
                    title: 'Initial Task',
                    role: 'DEV',
                    status: 'PENDING'
                })
                CREATE (p)-[:HAS_SUBTASK]->(s)
            """, case_id=case_id, subtask_id=subtask_id)
        
        # Update subtask
        properties = {
            "id": subtask_id,
            "title": "Updated Task",
            "status": "IN_PROGRESS",
            "assignee": "dev-agent-1"
        }
        command_store.upsert_entity("Subtask", subtask_id, properties)
        
        # Verify update
        with command_store._session() as session:
            result = session.run("""
                MATCH (s:Subtask {id: $subtask_id})
                RETURN s.title as title, s.status as status, s.assignee as assignee
            """, subtask_id=subtask_id)
            
            record = result.single()
            assert record["title"] == "Updated Task"
            assert record["status"] == "IN_PROGRESS"
            assert record["assignee"] == "dev-agent-1"


class TestMilestonePersistence:
    """Integration tests for milestone/event persistence."""
    
    @pytest.fixture
    def command_store(self, neo4j_connection):
        """Create Neo4j command store for testing."""
        from unittest.mock import Mock
        config = Mock()
        store = Neo4jCommandStore(cfg=config, driver=neo4j_connection)
        return store
    
    def test_create_milestone(self, command_store, clean_test_case):
        """Test creating a milestone event."""
        case_id = clean_test_case
        event_id = f"{case_id}-EVENT-001"
        
        properties = {
            "id": event_id,
            "case_id": case_id,
            "event_type": "milestone",
            "description": "Plan approved",
            "timestamp_ms": int(time.time() * 1000)
        }
        
        # Create event
        command_store.upsert_entity("Event", event_id, properties)
        
        # Verify event was created
        with command_store._session() as session:
            result = session.run("""
                MATCH (e:Event {id: $event_id})
                RETURN e.id as id, e.event_type as event_type, 
                       e.description as description
            """, event_id=event_id)
            
            record = result.single()
            assert record is not None
            assert record["id"] == event_id
            assert record["event_type"] == "milestone"
            assert record["description"] == "Plan approved"


class TestScopeDetection:
    """Integration tests for scope detection."""
    
    def test_detect_case_header_scope(self):
        """Test detection of CASE_HEADER scope."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Case: Test Case (TEST-001)
        Status: IN_PROGRESS
        Description: Test case description
        """
        
        # Import the actual server class to test the method
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        # Create a mock servicer with minimal initialization
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "CASE_HEADER" in scopes
    
    def test_detect_plan_header_scope(self):
        """Test detection of PLAN_HEADER scope."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Plan: PLAN-001 (Version 1)
        Total Subtasks: 5
        Completed Subtasks: 2
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "PLAN_HEADER" in scopes
    
    def test_detect_subtasks_scope(self):
        """Test detection of SUBTASKS_ROLE scope."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Your Subtasks:
        - TASK-001: Implement feature X
        - TASK-002: Write tests for feature X
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "SUBTASKS_ROLE" in scopes
    
    def test_detect_decisions_scope(self):
        """Test detection of DECISIONS_RELEVANT_ROLE scope."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Recent Decisions:
        - DEC-001: Use PostgreSQL for database
        - DEC-002: Use React for frontend
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "DECISIONS_RELEVANT_ROLE" in scopes
    
    def test_detect_milestones_scope(self):
        """Test detection of MILESTONES scope."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Recent Milestones:
        - Plan approved (2025-01-15)
        - First subtask completed (2025-01-16)
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "MILESTONES" in scopes
    
    def test_detect_no_scopes_when_empty(self):
        """Test that no scopes are detected when content markers are absent."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## No subtasks assigned.
        ## No relevant decisions.
        ## No recent milestones.
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        # Should not detect SUBTASKS_ROLE, DECISIONS, or MILESTONES
        # because they have "No" indicators
        assert "SUBTASKS_ROLE" not in scopes
        assert "DECISIONS_RELEVANT_ROLE" not in scopes
        assert "MILESTONES" not in scopes
    
    def test_detect_multiple_scopes(self):
        """Test detection of multiple scopes in same content."""
        from unittest.mock import Mock
        
        prompt_blocks = Mock()
        prompt_blocks.context = """
        ## Case: Test Case (TEST-001)
        Status: IN_PROGRESS
        
        ## Plan: PLAN-001 (Version 1)
        Total Subtasks: 5
        
        ## Your Subtasks:
        - TASK-001: Implement feature
        
        ## Recent Decisions:
        - DEC-001: Architecture decision
        """
        
        import os
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../.."))
        from services.context.server import ContextServiceServicer
        
        servicer = Mock(spec=ContextServiceServicer)
        servicer._detect_scopes = ContextServiceServicer._detect_scopes.__get__(servicer)
        
        scopes = servicer._detect_scopes(prompt_blocks)
        
        assert "CASE_HEADER" in scopes
        assert "PLAN_HEADER" in scopes
        assert "SUBTASKS_ROLE" in scopes
        assert "DECISIONS_RELEVANT_ROLE" in scopes

