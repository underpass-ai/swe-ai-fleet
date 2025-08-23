from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, List
import json
from app.routers.auth import get_current_user_from_token
from datetime import datetime

router = APIRouter()

# Store active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.active_connections:
            self.active_connections[project_id] = []
        self.active_connections[project_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.active_connections:
            self.active_connections[project_id].remove(websocket)
            if not self.active_connections[project_id]:
                del self.active_connections[project_id]
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast_to_project(self, message: str, project_id: int):
        if project_id in self.active_connections:
            for connection in self.active_connections[project_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Remove broken connections
                    self.active_connections[project_id].remove(connection)

manager = ConnectionManager()

async def get_current_user_from_token_ws(token: str):
    # Simplified token validation for WebSocket
    # In production, you should implement proper JWT validation
    try:
        # This is a simplified version - implement proper JWT validation
        return {"username": "user", "id": 1}  # Placeholder
    except:
        return None

@router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: int):
    await manager.connect(websocket, project_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle different message types
            message_type = message_data.get("type")
            
            if message_type == "task_update":
                # Broadcast task updates to all team members
                await manager.broadcast_to_project(
                    json.dumps({
                        "type": "task_update",
                        "data": message_data.get("data"),
                        "timestamp": message_data.get("timestamp")
                    }),
                    project_id
                )
            
            elif message_type == "comment_added":
                # Broadcast new comments
                await manager.broadcast_to_project(
                    json.dumps({
                        "type": "comment_added",
                        "data": message_data.get("data"),
                        "timestamp": message_data.get("timestamp")
                    }),
                    project_id
                )
            
            elif message_type == "sprint_update":
                # Broadcast sprint updates
                await manager.broadcast_to_project(
                    json.dumps({
                        "type": "sprint_update",
                        "data": message_data.get("data"),
                        "timestamp": message_data.get("timestamp")
                    }),
                    project_id
                )
            
            elif message_type == "team_notification":
                # Send team notifications
                await manager.broadcast_to_project(
                    json.dumps({
                        "type": "team_notification",
                        "data": message_data.get("data"),
                        "timestamp": message_data.get("timestamp")
                    }),
                    project_id
                )
            
            elif message_type == "ping":
                # Respond to ping with pong
                await manager.send_personal_message(
                    json.dumps({"type": "pong", "timestamp": message_data.get("timestamp")}),
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, project_id)
    except Exception as e:
        # Log error and disconnect
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, project_id)

# Helper function to send notifications to project team
async def send_project_notification(project_id: int, notification_type: str, data: dict):
    message = {
        "type": "team_notification",
        "data": {
            "notification_type": notification_type,
            "content": data
        },
        "timestamp": str(datetime.utcnow())
    }
    await manager.broadcast_to_project(json.dumps(message), project_id)

# Helper function to send task updates
async def send_task_update(project_id: int, task_data: dict):
    message = {
        "type": "task_update",
        "data": task_data,
        "timestamp": str(datetime.utcnow())
    }
    await manager.broadcast_to_project(json.dumps(message), project_id)