#!/usr/bin/env python3
"""
Delete Councils - Standalone script to delete all councils.

Usage in Kubernetes Job.
"""

import asyncio
import logging
import os
import sys

import grpc

# Import generated gRPC code (generated during Docker build in /app/gen)
from gen import orchestrator_pb2, orchestrator_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def delete_councils():
    """Delete all councils."""
    
    # Get configuration
    orchestrator_address = os.getenv(
        "ORCHESTRATOR_ADDRESS",
        "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
    )
    
    # Roles to delete
    roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
    
    logger.info(f"🗑️  Deleting councils from {orchestrator_address}")
    logger.info(f"   Roles: {roles}")
    
    # Connect to Orchestrator
    channel = grpc.aio.insecure_channel(orchestrator_address)
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    try:
        # Wait for Orchestrator to be ready
        logger.info("⏳ Waiting for Orchestrator to be ready...")
        max_retries = 10
        for i in range(max_retries):
            try:
                status_request = orchestrator_pb2.GetStatusRequest(include_stats=False)
                status_response = await stub.GetStatus(status_request)
                logger.info(f"✅ Orchestrator is ready (status: {status_response.status})")
                break
            except Exception as e:
                if i < max_retries - 1:
                    logger.info(f"   Orchestrator not ready yet, retrying... ({i+1}/{max_retries})")
                    await asyncio.sleep(2)
                else:
                    logger.error(f"❌ Orchestrator not ready after {max_retries} retries: {e}")
                    await channel.close()
                    return False
        
        # Delete councils
        deleted_councils = []
        skipped_councils = []
        failed_councils = []
        
        for role in roles:
            try:
                logger.info(f"🗑️  Deleting council for role: {role}")
                
                request = orchestrator_pb2.DeleteCouncilRequest(role=role)
                await stub.DeleteCouncil(request)
                
                deleted_councils.append(role)
                logger.info(f"✅ Council deleted: {role}")
                
            except grpc.aio.AioRpcError as e:
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    skipped_councils.append(role)
                    logger.info(f"⏭️  Council not found (already deleted?): {role}")
                else:
                    failed_councils.append(role)
                    logger.error(f"❌ Failed to delete council {role}: {e.details()}")
            except Exception as e:
                failed_councils.append(role)
                logger.error(f"❌ Unexpected error deleting {role}: {e}")
        
        # Summary
        logger.info("")
        logger.info("═" * 63)
        logger.info("🎯 Council Deletion Summary:")
        logger.info(f"   Total roles: {len(roles)}")
        logger.info(f"   ✅ Deleted: {len(deleted_councils)} ({', '.join(deleted_councils) if deleted_councils else ''})")
        logger.info(f"   ⏭️  Skipped: {len(skipped_councils)} ({', '.join(skipped_councils) if skipped_councils else ''})")
        logger.info(f"   ❌ Failed: {len(failed_councils)} ({', '.join(failed_councils) if failed_councils else ''})")
        logger.info("═" * 63)
        
        success = len(failed_councils) == 0
        if success:
            logger.info("🎉 Council deletion completed successfully")
        else:
            logger.error("❌ Council deletion failed")
        
        await channel.close()
        return success
        
    except Exception as e:
        logger.error(f"❌ Fatal error during deletion: {e}", exc_info=True)
        await channel.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(delete_councils())
    sys.exit(0 if success else 1)

