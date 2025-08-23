from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn

from app.routers import auth, projects, sprints, tasks, team, websocket
from app.database import engine
from app.models import Base

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Agile Team Collaboration Platform",
    description="A platform for Human Product Owners to collaborate with AI-powered agile team members",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(sprints.router, prefix="/api/sprints", tags=["Sprints"])
app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
app.include_router(team.router, prefix="/api/team", tags=["Team"])
app.include_router(websocket.router, prefix="/api/ws", tags=["WebSocket"])

# Mount static files for frontend
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="static")

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "message": "Agile Team Platform is running"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)