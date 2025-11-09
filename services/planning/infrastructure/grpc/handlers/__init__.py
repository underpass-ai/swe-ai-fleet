"""gRPC handlers organized by domain aggregate.

Following Single Responsibility Principle and Hexagonal Architecture.
"""

from services.planning.infrastructure.grpc.handlers.decision_handlers import DecisionHandlers
from services.planning.infrastructure.grpc.handlers.epic_handlers import EpicHandlers
from services.planning.infrastructure.grpc.handlers.project_handlers import ProjectHandlers
from services.planning.infrastructure.grpc.handlers.story_handlers import StoryHandlers
from services.planning.infrastructure.grpc.handlers.task_handlers import TaskHandlers

__all__ = [
    "ProjectHandlers",
    "EpicHandlers",
    "StoryHandlers",
    "TaskHandlers",
    "DecisionHandlers",
]

