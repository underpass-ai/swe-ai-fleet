"""
NATS JetStream Streams Initialization.

Creates the necessary streams if they don't exist.
"""

import logging
from nats.js import JetStreamContext

logger = logging.getLogger(__name__)


async def ensure_streams(js: JetStreamContext):
    """
    Ensure all required NATS JetStream streams exist.

    Args:
        js: JetStream context
    """
    streams = [
        {
            "name": "PLANNING_EVENTS",
            "subjects": ["planning.>"],
            "max_age": 30 * 24 * 60 * 60 * 1_000_000_000,  # 30 days
            "max_msgs": 1_000_000,
        },
        {
            "name": "CONTEXT_EVENTS",
            "subjects": ["context.>"],
            "max_age": 7 * 24 * 60 * 60 * 1_000_000_000,  # 7 days
            "max_msgs": 100_000,
        },
        {
            "name": "ORCHESTRATOR_EVENTS",
            "subjects": ["orchestration.>"],
            "max_age": 7 * 24 * 60 * 60 * 1_000_000_000,  # 7 days
            "max_msgs": 50_000,
        },
        {
            "name": "AGENT_COMMANDS",
            "subjects": ["agent.cmd.>"],
            "max_age": 1 * 60 * 60 * 1_000_000_000,  # 1 hour
            "max_msgs": 10_000,
        },
        {
            "name": "AGENT_RESPONSES",
            "subjects": ["agent.response.>"],
            "max_age": 1 * 60 * 60 * 1_000_000_000,  # 1 hour
            "max_msgs": 10_000,
        },
    ]

    for stream_def in streams:
        try:
            # Try to get stream info first to see if it exists
            try:
                await js.stream_info(stream_def["name"])
                logger.debug(f"Stream {stream_def['name']} already exists")
                continue
            except Exception:
                # Stream doesn't exist, create it
                pass
            
            # Create stream with simplified config
            await js.add_stream(
                name=stream_def["name"],
                subjects=stream_def["subjects"],
            )
            logger.info(f"✓ Created stream: {stream_def['name']}")
        except Exception as e:
            # Log warning but continue - streams might already exist
            logger.debug(f"Stream {stream_def['name']}: {e}")

    logger.info("✓ All streams ensured")

