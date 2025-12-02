"""ReviewStoryWithCouncilsUseCase - Coordinate multi-council story review.

Use Case (Application Layer):
- Coordinates review of a story by multiple councils (ARCHITECT, QA, DEVOPS)
- Fetches context from Context Service
- Deliberates with each council via Orchestrator
- Generates PlanPreliminary from feedbacks
- Returns StoryReviewResult

This is a KEY use case that bridges Planning Service with Orchestrator Service.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from planning.application.ports import ContextPort, OrchestratorPort
from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    DeliberationResponse,
    TaskConstraints,
)
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.plan_preliminary import PlanPreliminary
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewStoryWithCouncilsUseCase:
    """
    Coordinate story review by multiple councils.

    This use case:
    1. Fetches story context from Context Service
    2. For each role (ARCHITECT, QA, DEVOPS):
       - Constructs DeliberationRequest with context
       - Calls Orchestrator.Deliberate
       - Extracts feedback from winner proposal
    3. Generates PlanPreliminary from consolidated feedbacks
    4. Extracts tasks_outline from feedbacks
    5. Generates recommendations
    6. Returns StoryReviewResult (PENDING approval)

    Dependencies:
    - OrchestratorPort: For multi-agent deliberations
    - ContextPort: For story context retrieval
    """

    orchestrator: OrchestratorPort
    context: ContextPort

    async def execute(
        self,
        story_id: StoryId,
        roles: tuple[str, ...] = ("ARCHITECT", "QA", "DEVOPS"),
    ) -> StoryReviewResult:
        """
        Review story with multiple councils.

        Args:
            story_id: Story to review
            roles: Roles to involve in review (default: ARCHITECT, QA, DEVOPS)

        Returns:
            StoryReviewResult with feedbacks and plan preliminary

        Raises:
            OrchestratorError: If deliberation fails
            ContextServiceError: If context retrieval fails
        """
        logger.info(
            f"Starting council review for story {story_id.value} "
            f"with roles: {', '.join(roles)}"
        )

        # 1. Fetch context from Context Service
        context_response = await self.context.get_context(
            story_id=story_id.value,
            role="ARCHITECT",  # Generic context (not role-specific)
            phase="DESIGN",    # Planning/design phase
            token_budget=2000,
        )

        context_text = context_response.context

        logger.info(
            f"Retrieved context for story {story_id.value}: "
            f"{context_response.token_count} tokens"
        )

        # 2. Deliberate with each council
        reviews: dict[str, DeliberationResponse] = {}

        for role in roles:
            logger.info(f"Starting deliberation with {role} council...")

            # Construct deliberation request
            deliberation_request = DeliberationRequest(
                task_description=self._build_task_description(story_id, context_text),
                role=role,
                constraints=TaskConstraints(
                    rubric=self._build_rubric(role),
                    requirements=self._build_requirements(role),
                    timeout_seconds=180,
                    max_iterations=2,
                ),
                rounds=1,
                num_agents=3,
            )

            # Call Orchestrator
            response = await self.orchestrator.deliberate(deliberation_request)

            reviews[role] = response

            logger.info(
                f"{role} council completed: winner={response.winner_id}, "
                f"duration={response.duration_ms}ms"
            )

        # 3. Generate PlanPreliminary from feedbacks
        plan_preliminary = self._generate_preliminary_plan(story_id, reviews)

        # 4. Extract feedback strings
        architect_feedback = self._extract_feedback(reviews.get("ARCHITECT"))
        qa_feedback = self._extract_feedback(reviews.get("QA"))
        devops_feedback = self._extract_feedback(reviews.get("DEVOPS"))

        # 5. Generate recommendations
        recommendations = self._generate_recommendations(reviews)

        # 6. Create StoryReviewResult
        reviewed_at = datetime.now(UTC)
        review_result = StoryReviewResult(
            story_id=story_id,
            plan_preliminary=plan_preliminary,
            architect_feedback=architect_feedback,
            qa_feedback=qa_feedback,
            devops_feedback=devops_feedback,
            recommendations=recommendations,
            approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
            reviewed_at=reviewed_at,
        )

        logger.info(f"Council review completed for story {story_id.value}")

        return review_result

    def _build_task_description(self, story_id: StoryId, context: str) -> str:
        """Build task description for deliberation."""
        return f"""Review user story {story_id.value} for technical feasibility and completeness.

