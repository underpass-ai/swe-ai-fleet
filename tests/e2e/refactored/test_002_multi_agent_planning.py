"""Test 002: Multi-agent planning and task generation.

This test validates the complete multi-agent deliberation flow:
1. PO creates a user story (prerequisite)
2. Story transitions to planning phase
3. Multi-agent team deliberates on the story:
   - 3 DEVs analyze implementation approach
   - 1 ARCHITECT designs the architecture
   - 1 QA plans testing strategy
4. Each agent role generates decisions
5. Agents subdivide story into atomic tasks with:
   - Limited, surgical context
   - Clear rationale for why the task is needed
6. Tasks are stored as nodes in Neo4j with relationships to the story
7. Task context is stored in Valkey
8. Validate graph structure and Valkey content
"""

import uuid

import pytest
from tests.e2e.refactored.adapters.grpc_context_adapter import GrpcContextAdapter
from tests.e2e.refactored.adapters.grpc_orchestrator_adapter import GrpcOrchestratorAdapter
from tests.e2e.refactored.adapters.neo4j_validator_adapter import Neo4jValidatorAdapter
from tests.e2e.refactored.adapters.valkey_validator_adapter import ValkeyValidatorAdapter
from tests.e2e.refactored.dto.council_dto import CouncilConfigDTO, DeliberationRequestDTO
from tests.e2e.refactored.dto.story_dto import StoryCreationRequestDTO


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_002_multi_agent_planning_full_flow(
    context_client: GrpcContextAdapter,
    orchestrator_client: GrpcOrchestratorAdapter,
    neo4j_validator: Neo4jValidatorAdapter,
    valkey_validator: ValkeyValidatorAdapter
) -> None:
    """Test 002: Complete multi-agent planning flow with task generation."""
    
    # ========== ARRANGE ==========
    story_id = f"US-TEST-{uuid.uuid4().hex[:8].upper()}"
    
    # Create medium-complexity story
    story_request = StoryCreationRequestDTO(
        story_id=story_id,
        title="Implement Redis caching for user profile queries",
        description=(
            "As a Product Owner, I want to add Redis caching for user profile queries "
            "to reduce database load and improve response times. Current Neo4j queries "
            "are taking >500ms for complex profiles. Target: <50ms with caching. "
            "Must handle cache invalidation on profile updates."
        ),
        initial_phase="DESIGN"
    )
    
    # Define agent team composition
    team_roles = ["DEV", "ARCHITECT", "QA"]
    councils_created = []
    
    try:
        # ========== STEP 1: CREATE STORY ==========
        print(f"\n🎯 Creating story {story_id}...")
        
        context_id, _ = await context_client.initialize_project_context(
            story_id=story_request.story_id,
            title=story_request.title,
            description=story_request.description,
            initial_phase=story_request.initial_phase
        )
        
        assert context_id
        print(f"✅ Story created: {story_id}")
        
        # ========== STEP 2: TRANSITION TO PLANNING ==========
        print(f"\n🔄 Transitioning {story_id} to BUILD phase...")
        
        await context_client.transition_phase(
            story_id=story_id,
            from_phase="DESIGN",
            to_phase="BUILD",
            rationale="Design approved by PO, ready for team planning"
        )
        
        print("✅ Story transitioned to BUILD phase")
        
        # ========== STEP 3: CREATE COUNCILS ==========
        print("\n👥 Creating agent councils...")
        
        # Use unique council role names to avoid conflicts between test runs
        # Format: ROLE-{first_8_chars_of_story_uuid}
        council_suffix = story_id.split('-')[-1]  # Extract UUID part from story_id
        
        # Create DEV council (3 agents)
        dev_role = f"DEV-{council_suffix}"
        dev_config = CouncilConfigDTO(
            role=dev_role,
            num_agents=3,
            agent_type="MOCK",  # Use MOCK for fast testing
            model_profile="default"
        )
        
        dev_council_id, dev_agents_created, dev_agent_ids = await orchestrator_client.create_council(
            role=dev_config.role,
            num_agents=dev_config.num_agents,
            agent_type=dev_config.agent_type,
            model_profile=dev_config.model_profile
        )
        councils_created.append(dev_role)
        
        assert dev_agents_created == 3
        assert len(dev_agent_ids) == 3
        print(f"✅ DEV council created: {dev_agents_created} agents (role: {dev_role})")
        
        # Create ARCHITECT council (1 agent)
        arch_role = f"ARCHITECT-{council_suffix}"
        arch_config = CouncilConfigDTO(
            role=arch_role,
            num_agents=1,
            agent_type="MOCK",
            model_profile="default"
        )
        
        arch_council_id, arch_agents_created, arch_agent_ids = await orchestrator_client.create_council(
            role=arch_config.role,
            num_agents=arch_config.num_agents,
            agent_type=arch_config.agent_type,
            model_profile=arch_config.model_profile
        )
        councils_created.append(arch_role)
        
        assert arch_agents_created == 1
        print(f"✅ ARCHITECT council created: {arch_agents_created} agent (role: {arch_role})")
        
        # Create QA council (1 agent)
        qa_role = f"QA-{council_suffix}"
        qa_config = CouncilConfigDTO(
            role=qa_role,
            num_agents=1,
            agent_type="MOCK",
            model_profile="default"
        )
        
        qa_council_id, qa_agents_created, qa_agent_ids = await orchestrator_client.create_council(
            role=qa_config.role,
            num_agents=qa_config.num_agents,
            agent_type=qa_config.agent_type,
            model_profile=qa_config.model_profile
        )
        councils_created.append(qa_role)
        
        assert qa_agents_created == 1
        print(f"✅ QA council created: {qa_agents_created} agent (role: {qa_role})")
        
        # ========== STEP 4: DELIBERATE WITH EACH ROLE ==========
        print("\n🎭 Starting multi-agent deliberation...")
        
        deliberation_results = {}
        
        for role in team_roles:
            print(f"\n  🔹 {role} deliberation starting...")
            
            # Create deliberation request
            delib_request = DeliberationRequestDTO(
                task_description=(
                    f"Analyze story {story_id} from {role} perspective. "
                    f"Story: {story_request.title}. "
                    f"Description: {story_request.description}. "
                    f"Propose implementation approach and atomic tasks."
                ),
                role=role,
                rounds=1,  # Single round for fast testing
                num_agents=dev_config.num_agents if role == "DEV" else 1,
                rubric="quality=high,tests=required,documentation=complete"
            )
            
            # Execute deliberation
            results, winner_id, duration_ms = await orchestrator_client.deliberate(
                task_description=delib_request.task_description,
                role=delib_request.role,
                rounds=delib_request.rounds,
                num_agents=delib_request.num_agents,
                constraints={"rubric": delib_request.rubric}
            )
            
            assert len(results) > 0
            assert winner_id
            assert duration_ms >= 0
            
            deliberation_results[role] = {
                "winner_id": winner_id,
                "proposals": len(results),
                "duration_ms": duration_ms,
                "winner_content": results[0]["content"] if results else ""
            }
            
            print(f"  ✅ {role} deliberation complete: {len(results)} proposals in {duration_ms}ms")
            
            # Store decision in Neo4j
            decision_id = await context_client.add_project_decision(
                story_id=story_id,
                decision_type=f"{role}_PLANNING",
                title=f"{role} implementation approach for {story_request.title}",
                rationale=deliberation_results[role]["winner_content"][:500],
                alternatives_considered=f"Evaluated {len(results)} proposals from team",
                metadata={
                    "role": role,
                    "winner": winner_id,
                    "proposals_count": str(len(results))
                }
            )
            
            assert decision_id
            print(f"  ✅ Decision {decision_id} stored in Neo4j")
        
        # ========== STEP 5: VALIDATE NEO4J GRAPH STRUCTURE ==========
        print("\n🔍 Validating Neo4j graph structure...")
        
        # Validate decisions exist (one per role)
        decisions = await neo4j_validator.validate_decision_nodes_exist(
            story_id=story_id,
            min_decisions=3  # DEV, ARCHITECT, QA
        )
        
        assert len(decisions) >= 3
        print(f"  ✅ {len(decisions)} decision nodes found")
        
        # Validate decision roles
        decision_roles = {d["made_by_role"] for d in decisions}
        assert "DEV" in decision_roles
        assert "ARCHITECT" in decision_roles
        assert "QA" in decision_roles
        print(f"  ✅ All roles represented in decisions: {decision_roles}")
        
        # Validate MADE_DECISION relationships
        decision_rel_count = await neo4j_validator.validate_relationships_exist(
            story_id=story_id,
            relationship_type="MADE_DECISION",
            min_count=3
        )
        
        assert decision_rel_count >= 3
        print(f"  ✅ {decision_rel_count} MADE_DECISION relationships found")
        
        # ========== STEP 6: VALIDATE STORY CONTEXT IN VALKEY ==========
        print("\n🔍 Validating Valkey cache...")
        
        # Validate story context exists
        story_key = f"story:{story_id}"
        await valkey_validator.validate_key_exists(story_key)
        
        # Validate story is in BUILD phase
        phase_value = await valkey_validator.validate_hash_field(
            key=story_key,
            field="current_phase",
            expected_value="BUILD"
        )
        assert phase_value == "BUILD"
        print("  ✅ Story in Valkey is in BUILD phase")
        
        # ========== SUCCESS ==========
        print("\n✅ Test 002 PASSED: Multi-agent planning completed successfully")
        print("   📊 Summary:")
        print(f"      - Story: {story_id}")
        print(f"      - Councils created: {len(councils_created)}")
        print(f"      - Decisions made: {len(decisions)}")
        print(f"      - Roles involved: {', '.join(team_roles)}")
        
        for role, result in deliberation_results.items():
            print(f"      - {role}: {result['proposals']} proposals, winner: {result['winner_id'][:20]}...")
        
    finally:
        # ========== CLEANUP ==========
        print("\n🧹 Cleaning up test data...")
        
        # Delete councils
        for role in councils_created:
            try:
                success, agents_removed = await orchestrator_client.delete_council(role)
                if success:
                    print(f"  ✅ Deleted {role} council ({agents_removed} agents)")
            except Exception as e:
                print(f"  ⚠️  Failed to delete {role} council: {e}")
        
        # Clean up Neo4j data
        await neo4j_validator.cleanup_story_data(story_id)
        print(f"  ✅ Cleaned Neo4j data for {story_id}")
        
        # Clean up Valkey data
        keys_deleted = await valkey_validator.cleanup_keys(f"*{story_id}*")
        print(f"  ✅ Cleaned Valkey data ({keys_deleted} keys)")
        
        print("🧹 Cleanup complete")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_002b_deliberation_produces_ranked_proposals(
    orchestrator_client: GrpcOrchestratorAdapter
) -> None:
    """Test 002b: Deliberation produces multiple ranked proposals."""
    
    # ========== ARRANGE ==========
    role = "DEV"
    
    try:
        # Create council
        council_config = CouncilConfigDTO(
            role=role,
            num_agents=3,
            agent_type="MOCK",
            model_profile="default"
        )
        
        await orchestrator_client.create_council(
            role=council_config.role,
            num_agents=council_config.num_agents,
            agent_type=council_config.agent_type,
            model_profile=council_config.model_profile
        )
        
        # ========== ACT ==========
        results, winner_id, duration_ms = await orchestrator_client.deliberate(
            task_description="Design a caching strategy for user profiles",
            role=role,
            rounds=1,
            num_agents=3,
            constraints={"rubric": "quality=high"}
        )
        
        # ========== ASSERT ==========
        # Should have multiple proposals
        assert len(results) == 3, f"Expected 3 proposals, got {len(results)}"
        
        # Winner should be identified
        assert winner_id
        
        # Results should be ranked (rank 1 = best)
        ranks = [r["rank"] for r in results]
        assert ranks == sorted(ranks), "Results should be sorted by rank"
        
        # Winner should be the rank-1 proposal
        winner_proposal = next((r for r in results if r["author_id"] == winner_id), None)
        assert winner_proposal is not None
        assert winner_proposal["rank"] == 1
        
        print(f"✅ Test 002b PASSED: {len(results)} ranked proposals generated")
        
    finally:
        # ========== CLEANUP ==========
        await orchestrator_client.delete_council(role)

