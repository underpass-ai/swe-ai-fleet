"""Mapper: NATS agent.response.completed payload → Domain Value Objects.

Infrastructure Mapper:
- Converts external NATS payload (DTO) → domain Value Objects
- Anti-corruption layer (external format → domain)
"""

from typing import Any

from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId


class TaskDerivationResultPayloadMapper:
    """
    Mapper: Convert NATS agent.response.completed payload to domain Value Objects.

    Infrastructure Layer Responsibility:
    - Domain should not know about NATS payload format
    - Payload parsing centralized in one place
    - Uses explicit payload fields (no legacy task_id parsing)

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Converts DTO (dict) → domain VOs
    - Anti-corruption layer
    """

    @staticmethod
    def extract_plan_id(payload: dict[str, Any]) -> PlanId | None:
        """
        Extract plan_id from payload.

        Args:
            payload: NATS message payload (dict).

        Returns:
            PlanId if found, None otherwise.
        """
        plan_id_str = payload.get("plan_id", "")
        if plan_id_str:
            return PlanId(plan_id_str)

        return None

    @staticmethod
    def extract_story_id(payload: dict[str, Any]) -> StoryId:
        """
        Extract story_id from payload.

        Args:
            payload: NATS message payload (dict).

        Returns:
            StoryId value object.

        Raises:
            ValueError: If story_id is missing or empty.
        """
        story_id_str = payload.get("story_id", "")
        if not story_id_str:
            raise ValueError("Missing required field: story_id")

        return StoryId(story_id_str)

    @staticmethod
    def extract_role(payload: dict[str, Any]) -> str:
        """
        Extract role from payload.

        Args:
            payload: NATS message payload (dict).

        Returns:
            Role string.

        Raises:
            ValueError: If role is missing or empty.
        """
        role_str = payload.get("role", "")
        if not role_str:
            raise ValueError("Missing required field: role")

        return role_str

    @staticmethod
    def extract_llm_text(payload: dict[str, Any]) -> str:
        """
        Extract LLM generated text from payload.

        Expected payload structure:
        {
            "result": {
                "proposal": "LLM generated text here..."
            }
        }

        Args:
            payload: NATS message payload (dict).

        Returns:
            LLM generated text string.

        Raises:
            ValueError: If result.proposal is missing or empty.
        """
        result = payload.get("result", {})
        generated_text = result.get("proposal", "")

        if not generated_text:
            raise ValueError("Missing or empty LLM result.proposal")

        return generated_text
