"""E2E tests for ProjectorCoordinator.

Tests verify that the coordinator properly routes multiple entity types.
Runs inside container with docker-compose.e2e.yml infrastructure.
"""

import json
import time

import pytest

from services.context.gen import context_pb2

pytestmark = pytest.mark.e2e


class TestProjectorCoordinatorE2E:
    """E2E tests for coordinator orchestrating multiple projections."""
    
    @pytest.mark.skip(reason="Multiple use cases not yet integrated in UpdateContext server")
    def test_handle_multiple_entity_types_in_one_request(
        self, context_stub, neo4j_client
    ):
        """Test that coordinator routes different entity types correctly."""
        # Arrange
        story_id = "E2E-COORDINATOR-001"
        
        request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="MULTI-CREATE",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="CASE",
                    entity_id=f"{story_id}-CASE",
                    payload=json.dumps({"title": "Coordinator test case"}),
                    reason="Case"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="PLAN",
                    entity_id=f"{story_id}-PLAN",
                    payload=json.dumps({"version": 1, "status": "DRAFT"}),
                    reason="Plan"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-SUBTASK",
                    payload=json.dumps({"description": "Test subtask"}),
                    reason="Subtask"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DECISION",
                    payload=json.dumps({"title": "Test decision"}),
                    reason="Decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        # Act
        response = context_stub.UpdateContext(request)
        
        # Assert
        assert response is not None
        assert len(response.warnings) == 0
        
        time.sleep(1.5)  # Allow all projections
        
        # Verify all entities
        with neo4j_client.session() as session:
            # Check Case
            case_result = session.run(
                "MATCH (c:Case) WHERE c.case_id CONTAINS $id RETURN count(c) as cnt",
                id=story_id
            )
            assert list(case_result)[0]["cnt"] >= 1
            
            # Check Plan
            plan_result = session.run(
                "MATCH (p:Plan) WHERE p.plan_id CONTAINS $id RETURN count(p) as cnt",
                id=story_id
            )
            assert list(plan_result)[0]["cnt"] >= 1
            
            # Check Subtask
            subtask_result = session.run(
                "MATCH (s:Subtask) WHERE s.sub_id CONTAINS $id RETURN count(s) as cnt",
                id=story_id
            )
            assert list(subtask_result)[0]["cnt"] >= 1
            
            # Check Decision
            decision_result = session.run(
                "MATCH (d:Decision) WHERE d.node_id CONTAINS $id RETURN count(d) as cnt",
                id=story_id
            )
            assert list(decision_result)[0]["cnt"] >= 1

