"""Task Derivation Service entrypoint (placeholder).

API-first approach: the service wiring and gRPC server will be implemented
after the synchronous/asynchronous contracts and adapters are finalized.
"""

import asyncio
import logging

logger = logging.getLogger(__name__)


async def serve() -> None:
    """Placeholder async server entrypoint."""
    logger.info("Task Derivation Service server placeholder - no-op for now.")
    await asyncio.Future()  # Keep the event loop alive (until cancellation)


if __name__ == "__main__":
    asyncio.run(serve())

