#!/usr/bin/env python3
"""
Initialize Councils - Standalone script for council auto-initialization.

This script creates councils for all configured roles via gRPC CreateCouncil calls.
Keeps initialization logic separate from server startup for cleaner architecture.
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


async def init_councils():
    """Initialize councils for all roles."""
    
    # Get configuration
    orchestrator_address = os.getenv(
        "ORCHESTRATOR_ADDRESS",
        "localhost:50055"
    )
    
    # Roles to initialize
    roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
    num_agents_per_council = int(os.getenv("NUM_AGENTS_PER_COUNCIL", "3"))
    
    logger.info(f"🤖 Initializing councils on {orchestrator_address}")
    logger.info(f"   Roles: {roles}")
    logger.info(f"   Agents per council: {num_agents_per_council}")
    
    # Connect to Orchestrator
    channel = grpc.aio.insecure_channel(orchestrator_address)
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    # Wait for Orchestrator to be ready
    logger.info("⏳ Waiting for Orchestrator to be ready...")
    max_retries = 30
    for i in range(max_retries):
        try:
            # Try to get status
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
    
    # Create councils
    created_councils = []
    failed_councils = []
    
    for role in roles:
        try:
            logger.info(f"📤 Creating council for role: {role}")
            
            # Build council config
            council_config = orchestrator_pb2.CouncilConfig(
                deliberation_rounds=1,
                enable_peer_review=True,
                model_profile="Qwen/Qwen3-0.6B",
                agent_type="RAY_VLLM"  # Use Ray-based vLLM agents
            )
            
            # Create council request
            request = orchestrator_pb2.CreateCouncilRequest(
                role=role,
                num_agents=num_agents_per_council,
                config=council_config
            )
            
            # Call CreateCouncil RPC
            response = await stub.CreateCouncil(request)
            
            if response.agents_created > 0:
                created_councils.append(role)
                logger.info(
                    f"✅ Council created: {role} "
                    f"(council_id: {response.council_id}, "
                    f"agents: {response.agents_created})"
                )
                logger.info(f"   Agent IDs: {', '.join(response.agent_ids)}")
            else:
                failed_councils.append(role)
                logger.error(f"❌ Failed to create council for {role}: No agents created")
                
        except grpc.aio.AioRpcError as e:
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                created_councils.append(role)
                logger.info(f"✅ Council already exists: {role} (skipping)")
            else:
                failed_councils.append(role)
                logger.error(f"❌ Failed to create council for {role}: {e.details()}")
        except Exception as e:
            failed_councils.append(role)
            logger.error(f"❌ Failed to create council for {role}: {e}", exc_info=True)
    
    # Summary
    logger.info("")
    logger.info("═══════════════════════════════════════════════════════════")
    logger.info(f"🎯 Council Initialization Summary:")
    logger.info(f"   Total roles: {len(roles)}")
    logger.info(f"   ✅ Created: {len(created_councils)} ({', '.join(created_councils)})")
    if failed_councils:
        logger.info(f"   ❌ Failed: {len(failed_councils)} ({', '.join(failed_councils)})")
    logger.info(f"   Total agents: {len(created_councils) * num_agents_per_council}")
    logger.info("═══════════════════════════════════════════════════════════")
    
    # Close connection
    await channel.close()
    
    # Return success if at least one council was created
    return len(created_councils) > 0


async def verify_councils():
    """Verify councils were created successfully."""
    orchestrator_address = os.getenv(
        "ORCHESTRATOR_ADDRESS",
        "localhost:50055"
    )
    
    channel = grpc.aio.insecure_channel(orchestrator_address)
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    try:
        logger.info("🔍 Verifying created councils...")
        
        request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
        response = await stub.ListCouncils(request)
        
        logger.info(f"📊 Active Councils: {len(response.councils)}")
        
        for council in response.councils:
            logger.info(
                f"   • {council.role}: {council.num_agents} agents "
                f"(status: {council.status}, model: {council.model})"
            )
            if council.agents:
                agent_ids = [agent.agent_id for agent in council.agents]
                logger.info(f"     Agents: {', '.join(agent_ids)}")
        
        await channel.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to verify councils: {e}")
        await channel.close()
        return False


async def main():
    """Main entry point."""
    logger.info("🚀 Council Initialization Script")
    logger.info("")
    
    # Initialize councils
    success = await init_councils()
    
    if not success:
        logger.error("❌ Council initialization failed")
        sys.exit(1)
    
    # Wait a bit for councils to be fully ready
    await asyncio.sleep(2)
    
    # Verify
    verified = await verify_councils()
    
    if verified:
        logger.info("")
        logger.info("✅ Council initialization completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Council verification failed")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

