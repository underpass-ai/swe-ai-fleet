"""Domain Entities for Monitoring Service.

Aggregate roots representing business concepts.
Zero external dependencies - pure domain logic.
"""

from .stream_info import StreamInfo
from .stream_query import StreamQuery

__all__ = ["StreamInfo", "StreamQuery"]
