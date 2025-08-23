from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models import UserRole, TaskStatus, TaskPriority

# Base schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: UserRole

class ProjectBase(BaseModel):
    name: str
    description: str

class SprintBase(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime

class TaskBase(BaseModel):
    title: str
    description: str
    priority: TaskPriority = TaskPriority.MEDIUM
    story_points: Optional[int] = None
    estimated_hours: Optional[int] = None

class TeamMemberBase(BaseModel):
    role: UserRole
    is_ai_agent: bool = False
    agent_config: Optional[str] = None

class TaskCommentBase(BaseModel):
    content: str

# Create schemas
class UserCreate(UserBase):
    password: str

class ProjectCreate(ProjectBase):
    pass

class SprintCreate(SprintBase):
    project_id: int

class TaskCreate(TaskBase):
    project_id: int
    sprint_id: Optional[int] = None
    assigned_to_id: Optional[int] = None

class TeamMemberCreate(TeamMemberBase):
    user_id: int
    project_id: int

class TaskCommentCreate(TaskCommentBase):
    task_id: int

# Update schemas
class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class SprintUpdate(BaseModel):
    name: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    sprint_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    story_points: Optional[int] = None
    estimated_hours: Optional[int] = None
    actual_hours: Optional[int] = None

# Response schemas
class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ProjectResponse(ProjectBase):
    id: int
    product_owner_id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    product_owner: UserResponse

    class Config:
        from_attributes = True

class SprintResponse(SprintBase):
    id: int
    project_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class TaskResponse(TaskBase):
    id: int
    project_id: int
    sprint_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    created_by_id: int
    status: TaskStatus
    actual_hours: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    assigned_to: Optional[UserResponse] = None
    created_by: UserResponse

    class Config:
        from_attributes = True

class TeamMemberResponse(TeamMemberBase):
    id: int
    user_id: int
    project_id: int
    joined_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True

class TaskCommentResponse(TaskCommentBase):
    id: int
    task_id: int
    user_id: int
    created_at: datetime
    user: UserResponse

    class Config:
        from_attributes = True

# Authentication schemas
class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Dashboard schemas
class ProjectDashboard(BaseModel):
    project: ProjectResponse
    team_members: List[TeamMemberResponse]
    current_sprint: Optional[SprintResponse] = None
    tasks_summary: dict
    sprint_burndown: List[dict]

class SprintDashboard(BaseModel):
    sprint: SprintResponse
    tasks: List[TaskResponse]
    team_velocity: float
    completion_percentage: float