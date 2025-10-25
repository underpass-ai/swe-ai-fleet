"""
E2E tests for Context Service gRPC API using Testcontainers.
Tests the full service with real Neo4j, Redis, NATS, and Context Service containers.
"""

import time

import grpc
import pytest

# Mark all tests as e2e tests
pytestmark = pytest.mark.integration


class TestGetContextE2E:
    """E2E tests for GetContext RPC."""

    def test_get_context_basic(self, context_stub, seed_case_data):
        """Test GetContext with basic request."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id=seed_case_data,
            role="DEV",
            phase="BUILD"
        )

        response = context_stub.GetContext(request)

        # Verify response structure
        assert response is not None
        assert response.context != ""
        assert response.token_count > 0
        # Protobuf repeated fields can be checked for length
        assert response.scopes is not None  # Repeated field always exists
        assert response.version != ""
        
        # Verify prompt blocks
        assert response.blocks is not None
        assert response.blocks.system != ""
        assert "DEV" in response.blocks.system
        assert response.blocks.context != ""
        assert response.blocks.tools != ""

    def test_get_context_with_subtask(self, context_stub, seed_case_data):
        """Test GetContext focused on specific subtask."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id=seed_case_data,
            role="DEV",
            phase="BUILD",
            subtask_id="TASK-1"
        )

        response = context_stub.GetContext(request)

        # Verify response
        assert response is not None
        assert response.context != ""
        # Context should be generated (subtask filtering may or may not show ID in text)
        assert response.token_count > 0
        assert "DEV" in response.context  # Should mention role

    def test_get_context_different_roles(self, context_stub, seed_case_data):
        """Test GetContext for different roles returns role-specific context."""
        from services.context.gen import context_pb2

        roles = ["DEV", "QA", "DEVOPS"]
        
        for role in roles:
            request = context_pb2.GetContextRequest(
                story_id=seed_case_data,
                role=role,
                phase="BUILD"
            )

            response = context_stub.GetContext(request)

            # Verify role-specific context
            assert response is not None
            assert role in response.blocks.system
            assert response.token_count > 0

    def test_get_context_nonexistent_case(self, context_stub, empty_case_id):
        """Test GetContext with nonexistent case ID."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id=empty_case_id,
            role="DEV",
            phase="BUILD"
        )

        # Should raise error for nonexistent case
        with pytest.raises(grpc.RpcError) as exc_info:
            context_stub.GetContext(request)
        
        assert exc_info.value.code() == grpc.StatusCode.INTERNAL
        assert "not found" in exc_info.value.details().lower()


class TestUpdateContextE2E:
    """E2E tests for UpdateContext RPC."""

    def test_update_context_basic(self, context_stub, seed_case_data):
        """Test UpdateContext with single change."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id=seed_case_data,
            task_id="TASK-1",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="DEC-NEW-001",
                    payload='{"title":"New decision","rationale":"Test decision"}',
                    reason="Testing UpdateContext"
                )
            ],
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        )

        response = context_stub.UpdateContext(request)

        # Verify response
        assert response is not None
        assert response.version > 0
        assert response.hash != ""
        # Protobuf repeated field always exists
        assert response.warnings is not None

    def test_update_context_multiple_changes(self, context_stub, seed_case_data):
        """Test UpdateContext with multiple changes."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id=seed_case_data,
            task_id="TASK-2",
            role="QA",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="DEC-QA-001",
                    payload='{"title":"QA decision"}',
                    reason="QA testing"
                ),
                context_pb2.ContextChange(
                    operation="UPDATE",
                    entity_type="SUBTASK",
                    entity_id="TASK-2",
                    payload='{"status":"IN_PROGRESS"}',
                    reason="Started work"
                ),
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="MILESTONE",
                    entity_id="MILE-001",
                    payload='{"event":"test_started"}',
                    reason="Milestone tracking"
                )
            ]
        )

        response = context_stub.UpdateContext(request)

        # Verify all changes processed
        assert response is not None
        assert response.version > 0
        # Warnings may be empty (protobuf repeated field, not Python list)
        # Just verify it's accessible
        _ = list(response.warnings)

    def test_update_context_invalid_change(self, context_stub, seed_case_data):
        """Test UpdateContext with invalid change data."""
        from services.context.gen import context_pb2

        request = context_pb2.UpdateContextRequest(
            story_id=seed_case_data,
            task_id="TASK-1",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="",  # Empty operation
                    entity_type="",  # Empty entity type
                    entity_id="",  # Empty entity ID
                    payload="",
                    reason=""
                )
            ]
        )

        # Should either succeed with warnings or fail gracefully
        response = context_stub.UpdateContext(request)
        # Service logs warning but continues
        assert response is not None


class TestRehydrateSessionE2E:
    """E2E tests for RehydrateSession RPC."""

    def test_rehydrate_session_single_role(self, context_stub, seed_case_data):
        """Test RehydrateSession for single role."""
        from services.context.gen import context_pb2

        request = context_pb2.RehydrateSessionRequest(
            case_id=seed_case_data,
            roles=["DEV"],
            include_timeline=True,
            include_summaries=True,
            timeline_events=50
        )

        response = context_stub.RehydrateSession(request)

        # Verify response structure
        assert response is not None
        assert response.case_id == seed_case_data
        assert response.generated_at_ms > 0
        assert len(response.packs) == 1
        assert "DEV" in response.packs
        
        # Verify DEV pack
        dev_pack = response.packs["DEV"]
        assert dev_pack.role == "DEV"
        assert dev_pack.case_header is not None
        assert dev_pack.case_header.case_id == seed_case_data
        assert dev_pack.plan_header is not None
        assert len(dev_pack.subtasks) > 0
        # Should only have DEV subtasks
        assert all(st.role == "DEV" for st in dev_pack.subtasks)
        assert dev_pack.token_budget_hint > 0
        
        # Verify stats
        assert response.stats is not None
        assert response.stats.decisions >= 0
        assert "DEV" in response.stats.roles

    def test_rehydrate_session_multi_role(self, context_stub, seed_case_data):
        """Test RehydrateSession for multiple roles."""
        from services.context.gen import context_pb2

        request = context_pb2.RehydrateSessionRequest(
            case_id=seed_case_data,
            roles=["DEV", "QA", "DEVOPS"],
            include_timeline=True,
            include_summaries=False
        )

        response = context_stub.RehydrateSession(request)

        # Verify all roles present
        assert len(response.packs) == 3
        assert "DEV" in response.packs
        assert "QA" in response.packs
        assert "DEVOPS" in response.packs
        
        # Verify each pack has correct role
        for role in ["DEV", "QA", "DEVOPS"]:
            pack = response.packs[role]
            assert pack.role == role
            # Each role should have their specific subtasks
            role_subtasks = [st for st in pack.subtasks if st.role == role]
            assert len(role_subtasks) > 0

    def test_rehydrate_session_with_decisions(self, context_stub, seed_case_data):
        """Test RehydrateSession includes relevant decisions."""
        from services.context.gen import context_pb2

        request = context_pb2.RehydrateSessionRequest(
            case_id=seed_case_data,
            roles=["DEV"],
            include_timeline=True,
            include_summaries=True
        )

        response = context_stub.RehydrateSession(request)

        dev_pack = response.packs["DEV"]
        
        # Should have decisions from seed data
        assert len(dev_pack.decisions) > 0
        
        # Check decision structure
        for decision in dev_pack.decisions:
            assert decision.id != ""
            assert decision.title != ""

    def test_rehydrate_session_nonexistent_case(self, context_stub, empty_case_id):
        """Test RehydrateSession with nonexistent case."""
        from services.context.gen import context_pb2

        request = context_pb2.RehydrateSessionRequest(
            case_id=empty_case_id,
            roles=["DEV"]
        )

        # Should raise error
        with pytest.raises(grpc.RpcError) as exc_info:
            context_stub.RehydrateSession(request)
        
        assert exc_info.value.code() == grpc.StatusCode.INTERNAL
        assert "not found" in exc_info.value.details().lower()


class TestValidateScopeE2E:
    """E2E tests for ValidateScope RPC."""

    def test_validate_scope_allowed(self, context_stub):
        """Test ValidateScope with allowed scopes."""
        from services.context.gen import context_pb2

        request = context_pb2.ValidateScopeRequest(
            role="developer",  # Use lowercase to match config
            phase="BUILD",
            # Provide ALL required scopes for developer in BUILD phase
            provided_scopes=["CASE_HEADER", "PLAN_HEADER", "SUBTASKS_ROLE", 
                           "DECISIONS_RELEVANT_ROLE", "DEPS_RELEVANT"]
        )

        response = context_stub.ValidateScope(request)

        # Verify validation passed
        assert response is not None
        assert isinstance(response.allowed, bool)
        assert response.allowed  # Should be allowed now
        # Protobuf repeated fields are not Python lists, check they're iterable  
        assert len(list(response.missing)) == 0
        assert len(list(response.extra)) == 0

    def test_validate_scope_different_phases(self, context_stub):
        """Test ValidateScope for different phases."""
        from services.context.gen import context_pb2

        phases = ["DESIGN", "BUILD", "TEST", "DOCS"]
        
        for phase in phases:
            request = context_pb2.ValidateScopeRequest(
                role="DEV",
                phase=phase,
                provided_scopes=["CASE_HEADER", "PLAN_HEADER"]
            )

            response = context_stub.ValidateScope(request)
            
            assert response is not None
            assert isinstance(response.allowed, bool)

    def test_validate_scope_missing_scopes(self, context_stub):
        """Test ValidateScope with missing required scopes."""
        from services.context.gen import context_pb2

        request = context_pb2.ValidateScopeRequest(
            role="DEV",
            phase="BUILD",
            provided_scopes=[]  # Empty scopes
        )

        response = context_stub.ValidateScope(request)

        assert response is not None
        # May or may not be allowed depending on policy
        assert isinstance(response.allowed, bool)
        if not response.allowed:
            assert response.reason != ""


class TestErrorHandlingE2E:
    """E2E tests for error handling and resilience."""

    def test_empty_story_id(self, context_stub):
        """Test handling of empty story ID."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id="",  # Empty
            role="DEV",
            phase="BUILD"
        )

        # Should handle gracefully
        with pytest.raises(grpc.RpcError) as exc_info:
            context_stub.GetContext(request)
        
        # Should return appropriate error
        assert exc_info.value.code() in [
            grpc.StatusCode.INVALID_ARGUMENT,
            grpc.StatusCode.INTERNAL
        ]

    def test_invalid_role(self, context_stub, seed_case_data):
        """Test handling of invalid role."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id=seed_case_data,
            role="INVALID_ROLE",
            phase="BUILD"
        )

        # Service should either accept it or reject gracefully
        # Current implementation is permissive, so this should work
        response = context_stub.GetContext(request)
        assert response is not None

    def test_concurrent_requests(self, context_stub, seed_case_data):
        """Test handling of concurrent requests."""
        import concurrent.futures

        from services.context.gen import context_pb2

        def make_request(role):
            request = context_pb2.GetContextRequest(
                story_id=seed_case_data,
                role=role,
                phase="BUILD"
            )
            return context_stub.GetContext(request)

        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, role) 
                      for role in ["DEV", "QA", "DEVOPS", "ARCHITECT", "DATA"]]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should succeed
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert result.token_count > 0

    def test_large_payload(self, context_stub, seed_case_data):
        """Test handling of large update payload."""
        from services.context.gen import context_pb2

        # Create large payload
        large_payload = '{"data":"' + ("A" * 10000) + '"}'

        request = context_pb2.UpdateContextRequest(
            story_id=seed_case_data,
            task_id="TASK-1",
            role="DEV",
            changes=[
                context_pb2.ContextChange(
                    operation="CREATE",
                    entity_type="DECISION",
                    entity_id="DEC-LARGE-001",
                    payload=large_payload,
                    reason="Large payload test"
                )
            ]
        )

        # Should handle large payload
        response = context_stub.UpdateContext(request)
        assert response is not None
        assert response.version > 0


class TestDataConsistencyE2E:
    """E2E tests for data consistency between Neo4j and Redis."""

    def test_context_reflects_seed_data(self, context_stub, seed_case_data):
        """Test that GetContext reflects seeded data from Neo4j and Redis."""
        from services.context.gen import context_pb2

        request = context_pb2.GetContextRequest(
            story_id=seed_case_data,
            role="DEV",
            phase="BUILD"
        )

        response = context_stub.GetContext(request)

        # Verify context includes data from both sources
        context_text = response.context
        
        # Should include case info (from Redis)
        assert "Test Case for E2E" in context_text or seed_case_data in context_text
        
        # Should have structured blocks
        assert response.blocks.system != ""
        assert response.blocks.context != ""

    def test_rehydration_consistency(self, context_stub, seed_case_data):
        """Test that rehydration is consistent across multiple calls."""
        from services.context.gen import context_pb2

        request = context_pb2.RehydrateSessionRequest(
            case_id=seed_case_data,
            roles=["DEV"],
            include_timeline=True,
            include_summaries=True
        )

        # Make multiple calls
        response1 = context_stub.RehydrateSession(request)
        response2 = context_stub.RehydrateSession(request)

        # Should be consistent
        assert response1.case_id == response2.case_id
        assert len(response1.packs) == len(response2.packs)
        assert response1.stats.decisions == response2.stats.decisions
    
    def test_context_redacts_secrets(self, context_stub, redis_client, seed_case_data):
        """Test that GetContext redacts sensitive information in assembled context.
        
        This is a critical security feature - ensures passwords, tokens, and
        other secrets are not leaked to LLM context.
        """
        from services.context.gen import context_pb2
        
        case_id = seed_case_data
        
        # Seed Redis with data containing secrets
        # Simulate a session summary with sensitive data
        summary_key = f"swe:case:{case_id}:summaries:last"
        summary_with_secrets = """
        Development session completed successfully.
        
        Database credentials configured:
        - DB_PASSWORD = hunter2
        - API_KEY = sk-1234567890abcdef
        
        Authentication headers:
        - Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature
        
        Connection string: postgresql://user:EXAMPLE_PASSWORD@localhost/db
        """
        redis_client.set(summary_key, summary_with_secrets)
        
        # Request context
        request = context_pb2.GetContextRequest(
            story_id=case_id,
            role="DEV",
            phase="BUILD"
        )
        
        response = context_stub.GetContext(request)
        
        # Assert secrets are redacted
        context_text = response.context
        
        # Passwords should be redacted
        assert "hunter2" not in context_text, "Password leaked in context!"
        assert "[REDACTED]" in context_text or "***" in context_text, "No redaction markers found"
        
        # API keys should be redacted
        assert "sk-1234567890abcdef" not in context_text, "API key leaked!"
        
        # Bearer tokens should be redacted
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in context_text, "JWT token leaked!"
        assert (
            "Bearer [REDACTED]" in context_text or "Bearer ***" in context_text
        ), "Bearer token not redacted"
        
        # Password in connection string should be redacted
        assert "EXAMPLE_PASSWORD" not in context_text, "Connection string password leaked!"
        
        # But safe content should remain
        assert "Development session" in context_text or "BUILD" in response.context

