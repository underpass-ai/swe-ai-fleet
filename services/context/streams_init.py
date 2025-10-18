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
            "name": "CONTEXT",  # ← CORRECTED: Match existing stream name
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
                stream_info = await js.stream_info(stream_def["name"])
                logger.info(f"Stream {stream_def['name']} already exists (storage: {stream_info.config.storage})")
                continue
            except Exception:
                # Stream doesn't exist, create it
                pass
            
            # Create stream with PERSISTENT file storage
            # This ensures streams survive NATS pod restarts
            from nats.js.api import StorageType, RetentionPolicy, DiscardPolicy
            
            await js.add_stream(
                name=stream_def["name"],
                subjects=stream_def["subjects"],
                storage=StorageType.FILE,  # ← CRITICAL: Persistent storage
                retention=RetentionPolicy.LIMITS,
                discard=DiscardPolicy.OLD,
                max_age=stream_def["max_age"],
                max_msgs=stream_def["max_msgs"],
                num_replicas=1,
            )
            logger.info(f"✓ Created PERSISTENT stream: {stream_def['name']} (storage: FILE)")
        except Exception as e:
            # Log warning but continue - streams might already exist
            logger.warning(f"Stream {stream_def['name']}: {e}")

    logger.info("✓ All persistent streams ensured")

