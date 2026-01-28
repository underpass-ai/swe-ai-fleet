"""gRPC handlers for Planning Service.

Each handler is a standalone function that:
- Receives (request, context, use_case/storage)
- Returns protobuf response
- Uses mappers for all protobuf conversions
- Follows single responsibility principle
- Zero business logic (delegated to use cases)
"""

# Project handlers (4)
# Decision handlers (2)
# Backlog Review Ceremony handlers (10)
from planning.infrastructure.grpc.handlers.add_stories_to_review_handler import (
    add_stories_to_review_handler,
)
from planning.infrastructure.grpc.handlers.approve_review_plan_handler import (
    approve_review_plan_handler,
)
from planning.infrastructure.grpc.handlers.complete_cancel_ceremony_handlers import (
    cancel_backlog_review_ceremony_handler,
    complete_backlog_review_ceremony_handler,
)
from planning.infrastructure.grpc.handlers.create_backlog_review_ceremony_handler import (
    create_backlog_review_ceremony_handler,
)
from planning.infrastructure.grpc.handlers.get_backlog_review_ceremony_handler import (
    get_backlog_review_ceremony_handler,
)
from planning.infrastructure.grpc.handlers.list_backlog_review_ceremonies_handler import (
    list_backlog_review_ceremonies_handler,
)
from planning.infrastructure.grpc.handlers.reject_review_plan_handler import (
    reject_review_plan_handler,
)
from planning.infrastructure.grpc.handlers.remove_story_from_review_handler import (
    remove_story_from_review_handler,
)
from planning.infrastructure.grpc.handlers.add_agent_deliberation_handler import (
    add_agent_deliberation_handler,
)
from planning.infrastructure.grpc.handlers.start_backlog_review_ceremony_handler import (
    start_backlog_review_ceremony_handler,
)
from planning.infrastructure.grpc.handlers.start_planning_ceremony_handler import (
    start_planning_ceremony_handler,
)

from .approve_decision_handler import approve_decision_handler

# Epic handlers (4)
from .create_epic_handler import create_epic_handler
from .create_project_handler import create_project_handler
from .delete_epic_handler import delete_epic_handler
from .delete_project_handler import delete_project_handler

# Story handlers (5)
from .create_story_handler import create_story_handler
from .delete_story_handler import delete_story_handler

# Task handlers (3)
from .create_task_handler import create_task_handler
from .get_epic_handler import get_epic_handler
from .get_project_handler import get_project_handler
from .get_story_handler import get_story_handler
from .get_task_handler import get_task_handler
from .list_epics_handler import list_epics_handler
from .list_projects_handler import list_projects_handler
from .list_stories_handler import list_stories_handler
from .list_tasks_handler import list_tasks_handler
from .reject_decision_handler import reject_decision_handler
from .transition_story_handler import transition_story_handler

__all__ = [
    # Project (4)
    "create_project_handler",
    "delete_project_handler",
    "get_project_handler",
    "list_projects_handler",
    # Epic (4)
    "create_epic_handler",
    "delete_epic_handler",
    "get_epic_handler",
    "list_epics_handler",
    # Story (5)
    "create_story_handler",
    "delete_story_handler",
    "get_story_handler",
    "list_stories_handler",
    "transition_story_handler",
    # Task (3)
    "create_task_handler",
    "get_task_handler",
    "list_tasks_handler",
    # Decision (2)
    "approve_decision_handler",
    "reject_decision_handler",
    # Backlog Review Ceremony (10)
    "add_agent_deliberation_handler",
    "add_stories_to_review_handler",
    "approve_review_plan_handler",
    "cancel_backlog_review_ceremony_handler",
    "complete_backlog_review_ceremony_handler",
    "create_backlog_review_ceremony_handler",
    "get_backlog_review_ceremony_handler",
    "list_backlog_review_ceremonies_handler",
    "reject_review_plan_handler",
    "remove_story_from_review_handler",
    "start_backlog_review_ceremony_handler",
    # Planning Ceremony (processor)
    "start_planning_ceremony_handler",
]
