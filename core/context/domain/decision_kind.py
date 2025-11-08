"""DecisionKind enum - Categories of technical decisions."""

from enum import Enum


class DecisionKind(str, Enum):
    """Categories of technical decisions made during development.

    Each kind represents a different aspect of system design or implementation.
    """

    # Architecture decisions
    ARCHITECTURE = "architecture"
    SYSTEM_DESIGN = "system_design"
    INTEGRATION = "integration"

    # Implementation decisions
    IMPLEMENTATION = "implementation"
    ALGORITHM = "algorithm"
    DATA_STRUCTURE = "data_structure"

    # Testing decisions
    TESTING = "testing"
    TEST_STRATEGY = "test_strategy"
    QUALITY = "quality"

    # Infrastructure decisions
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    DEVOPS = "devops"
    SECURITY = "security"

    # Data decisions
    DATA = "data"
    SCHEMA = "schema"
    MIGRATION = "migration"

    # Performance decisions
    PERFORMANCE = "performance"
    SCALABILITY = "scalability"
    OPTIMIZATION = "optimization"

    # API decisions
    API_DESIGN = "api_design"
    CONTRACT = "contract"

    def __str__(self) -> str:
        """Return the string value."""
        return self.value






