"""E2E tests for ProjectSubtaskUseCase.

Tests verify that subtask projection works correctly with real Neo4j.
Runs inside container with docker-compose.e2e.yml infrastructure.
"""

import json
import time

import pytest

from services.context.gen import context_pb2

pytestmark = pytest.mark.e2e


class TestProjectSubtaskE2E:
    """E2E tests for subtask projection to Neo4j."""
    
    def test_create_subtask_node(self, context_stub, neo4j_client):
        """Test that creating a subtask persists to Neo4j."""
        # Arrange
        subtask_id = "E2E-SUBTASK-001"
        story_id = "E2E-STORY-SUBTASK-001"
        
        request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="SUBTASK-CREATE",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=subtask_id,
                    payload=json.dumps({
                        "sub_id": subtask_id,
                        "title": "Implement login endpoint",
                        "type": "development",
                        "plan_id": "E2E-PLAN-001"
                    }),
                    reason="New subtask"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        # Act
        response = context_stub.UpdateContext(request)
        
        # Assert
        assert response is not None
        assert len(response.warnings) == 0
        
        time.sleep(1.0)
        
        # Verify in Neo4j
        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (s:Subtask {sub_id: $sub_id}) RETURN s",
                sub_id=subtask_id
            )
            records = list(result)
            
            assert len(records) == 1, f"Expected 1 subtask, found {len(records)}"
            subtask = records[0]["s"]
            assert subtask["sub_id"] == subtask_id
            assert subtask["title"] == "Implement login endpoint"
            assert subtask["type"] == "development"
            assert subtask["plan_id"] == "E2E-PLAN-001"
    
    def test_update_subtask_status(self, context_stub, neo4j_client):
        """Test updating subtask status."""
        # Arrange - Create
        subtask_id = "E2E-SUBTASK-UPDATE-001"
        story_id = "E2E-STORY-UPDATE-001"
        
        create_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="CREATE",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=subtask_id,
                    payload=json.dumps({
                        "sub_id": subtask_id,
                        "title": "Test subtask",
                        "type": "task",
                        "plan_id": story_id,
                        "last_status": "QUEUED"
                    }),
                    reason="Create"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        context_stub.UpdateContext(create_request)
        time.sleep(1.0)
        
        # Act - Update status
        update_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="START",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id=subtask_id,
                    payload=json.dumps({
                        "last_status": "IN_PROGRESS"
                    }),
                    reason="Started"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(update_request)
        assert response is not None
        assert len(response.warnings) == 0
        
        time.sleep(1.0)
        
        # Assert
        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (s:Subtask {sub_id: $sub_id}) RETURN s",
                sub_id=subtask_id
            )
            records = list(result)
            
            assert len(records) == 1
            subtask = records[0]["s"]
            assert subtask["last_status"] == "IN_PROGRESS"

