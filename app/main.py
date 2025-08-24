from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import random

from .context import ContextAssembler
from .policy import PromptScopePolicy

# -----------------------------
# App setup
# -----------------------------
app = FastAPI(title="Agile Team Simulator", version="0.1.0")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (frontend)
STATIC_DIR = Path("/workspace/static").resolve()
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# -----------------------------
# Domain models
# -----------------------------
ROLES: List[str] = [
    "Product Owner",
    "Project Manager",
    "Architect",
    "QA",
    "DevOps",
    "Backend Developer",
    "Frontend Developer",
]


class Message(BaseModel):
    id: str
    sender: str
    role: str
    text: str
    timestamp: str


class GoalInput(BaseModel):
    title: str
    description: str = ""
    epic: str = "General"


class BacklogItem(BaseModel):
    id: str
    title: str
    description: str
    status: str
    created_at: str
    epic: str
    events: List[str]


# -----------------------------
# In-memory state
# -----------------------------
class State:
    def __init__(self) -> None:
        self.backlog_items: Dict[str, BacklogItem] = {}
        self.messages: List[Message] = []
        self.lock = asyncio.Lock()


STATE = State()

# Storage (Redis for context, Neo4j for decisions)
from .storage import Storage
STORAGE = Storage()

POLICY = PromptScopePolicy()
ASSEMBLER = ContextAssembler(STORAGE, POLICY)

# LLM calls/responses
class LLMCall(BaseModel):
    session_id: str
    task_id: str | None = None
    requester: str
    content: str
    meta: Dict[str, Any] = {}


class LLMResponse(BaseModel):
    session_id: str
    task_id: str | None = None
    responder: str
    content: str
    meta: Dict[str, Any] = {}


# -----------------------------
# WebSocket connection manager
# -----------------------------
class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        dead: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json({"type": event_type, "payload": payload})
            except Exception:
                dead.append(connection)
        for d in dead:
            await self.disconnect(d)


MANAGER = ConnectionManager()


# -----------------------------
# Helpers
# -----------------------------

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


async def push_chat(sender: str, role: str, text: str) -> Message:
    message = Message(id=str(uuid.uuid4()), sender=sender, role=role, text=text, timestamp=now_iso())
    async with STATE.lock:
        STATE.messages.append(message)
        await STORAGE.save_messages([m.dict() for m in STATE.messages])
    await MANAGER.broadcast("chat", message.dict())
    # Log generic communication as decision context
    await STORAGE.log_decision(role=role, sender=sender, action=f"message: {text[:120]}", task_id=None, task_title=None, epic=None, timestamp=message.timestamp)
    return message


async def push_backlog_update(item: BacklogItem) -> None:
    await MANAGER.broadcast("backlog_update", {"item": item.dict()})
    # Persist entire backlog for simplicity
    async with STATE.lock:
        await STORAGE.save_backlog({k: v.dict() for k, v in STATE.backlog_items.items()})


async def simulate_workflow(item_id: str) -> None:
    role_sequence = [
        "Project Manager",
        "Architect",
        "Backend Developer",
        "Frontend Developer",
        "QA",
        "DevOps",
    ]

    for role in role_sequence:
        await asyncio.sleep(random.uniform(0.5, 1.8))
        async with STATE.lock:
            item = STATE.backlog_items.get(item_id)
            if not item:
                return
            event_text = f"{role} progressed the work on '{item.title}'."
            item.events.append(event_text)
            item.status = f"In Progress: {role}"
        await push_chat(sender=role, role=role, text=event_text)
        await STORAGE.log_decision(role=role, sender=role, action=event_text, task_id=item.id, task_title=item.title, epic=item.epic, timestamp=now_iso())
        await push_backlog_update(item)

    await asyncio.sleep(random.uniform(0.5, 1.5))
    async with STATE.lock:
        item = STATE.backlog_items.get(item_id)
        if not item:
            return
        item.status = "Done"
        item.events.append("Work completed across roles.")
    await push_chat(sender="System", role="System", text=f"Backlog item '{item.title}' completed.")
    await STORAGE.log_decision(role="System", sender="System", action=f"completed: {item.title}", task_id=item.id, task_title=item.title, epic=item.epic, timestamp=now_iso())
    await push_backlog_update(item)


# -----------------------------
# Routes
# -----------------------------
@app.on_event("startup")
async def on_startup() -> None:
    await STORAGE.connect()
    try:
        data = await STORAGE.load_state()
        async with STATE.lock:
            STATE.backlog_items = {
                k: BacklogItem(**v) for k, v in (data.get("backlog") or {}).items()
            }
            STATE.messages = [Message(**m) for m in (data.get("messages") or [])]
    except Exception:
        # proceed with empty state
        pass


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await STORAGE.close()


