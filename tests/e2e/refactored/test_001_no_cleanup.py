"""Test 001 - NO CLEANUP VERSION - to inspect persisted data.

This is a temporary test file to see what data is actually being saved.
"""

import pytest
from tests.e2e.refactored.adapters.grpc_context_adapter import GrpcContextAdapter
from tests.e2e.refactored.adapters.neo4j_validator_adapter import Neo4jValidatorAdapter
from tests.e2e.refactored.adapters.valkey_validator_adapter import ValkeyValidatorAdapter
from tests.e2e.refactored.dto.story_dto import StoryCreationRequestDTO


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_001_create_and_leave_data(
    context_client: GrpcContextAdapter,
    neo4j_validator: Neo4jValidatorAdapter,
    valkey_validator: ValkeyValidatorAdapter
) -> None:
    """Create a story and DON'T clean it up so we can inspect the data."""
    
    # Use a fixed story ID for easy inspection
    story_id = "INSPECT-DATA-001"
    
    story_request = StoryCreationRequestDTO(
        story_id=story_id,
        title="Test Story for Data Inspection",
        description="This story is created to inspect how data is persisted in Neo4j and Valkey.",
        initial_phase="DESIGN"
    )
    
    # Create story
    context_id, current_phase = await context_client.create_story(
        story_id=story_request.story_id,
        title=story_request.title,
        description=story_request.description,
        initial_phase=story_request.initial_phase
    )
    
    print(f"\n{'='*60}")
    print(f"Story Created: {story_id}")
    print(f"Context ID: {context_id}")
    print(f"Phase: {current_phase}")
    print(f"{'='*60}\n")
    
    # Validate it exists
    story_exists = await neo4j_validator.validate_story_node_exists(
        story_id=story_id,
        expected_title=story_request.title,
        expected_phase="DESIGN"
    )
    assert story_exists
    
    # Check Valkey
    story_key = f"story:{story_id}"
    key_exists = await valkey_validator.validate_key_exists(story_key)
    assert key_exists
    
    # Transition phase
    story_id_returned, transitioned_at = await context_client.transition_phase(
        story_id=story_id,
        from_phase="DESIGN",
        to_phase="BUILD",
        rationale="Test phase transition"
    )
    
    print(f"Phase transitioned to BUILD at: {transitioned_at}\n")
    
    print(f"{'='*60}")
    print("✅ Data created successfully!")
    print("\nTo inspect the data, run:")
    print("\n  Neo4j:")
    print("  kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword \\")
    print(f"    \"MATCH (p:ProjectCase {{story_id: '{story_id}'}}) RETURN p\"")
    print("\n  Valkey:")
    print(f"  kubectl exec -n swe-ai-fleet valkey-0 -- redis-cli HGETALL story:{story_id}")
    print("\n  View all data:")
    print("  cd tests/e2e/refactored && ./view-test-data.sh")
    print(f"{'='*60}\n")
    
    # NO CLEANUP - data stays in the database

