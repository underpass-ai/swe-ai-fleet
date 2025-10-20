"""Application services for orchestrator microservice.

Application Services (Facades) orchestrate multiple use cases and provide
a simplified interface for infrastructure layer (handlers, controllers).
"""

from .auto_dispatch_service import AutoDispatchService

__all__ = ["AutoDispatchService"]

