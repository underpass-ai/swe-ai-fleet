"""Domain Entities for Monitoring Service.

Aggregate roots representing business concepts.
Zero external dependencies - pure domain logic.
"""

from .stream_info import StreamInfo

__all__ = ["StreamInfo"]
