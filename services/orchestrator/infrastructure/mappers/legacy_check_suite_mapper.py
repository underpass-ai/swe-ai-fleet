"""Mapper for converting legacy CheckSuiteResult to CheckSuite entity.

This mapper handles the conversion from the old domain model
(src/swe_ai_fleet/orchestrator/domain/check_results) to the new
Hexagonal Architecture model (services/orchestrator/domain/entities).

Legacy format (from src/swe_ai_fleet/orchestrator):
- CheckSuiteResult object with .policy, .lint, .dryrun attributes
- Each has .ok, .violations, .issues, .errors attributes

New format:
- CheckSuite entity with PolicyResult, LintResult, DryRunResult
- Immutable, with business logic (all_passed(), overall_score())
"""

from __future__ import annotations

from typing import Any

from services.orchestrator.domain.entities import CheckSuite


class LegacyCheckSuiteMapper:
    """Maps legacy CheckSuiteResult to CheckSuite entity."""
    
    @staticmethod
    def from_legacy_object(legacy_check_suite: Any) -> CheckSuite:
        """Convert legacy CheckSuiteResult object to CheckSuite entity.
        
        Handles conversion from old domain model (used by peer_deliberation_usecase)
        to new Hexagonal Architecture model.
        
        Args:
            legacy_check_suite: Legacy CheckSuiteResult object with .to_dict() method
            
        Returns:
            CheckSuite entity
        """
        # Legacy objects have .to_dict() method
        check_dict = legacy_check_suite.to_dict()
        return CheckSuite.from_dict(check_dict)
    
    @staticmethod
    def from_dict_or_object(check_suite: dict[str, Any] | Any) -> CheckSuite:
        """Convert either dict or legacy object to CheckSuite entity.
        
        This is a convenience method for cases where the input format
        is unknown (dict from to_dict() or legacy object).
        
        Args:
            check_suite: Either a dict or legacy CheckSuiteResult object
            
        Returns:
            CheckSuite entity
        """
        if isinstance(check_suite, dict):
            # Already in dict format
            return CheckSuite.from_dict(check_suite)
        else:
            # Legacy object - convert via to_dict()
            return LegacyCheckSuiteMapper.from_legacy_object(check_suite)

