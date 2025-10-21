#!/usr/bin/env python3
"""
Delete NATS JetStream Streams.

Deletes all streams for cleanup/reset.
"""

import asyncio
import logging
import os
import sys

import nats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def delete_streams():
    """Delete all NATS JetStream streams."""
    
    nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
    
    logger.info(f"🗑️  Deleting NATS JetStream streams at {nats_url}")
    
    # Connect to NATS
    try:
        nc = await nats.connect(nats_url)
        js = nc.jetstream()
        logger.info("✅ Connected to NATS")
    except Exception as e:
        logger.error(f"❌ Failed to connect to NATS: {e}")
        return False
    
    deleted_streams = []
    failed_streams = []
    
    try:
        # Get all streams
        streams_info = await js.streams_info()
        
        logger.info(f"📊 Found {len(streams_info)} streams")
        
        for stream_info in streams_info:
            stream_name = stream_info.config.name
            try:
                await js.delete_stream(stream_name)
                deleted_streams.append(stream_name)
                logger.info(f"✅ Deleted stream: {stream_name}")
            except Exception as e:
                failed_streams.append(stream_name)
                logger.error(f"❌ Failed to delete stream {stream_name}: {e}")
        
        await nc.close()
        
        # Summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("🎯 NATS Streams Deletion Summary:")
        logger.info(f"   Total streams: {len(streams_info)}")
        logger.info(f"   ✅ Deleted: {len(deleted_streams)} ({', '.join(deleted_streams) if deleted_streams else 'none'})")
        logger.info(f"   ❌ Failed: {len(failed_streams)} ({', '.join(failed_streams) if failed_streams else 'none'})")
        logger.info("=" * 70)
        
        if failed_streams:
            logger.error("❌ Stream deletion failed")
            return False
        else:
            logger.info("✅ Stream deletion completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        await nc.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(delete_streams())
    sys.exit(0 if success else 1)

