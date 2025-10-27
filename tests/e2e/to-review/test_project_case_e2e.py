"""E2E tests for ProjectCaseUseCase.

Tests verify that case projection works correctly with real Neo4j.
Runs inside container with docker-compose.e2e.yml infrastructure.
"""

import json
import time

import pytest
from services.context.gen import context_pb2

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestProjectCaseE2E:
    """E2E tests for case projection to Neo4j."""
    
    def test_create_case_node(self, context_stub, neo4j_client):
        """Test that creating a case via UpdateContext persists to Neo4j."""
        # Arrange
        case_id = "E2E-CASE-CREATE-001"
        
        request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="INITIAL",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="CASE",
                    entity_id=case_id,
                    payload=json.dumps({
                        "case_id": case_id,
                        "name": "E2E Test Case"
                    }),
                    reason="Initial case creation"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        # Act
        response = context_stub.UpdateContext(request)
        
        # Assert
        assert response is not None
        assert response.version > 0  # Version incremented
        assert len(response.warnings) == 0  # No warnings
        
        # Wait for async projection
        time.sleep(1.0)
        
        # Verify in Neo4j
        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (c:Case {case_id: $case_id}) RETURN c",
                case_id=case_id
            )
            records = list(result)
            
            assert len(records) == 1, f"Expected 1 case, found {len(records)}"
            case_node = records[0]["c"]
            assert case_node["case_id"] == case_id
            assert case_node["name"] == "E2E Test Case"
    
    def test_update_case_node(self, context_stub, neo4j_client):
        """Test that updating a case modifies existing node."""
        # Arrange - Create
        case_id = "E2E-CASE-UPDATE-001"
        
        create_request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="CREATE",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="CASE",
                    entity_id=case_id,
                    payload=json.dumps({
                        "case_id": case_id,
                        "name": "Original Name"
                    }),
                    reason="Initial"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        context_stub.UpdateContext(create_request)
        time.sleep(1.0)
        
        # Act - Update
        update_request = context_pb2.UpdateContextRequest(
            story_id=case_id,
            task_id="UPDATE",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="CASE",
                    entity_id=case_id,
                    payload=json.dumps({
                        "case_id": case_id,
                        "name": "Updated Name"
                    }),
                    reason="Name update"
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
                "MATCH (c:Case {case_id: $case_id}) RETURN c",
                case_id=case_id
            )
            records = list(result)
            
            assert len(records) == 1
            case_node = records[0]["c"]
            assert case_node["case_id"] == case_id
            assert case_node["name"] == "Updated Name"

