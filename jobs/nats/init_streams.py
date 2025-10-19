#!/usr/bin/env python3
"""
Initialize NATS JetStream Streams.

Creates all required streams for SWE AI Fleet.
"""

import asyncio
import logging
import os
import sys

import nats
from nats.js.api import StreamConfig, RetentionPolicy, DiscardPolicy

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def init_streams():
    """Initialize all NATS JetStream streams."""
    
    nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
    
    logger.info(f"🚀 Initializing NATS JetStream streams at {nats_url}")
    
    # Connect to NATS
    try:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()
        logger.info("✅ Connected to NATS")
    except Exception as e:
        logger.error(f"❌ Failed to connect to NATS: {e}")
        return False
    
    # Define streams (names must match what services expect)
    streams = [
        {
            "name": "PLANNING_EVENTS",
            "subjects": ["planning.>"],
            "description": "Planning service events (stories, plans, transitions)",
        },
        {
            "name": "AGENT_REQUESTS",
            "subjects": ["agent.request.>"],
            "description": "Agent execution requests",
        },
        {
            "name": "AGENT_RESPONSES",
            "subjects": ["agent.response.>"],
            "description": "Agent execution responses and results",
        },
        {
            "name": "CONTEXT",
            "subjects": ["context.>"],
            "description": "Context service events (updates, queries)",
        },
        {
            "name": "ORCHESTRATOR_EVENTS",
            "subjects": ["orchestration.>"],
            "description": "Orchestration events (deliberations, results)",
        },
    ]
    
    created_streams = []
    existing_streams = []
    failed_streams = []
    
    for stream_def in streams:
        try:
            # Try to get stream info
            try:
                await js.stream_info(stream_def["name"])
                existing_streams.append(stream_def["name"])
                logger.info(f"✅ Stream already exists: {stream_def['name']}")
            except:
                # Stream doesn't exist, create it
                config = StreamConfig(
                    name=stream_def["name"],
                    subjects=stream_def["subjects"],
                    retention=RetentionPolicy.WORK_QUEUE,
                    discard=DiscardPolicy.OLD,
                    max_age=86400 * 7,  # 7 days
                    max_msgs=1000000,
                )
                await js.add_stream(config)
                created_streams.append(stream_def["name"])
                logger.info(f"✅ Stream created: {stream_def['name']}")
                logger.info(f"   Subjects: {', '.join(stream_def['subjects'])}")
                logger.info(f"   Description: {stream_def['description']}")
        except Exception as e:
            failed_streams.append(stream_def["name"])
            logger.error(f"❌ Error with stream {stream_def['name']}: {e}")
    
    await nc.close()
    
    # Summary
    logger.info("")
    logger.info("=" * 70)
    logger.info("🎯 NATS Streams Initialization Summary:")
    logger.info(f"   Total streams: {len(streams)}")
    logger.info(f"   ✅ Created: {len(created_streams)} ({', '.join(created_streams) if created_streams else 'none'})")
    logger.info(f"   ⏭️  Already exist: {len(existing_streams)} ({', '.join(existing_streams) if existing_streams else 'none'})")
    logger.info(f"   ❌ Failed: {len(failed_streams)} ({', '.join(failed_streams) if failed_streams else 'none'})")
    logger.info("=" * 70)
    
    if failed_streams:
        logger.error("❌ Stream initialization failed")
        return False
    else:
        logger.info("✅ Stream initialization completed successfully")
        return True


if __name__ == "__main__":
    success = asyncio.run(init_streams())
    sys.exit(0 if success else 1)

