"""E2E tests for ProjectPlanVersionUseCase.

Tests verify that plan version projection works correctly with real Neo4j.
Runs inside container with docker-compose.e2e.yml infrastructure.
"""

import json
import time

import pytest

from services.context.gen import context_pb2

pytestmark = pytest.mark.e2e


class TestProjectPlanVersionE2E:
    """E2E tests for plan version projection to Neo4j."""
    
    def test_create_plan_node(self, context_stub, neo4j_client):
        """Test that creating a plan persists to Neo4j."""
        # Arrange
        plan_id = "E2E-PLAN-001"
        story_id = "E2E-STORY-PLAN-001"
        
        request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="PLAN-CREATE",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="PLAN",
                    entity_id=plan_id,
                    payload=json.dumps({
                        "plan_id": plan_id,
                        "version": 1,
                        "case_id": story_id
                    }),
                    reason="Initial plan"
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
                "MATCH (p:PlanVersion {plan_id: $plan_id}) RETURN p",
                plan_id=plan_id
            )
            records = list(result)
            
            assert len(records) == 1, f"Expected 1 plan, found {len(records)}"
            plan = records[0]["p"]
            assert plan["plan_id"] == plan_id
            assert plan["version"] == 1
            assert plan["case_id"] == story_id
    
    def test_track_plan_versions(self, context_stub, neo4j_client):
        """Test that multiple plan versions are tracked."""
        # Arrange
        plan_base_id = "E2E-PLAN-VERSIONS"
        story_id = "E2E-STORY-VERSIONS-001"
        
        # Create version 1
        v1_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="PLAN-V1",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="PLAN",
                    entity_id=f"{plan_base_id}-v1",
                    payload=json.dumps({
                        "version": 1,
                        "status": "APPROVED",
                        "total_subtasks": 3
                    }),
                    reason="First version"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        context_stub.UpdateContext(v1_request)
        time.sleep(0.5)
        
        # Create version 2
        v2_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="PLAN-V2",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="PLAN",
                    entity_id=f"{plan_base_id}-v2",
                    payload=json.dumps({
                        "version": 2,
                        "status": "DRAFT",
                        "total_subtasks": 5
                    }),
                    reason="Revised version"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        # Act
        response = context_stub.UpdateContext(v2_request)
        assert response is not None
        assert len(response.warnings) == 0
        
        time.sleep(1.0)
        
        # Assert - Both versions exist
        with neo4j_client.session() as session:
            result = session.run(
                """
                MATCH (p:PlanVersion)
                WHERE p.plan_id STARTS WITH $prefix
                RETURN p
                ORDER BY p.version
                """,
                prefix=plan_base_id
            )
            records = list(result)
            
            assert len(records) == 2, f"Expected 2 versions, found {len(records)}"
            assert records[0]["p"]["version"] == 1
            assert records[1]["p"]["version"] == 2

