#!/usr/bin/env python3
"""
Trigger Deliberation - Job to trigger a real deliberation in the Orchestrator.

This script calls the Orchestrator's Deliberate RPC endpoint with a real task
and waits for the result.
"""

import asyncio
import logging
import os
import sys
import time

import grpc

# Import generated gRPC code (generated during Docker build in /app/gen)
from gen import orchestrator_pb2, orchestrator_pb2_grpc

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


async def trigger_deliberation():
    """Trigger a real deliberation."""
    
    # Get configuration
    orchestrator_address = os.getenv(
        "ORCHESTRATOR_ADDRESS",
        "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
    )
    
    role = os.getenv("ROLE", "DEV")
    num_rounds = int(os.getenv("NUM_ROUNDS", "1"))
    timeout_seconds = int(os.getenv("TIMEOUT_SECONDS", "120"))
    
    logger.info(f"🎯 Triggering deliberation on {orchestrator_address}")
    logger.info(f"   Role: {role}")
    logger.info(f"   Rounds: {num_rounds}")
    logger.info(f"   Timeout: {timeout_seconds}s")
    
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
        
        # Create a real deliberation task
        logger.info("")
        logger.info("=" * 70)
        logger.info("🚀 Creating Deliberation Task")
        logger.info("=" * 70)
        
        # Create task description
        task_description = """
Review the authentication module for security vulnerabilities and best practices.

Focus Areas:
1. Check for SQL injection vulnerabilities in database.py
2. Verify password hashing is using bcrypt with proper salt in auth.py
3. Ensure session management follows OWASP guidelines in session.py
4. Review error handling to prevent information leakage
5. Validate input sanitization across all modules

Files to Review:
- auth.py: Main authentication logic
- session.py: Session management
- database.py: Database queries
- tests/test_auth.py: Unit tests

Expected Output:
- List of identified security vulnerabilities with severity levels
- Specific code improvements with example implementations
- Compliance assessment against OWASP Top 10
- Error handling recommendations
        """.strip()
        
        # Create request (constraints are optional)
        request = orchestrator_pb2.DeliberateRequest(
            task_description=task_description,
            role=role,
            rounds=num_rounds,
            num_agents=3  # 3 agents in the council
        )
        
        logger.info(f"Role: {role}")
        logger.info(f"Rounds: {num_rounds}")
        logger.info(f"Agents: 3")
        logger.info(f"Description: {task_description[:100]}...")
        logger.info("")
        
        # Trigger deliberation
        logger.info("🎭 Calling Orchestrator.Deliberate()...")
        start_time = time.time()
        
        try:
            response = await stub.Deliberate(request, timeout=timeout_seconds + 30)
            
            elapsed = time.time() - start_time
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("📊 Deliberation Response")
            logger.info("=" * 70)
            logger.info(f"Winner ID: {response.winner_id}")
            logger.info(f"Duration: {response.duration_ms}ms")
            logger.info(f"Total Results: {len(response.results)}")
            logger.info(f"Elapsed Time: {elapsed:.2f}s")
            
            if response.results:
                logger.info("")
                logger.info("📝 Top Results:")
                for i, result in enumerate(response.results[:3], 1):  # Show top 3
                    logger.info(f"  #{i} Agent: {result.agent_id}")
                    logger.info(f"      Score: {result.score}")
                    if result.proposal:
                        logger.info(f"      Proposal: {result.proposal.content[:150]}...")
            
            if response.metadata:
                logger.info("")
                logger.info("📊 Metadata:")
                logger.info(f"  Version: {response.metadata.version}")
                logger.info(f"  Timestamp: {response.metadata.timestamp}")
            
            logger.info("=" * 70)
            
            success = len(response.results) > 0
            if success:
                logger.info("🎉 Deliberation completed successfully!")
            else:
                logger.warning("⚠️  Deliberation returned no results")
            
            await channel.close()
            return success
            
        except grpc.aio.AioRpcError as e:
            logger.error(f"❌ gRPC Error: {e.code()}: {e.details()}")
            await channel.close()
            return False
        
    except Exception as e:
        logger.error(f"❌ Fatal error during deliberation: {e}", exc_info=True)
        await channel.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(trigger_deliberation())
    sys.exit(0 if success else 1)

