"""TaskType enum for Planning Service.

Aligned with core/context/domain/task_type.py for consistency.
"""

from enum import Enum


class TaskType(str, Enum):
    """Types of tasks that can be assigned to agents.

    Each type indicates the nature of work required.
    Aligned with Context Service for cross-service consistency.
    """

    # Development tasks
    DEVELOPMENT = "development"
    FEATURE = "feature"
    REFACTOR = "refactor"
    BUG_FIX = "bug_fix"

    # Testing tasks
    TESTING = "testing"
    UNIT_TEST = "unit_test"
    INTEGRATION_TEST = "integration_test"
    E2E_TEST = "e2e_test"

    # Review tasks
    CODE_REVIEW = "code_review"
    DESIGN_REVIEW = "design_review"
    ARCHITECTURE_REVIEW = "architecture_review"

    # Infrastructure tasks
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE = "infrastructure"
    DEVOPS = "devops"

    # Documentation tasks
    DOCUMENTATION = "documentation"
    API_DOCS = "api_docs"

    # Data tasks
    DATA_MIGRATION = "data_migration"
    SCHEMA_CHANGE = "schema_change"

    # Backlog review tasks
    BACKLOG_REVIEW_IDENTIFIED = "backlog_review_identified"

    def __str__(self) -> str:
        """Return string value.

        Returns:
            String representation
        """
        return self.value

