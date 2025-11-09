"""gRPC handlers for Context Service.

Following Single Responsibility Principle:
- One handler class per bounded context concern
- Each handler is 50-150 lines
- Clear separation of responsibilities
"""

from services.context.handlers.context_retrieval_handler import ContextRetrievalHandler
from services.context.handlers.context_update_handler import ContextUpdateHandler
from services.context.handlers.decision_handler import DecisionHandler
from services.context.handlers.phase_handler import PhaseHandler
from services.context.handlers.story_management_handler import StoryManagementHandler
from services.context.handlers.task_management_handler import TaskManagementHandler
from services.context.handlers.validation_handler import ValidationHandler

__all__ = [
    "ContextRetrievalHandler",
    "ContextUpdateHandler",
    "StoryManagementHandler",
    "TaskManagementHandler",
    "DecisionHandler",
    "PhaseHandler",
    "ValidationHandler",
]