@app.get("/")
async def index(_: Request):
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse({"message": "Frontend not built yet."}, status_code=200)
    return FileResponse(str(index_file))


@app.get("/roles")
async def get_roles():
    return {"roles": ROLES}


@app.get("/state")
async def get_state():
    async with STATE.lock:
        backlog = [item.dict() for item in STATE.backlog_items.values()]
        messages = [m.dict() for m in STATE.messages[-200:]]
    return {"roles": ROLES, "backlog": backlog, "messages": messages}


class MessageInput(BaseModel):
    sender: str
    role: str
    text: str


@app.post("/message")
async def post_message(msg: MessageInput):
    if msg.role not in ROLES and msg.role != "System":
        return JSONResponse({"error": "Unknown role"}, status_code=400)
    message = await push_chat(sender=msg.sender, role=msg.role, text=msg.text)
    return message.dict()


@app.post("/goals")
async def post_goal(goal: GoalInput):
    item = BacklogItem(
        id=str(uuid.uuid4()),
        title=goal.title.strip(),
        description=goal.description.strip(),
        status="New",
        created_at=now_iso(),
        epic=goal.epic.strip() or "General",
        events=["Created by Product Owner"],
    )
    async with STATE.lock:
        STATE.backlog_items[item.id] = item
        await STORAGE.save_backlog({k: v.dict() for k, v in STATE.backlog_items.items()})
    await push_chat(sender="Product Owner", role="Product Owner", text=f"Proposed goal: {item.title} (Epic: {item.epic})")
    await STORAGE.log_decision(role="Product Owner", sender="Product Owner", action=f"created: {item.title}", task_id=item.id, task_title=item.title, epic=item.epic, timestamp=now_iso())
    await push_backlog_update(item)
    # Start simulated workflow
    asyncio.create_task(simulate_workflow(item.id))
    return item.dict()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await MANAGER.connect(websocket)
    try:
        # Send initial state snapshot
        async with STATE.lock:
            snapshot = {
                "roles": ROLES,
                "backlog": [item.dict() for item in STATE.backlog_items.values()],
                "messages": [m.dict() for m in STATE.messages[-200:]],
            }
        await websocket.send_json({"type": "init", "payload": snapshot})

        while True:
            # Keep the connection alive; clients are write-only over REST for simplicity
            await websocket.receive_text()
    except WebSocketDisconnect:
        await MANAGER.disconnect(websocket)
    except Exception:
        await MANAGER.disconnect(websocket)


# Reports
@app.get("/reports/epic/{epic}/tasks")
async def report_tasks_by_epic(epic: str):
    data = await STORAGE.report_tasks_by_epic(epic)
    return {"epic": epic, "tasks": data}


@app.get("/reports/epic/{epic}/users")
async def report_users_by_epic(epic: str):
    data = await STORAGE.report_user_history_by_epic(epic)
    return {"epic": epic, "users": data}


@app.post("/llm/call")
async def llm_call(payload: LLMCall):
    entry_id = await STORAGE.save_llm_call(
        session_id=payload.session_id,
        task_id=payload.task_id,
        requester=payload.requester,
        content=payload.content,
        meta=payload.meta,
    )
    return {"id": entry_id}


@app.post("/llm/response")
async def llm_response(payload: LLMResponse):
    entry_id = await STORAGE.save_llm_response(
        session_id=payload.session_id,
        task_id=payload.task_id,
        responder=payload.responder,
        content=payload.content,
        meta=payload.meta,
    )
    return {"id": entry_id}


@app.get("/context")
async def get_context(role: str, session_id: str, task_id: str | None = None, max_chars: int = 4000):
    ctx = await ASSEMBLER.assemble(role=role, session_id=session_id, task_id=task_id, max_chars=max_chars)
    return ctx


# Tool execution (policy check only; tool execution mocked)
class ToolExec(BaseModel):
    role: str
    tool: str
    args: List[str] = []


@app.post("/tools/exec")
async def exec_tool(req: ToolExec):
    allowed = POLICY.is_tool_allowed(req.role, req.tool)
    if not allowed:
        return JSONResponse({"error": "tool not allowed"}, status_code=403)
    # In a real system, dispatch to tool runner sandbox
    await STORAGE.log_decision(role=req.role, sender=req.role, action=f"tool:{req.tool} {req.args}", task_id=None, task_title=None, epic=None)
    return {"ok": True}


# Convenience for local `python app/main.py`
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)