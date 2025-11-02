"""Test 001: PO creates user story and validates persistence in Valkey + Neo4j.

This test validates the complete flow:
1. PO creates a medium-complexity user story via Context Service
2. Story is persisted in Neo4j as a ProjectCase node
3. Story is persisted in Valkey for caching
4. All properties are validated in both stores
"""

import uuid
import pytest

from tests.e2e.refactored.adapters.grpc_context_adapter import GrpcContextAdapter
from tests.e2e.refactored.adapters.neo4j_validator_adapter import Neo4jValidatorAdapter
from tests.e2e.refactored.adapters.valkey_validator_adapter import ValkeyValidatorAdapter
from tests.e2e.refactored.dto.story_dto import StoryCreationRequestDTO, StoryCreationResponseDTO


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_001_po_creates_story_validates_persistence(
    context_client: GrpcContextAdapter,
    neo4j_validator: Neo4jValidatorAdapter,
    valkey_validator: ValkeyValidatorAdapter
) -> None:
    """Test 001: PO creates story and validates persistence in Neo4j + Valkey."""
    
    # ========== ARRANGE ==========
    # Generate unique story ID for test isolation
    story_id = f"US-TEST-{uuid.uuid4().hex[:8].upper()}"
    
    # Create story request DTO
    story_request = StoryCreationRequestDTO(
        story_id=story_id,
        title="Implement user authentication with OAuth2",
        description=(
            "As a Product Owner, I want to implement OAuth2 authentication "
            "so that users can securely log in using their Google or GitHub accounts. "
            "This is a medium-complexity story requiring backend API changes, "
            "database schema updates, and frontend integration."
        ),
        initial_phase="DESIGN"
    )
    
    try:
        # ========== ACT ==========
        # Step 1: Create story via Context Service (gRPC)
        context_id, current_phase = await context_client.initialize_project_context(
            story_id=story_request.story_id,
            title=story_request.title,
            description=story_request.description,
            initial_phase=story_request.initial_phase
        )
        
        # Validate gRPC response
        response = StoryCreationResponseDTO(
            context_id=context_id,
            story_id=story_id,
            current_phase=current_phase
        )
        
        assert response.story_id == story_id
        assert response.current_phase == "DESIGN"
        
        # ========== ASSERT - NEO4J VALIDATION ==========
        # Step 2: Validate ProjectCase node exists in Neo4j
        story_exists = await neo4j_validator.validate_story_node_exists(
            story_id=story_id,
            expected_title=story_request.title,
            expected_phase="DESIGN"
        )
        assert story_exists is True
        
        # Step 3: Validate relationships (story should have no decisions yet)
        decision_count = await neo4j_validator.validate_relationships_exist(
            story_id=story_id,
            relationship_type="MADE_DECISION",
            min_count=0  # No decisions yet
        )
        assert decision_count == 0
        
        # ========== ASSERT - VALKEY VALIDATION ==========
        # Step 4: Validate story exists in Valkey cache
        story_key = f"story:{story_id}"
        
        key_exists = await valkey_validator.validate_key_exists(story_key)
        assert key_exists is True
        
        # Step 5: Validate story fields in Valkey hash
        title_value = await valkey_validator.validate_hash_field(
            key=story_key,
            field="title",
            expected_value=story_request.title
        )
        assert title_value == story_request.title
        
        phase_value = await valkey_validator.validate_hash_field(
            key=story_key,
            field="current_phase",
            expected_value="DESIGN"
        )
        assert phase_value == "DESIGN"
        
        description_value = await valkey_validator.validate_hash_field(
            key=story_key,
            field="description"
        )
        assert story_request.description in description_value
        
        # ========== SUCCESS ==========
        print(f"✅ Test 001 PASSED: Story {story_id} persisted correctly in Neo4j + Valkey")
        
    finally:
        # ========== CLEANUP ==========
        # Clean up test data for isolation
        await neo4j_validator.cleanup_story_data(story_id)
        await valkey_validator.cleanup_keys(f"story:{story_id}*")
        print(f"🧹 Cleaned up test data for {story_id}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_001b_story_creation_validates_phase_transition(
    context_client: GrpcContextAdapter,
    neo4j_validator: Neo4jValidatorAdapter,
    valkey_validator: ValkeyValidatorAdapter
) -> None:
    """Test 001b: Validate phase transition is persisted correctly."""
    
    # ========== ARRANGE ==========
    story_id = f"US-TEST-{uuid.uuid4().hex[:8].upper()}"
    
    story_request = StoryCreationRequestDTO(
        story_id=story_id,
        title="Add GraphQL API for product catalog",
        description="Implement GraphQL API to replace REST endpoints for product catalog queries.",
        initial_phase="DESIGN"
    )
    
    try:
        # ========== ACT ==========
        # Step 1: Create story
        await context_client.initialize_project_context(
            story_id=story_request.story_id,
            title=story_request.title,
            description=story_request.description,
            initial_phase=story_request.initial_phase
        )
        
        # Step 2: Transition phase from DESIGN to BUILD
        story_id_returned, transitioned_at = await context_client.transition_phase(
            story_id=story_id,
            from_phase="DESIGN",
            to_phase="BUILD",
            rationale="Architecture approved, ready for implementation"
        )
        
        assert story_id_returned == story_id
        assert transitioned_at  # Timestamp should be populated
        
        # ========== ASSERT - NEO4J VALIDATION ==========
        # Step 3: Validate story is now in BUILD phase
        story_exists = await neo4j_validator.validate_story_node_exists(
            story_id=story_id,
            expected_title=story_request.title,
            expected_phase="BUILD"
        )
        assert story_exists is True
        
        # Step 4: Validate phase transition relationship exists
        transition_count = await neo4j_validator.validate_relationships_exist(
            story_id=story_id,
            relationship_type="HAS_PHASE",
            min_count=1
        )
        assert transition_count >= 1
        
        # ========== SUCCESS ==========
        print(f"✅ Test 001b PASSED: Phase transition persisted correctly for {story_id}")
        
    finally:
        # ========== CLEANUP ==========
        await neo4j_validator.cleanup_story_data(story_id)
        await valkey_validator.cleanup_keys(f"story:{story_id}*")
        print(f"🧹 Cleaned up test data for {story_id}")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_001c_story_creation_fails_with_invalid_phase(
    context_client: GrpcContextAdapter
) -> None:
    """Test 001c: Story creation fails with invalid initial phase."""
    
    # ========== ARRANGE ==========
    story_id = f"US-TEST-{uuid.uuid4().hex[:8].upper()}"
    
    # ========== ACT & ASSERT ==========
    # Invalid phase should raise ValueError from DTO validation
    with pytest.raises(ValueError, match="invalid initial_phase"):
        StoryCreationRequestDTO(
            story_id=story_id,
            title="Test story",
            description="Test description",
            initial_phase="INVALID_PHASE"
        )
    
    print("✅ Test 001c PASSED: Invalid phase rejected at DTO validation")

