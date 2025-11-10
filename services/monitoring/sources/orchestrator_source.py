"""
Orchestrator data source for monitoring.

Fetches councils and agents information via gRPC.
"""
import logging
import os

import grpc

logger = logging.getLogger(__name__)


class OrchestratorSource:
    """Monitor Orchestrator service."""

    def __init__(self):
        self.channel: grpc.aio.Channel | None = None
        self.stub = None
        self.address = os.getenv(
            "ORCHESTRATOR_ADDRESS",
            "orchestrator.swe-ai-fleet.svc.cluster.local:50055"
        )

    async def connect(self):
        """Connect to Orchestrator via gRPC."""
        try:
            self.channel = grpc.aio.insecure_channel(self.address)
            # Wait for channel to be ready (truly async operation)
            await self.channel.channel_ready()
            logger.info(f"✅ Connected to Orchestrator at {self.address}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Orchestrator: {e}")
            self.channel = None

    async def get_councils(self) -> dict:
        """Get active councils and their agents."""
        if not self.channel:
            return {
                "connected": False,
                "error": "Orchestrator not connected"
            }

        try:
            # Import generated gRPC stubs (generated during Docker build)
            from gen import orchestrator_pb2, orchestrator_pb2_grpc

            # Create gRPC stub
            stub = orchestrator_pb2_grpc.OrchestratorServiceStub(self.channel)

            # Call ListCouncils method with include_agents=True to get agent details
            request = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
            response = await stub.ListCouncils(request)

            # Transform response to expected format
            councils_data = []
            for council_info in response.councils:
                # Map role to emoji
                role_emojis = {
                    "DEV": "🧑‍💻",
                    "QA": "🧪",
                    "ARCHITECT": "🏗️",
                    "DEVOPS": "⚙️",
                    "DATA": "📊"
                }

                # Use REAL agents from proto response
                agents = []
                if council_info.agents:
                    # Use agent details from proto
                    for agent_info in council_info.agents:
                        agents.append({
                            "id": agent_info.agent_id,
                            "status": agent_info.status or "idle"
                        })
                else:
                    # Fallback if agents not included (shouldn't happen with include_agents=True)
                    for i in range(council_info.num_agents):
                        agents.append({
                            "id": f"agent-{council_info.role.lower()}-{i+1:03d}",
                            "status": "idle"
                        })

                councils_data.append({
                    "role": council_info.role,
                    "emoji": role_emojis.get(council_info.role, "🤖"),
                    "agents": agents,
                    "status": "active" if council_info.status == "active" else "idle",
                    "model": council_info.model or "unknown",  # Use REAL model from proto
                    "total_agents": council_info.num_agents
                })

            return {
                "connected": True,
                "councils": councils_data,
                "total_councils": len(councils_data),
                "total_agents": sum(c["total_agents"] for c in councils_data)
            }

        except Exception as e:
            logger.error(f"❌ Failed to get councils: {e}")
            return {
                "connected": False,
                "error": str(e)
            }

    async def close(self):
        """Close Orchestrator connection."""
        if self.channel:
            await self.channel.close()
            logger.info("🔌 Closed Orchestrator connection")
