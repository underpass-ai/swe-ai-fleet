"""ExtractTasksFromDeliberationsUseCase - Extract tasks from agent deliberations.

Use Case (Application Layer):
- Called when all role deliberations for a story are complete
- Submits task extraction job to Ray Executor with vLLM agent
- Agent analyzes all agent deliberations and extracts structured tasks
- Each task will have associated agent deliberations for observability

Following Event-Driven Architecture:
- Called by DeliberationsCompleteConsumer when story has all role deliberations
- Ray Executor executes vLLM agent asynchronously
- Result published to NATS (agent.response.completed with task extraction results)
- TaskExtractionResultConsumer processes results and creates tasks
"""

import json
import logging
from dataclasses import dataclass

from backlog_review_processor.application.ports.planning_port import PlanningPort
from backlog_review_processor.application.ports.ray_executor_port import RayExecutorPort
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId

logger = logging.getLogger(__name__)


@dataclass
class ExtractTasksFromDeliberationsUseCase:
    """
    Extract tasks from agent deliberations using vLLM agent.

    This use case:
    1. Receives story with all role deliberations complete
    2. Builds prompt with all agent deliberations
    3. Submits task extraction job to Ray Executor
    4. Ray Executor calls vLLM agent to analyze deliberations
    5. Agent returns structured tasks with associated deliberations
    6. Tasks are created via TaskExtractionResultConsumer

    Dependencies:
    - RayExecutorPort: For submitting task extraction job
    - PlanningPort: For creating tasks (will be called by consumer)
    """

    ray_executor: RayExecutorPort

    async def execute(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        agent_deliberations: list[dict],
    ) -> None:
        """
        Extract tasks from agent deliberations.

        Args:
            ceremony_id: Ceremony identifier
            story_id: Story identifier
            agent_deliberations: List of agent deliberations (dicts with agent_id, role, proposal, etc.)

        Raises:
            RayExecutorError: If submission to Ray Executor fails
        """
        if not agent_deliberations:
            logger.warning(
                f"No agent deliberations found for story {story_id.value}, "
                f"skipping task extraction"
            )
            return

        # Build prompt with all agent deliberations
        prompt = self._build_extraction_prompt(story_id, agent_deliberations)

        # Build task_id for tracking
        task_id = f"ceremony-{ceremony_id.value}:story-{story_id.value}:task-extraction"

        # Submit to Ray Executor (fire-and-forget)
        deliberation_id = await self.ray_executor.submit_task_extraction(
            task_id=task_id,
            task_description=prompt,
            story_id=story_id,
            ceremony_id=ceremony_id,
        )

        logger.info(
            f"📤 Submitted task extraction job: "
            f"deliberation_id={deliberation_id.value}, "
            f"story={story_id.value}, "
            f"num_deliberations={len(agent_deliberations)}"
        )

    def _build_extraction_prompt(
        self, story_id: StoryId, agent_deliberations: list[dict]
    ) -> str:
        """
        Build prompt for task extraction agent.

        Includes all agent deliberations and instructions for extracting tasks.

        Args:
            story_id: Story identifier
            agent_deliberations: List of agent deliberations (dicts)

        Returns:
            Prompt string for vLLM agent
        """
        deliberations_text = []
        for i, deliberation in enumerate(agent_deliberations, 1):
            agent_id = deliberation.get("agent_id", "unknown")
            role = deliberation.get("role", "unknown")
            proposal = deliberation.get("proposal", {})

            # Extract feedback text from proposal
            if isinstance(proposal, dict):
                feedback_text = proposal.get("content", str(proposal))
            else:
                feedback_text = str(proposal)

            deliberations_text.append(
                f"--- Deliberation {i}: {agent_id} ({role}) ---\n"
                f"{feedback_text}\n"
            )

        prompt = f"""You are a task extraction specialist. Analyze the following agent deliberations for a user story and extract concrete, actionable tasks.

Story ID: {story_id.value}

Agent Deliberations:
{chr(10).join(deliberations_text)}

Instructions:
1. Analyze all agent deliberations carefully
2. Extract concrete, actionable tasks that need to be completed
3. Each task should be specific, measurable, and have clear acceptance criteria
4. Tasks should be ordered logically (dependencies considered)
5. For each task, identify which agent deliberations contributed to it
6. Return a JSON array of tasks with the following structure:
   {{
     "tasks": [
       {{
         "title": "Task title",
         "description": "Detailed description",
         "estimated_hours": 8,
         "deliberation_indices": [0, 1, 2],  // Indices of deliberations that contributed
         "priority": 1  // 1 = highest priority
       }}
     ]
   }}

Return ONLY valid JSON, no markdown, no explanations.
"""

        return prompt

