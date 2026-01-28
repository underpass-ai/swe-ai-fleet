#!/usr/bin/env python3
"""
Purge AGENT_RESPONSES NATS JetStream.

Removes all messages from the AGENT_RESPONSES stream (agent.response.>).
Use after changing the message format (e.g. to EventEnvelope) to clear
old messages that would otherwise fail parsing.
"""

import asyncio
import logging
import os
import sys

import nats

AGENT_RESPONSES_STREAM = "AGENT_RESPONSES"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def purge_agent_responses() -> bool:
    """Purge all messages from AGENT_RESPONSES stream."""
    nats_url = os.getenv(
        "NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222"
    )

    logger.info("Purging AGENT_RESPONSES stream at %s", nats_url)

    try:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()
        logger.info("Connected to NATS")
    except Exception as e:
        logger.error("Failed to connect to NATS: %s", e)
        return False

    try:
        await js.purge_stream(AGENT_RESPONSES_STREAM)
        logger.info("Purged stream: %s", AGENT_RESPONSES_STREAM)
        await nc.close()
        logger.info("Done")
        return True
    except Exception as e:
        logger.error("Failed to purge %s: %s", AGENT_RESPONSES_STREAM, e)
        await nc.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(purge_agent_responses())
    sys.exit(0 if success else 1)
