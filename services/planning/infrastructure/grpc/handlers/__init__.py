"""gRPC handlers for Planning Service.

Each handler is a standalone function that:
- Receives (request, context, use_case/storage)
- Returns protobuf response
- Uses mappers for all protobuf conversions
- Follows single responsibility principle
- Zero business logic (delegated to use cases)
"""

# Project handlers (3)
# Decision handlers (2)
from .approve_decision_handler import approve_decision_handler

# Epic handlers (3)
from .create_epic_handler import create_epic_handler
from .create_project_handler import create_project_handler

# Story handlers (4)
from .create_story_handler import create_story_handler

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
    # Project (3)
    "create_project_handler",
    "get_project_handler",
    "list_projects_handler",
    # Epic (3)
    "create_epic_handler",
    "get_epic_handler",
    "list_epics_handler",
    # Story (4)
    "create_story_handler",
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
]
