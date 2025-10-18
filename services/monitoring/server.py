"""
Monitoring Dashboard Backend - FastAPI Server

Real-time monitoring dashboard for SWE AI Fleet.
Aggregates events from NATS, Kubernetes, Ray, Neo4j, and ValKey.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import nats
from nats.js import JetStreamContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MonitoringAggregator:
    """Aggregates events from all system sources."""
    
    def __init__(self):
        self.nats_client = None
        self.js: JetStreamContext = None
        self.subscribers: Set[WebSocket] = set()
        self.vllm_streaming_subscribers: Set[WebSocket] = set()  # New: vLLM streaming subscribers
        self.event_history: List[Dict] = []
        self.max_history = 100
        self.active_vllm_streams: Dict[str, Dict] = {}  # New: Track active vLLM streams
        
    async def start(self):
        """Initialize connections to all data sources."""
        logger.info("🚀 Starting Monitoring Aggregator...")
        
        # Connect to NATS
        nats_url = os.getenv("NATS_URL", "nats://nats.swe-ai-fleet.svc.cluster.local:4222")
        try:
            self.nats_client = await nats.connect(nats_url)
            self.js = self.nats_client.jetstream()
            logger.info(f"✅ Connected to NATS: {nats_url}")
            
            # Subscribe to all events
            await self._subscribe_to_events()
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
    
    async def _subscribe_to_events(self):
        """Subscribe to all NATS event streams."""
        subjects = [
            "planning.>",
            "orchestration.>", 
            "context.>",
            "agent.results.>",
            "vllm.streaming.>",
        ]
        
        for subject in subjects:
            try:
                await self.js.subscribe(
                    subject=subject,
                    cb=self._handle_nats_event,
                    durable=f"monitoring-{subject.replace('.>', '').replace('.', '-')}"
                )
                logger.info(f"✅ Subscribed to {subject}")
            except Exception as e:
                logger.warning(f"⚠️  Failed to subscribe to {subject}: {e}")
    
    async def _handle_nats_event(self, msg):
        """Handle incoming NATS event."""
        try:
            subject = msg.subject
            data = msg.data.decode('utf-8')
            
            # Parse JSON if possible
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                payload = {"raw": data}
            
            event = {
                "source": "NATS",
                "type": subject,
                "subject": subject,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "data": payload,
                "metadata": {
                    "sequence": msg.metadata.sequence.stream if msg.metadata else None,
                    "stream": msg.metadata.stream if msg.metadata else None,
                }
            }
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
            
            # Handle vLLM streaming events specially
            if subject.startswith("vllm.streaming."):
                await self.handle_vllm_stream_event(msg)
            else:
                # Broadcast to all connected clients
                await self.broadcast(event)
            
            await msg.ack()
            
        except Exception as e:
            logger.error(f"❌ Error handling NATS event: {e}", exc_info=True)
    
    async def broadcast(self, event: Dict):
        """Broadcast event to all connected WebSocket clients."""
        if not self.subscribers:
            return
        
        message = json.dumps(event)
        disconnected = set()
        
        for websocket in self.subscribers:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.subscribers -= disconnected
    
    async def handle_vllm_stream_event(self, msg):
        """Handle vLLM streaming events from NATS."""
        try:
            subject = msg.subject
            data = msg.data.decode('utf-8')
            
            # Parse the streaming event
            stream_event = json.loads(data)
            
            # Extract agent_id from subject (vllm.streaming.{agent_id})
            agent_id = subject.split('.')[-1]
            
            # Update active streams
            if stream_event["type"] == "vllm_stream_start":
                self.active_vllm_streams[agent_id] = {
                    **stream_event,
                    "start_time": time.time(),
                    "total_tokens": 0,
                    "last_activity": time.time()
                }
            elif stream_event["type"] == "vllm_token":
                if agent_id in self.active_vllm_streams:
                    self.active_vllm_streams[agent_id]["total_tokens"] += 1
                    self.active_vllm_streams[agent_id]["last_activity"] = time.time()
            elif stream_event["type"] == "vllm_stream_complete":
                if agent_id in self.active_vllm_streams:
                    self.active_vllm_streams[agent_id]["is_complete"] = True
                    self.active_vllm_streams[agent_id]["last_activity"] = time.time()
            
            # Broadcast to vLLM streaming subscribers
            await self.broadcast_vllm_stream({
                **stream_event,
                "agent_id": agent_id,
                "timestamp": time.time()
            })
            
        except Exception as e:
            logger.error(f"❌ Error handling vLLM stream event: {e}")
    
    async def broadcast_vllm_stream(self, stream_data: Dict):
        """Broadcast vLLM streaming data to subscribed clients."""
        if not self.vllm_streaming_subscribers:
            return
        
        message = json.dumps(stream_data)
        disconnected = set()
        
        for websocket in self.vllm_streaming_subscribers:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.warning(f"Failed to send vLLM stream to client: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.vllm_streaming_subscribers -= disconnected
    
    def add_vllm_stream(self, agent_id: str, stream_info: Dict):
        """Add a new vLLM stream."""
        self.active_vllm_streams[agent_id] = {
            **stream_info,
            "start_time": time.time(),
            "total_tokens": 0,
            "last_activity": time.time()
        }
    
    def update_vllm_stream(self, agent_id: str, token: str, is_complete: bool = False):
        """Update vLLM stream with new token."""
        if agent_id in self.active_vllm_streams:
            stream = self.active_vllm_streams[agent_id]
            stream["total_tokens"] += 1
            stream["last_activity"] = time.time()
            stream["is_complete"] = is_complete
            
            if is_complete:
                # Stream completed, remove after a delay
                asyncio.create_task(self._remove_completed_stream(agent_id))
    
    async def _remove_completed_stream(self, agent_id: str, delay: int = 30):
        """Remove completed stream after delay."""
        await asyncio.sleep(delay)
        if agent_id in self.active_vllm_streams:
            del self.active_vllm_streams[agent_id]
    
    async def stop(self):
        """Cleanup connections."""
        logger.info("🛑 Stopping Monitoring Aggregator...")
        if self.nats_client:
            await self.nats_client.close()
        logger.info("✅ Stopped")


# Global aggregator instance
aggregator = MonitoringAggregator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    await aggregator.start()
    yield
    # Shutdown
    await aggregator.stop()


# Create FastAPI app
app = FastAPI(
    title="SWE AI Fleet Monitoring Dashboard",
    description="Real-time monitoring dashboard for multi-agent system",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming."""
    await websocket.accept()
    aggregator.subscribers.add(websocket)
    
    logger.info(f"✅ WebSocket client connected (total: {len(aggregator.subscribers)})")
    
    # Send event history to new client
    try:
        for event in aggregator.event_history:
            await websocket.send_text(json.dumps(event))
    except Exception as e:
        logger.error(f"Failed to send history: {e}")
    
    try:
        # Keep connection alive
        while True:
            # Wait for messages from client (ping/pong)
            data = await websocket.receive_text()
            
            # Echo back as heartbeat
            if data == "ping":
                await websocket.send_text("pong")
    
    except WebSocketDisconnect:
        aggregator.subscribers.discard(websocket)
        logger.info(f"✅ WebSocket client disconnected (remaining: {len(aggregator.subscribers)})")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        aggregator.subscribers.discard(websocket)


