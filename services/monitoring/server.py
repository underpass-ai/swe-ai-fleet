"""
Monitoring Dashboard Backend - FastAPI Server

Real-time monitoring dashboard for SWE AI Fleet.
Aggregates events from NATS, Kubernetes, Ray, Neo4j, and ValKey.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
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
        self.event_history: List[Dict] = []
        self.max_history = 100
        
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


@app.get("/")
async def dashboard():
    """Serve simple HTML dashboard."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SWE AI Fleet - Monitoring Dashboard</title>
        <style>
            body {
                font-family: 'Courier New', monospace;
                background: #0f172a;
                color: #e2e8f0;
                padding: 20px;
                margin: 0;
            }
            h1 {
                color: #3b82f6;
                border-bottom: 2px solid #3b82f6;
                padding-bottom: 10px;
            }
            #events {
                background: #1e293b;
                padding: 20px;
                border-radius: 8px;
                max-height: 600px;
                overflow-y: auto;
            }
            .event {
                margin: 10px 0;
                padding: 10px;
                background: #334155;
                border-left: 4px solid #3b82f6;
                border-radius: 4px;
            }
            .timestamp {
                color: #94a3b8;
                font-size: 0.9em;
            }
            .subject {
                color: #10b981;
                font-weight: bold;
            }
            .status {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                margin-left: 10px;
            }
            .status.connected { background: #10b981; color: white; }
            .status.disconnected { background: #ef4444; color: white; }
        </style>
    </head>
    <body>
        <h1>🎯 SWE AI Fleet - Real-Time Monitoring Dashboard</h1>
        <div>
            Status: <span class="status connected" id="status">Connected</span>
            | Events: <span id="event-count">0</span>
        </div>
        <div id="events"></div>
        
        <script>
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            const eventsDiv = document.getElementById('events');
            const statusSpan = document.getElementById('status');
            const countSpan = document.getElementById('event-count');
            let eventCount = 0;
            
            ws.onopen = () => {
                console.log('✅ WebSocket connected');
                statusSpan.textContent = 'Connected';
                statusSpan.className = 'status connected';
            };
            
            ws.onclose = () => {
                console.log('❌ WebSocket disconnected');
                statusSpan.textContent = 'Disconnected';
                statusSpan.className = 'status disconnected';
            };
            
            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    
                    const eventDiv = document.createElement('div');
                    eventDiv.className = 'event';
                    
                    const timestamp = new Date(data.timestamp).toLocaleTimeString();
                    
                    eventDiv.innerHTML = `
                        <div class="timestamp">${timestamp}</div>
                        <div class="subject">${data.subject || data.type}</div>
                        <pre style="margin: 5px 0; font-size: 0.9em;">${JSON.stringify(data.data, null, 2)}</pre>
                    `;
                    
                    eventsDiv.insertBefore(eventDiv, eventsDiv.firstChild);
                    
                    // Keep only last 50 events in DOM
                    while (eventsDiv.children.length > 50) {
                        eventsDiv.removeChild(eventsDiv.lastChild);
                    }
                    
                    eventCount++;
                    countSpan.textContent = eventCount;
                    
                } catch (e) {
                    console.error('Failed to parse event:', e);
                }
            };
            
            // Heartbeat
            setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send('ping');
                }
            }, 30000);
        </script>
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

