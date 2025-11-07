"""
Shared Kernel - Domain concepts shared across bounded contexts.

Following DDD Shared Kernel pattern:
- Contains domain concepts used by multiple bounded contexts
- Changes require coordination between teams
- Managed carefully to avoid coupling

Contents:
- domain/action.py: Action/ActionEnum used by agents_and_tools + workflow
"""

