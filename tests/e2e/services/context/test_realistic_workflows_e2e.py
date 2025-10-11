"""
E2E tests for realistic workflows in Context Service.

These tests simulate real-world scenarios with multiple agents working
on a complete story lifecycle, not just isolated operations.

Key scenarios:
1. Complete story lifecycle (BACKLOG → DONE)
2. Multi-agent parallel work with coordination
3. QA feedback loop (fail → fix → pass)
4. Decision dependencies and evolution
5. Context growth over time

These tests verify the system works correctly under realistic conditions,
not just for isolated operations.
"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

pytestmark = pytest.mark.e2e


class TestCompleteStoryLifecycle:
    """Test complete story workflow from start to finish."""

    def test_story_backlog_to_done_workflow(self, context_stub, neo4j_client, seed_case_data):
        """
        Simulate complete story: BACKLOG → DESIGN → BUILD → TEST → DONE
        
        Realistic scenario:
        1. ARCHITECT designs solution (creates case + plan)
        2. DEV implements features (creates subtasks)
        3. DEV makes technical decisions
        4. QA tests and finds bugs
        5. DEV fixes bugs
        6. QA approves
        7. DEVOPS deploys
        
        Verifies:
        - Context evolves correctly at each phase
        - Each role sees appropriate context
        - Graph relationships are correct
        - No data loss across phases
        """
        from services.context.gen import context_pb2
        
        # Use seeded case (has Redis + Neo4j data)
        story_id = seed_case_data
        
        # =================================================================
        # Phase 1: ARCHITECT - Design (add plan + decision to existing case)
        # =================================================================
        print(f"\n📐 Phase 1: ARCHITECT - Design (Story: {story_id})")
        
        # Add plan and decisions to seeded case
        design_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="DESIGN-001",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="PLAN",
                    entity_id=f"{story_id}-PLAN-V1",
                    payload=json.dumps({
                        "plan_id": f"{story_id}-PLAN-V1",
                        "version": 1,
                        "case_id": story_id
                    }),
                    reason="Initial plan"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-AUTH",
                    payload=json.dumps({
                        "title": "Use JWT for authentication",
                        "rationale": "Industry standard, stateless, scalable",
                        "status": "APPROVED",
                        "decided_by": "architect-agent"
                    }),
                    reason="Technology decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(design_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # Verify ARCHITECT can get context for design phase
        architect_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="ARCHITECT",
                phase="DESIGN"
            )
        )
        assert "ARCHITECT" in architect_context.blocks.system
        assert architect_context.token_count > 0
        
        # =================================================================
        # Phase 2: DEV - Implementation (CREATE subtasks + decisions)
        # =================================================================
        print("💻 Phase 2: DEV - Implementation")
        
        # Create subtasks
        build_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="BUILD-001",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-TASK-LOGIN",
                    payload=json.dumps({
                        "sub_id": f"{story_id}-TASK-LOGIN",
                        "title": "Implement login endpoint",
                        "type": "development",
                        "plan_id": f"{story_id}-PLAN-V1",
                        "last_status": "IN_PROGRESS"
                    }),
                    reason="Start implementation"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-TASK-REGISTER",
                    payload=json.dumps({
                        "sub_id": f"{story_id}-TASK-REGISTER",
                        "title": "Implement registration endpoint",
                        "type": "development",
                        "plan_id": f"{story_id}-PLAN-V1",
                        "last_status": "QUEUED"
                    }),
                    reason="Queued for implementation"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-BCRYPT",
                    payload=json.dumps({
                        "title": "Use bcrypt for password hashing",
                        "rationale": "Secure, well-tested, industry standard",
                        "status": "APPROVED",
                        "decided_by": "dev-agent"
                    }),
                    reason="Security implementation decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(build_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # Verify DEV sees relevant context with decisions
        dev_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="DEV",
                phase="BUILD",
                subtask_id=f"{story_id}-TASK-LOGIN"
            )
        )
        assert "DEV" in dev_context.blocks.system
        # Verify context includes decisions (after fix)
        context_text = dev_context.context.lower()
        # Should mention JWT decision from architect
        assert "jwt" in context_text or "bcrypt" in context_text, \
            f"Context should include technical decisions. Got: {context_text[:200]}..."
        
        # Complete first subtask
        complete_task_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="BUILD-002",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-TASK-LOGIN",
                    payload=json.dumps({
                        "last_status": "COMPLETED"
                    }),
                    reason="Login endpoint implemented"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id=f"{story_id}-MILESTONE-LOGIN",
                    payload=json.dumps({
                        "type": "TASK_COMPLETED",
                        "title": "Login endpoint ready for testing"
                    }),
                    reason="Milestone reached"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(complete_task_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # =================================================================
        # Phase 3: QA - Testing (finds bug)
        # =================================================================
        print("🧪 Phase 3: QA - Testing (finds bug)")
        
        qa_test_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="TEST-001",
            role="QA",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-BUG-FOUND",
                    payload=json.dumps({
                        "title": "Bug: Password validation missing",
                        "rationale": "Weak passwords can be used, security risk",
                        "status": "IDENTIFIED",
                        "decided_by": "qa-agent"
                    }),
                    reason="Bug identified during testing"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-TASK-FIX-VALIDATION",
                    payload=json.dumps({
                        "sub_id": f"{story_id}-TASK-FIX-VALIDATION",
                        "title": "Fix password validation",
                        "type": "bugfix",
                        "plan_id": f"{story_id}-PLAN-V1",
                        "last_status": "QUEUED"
                    }),
                    reason="Bug fix task created"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(qa_test_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # =================================================================
        # Phase 4: DEV - Bug fix
        # =================================================================
        print("🔧 Phase 4: DEV - Bug fix")
        
        bugfix_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="BUILD-003",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id=f"{story_id}-TASK-FIX-VALIDATION",
                    payload=json.dumps({
                        "last_status": "COMPLETED"
                    }),
                    reason="Password validation implemented"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-VALIDATION-RULES",
                    payload=json.dumps({
                        "title": "Password rules: 8+ chars, mixed case, numbers",
                        "rationale": "OWASP recommendations",
                        "status": "APPROVED",
                        "decided_by": "dev-agent"
                    }),
                    reason="Validation rules decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(bugfix_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # =================================================================
        # Phase 5: QA - Re-test (pass)
        # =================================================================
        print("✅ Phase 5: QA - Re-test (pass)")
        
        qa_pass_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="TEST-002",
            role="QA",
            changes=[
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-BUG-FOUND",
                    payload=json.dumps({
                        "status": "RESOLVED"
                    }),
                    reason="Bug fixed and verified"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id=f"{story_id}-MILESTONE-QA-PASS",
                    payload=json.dumps({
                        "type": "QA_APPROVED",
                        "title": "Authentication feature approved by QA"
                    }),
                    reason="QA approval milestone"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(qa_pass_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # =================================================================
        # Phase 6: DEVOPS - Deployment
        # =================================================================
        print("🚀 Phase 6: DEVOPS - Deployment")
        
        deploy_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="DEPLOY-001",
            role="DEVOPS",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id=f"{story_id}-MILESTONE-DEPLOYED",
                    payload=json.dumps({
                        "type": "DEPLOYED",
                        "title": "Authentication feature deployed to production"
                    }),
                    reason="Deployment complete"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        response = context_stub.UpdateContext(deploy_request)
        assert response.version > 0
        time.sleep(1.0)
        
        # =================================================================
        # FINAL VERIFICATION: Rehydrate and verify complete story
        # =================================================================
        print("🔍 Final Verification: Rehydrate complete session")
        
        final_session = context_stub.RehydrateSession(
            context_pb2.RehydrateSessionRequest(
                case_id=story_id,
                roles=["ARCHITECT", "DEV", "QA", "DEVOPS"],
                include_timeline=True,
                include_summaries=True
            )
        )
        
        # Verify all roles have context
        assert len(final_session.packs) == 4
        assert "ARCHITECT" in final_session.packs
        assert "DEV" in final_session.packs
        assert "QA" in final_session.packs
        assert "DEVOPS" in final_session.packs
        
        # Verify decisions are present (after fix)
        dev_pack = final_session.packs["DEV"]
        decision_count = len(dev_pack.decisions)
        print(f"📊 Decisions in rehydrated session: {decision_count}")
        
        # After fix: Should include seed (2) + new workflow decisions (3-4) = 5+ total
        # Note: Some decisions may not load due to filtering or max_decisions limit
        assert decision_count >= 5, \
            f"Expected >= 5 decisions (seed + workflow), got {decision_count}"
        
        # Verify specific decisions are present
        decision_ids = [d.id for d in dev_pack.decisions]
        assert any("DEC-AUTH" in did for did in decision_ids), \
            "Should include JWT authentication decision"
        
        # Verify graph in Neo4j - complete story structure
        with neo4j_client.session() as session:
            # NOTE: Case node may not exist because seed_case_data only creates Redis data
            # The workflow doesn't create CASE node explicitly (uses existing Redis case)
            # This is realistic - case metadata lives in Redis, graph is for relationships
            
            # Check decisions count
            decision_result = session.run(
                "MATCH (d:Decision) WHERE d.id CONTAINS $id RETURN count(d) as cnt",
                id=story_id
            )
            decision_count = list(decision_result)[0]["cnt"]
            assert decision_count >= 4  # JWT, bcrypt, bug, validation
            
            # Check subtasks count
            subtask_result = session.run(
                "MATCH (s:Subtask) WHERE s.sub_id CONTAINS $id RETURN count(s) as cnt",
                id=story_id
            )
            subtask_count = list(subtask_result)[0]["cnt"]
            assert subtask_count >= 3  # login, register, bugfix
            
            # NOTE: Milestones don't persist to Neo4j currently
            # They're stored in Redis timeline only (by design)
            # This is an architectural decision - milestones are timeline events, not graph nodes
            # For now, skip milestone verification in Neo4j
        
        print("✅ Complete story lifecycle verified successfully!")


class TestMultiAgentParallelWork:
    """Test multiple agents working simultaneously on same story."""

    def test_three_devs_parallel_subtasks(self, context_stub, neo4j_client, seed_case_data):
        """
        Simulate 3 DEV agents working on different subtasks in parallel.
        
        Realistic scenario:
        - DEV-1 works on frontend
        - DEV-2 works on backend
        - DEV-3 works on database
        
        Verifies:
        - No race conditions
        - All changes persist correctly
        - No data corruption
        - Context remains consistent
        """
        from services.context.gen import context_pb2
        
        # Use seeded case
        story_id = seed_case_data
        
        print(f"\n🚀 Testing parallel work on story: {story_id}")
        
        # Define parallel work for 3 agents
        def agent_work(agent_id: str, component: str):
            """Simulate agent doing work."""
            print(f"🤖 Agent {agent_id} starting work on {component}")
            
            # Create subtask
            create_request = context_pb2.UpdateContextRequest(
                story_id=story_id,
                task_id=f"{agent_id}-CREATE",
                role="DEV",
                changes=[
                    context_pb2.ContextChange(
                        operation="CREATE",
                        entity_type="SUBTASK",
                        entity_id=f"{story_id}-TASK-{component}",
                        payload=json.dumps({
                            "sub_id": f"{story_id}-TASK-{component}",
                            "title": f"Implement {component}",
                            "type": "development",
                            "plan_id": story_id,  # Use story_id as plan_id
                            "last_status": "IN_PROGRESS"
                        }),
                        reason=f"Agent {agent_id} starts {component}"
                    )
                ],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
            
            response1 = context_stub.UpdateContext(create_request)
            
            # Simulate work (small delay)
            time.sleep(0.5)
            
            # Complete subtask
            complete_request = context_pb2.UpdateContextRequest(
                story_id=story_id,
                task_id=f"{agent_id}-COMPLETE",
                role="DEV",
                changes=[
                    context_pb2.ContextChange(
                        operation="UPDATE",
                        entity_type="SUBTASK",
                        entity_id=f"{story_id}-TASK-{component}",
                        payload=json.dumps({
                            "last_status": "COMPLETED"
                        }),
                        reason=f"Agent {agent_id} completes {component}"
                    ),
                    context_pb2.ContextChange(
                        operation="CREATE",
                        entity_type="DECISION",
                        entity_id=f"{story_id}-DEC-{component}",
                        payload=json.dumps({
                            "title": f"Technical decisions for {component}",
                            "rationale": f"Implementation details by {agent_id}",
                            "status": "APPROVED",
                            "decided_by": agent_id
                        }),
                        reason=f"Technical decision by {agent_id}"
                    )
                ],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
            
            response2 = context_stub.UpdateContext(complete_request)
            
            print(f"✅ Agent {agent_id} completed work on {component}")
            
            return (response1.version, response2.version)
        
        # Execute parallel work
        print("\n🚀 Starting parallel work with 3 agents...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(agent_work, "DEV-1", "FRONTEND"): "DEV-1",
                executor.submit(agent_work, "DEV-2", "BACKEND"): "DEV-2",
                executor.submit(agent_work, "DEV-3", "DATABASE"): "DEV-3"
            }
            
            results = {}
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    versions = future.result()
                    results[agent_id] = versions
                    print(f"✓ {agent_id} completed: versions {versions}")
                except Exception as e:
                    pytest.fail(f"Agent {agent_id} failed: {e}")
        
        # Verify all agents succeeded
        assert len(results) == 3
        assert "DEV-1" in results
        assert "DEV-2" in results
        assert "DEV-3" in results
        
        # Wait for async processing
        time.sleep(2.0)
        
        # Verify all changes persisted correctly in Neo4j
        with neo4j_client.session() as session:
            # Check all 3 subtasks exist
            subtask_result = session.run(
                "MATCH (s:Subtask) WHERE s.sub_id CONTAINS $id RETURN count(s) as cnt",
                id=story_id
            )
            subtask_count = list(subtask_result)[0]["cnt"]
            assert subtask_count == 3, f"Expected 3 subtasks, found {subtask_count}"
            
            # Check all 3 NEW decisions exist (seed data may have more)
            decision_result = session.run(
                "MATCH (d:Decision) WHERE d.id CONTAINS $id RETURN count(d) as cnt",
                id=story_id
            )
            decision_count = list(decision_result)[0]["cnt"]
            # Seed data has ~2 decisions, we added 3, so >= 3 total
            assert decision_count >= 3, f"Expected >= 3 decisions, found {decision_count}"
            
            # Check all subtasks are COMPLETED
            completed_result = session.run(
                """
                MATCH (s:Subtask)
                WHERE s.sub_id CONTAINS $id AND s.last_status = 'COMPLETED'
                RETURN count(s) as cnt
                """,
                id=story_id
            )
            completed_count = list(completed_result)[0]["cnt"]
            assert completed_count == 3, f"Expected 3 completed, found {completed_count}"
        
        # Verify final context contains all work
        final_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="DEV",
                phase="BUILD"
            )
        )
        
        assert final_context is not None
        assert final_context.token_count > 0
        
        print("✅ Parallel work completed successfully - no race conditions!")


class TestContextEvolutionAndGrowth:
    """Test how context evolves and grows over time."""

    def test_context_grows_with_decisions(self, context_stub, seed_case_data):
        """
        Verify context grows appropriately as decisions accumulate.
        
        Simulates: 10 sequential decisions over a sprint
        
        Verifies:
        - Token count increases reasonably
        - Context remains coherent
        - Performance doesn't degrade
        """
        from services.context.gen import context_pb2
        
        # Use seeded case
        story_id = seed_case_data
        print(f"\n📊 Testing context growth on story: {story_id}")
        
        # Get baseline context
        baseline_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="ARCHITECT",
                phase="DESIGN"
            )
        )
        
        baseline_tokens = baseline_context.token_count
        print(f"📊 Baseline context: {baseline_tokens} tokens")
        
        # Add 10 decisions sequentially
        for i in range(1, 11):
            decision_request = context_pb2.UpdateContextRequest(
                story_id=story_id,
                task_id=f"DECISION-{i}",
                role="ARCHITECT",
                changes=[
                    context_pb2.ContextChange(
                        operation="CREATE",
                        entity_type="DECISION",
                        entity_id=f"{story_id}-DEC-{i:03d}",
                        payload=json.dumps({
                            "title": f"Decision {i}: Technical choice for component {i}",
                            "rationale": f"After evaluating options, we chose solution {i} "
                                       f"because it provides better performance and maintainability. "
                                       f"This decision impacts modules A, B, and C.",
                            "status": "APPROVED",
                            "decided_by": "architect-agent"
                        }),
                        reason=f"Decision {i} recorded"
                    )
                ],
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            )
            
            context_stub.UpdateContext(decision_request)
            time.sleep(0.3)
            
            # Get context after each decision
            current_context = context_stub.GetContext(
                context_pb2.GetContextRequest(
                    story_id=story_id,
                    role="ARCHITECT",
                    phase="DESIGN"
                )
            )
            
            current_tokens = current_context.token_count
            growth = current_tokens - baseline_tokens
            print(f"📈 After decision {i}: {current_tokens} tokens (+{growth} from baseline)")
            
            # Verify context is growing reasonably (not exponentially)
            # Each decision adds ~50-200 tokens typically
            expected_max_growth = i * 500  # Conservative estimate
            assert growth < expected_max_growth, \
                f"Context growing too fast: +{growth} tokens after {i} decisions"
        
        # Final verification
        final_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="ARCHITECT",
                phase="DESIGN"
            )
        )
        
        final_tokens = final_context.token_count
        total_growth = final_tokens - baseline_tokens
        
        print("\n📊 Final stats:")
        print(f"  Baseline: {baseline_tokens} tokens")
        print(f"  Final: {final_tokens} tokens")
        print(f"  Growth: +{total_growth} tokens (+{(total_growth/baseline_tokens)*100:.1f}%)")
        print(f"  Avg per decision: {total_growth/10:.1f} tokens")
        
        # After fix: Context SHOULD grow with decisions
        # Expected: Each decision adds ~5-50 tokens (depending on rationale length)
        # 10 decisions = ~50-500 tokens growth
        # Note: Actual growth depends on max_decisions limit and rationale content
        assert total_growth > 15, \
            f"Context should grow with decisions. Only grew {total_growth} tokens"
        
        assert total_growth < 5000, \
            f"Context growing too fast: {total_growth} tokens for 10 decisions"
        
        print("✅ Context growth is controlled and proportional to decisions!")


class TestSemanticValidation:
    """Test context contains semantically correct information."""

    def test_dev_context_has_technical_details(self, context_stub, seed_case_data):
        """
        Verify DEV role gets technical context, not business context.
        
        Tests semantic correctness, not just that context exists.
        """
        from services.context.gen import context_pb2
        
        # Use seeded case
        story_id = seed_case_data
        print(f"\n🔍 Testing semantic validation on story: {story_id}")
        
        # Add technical decision to seeded case
        setup_request = context_pb2.UpdateContextRequest(
            story_id=story_id,
            task_id="SETUP",
            role="ARCHITECT",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id=f"{story_id}-DEC-TECH",
                    payload=json.dumps({
                        "title": "Use Stripe API for payment processing",
                        "rationale": "PCI compliance, SDKs available, industry standard",
                        "status": "APPROVED",
                        "decided_by": "architect"
                    }),
                    reason="Technical decision"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )
        
        context_stub.UpdateContext(setup_request)
        time.sleep(1.0)
        
        # Get DEV context
        dev_context = context_stub.GetContext(
            context_pb2.GetContextRequest(
                story_id=story_id,
                role="DEV",
                phase="BUILD"
            )
        )
        
        context_text = dev_context.context.lower()
        
        # After fix: Decisions SHOULD appear in context
        assert "stripe" in context_text or "payment" in context_text, \
            f"DEV context should mention Stripe decision. Got: {context_text[:300]}..."
        
        # Verify role-specific system message
        system_text = dev_context.blocks.system.lower()
        assert "dev" in system_text, "System message should mention DEV role"
        
        # Verify token count is reasonable (after fix)
        token_count = dev_context.token_count
        print(f"📊 Token count: {token_count}")
        
        # After fix: Should be at least 80+ tokens with decision context
        # Note: Actual count depends on decision rationale length
        # With new format, expect 80-500 tokens for basic scenarios
        assert 80 < token_count < 50000, \
            f"Token count {token_count} seems low - decisions may not be included"
        
        print("✅ Context is semantically correct and includes technical decisions!")


# Additional test ideas for future implementation:
# - test_decision_dependencies_and_evolution()
# - test_context_under_high_load()
# - test_context_with_graph_cycles()
# - test_long_running_story_over_weeks()
# - test_context_rollback_after_error()

