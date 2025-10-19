"""Mapper for CheckSuite entity."""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.entities import (
    CheckSuite,
    DryRunResult,
    LintResult,
    PolicyResult,
)


class CheckSuiteMapper:
    """Maps CheckSuite entity to/from Protobuf DTOs.
    
    Applies "Tell, Don't Ask" principle by letting CheckSuite
    provide its data rather than asking for internals.
    """
    
    @staticmethod
    def to_proto(entity: CheckSuite, orchestrator_pb2: Any) -> Any:
        """Convert CheckSuite entity to protobuf CheckSuite.
        
        Tell, Don't Ask: Use entity's methods instead of asking for internals.
        
        Args:
            entity: CheckSuite domain entity
            orchestrator_pb2: Protobuf module
            
        Returns:
            orchestrator_pb2.CheckSuite instance
        """
        # Build policy result if present
        policy = None
        if entity.policy:
            policy = orchestrator_pb2.PolicyResult(
                passed=entity.policy.passed,
                violations=entity.policy.violations,
                score=entity.policy.score,
            )
        
        # Build lint result if present
        lint = None
        if entity.lint:
            lint = orchestrator_pb2.LintResult(
                passed=entity.lint.passed,
                errors=entity.lint.errors,
                warnings=entity.lint.warnings,
                score=entity.lint.score,
            )
        
        # Build dryrun result if present
        dryrun = None
        if entity.dryrun:
            dryrun = orchestrator_pb2.DryRunResult(
                passed=entity.dryrun.passed,
                exit_code=entity.dryrun.exit_code,
                output=entity.dryrun.output,
                score=entity.dryrun.score,
            )
        
        # Tell entity to check if all passed (Tell, Don't Ask)
        all_passed = entity.all_passed()
        
        return orchestrator_pb2.CheckSuite(
            policy=policy,
            lint=lint,
            dryrun=dryrun,
            all_passed=all_passed,
        )
    
    @staticmethod
    def from_proto(proto: Any) -> CheckSuite:
        """Convert protobuf CheckSuite to CheckSuite entity.
        
        Args:
            proto: orchestrator_pb2.CheckSuite instance
            
        Returns:
            CheckSuite domain entity
        """
        policy = None
        if proto.HasField("policy"):
            policy = PolicyResult(
                passed=proto.policy.passed,
                violations=list(proto.policy.violations),
                score=proto.policy.score,
            )
        
        lint = None
        if proto.HasField("lint"):
            lint = LintResult(
                passed=proto.lint.passed,
                errors=proto.lint.errors,
                warnings=proto.lint.warnings,
                score=proto.lint.score,
            )
        
        dryrun = None
        if proto.HasField("dryrun"):
            dryrun = DryRunResult(
                passed=proto.dryrun.passed,
                exit_code=proto.dryrun.exit_code,
                output=proto.dryrun.output,
                score=proto.dryrun.score,
            )
        
        return CheckSuite(policy=policy, lint=lint, dryrun=dryrun)

