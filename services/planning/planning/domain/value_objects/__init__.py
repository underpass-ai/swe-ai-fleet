"""Domain value objects for Planning Service.

Organized by domain affinity:
- identifiers: Entity IDs
- statuses: States and statuses
- content: Textual content
- scoring: Quality scoring
- task_derivation: Task decomposition domain
- actors: Roles and users
"""

# Existing exports (mantener backward compatibility)
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.content.brief import Brief
from planning.domain.value_objects.content.comment import Comment
from planning.domain.value_objects.content.reason import Reason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.decision_id import DecisionId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.scoring.dor_score import DORScore
from planning.domain.value_objects.statuses.story_state import StoryState, StoryStateEnum

# New task derivation exports
from planning.domain.value_objects.actors.role import Role
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.identifiers.deliberation_id import DeliberationId
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.domain.value_objects.task_derivation.dependency_graph import DependencyGraph
from planning.domain.value_objects.task_derivation.keyword import Keyword
from planning.domain.value_objects.task_derivation.llm_prompt import LLMPrompt
from planning.domain.value_objects.task_derivation.task_node import TaskNode

__all__ = [
    # Existing (backward compatibility)
    "Brief",
    "Comment",
    "DecisionId",
    "DORScore",
    "Reason",
    "StoryId",
    "StoryState",
    "StoryStateEnum",
    "TaskId",
    "Title",
    "UserName",
    # New (task derivation)
    "DependencyEdge",
    "DependencyGraph",
    "DependencyReason",
    "DeliberationId",
    "Keyword",
    "LLMPrompt",
    "Role",
    "TaskNode",
]