Analyze the story and provide specific feedback on:
- Technical feasibility and architecture
- Testing requirements and strategies
- Infrastructure and deployment needs
- Dependencies (services, libraries, infrastructure)
- Risks and considerations
- High-level tasks needed (outline format)

Story Context:
{context}

Provide your analysis and recommendations.
"""

    def _build_rubric(self, role: str) -> str:
        """Build role-specific rubric."""
        rubrics = {
            "ARCHITECT": "Evaluate: technical_feasibility (high), architecture_quality (high), scalability (medium), maintainability (high)",
            "QA": "Evaluate: testability (high), test_coverage_potential (high), automation_feasibility (high), quality_assurance (high)",
            "DEVOPS": "Evaluate: infrastructure_requirements (complete), deployment_complexity (low), observability (high), operational_complexity (low)",
        }
        return rubrics.get(role, "Evaluate: completeness, feasibility, quality")

    def _build_requirements(self, role: str) -> tuple[str, ...]:
        """Build role-specific requirements."""
        requirements_map = {
            "ARCHITECT": (
                "Identify all technical components needed",
                "List architectural patterns to apply",
                "Identify technical dependencies (services, libraries)",
                "Estimate complexity as LOW, MEDIUM, or HIGH",
                "List high-level development tasks",
            ),
            "QA": (
                "Identify testing strategies (unit, integration, e2e)",
                "List test scenarios and edge cases",
                "Estimate testability (easy, moderate, complex)",
                "List high-level testing tasks",
            ),
            "DEVOPS": (
                "Identify infrastructure requirements (databases, caches, services)",
                "List deployment considerations",
                "Identify observability needs (metrics, logs, traces)",
                "List high-level devops tasks",
            ),
        }
        return requirements_map.get(
            role,
            ("Provide specific technical recommendations",),
        )

    def _generate_preliminary_plan(
        self,
        story_id: StoryId,
        reviews: dict[str, DeliberationResponse],
    ) -> PlanPreliminary:
        """
        Generate PlanPreliminary from council feedbacks.

        Consolidates feedbacks into a cohesive plan with:
        - Title and description
        - Acceptance criteria
        - Technical notes
        - Roles needed
        - Estimated complexity
        - Dependencies
        - Tasks outline (high-level tasks identified by councils)
        """
        # Extract content from winners
        architect_content = reviews["ARCHITECT"].get_winner_content() if "ARCHITECT" in reviews else ""
        qa_content = reviews["QA"].get_winner_content() if "QA" in reviews else ""
        devops_content = reviews["DEVOPS"].get_winner_content() if "DEVOPS" in reviews else ""

        # TODO: In production, parse these feedbacks more intelligently
        # For now, we'll use simple heuristics

        # Extract tasks outline from all feedbacks
        tasks_outline = self._extract_tasks_outline(reviews)

        # Consolidate technical notes
        technical_notes = self._consolidate_technical_notes(
            architect_content, qa_content, devops_content
        )

        # Estimate complexity (aggregate from feedbacks)
        estimated_complexity = self._estimate_complexity(
            architect_content, qa_content, devops_content
        )

        # Extract dependencies
        dependencies = self._extract_dependencies(
            architect_content, devops_content
        )

        # Build plan
        return PlanPreliminary(
            title=Title(f"Technical Plan for {story_id.value}"),
            description=Brief("Plan generated from council reviews"),
            acceptance_criteria=self._extract_acceptance_criteria(architect_content),
            technical_notes=technical_notes,
            roles=tuple(reviews.keys()),
            estimated_complexity=estimated_complexity,
            dependencies=dependencies,
            tasks_outline=tasks_outline,
        )

    def _extract_feedback(
        self,
        response: DeliberationResponse | None,
    ) -> str:
        """Extract feedback from deliberation response."""
        if not response:
            return "No feedback available"

        return response.get_winner_content()

    def _extract_tasks_outline(
        self,
        reviews: dict[str, DeliberationResponse],
    ) -> tuple[str, ...]:
        """
        Extract high-level tasks from council feedbacks.

        Parses feedbacks to identify task descriptions mentioned by councils.
        This is a simplified implementation - production would use LLM parsing.
        """
        # Simplified: Extract first few sentences that look like tasks
        # In production, this would use regex or LLM parsing
        tasks = []

        for role, _response in reviews.items():
            # TODO: Parse feedback content properly with regex/LLM in production
            # For now, add placeholder tasks based on role
            if role == "ARCHITECT":
                tasks.extend(["Setup architecture components", "Implement core logic"])
            elif role == "QA":
                tasks.extend(["Add unit tests", "Add integration tests"])
            elif role == "DEVOPS":
                tasks.extend(["Setup infrastructure", "Configure deployment"])

        return tuple(tasks) if tasks else ("Review and plan implementation",)

    def _consolidate_technical_notes(
        self,
        architect: str,
        qa: str,
        devops: str,
    ) -> str:
        """Consolidate technical notes from all councils."""
        notes = []

        if architect:
            notes.append(f"ARCHITECTURE:\n{architect[:500]}")  # Truncate

        if qa:
            notes.append(f"QA:\n{qa[:300]}")

        if devops:
            notes.append(f"DEVOPS:\n{devops[:300]}")

        return "\n\n".join(notes) if notes else "No technical notes"

    def _estimate_complexity(
        self,
        architect: str,
        qa: str,
        devops: str,
    ) -> str:
        """Estimate complexity from feedbacks."""
        # Simplified: Look for complexity keywords
        combined = f"{architect} {qa} {devops}".lower()

        if "complex" in combined or "difficult" in combined:
            return "HIGH"
        elif "simple" in combined or "straightforward" in combined:
            return "LOW"
        else:
            return "MEDIUM"

    def _extract_dependencies(
        self,
        architect: str,
        devops: str,
    ) -> tuple[str, ...]:
        """Extract technical dependencies from architect and devops feedbacks."""
        # Simplified: Look for common dependency keywords
        combined = f"{architect} {devops}".lower()
        dependencies = []

        # Common dependencies
        if "redis" in combined:
            dependencies.append("Redis")
        if "postgres" in combined or "database" in combined:
            dependencies.append("PostgreSQL")
        if "jwt" in combined:
            dependencies.append("JWT library")

        return tuple(dependencies) if dependencies else ()

    def _extract_acceptance_criteria(self, architect: str) -> tuple[str, ...]:
        """Extract acceptance criteria from architect feedback."""
        # Simplified: Return generic criteria
        # In production, parse from architect feedback
        return (
            "Implementation follows technical plan",
            "All tests pass",
            "Code review approved",
        )

    def _generate_recommendations(
        self,
        reviews: dict[str, DeliberationResponse],
    ) -> tuple[str, ...]:
        """Generate consolidated recommendations from all councils."""
        recommendations = []

        # Extract key recommendations from each council
        # Simplified implementation
        for role, response in reviews.items():
            feedback_content = response.get_winner_content()

            # Simple heuristic: Look for "recommend", "suggest", "should"
            if "recommend" in feedback_content.lower():
                recommendations.append(f"{role}: Consider recommendations in feedback")
            elif "risk" in feedback_content.lower():
                recommendations.append(f"{role}: Review identified risks")

        if not recommendations:
            recommendations.append("Review council feedbacks for detailed recommendations")

        return tuple(recommendations)

