"""gRPC handlers for Planning Service.

Each handler is a standalone function that:
- Receives (request, context, use_case/storage)
- Returns protobuf response
- Uses mappers for all protobuf conversions
- Follows single responsibility principle
- Zero business logic (delegated to use cases)
"""

# Project handlers (3)
from .create_project_handler import create_project
from .get_project_handler import get_project
from .list_projects_handler import list_projects

# Epic handlers (3)
from .create_epic_handler import create_epic
from .get_epic_handler import get_epic
from .list_epics_handler import list_epics

# Story handlers (4)
from .create_story_handler import create_story
from .get_story_handler import get_story
from .list_stories_handler import list_stories
from .transition_story_handler import transition_story

# Task handlers (3)
from .create_task_handler import create_task
from .get_task_handler import get_task
from .list_tasks_handler import list_tasks

# Decision handlers (2)
from .approve_decision_handler import approve_decision
from .reject_decision_handler import reject_decision

__all__ = [
    # Project (3)
    "create_project",
    "get_project",
    "list_projects",
    # Epic (3)
    "create_epic",
    "get_epic",
    "list_epics",
    # Story (4)
    "create_story",
    "get_story",
    "list_stories",
    "transition_story",
    # Task (3)
    "create_task",
    "get_task",
    "list_tasks",
    # Decision (2)
    "approve_decision",
    "reject_decision",
]
