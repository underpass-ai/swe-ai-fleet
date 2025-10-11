from __future__ import annotations

from importlib import import_module
from unittest.mock import Mock

import pytest

# Import the modules we need to test
context_assembler = import_module("swe_ai_fleet.context.context_assembler")
RoleContextFields = import_module("swe_ai_fleet.context.domain.role_context_fields").RoleContextFields
PromptBlocks = import_module("swe_ai_fleet.context.domain.scopes.prompt_blocks").PromptBlocks
PromptScopePolicy = import_module("swe_ai_fleet.context.domain.scopes.prompt_scope_policy").PromptScopePolicy
ScopeCheckResult = import_module("swe_ai_fleet.context.domain.scopes.scope_check_result").ScopeCheckResult


class TestContextAssembler:
    """Comprehensive unit tests for context_assembler module."""

    def _create_mock_role_context_fields(self, role: str = "dev") -> RoleContextFields:
        """Create a mock RoleContextFields for testing."""
        return RoleContextFields(
            role=role,
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001", "rationale": "Test plan rationale"},
            role_subtasks=[
                {
                    "subtask_id": "SUB-001",
                    "title": "First Subtask",
                    "depends_on": ["SUB-000"],
                },
                {
                    "subtask_id": "SUB-002",
                    "title": "Second Subtask",
                    "depends_on": [],
                },
            ],
            decisions_relevant=[
                {"id": "DEC-001", "title": "First Decision"},
                {"id": "DEC-002", "title": "Second Decision"},
                {"id": "DEC-003", "title": "Third Decision"},
                {"id": "DEC-004", "title": "Fourth Decision"},
                {"id": "DEC-005", "title": "Fifth Decision"},
            ],
            decision_dependencies=[{"src": "DEC-001", "dst": "DEC-002"}],
            impacted_subtasks=[
                {"subtask_id": "SUB-001"},
                {"subtask_id": "SUB-002"},
            ],
            recent_milestones=[{"id": f"MILESTONE-{i}", "ts_ms": i * 1000} for i in range(15)],
            last_summary="This is a test summary with password: secret123 and token: abc123",
            token_budget_hint=4096,
        )

    def _create_mock_bundle(self, role_context_fields: RoleContextFields):
        """Create a mock bundle with the given role context fields."""
        bundle = Mock()
        bundle.packs = {role_context_fields.role: role_context_fields}
        return bundle

    def _create_mock_rehydrator(self, bundle):
        """Create a mock rehydrator that returns the given bundle."""
        rehydrator = Mock()
        rehydrator.build.return_value = bundle
        return rehydrator

    def test_narrow_pack_to_subtask_filters_correctly(self):
        """Test _narrow_pack_to_subtask filters fields correctly."""
        pack = self._create_mock_role_context_fields("dev")
        narrowed = context_assembler._narrow_pack_to_subtask(pack, "SUB-001")

        # Should filter role_subtasks to only SUB-001
        assert len(narrowed.role_subtasks) == 1
        assert narrowed.role_subtasks[0]["subtask_id"] == "SUB-001"

        # Should filter impacted_subtasks to only SUB-001
        assert len(narrowed.impacted_subtasks) == 1
        assert narrowed.impacted_subtasks[0]["subtask_id"] == "SUB-001"

        # Should trim recent_milestones to last 10
        assert len(narrowed.recent_milestones) == 10
        assert narrowed.recent_milestones[-1]["id"] == "MILESTONE-14"

        # Other fields should remain unchanged
        assert narrowed.role == pack.role
        assert narrowed.case_header == pack.case_header
        assert narrowed.plan_header == pack.plan_header
        assert narrowed.decisions_relevant == pack.decisions_relevant
        assert narrowed.decision_dependencies == pack.decision_dependencies
        assert narrowed.last_summary == pack.last_summary
        assert narrowed.token_budget_hint == pack.token_budget_hint

    def test_narrow_pack_to_subtask_with_nonexistent_subtask(self):
        """Test _narrow_pack_to_subtask with nonexistent subtask ID."""
        pack = self._create_mock_role_context_fields("dev")
        narrowed = context_assembler._narrow_pack_to_subtask(pack, "NONEXISTENT")

        # Should return empty lists for filtered fields
        assert len(narrowed.role_subtasks) == 0
        assert len(narrowed.impacted_subtasks) == 0

        # Should still trim milestones
        assert len(narrowed.recent_milestones) == 10

    def test_build_title_returns_case_title(self):
        """Test _build_title returns the case title."""
        pack = self._create_mock_role_context_fields("dev")
        title = context_assembler._build_title(pack)
        assert title == "Test Case Title"

    def test_build_system_includes_role_and_title(self):
        """Test _build_system includes role and title."""
        system = context_assembler._build_system("dev", "Test Case Title")

        assert "dev" in system
        assert "Test Case Title" in system
        assert "agent" in system
        assert "Follow constraints" in system
        assert "Provide only necessary steps" in system

    def test_build_context_with_all_fields(self):
        """Test _build_context with all fields populated."""
        pack = self._create_mock_role_context_fields("dev")
        context = context_assembler._build_context(pack, current_subtask_id="SUB-001")

        # Should include case information
        assert "Case: CASE-001 — Test Case Title" in context

        # Should include plan rationale
        assert "Plan rationale: Test plan rationale" in context

        # Should include current subtask information
        assert "Current subtask: SUB-001 — First Subtask" in context
        assert "Depends on: SUB-000" in context

        # Should include relevant decisions (now with rationale, max 10)
        assert "Relevant decisions:" in context
        assert "DEC-001: First Decision" in context
        assert "DEC-002: Second Decision" in context
        # New format includes rationale if available
        assert "Rationale:" in context or "PROPOSED" in context  # Status or rationale shown

        # Should include last summary (truncated to 800 chars)
        assert "Last summary: This is a test summary with password: secret123 and token: abc123" in context

    def test_build_context_without_current_subtask(self):
        """Test _build_context without current_subtask_id."""
        pack = self._create_mock_role_context_fields("dev")
        context = context_assembler._build_context(pack, current_subtask_id=None)

        # Should not include current subtask information
        assert "Current subtask:" not in context
        assert "Depends on:" not in context

        # Should still include other information
        assert "Case: CASE-001 — Test Case Title" in context
        assert "Plan rationale: Test plan rationale" in context
        assert "Relevant decisions:" in context
        assert "Last summary:" in context

    def test_build_context_without_plan_rationale(self):
        """Test _build_context without plan rationale."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001"},  # No rationale
            role_subtasks=[
                {
                    "subtask_id": "SUB-001",
                    "title": "First Subtask",
                    "depends_on": ["SUB-000"],
                },
            ],
            decisions_relevant=[
                {"id": "DEC-001", "title": "First Decision"},
            ],
            decision_dependencies=[],
            impacted_subtasks=[
                {"subtask_id": "SUB-001"},
            ],
            recent_milestones=[],
            last_summary="Test summary",
            token_budget_hint=4096,
        )
        context = context_assembler._build_context(pack, current_subtask_id="SUB-001")

        # Should not include plan rationale
        assert "Plan rationale:" not in context

        # Should still include other information
        assert "Case: CASE-001 — Test Case Title" in context
        assert "Current subtask:" in context

    def test_build_context_without_decisions(self):
        """Test _build_context without decisions."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001", "rationale": "Test plan rationale"},
            role_subtasks=[
                {
                    "subtask_id": "SUB-001",
                    "title": "First Subtask",
                    "depends_on": ["SUB-000"],
                },
            ],
            decisions_relevant=[],  # No decisions
            decision_dependencies=[],
            impacted_subtasks=[
                {"subtask_id": "SUB-001"},
            ],
            recent_milestones=[],
            last_summary="Test summary",
            token_budget_hint=4096,
        )
        context = context_assembler._build_context(pack, current_subtask_id="SUB-001")

        # Should not include decisions
        assert "Relevant decisions:" not in context

        # Should still include other information
        assert "Case: CASE-001 — Test Case Title" in context
        assert "Current subtask:" in context

    def test_build_context_without_last_summary(self):
        """Test _build_context without last summary."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001", "rationale": "Test plan rationale"},
            role_subtasks=[
                {
                    "subtask_id": "SUB-001",
                    "title": "First Subtask",
                    "depends_on": ["SUB-000"],
                },
            ],
            decisions_relevant=[
                {"id": "DEC-001", "title": "First Decision"},
            ],
            decision_dependencies=[],
            impacted_subtasks=[
                {"subtask_id": "SUB-001"},
            ],
            recent_milestones=[],
            last_summary=None,  # No summary
            token_budget_hint=4096,
        )
        context = context_assembler._build_context(pack, current_subtask_id="SUB-001")

        # Should not include last summary
        assert "Last summary:" not in context

        # Should still include other information
        assert "Case: CASE-001 — Test Case Title" in context
        assert "Current subtask:" in context

    def test_build_context_with_long_summary(self):
        """Test _build_context truncates long summary."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001", "rationale": "Test plan rationale"},
            role_subtasks=[
                {
                    "subtask_id": "SUB-001",
                    "title": "First Subtask",
                    "depends_on": ["SUB-000"],
                },
            ],
            decisions_relevant=[
                {"id": "DEC-001", "title": "First Decision"},
            ],
            decision_dependencies=[],
            impacted_subtasks=[
                {"subtask_id": "SUB-001"},
            ],
            recent_milestones=[],
            last_summary="A" * 1000,  # Very long summary
            token_budget_hint=4096,
        )
        context = context_assembler._build_context(pack, current_subtask_id="SUB-001")

        # Should truncate to 800 characters
        summary_line = [line for line in context.split('\n') if line.startswith("Last summary:")][0]
        assert len(summary_line) <= 800 + len("Last summary: ")

    def test_build_prompt_blocks_success(self):
        """Test build_prompt_blocks successful execution."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        # Create policy that allows all detected scopes
        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"exec": {"dev": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
            current_subtask_id="SUB-001",
        )

        # Should return PromptBlocks
        assert isinstance(blocks, PromptBlocks)
        assert blocks.system.startswith("You are the dev agent")
        assert "Test Case Title" in blocks.system
        assert "Case: CASE-001 — Test Case Title" in blocks.context
        assert "Current subtask: SUB-001 — First Subtask" in blocks.context
        assert "You may call tools approved for your role" in blocks.tools

        # Should redact sensitive information
        assert "password: [REDACTED]" in blocks.context
        assert "token: [REDACTED]" in blocks.context

    def test_build_prompt_blocks_without_current_subtask(self):
        """Test build_prompt_blocks without current_subtask_id."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"exec": {"dev": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        # Should not narrow to subtask
        assert "Current subtask:" not in blocks.context
        assert "Case: CASE-001 — Test Case Title" in blocks.context

    def test_build_prompt_blocks_scope_violation_missing(self):
        """Test build_prompt_blocks raises error on missing scopes."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        # Create policy that requires a scope not present
        policy = PromptScopePolicy({"exec": {"dev": ["NONEXISTENT_SCOPE"]}})

        with pytest.raises(
            ValueError, match="Scope violation: missing=\\['NONEXISTENT_SCOPE'\\], extra=\\[.*\\]"
        ):
            context_assembler.build_prompt_blocks(
                rehydrator=rehydrator,
                policy=policy,
                case_id="CASE-001",
                role="dev",
                phase="exec",
            )

    def test_build_prompt_blocks_scope_violation_extra(self):
        """Test build_prompt_blocks handles extra scopes gracefully."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        # Create policy that allows fewer scopes than detected
        detected_scopes = pack.detect_scopes()
        allowed_scopes = list(detected_scopes)[:3]  # Only first 3 scopes
        policy = PromptScopePolicy({"exec": {"dev": allowed_scopes}})

        # Should not raise error for extra scopes, only missing ones
        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        assert isinstance(blocks, PromptBlocks)

    def test_build_prompt_blocks_with_architect_role(self):
        """Test build_prompt_blocks with architect role (different scope detection)."""
        pack = self._create_mock_role_context_fields("architect")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"plan": {"architect": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="architect",
            phase="plan",
        )

        assert isinstance(blocks, PromptBlocks)
        assert "architect" in blocks.system

    def test_build_prompt_blocks_with_qa_role(self):
        """Test build_prompt_blocks with qa role (different scope detection)."""
        pack = self._create_mock_role_context_fields("qa")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"test": {"qa": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="qa",
            phase="test",
        )

        assert isinstance(blocks, PromptBlocks)
        assert "qa" in blocks.system

    def test_build_prompt_blocks_rehydrator_called_correctly(self):
        """Test that rehydrator.build is called with correct parameters."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"exec": {"dev": list(detected_scopes)}})

        context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        # Verify rehydrator.build was called with correct RehydrationRequest
        rehydrator.build.assert_called_once()
        call_args = rehydrator.build.call_args[0][0]
        assert call_args.case_id == "CASE-001"
        assert call_args.roles == ["dev"]
        assert call_args.include_timeline is True
        assert call_args.include_summaries is True

    def test_build_prompt_blocks_policy_check_called_correctly(self):
        """Test that policy.check is called with correct parameters."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        # Mock the policy to track calls
        policy = Mock(spec=PromptScopePolicy)
        detected_scopes = pack.detect_scopes()
        policy.check.return_value = ScopeCheckResult(allowed=True, missing=set(), extra=set())

        context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        # Verify policy.check was called with correct parameters
        policy.check.assert_called_once()
        call_args = policy.check.call_args
        assert call_args[1]["phase"] == "exec"
        assert call_args[1]["role"] == "dev"
        assert call_args[1]["provided_scopes"] == detected_scopes

    def test_build_prompt_blocks_policy_redact_called_correctly(self):
        """Test that policy.redact is called with correct parameters."""
        pack = self._create_mock_role_context_fields("dev")
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        # Mock the policy to track calls
        policy = Mock(spec=PromptScopePolicy)
        policy.check.return_value = ScopeCheckResult(allowed=True, missing=set(), extra=set())
        policy.redact.return_value = "redacted context"

        context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        # Verify policy.redact was called with correct parameters
        policy.redact.assert_called_once()
        call_args = policy.redact.call_args
        assert call_args[0][0] == "dev"  # role
        assert "Case: CASE-001 — Test Case Title" in call_args[0][1]  # context_text

    def test_build_prompt_blocks_empty_role_subtasks(self):
        """Test build_prompt_blocks with empty role_subtasks."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Test Case Title"},
            plan_header={"plan_id": "PLAN-001", "rationale": "Test plan rationale"},
            role_subtasks=[],  # Empty role_subtasks
            decisions_relevant=[
                {"id": "DEC-001", "title": "First Decision"},
            ],
            decision_dependencies=[],
            impacted_subtasks=[],
            recent_milestones=[],
            last_summary="Test summary",
            token_budget_hint=4096,
        )
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"exec": {"dev": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
            current_subtask_id="SUB-001",
        )

        # Should still work without role_subtasks
        assert isinstance(blocks, PromptBlocks)
        assert "Current subtask:" not in blocks.context

    def test_build_prompt_blocks_minimal_pack(self):
        """Test build_prompt_blocks with minimal pack (only required fields)."""
        pack = RoleContextFields(
            role="dev",
            case_header={"case_id": "CASE-001", "title": "Minimal Case"},
            plan_header={"plan_id": "PLAN-001"},
        )
        bundle = self._create_mock_bundle(pack)
        rehydrator = self._create_mock_rehydrator(bundle)

        detected_scopes = pack.detect_scopes()
        policy = PromptScopePolicy({"exec": {"dev": list(detected_scopes)}})

        blocks = context_assembler.build_prompt_blocks(
            rehydrator=rehydrator,
            policy=policy,
            case_id="CASE-001",
            role="dev",
            phase="exec",
        )

        # Should work with minimal pack
        assert isinstance(blocks, PromptBlocks)
        assert "Case: CASE-001 — Minimal Case" in blocks.context
        assert "Minimal Case" in blocks.system
