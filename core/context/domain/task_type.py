"""TaskType enum - Types of tasks in the system."""

from enum import Enum


class TaskType(str, Enum):
    """Types of tasks that can be assigned to agents.

    Each type indicates the nature of work required.
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

    def __str__(self) -> str:
        """Return the string value."""
        return self.value