@app.websocket("/ws/vllm-stream")
async def vllm_streaming_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time vLLM text streaming."""
    await websocket.accept()
    aggregator.vllm_streaming_subscribers.add(websocket)
    
    logger.info(f"✅ vLLM Streaming client connected (total: {len(aggregator.vllm_streaming_subscribers)})")
    
    # Send current active streams to new client
    try:
        for agent_id, stream_info in aggregator.active_vllm_streams.items():
            stream_event = {
                "type": "vllm_stream_active",
                "agent_id": agent_id,
                "stream_info": stream_info,
                "timestamp": time.time()
            }
            await websocket.send_text(json.dumps(stream_event))
    except Exception as e:
        logger.error(f"Failed to send active streams: {e}")
    
    try:
        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_text()
            
            # Handle client requests
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("subscribe:"):
                # Client wants to subscribe to specific agent
                agent_id = data.split(":", 1)[1]
                logger.info(f"Client subscribed to agent {agent_id}")
                await websocket.send_text(json.dumps({
                    "type": "subscription_confirmed",
                    "agent_id": agent_id,
                    "timestamp": time.time()
                }))
            elif data.startswith("unsubscribe:"):
                # Client wants to unsubscribe from specific agent
                agent_id = data.split(":", 1)[1]
                logger.info(f"Client unsubscribed from agent {agent_id}")
                await websocket.send_text(json.dumps({
                    "type": "unsubscription_confirmed", 
                    "agent_id": agent_id,
                    "timestamp": time.time()
                }))
    
    except WebSocketDisconnect:
        aggregator.vllm_streaming_subscribers.discard(websocket)
        logger.info(f"✅ vLLM Streaming client disconnected (remaining: {len(aggregator.vllm_streaming_subscribers)})")
    except Exception as e:
        logger.error(f"vLLM Streaming WebSocket error: {e}")
        aggregator.vllm_streaming_subscribers.discard(websocket)


@app.get("/api/events")
async def get_events(limit: int = 50):
    """Get recent events from history."""
    return {
        "events": aggregator.event_history[-limit:],
        "total": len(aggregator.event_history)
    }


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "nats_connected": aggregator.nats_client is not None,
        "active_subscribers": len(aggregator.subscribers),
        "events_cached": len(aggregator.event_history)
    }


@app.get("/api/system/status")
async def get_system_status():
    """Get status of all system services."""
    try:
        # Check NATS
        nats_status = "running" if aggregator.nats_client is not None else "disconnected"
        
        # Check Orchestrator
        try:
            from sources.orchestrator_source import OrchestratorSource
            orchestrator_source = OrchestratorSource()
            await orchestrator_source.connect()
            orchestrator_status = "running" if orchestrator_source.channel else "disconnected"
            await orchestrator_source.close()
        except:
            orchestrator_status = "disconnected"
        
        # Check Context Service (Neo4j + ValKey)
        context_status = "running"
        try:
            from sources.neo4j_source import Neo4jSource
            neo4j_source = Neo4jSource()
            await neo4j_source.connect()
            if not neo4j_source.driver:
                context_status = "disconnected"
            await neo4j_source.close()
        except:
            context_status = "disconnected"
        
        # Check Ray Executor
        try:
            from sources.ray_source import RaySource
            ray_source = RaySource()
            await ray_source.connect()
            ray_status = "running" if ray_source.stub else "disconnected"
            await ray_source.close()
        except:
            ray_status = "disconnected"
        
        return {
            "services": [
                {
                    "name": "Monitoring Dashboard",
                    "status": "running",
                    "icon": "Activity"
                },
                {
                    "name": "NATS JetStream", 
                    "status": nats_status,
                    "icon": "Server"
                },
                {
                    "name": "Orchestrator",
                    "status": orchestrator_status,
                    "icon": "Cpu"
                },
                {
                    "name": "Context Service",
                    "status": context_status,
                    "icon": "Database"
                },
                {
                    "name": "Ray Executor",
                    "status": ray_status,
                    "icon": "Zap"
                }
            ]
        }
    except Exception as e:
        logger.error(f"❌ Failed to get system status: {e}")
        return {
            "services": [
                {"name": "Monitoring Dashboard", "status": "running", "icon": "Activity"},
                {"name": "NATS JetStream", "status": "error", "icon": "Server"},
                {"name": "Orchestrator", "status": "error", "icon": "Cpu"},
                {"name": "Context Service", "status": "error", "icon": "Database"},
                {"name": "Ray Executor", "status": "error", "icon": "Zap"}
            ],
            "error": str(e)
        }


@app.get("/api/councils")
async def get_councils():
    """Get active councils and their agents from Orchestrator."""
    from sources.orchestrator_source import OrchestratorSource
    
    source = OrchestratorSource()
    await source.connect()
    councils_data = await source.get_councils()
    await source.close()
    
    return councils_data


@app.get("/api/neo4j/stats")
async def get_neo4j_stats():
    """Get Neo4j graph statistics."""
    from sources.neo4j_source import Neo4jSource
    
    source = Neo4jSource()
    await source.connect()
    stats = await source.get_graph_stats()
    await source.close()
    
    return stats


@app.get("/api/valkey/stats")
async def get_valkey_stats():
    """Get ValKey cache statistics."""
    from sources.valkey_source import ValKeySource
    
    source = ValKeySource()
    await source.connect()
    stats = await source.get_cache_stats()
    await source.close()
    
    return stats


@app.get("/api/ray/executor")
async def get_ray_executor_stats():
    """Get Ray Executor Service statistics."""
    from sources.ray_source import RaySource
    
    source = RaySource()
    await source.connect()
    stats = await source.get_executor_stats()
    await source.close()
    
    return stats


@app.get("/api/ray/cluster")
async def get_ray_cluster_stats():
    """Get Ray Cluster statistics."""
    from sources.ray_source import RaySource
    
    source = RaySource()
    await source.connect()
    stats = await source.get_cluster_stats()
    await source.close()
    
    return stats


@app.get("/api/ray/jobs")
async def get_ray_active_jobs():
    """Get active Ray jobs."""
    from sources.ray_source import RaySource
    
    source = RaySource()
    await source.connect()
    jobs = await source.get_active_jobs()
    await source.close()
    
    return jobs


@app.get("/api/vllm/active-streams")
async def get_active_vllm_streams():
    """Get currently active vLLM streams from Ray Executor."""
    from sources.ray_source import RaySource
    
    source = RaySource()
    await source.connect()
    
    # Get active jobs from Ray
    jobs_data = await source.get_active_jobs()
    await source.close()
    
    active_streams = {}
    
    # Convert Ray jobs to vLLM streams
    for job in jobs_data.get("active_jobs", []):
        agent_id = job.get("job_id", "unknown")
        active_streams[agent_id] = {
            "agent_id": agent_id,
            "stream_info": {
                "task_description": f"Task: {job.get('task_id', 'Unknown')}",
                "role": job.get("role", "UNKNOWN"),
                "status": "streaming" if job.get("status") == "RUNNING" else "idle",
                "model": "Qwen/Qwen3-0.6B"
            },
            "start_time": time.time() - job.get("runtime_seconds", 0),
            "total_tokens": 0,
            "last_activity": time.time(),
            "is_complete": job.get("status") != "RUNNING"
        }
    
    return {
        "active_streams": active_streams,
        "total_active": len(active_streams),
        "timestamp": time.time()
    }


# ====== ADMIN OPERATIONS ======

@app.post("/api/admin/nats/clear")
async def clear_nats_streams():
    """Clear all NATS JetStream streams."""
    try:
        if not aggregator.js:
            return {"status": "error", "message": "NATS not connected"}
        
        # Get all streams
        streams_info = await aggregator.js.streams_info()
        deleted_streams = []
        
        for stream_info in streams_info:
            stream_name = stream_info.config.name
            try:
                await aggregator.js.delete_stream(stream_name)
                deleted_streams.append(stream_name)
                logger.info(f"🗑️  Deleted NATS stream: {stream_name}")
            except Exception as e:
                logger.error(f"Failed to delete stream {stream_name}: {e}")
        
        return {
            "status": "success",
            "message": f"Deleted {len(deleted_streams)} NATS streams",
            "deleted_streams": deleted_streams
        }
    except Exception as e:
        logger.error(f"❌ Error clearing NATS streams: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/ray/kill-jobs")
async def kill_ray_jobs():
    """Kill all active Ray jobs."""
    try:
        from sources.ray_source import RaySource
        
        source = RaySource()
        await source.connect()
        
        # Get active jobs
        jobs_data = await source.get_active_jobs()
        jobs = jobs_data.get("jobs", []) if isinstance(jobs_data, dict) else []
        
        killed_jobs = []
        for job in jobs:
            job_id = job.get("job_id")
            if job_id:
                # Note: Ray job killing would need to be implemented in ray_source
                killed_jobs.append(job_id)
                logger.info(f"🛑 Killed Ray job: {job_id}")
        
        await source.close()
        
        return {
            "status": "success",
            "message": f"Killed {len(killed_jobs)} Ray jobs",
            "killed_jobs": killed_jobs
        }
    except Exception as e:
        logger.error(f"❌ Error killing Ray jobs: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/valkey/clear")
async def clear_valkey():
    """Clear all ValKey data."""
    try:
        from sources.valkey_source import ValKeySource
        
        source = ValKeySource()
        await source.connect()
        
        # Clear all keys
        await source.client.flushall()
        logger.info("🗑️  Cleared all ValKey data")
        
        await source.close()
        
        return {
            "status": "success",
            "message": "ValKey cleared successfully"
        }
    except Exception as e:
        logger.error(f"❌ Error clearing ValKey: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/neo4j/clear")
async def clear_neo4j():
    """Clear all Neo4j data."""
    try:
        from sources.neo4j_source import Neo4jSource
        
        source = Neo4jSource()
        await source.connect()
        
        # Clear all nodes and relationships
        async with source.driver.session() as session:
            result = await session.run("MATCH (n) DETACH DELETE n")
            summary = await result.consume()
            nodes_deleted = summary.counters.nodes_deleted
            rels_deleted = summary.counters.relationships_deleted
        
        logger.info(f"🗑️  Cleared Neo4j: {nodes_deleted} nodes, {rels_deleted} relationships")
        
        await source.close()
        
        return {
            "status": "success",
            "message": f"Neo4j cleared: {nodes_deleted} nodes, {rels_deleted} relationships deleted"
        }
    except Exception as e:
        logger.error(f"❌ Error clearing Neo4j: {e}")
        return {"status": "error", "message": str(e)}


@app.post("/api/admin/test-cases/execute")
async def execute_test_case(test_case: str):
    """Execute a predefined test case (basic, medium, complex) - triggers deliberation directly."""
    try:
        # Define test cases
        test_cases = {
            "basic": {
                "title": "Add login button to homepage",
                "description": "Create a simple login button on the main page",
                "complexity": "basic",
                "estimated_hours": 2,
                "roles": ["DEV", "QA"]
            },
            "medium": {
                "title": "Implement user authentication system",
                "description": "Complete OAuth2 authentication with Google and GitHub providers, including JWT token management and session handling",
                "complexity": "medium",
                "estimated_hours": 8,
                "roles": ["ARCHITECT", "DEV", "QA"]
            },
            "complex": {
                "title": "Build real-time collaborative editing system",
                "description": "Implement a complete real-time collaborative editing system with WebSocket synchronization, conflict resolution, operational transforms, presence indicators, and version history",
                "complexity": "complex",
                "estimated_hours": 40,
                "roles": ["ARCHITECT", "DEV", "QA", "DEVOPS"]
            }
        }
        
        if test_case not in test_cases:
            raise HTTPException(status_code=400, detail=f"Invalid test case: {test_case}")
        
        case = test_cases[test_case]
        story_id = f"test-{test_case}-{int(time.time())}"
        plan_id = f"plan-{story_id}"
        
        # Publish PLAN APPROVAL directly (skip story creation for testing)
        if aggregator.js:
            # This event triggers deliberations in the Orchestrator
            event = {
                "type": "plan.approved",
                "story_id": story_id,
                "plan_id": plan_id,
                "approved_by": "backoffice-test",
                "roles": case["roles"],
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "title": case["title"],
                "description": case["description"],
                "complexity": case["complexity"]
            }
            
            await aggregator.js.publish(
                "planning.plan.approved",
                json.dumps(event).encode()
            )
            
            logger.info(f"🚀 Executed test case: {test_case} → Deliberation triggered")
            logger.info(f"   Story ID: {story_id}")
            logger.info(f"   Plan ID: {plan_id}")
            logger.info(f"   Roles: {', '.join(case['roles'])}")
            
            return {
                "status": "success",
                "message": f"Test case '{test_case}' submitted - Deliberation triggered for {len(case['roles'])} roles",
                "test_case": case,
                "story_id": story_id,
                "plan_id": plan_id,
                "roles": case["roles"]
            }
        else:
            return {
                "status": "error",
                "message": "NATS not connected"
            }
    except Exception as e:
        logger.error(f"❌ Error executing test case: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}


# Serve React SPA
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static files (JS, CSS, assets)
    app.mount("/assets", StaticFiles(directory=frontend_dist / "assets"), name="assets")
    
    @app.get("/")
    async def serve_spa():
        """Serve React SPA index.html"""
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"error": "Frontend not built"}
else:
    logger.warning("⚠️  Frontend dist directory not found, serving fallback HTML")
    
    @app.get("/")
    async def dashboard():
        """Serve fallback HTML dashboard."""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>SWE AI Fleet - Monitoring Dashboard</title>
            <style>
                body { font-family: monospace; background: #0f172a; color: #e2e8f0; padding: 20px; }
                h1 { color: #3b82f6; }
                .status { display: inline-block; padding: 4px 8px; border-radius: 4px; }
                .status.connected { background: #10b981; color: white; }
            </style>
        </head>
        <body>
            <h1>🎯 SWE AI Fleet - Monitoring Dashboard</h1>
            <p>⚠️  React frontend not built. Run: cd frontend && npm install && npm run build</p>
            <p>WebSocket: <span class="status connected" id="status">Connecting...</span></p>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"🚀 Starting Monitoring Dashboard on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

