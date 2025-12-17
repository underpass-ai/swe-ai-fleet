"""Unit tests for PlanPreliminary value object."""

import pytest
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary


class TestPlanPreliminary:
    """Test suite for PlanPreliminary value object."""

    def test_create_valid_plan(self) -> None:
        """Test creating a valid PlanPreliminary."""
        plan = PlanPreliminary(
            title=Title("User Authentication"),
            description=Brief("Implement JWT-based authentication"),
            acceptance_criteria=("User can register", "User can login"),
            technical_notes="Use python-jose for JWT, bcrypt for hashing",
            roles=("DEVELOPER", "QA"),
            estimated_complexity="MEDIUM",
            dependencies=("Redis", "python-jose"),
        )

        assert plan.title.value == "User Authentication"
        assert plan.description.value == "Implement JWT-based authentication"
        assert len(plan.acceptance_criteria) == 2
        assert "User can register" in plan.acceptance_criteria
        assert plan.estimated_complexity == "MEDIUM"
        assert len(plan.roles) == 2
        assert len(plan.dependencies) == 2

    def test_create_plan_with_tasks_outline(self) -> None:
        """Test creating plan with tasks_outline (hybrid flow)."""
        plan = PlanPreliminary(
            title=Title("User Authentication"),
            description=Brief("Implement JWT-based authentication"),
            acceptance_criteria=("User can register",),
            technical_notes="Use JWT",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
            tasks_outline=(
                "Setup JWT middleware",
                "Implement registration endpoint",
                "Add unit tests",
            ),
        )

        assert len(plan.tasks_outline) == 3
        assert "Setup JWT middleware" in plan.tasks_outline
        assert "Implement registration endpoint" in plan.tasks_outline
        assert "Add unit tests" in plan.tasks_outline

    def test_create_plan_without_tasks_outline_defaults_to_empty(self) -> None:
        """Test that tasks_outline defaults to empty tuple."""
        plan = PlanPreliminary(
            title=Title("Simple Plan"),
            description=Brief("Simple description"),
            acceptance_criteria=("Criterion 1",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )

        assert plan.tasks_outline == ()
        assert len(plan.tasks_outline) == 0

    def test_empty_acceptance_criteria_raises_value_error(self) -> None:
        """Test that empty acceptance criteria raises ValueError."""
        with pytest.raises(ValueError, match="at least one acceptance criterion"):
            PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=(),  # Empty!
                technical_notes="Notes",
                roles=("DEVELOPER",),
                estimated_complexity="LOW",
                dependencies=(),
            )

    def test_complexity_low(self) -> None:
        """Test LOW complexity."""
        plan = PlanPreliminary(
            title=Title("Simple Task"),
            description=Brief("Easy task"),
            acceptance_criteria=("Done",),
            technical_notes="",
            roles=(),
            estimated_complexity="LOW",
            dependencies=(),
        )

        assert plan.estimated_complexity == "LOW"

    def test_complexity_medium(self) -> None:
        """Test MEDIUM complexity."""
        plan = PlanPreliminary(
            title=Title("Medium Task"),
            description=Brief("Moderate task"),
            acceptance_criteria=("Done",),
            technical_notes="",
            roles=(),
            estimated_complexity="MEDIUM",
            dependencies=(),
        )

        assert plan.estimated_complexity == "MEDIUM"

    def test_complexity_high(self) -> None:
        """Test HIGH complexity."""
        plan = PlanPreliminary(
            title=Title("Complex Task"),
            description=Brief("Hard task"),
            acceptance_criteria=("Done",),
            technical_notes="",
            roles=(),
            estimated_complexity="HIGH",
            dependencies=(),
        )

        assert plan.estimated_complexity == "HIGH"

    def test_invalid_complexity_raises_value_error(self) -> None:
        """Test that invalid complexity raises ValueError."""
        with pytest.raises(ValueError, match="Invalid estimated_complexity"):
            PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="",
                roles=(),
                estimated_complexity="INVALID",  # Invalid!
                dependencies=(),
            )

    def test_complexity_case_sensitive(self) -> None:
        """Test that complexity validation is case-sensitive."""
        with pytest.raises(ValueError, match="Invalid estimated_complexity"):
            PlanPreliminary(
                title=Title("Plan"),
                description=Brief("Description"),
                acceptance_criteria=("Criterion",),
                technical_notes="",
                roles=(),
                estimated_complexity="low",  # Lowercase not allowed!
                dependencies=(),
            )

    def test_str_representation(self) -> None:
        """Test __str__ returns meaningful representation."""
        plan = PlanPreliminary(
            title=Title("Auth Plan"),
            description=Brief("Authentication"),
            acceptance_criteria=("User can login",),
            technical_notes="JWT",
            roles=("DEVELOPER",),
            estimated_complexity="MEDIUM",
            dependencies=(),
        )

        str_repr = str(plan)
        assert "Auth Plan" in str_repr
        assert "MEDIUM" in str_repr

    def test_immutability(self) -> None:
        """Test that PlanPreliminary is immutable (frozen dataclass)."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )

        with pytest.raises(AttributeError):
            plan.estimated_complexity = "HIGH"  # type: ignore

    def test_empty_roles_allowed(self) -> None:
        """Test that empty roles tuple is allowed."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=(),  # Empty is OK
            estimated_complexity="LOW",
            dependencies=(),
        )

        assert plan.roles == ()

    def test_empty_dependencies_allowed(self) -> None:
        """Test that empty dependencies tuple is allowed."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),  # Empty is OK
        )

        assert plan.dependencies == ()

    def test_empty_technical_notes_allowed(self) -> None:
        """Test that empty technical notes string is allowed."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="",  # Empty is OK
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )

        assert plan.technical_notes == ""

    def test_multiple_acceptance_criteria(self) -> None:
        """Test plan with multiple acceptance criteria."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=(
                "Criterion 1",
                "Criterion 2",
                "Criterion 3",
            ),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="HIGH",
            dependencies=(),
        )

        assert len(plan.acceptance_criteria) == 3

    def test_multiple_roles(self) -> None:
        """Test plan with multiple roles."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER", "QA", "DEVOPS"),
            estimated_complexity="HIGH",
            dependencies=(),
        )

        assert len(plan.roles) == 3
        assert "QA" in plan.roles

    def test_multiple_dependencies(self) -> None:
        """Test plan with multiple dependencies."""
        plan = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="HIGH",
            dependencies=("Redis", "PostgreSQL", "python-jose"),
        )

        assert len(plan.dependencies) == 3
        assert "PostgreSQL" in plan.dependencies

    def test_equality(self) -> None:
        """Test equality between two plans with same values."""
        plan1 = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )
        plan2 = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )

        assert plan1 == plan2

    def test_inequality_different_complexity(self) -> None:
        """Test inequality when complexity differs."""
        plan1 = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="LOW",
            dependencies=(),
        )
        plan2 = PlanPreliminary(
            title=Title("Plan"),
            description=Brief("Description"),
            acceptance_criteria=("Criterion",),
            technical_notes="Notes",
            roles=("DEVELOPER",),
            estimated_complexity="HIGH",  # Different!
            dependencies=(),
        )

        assert plan1 != plan2

