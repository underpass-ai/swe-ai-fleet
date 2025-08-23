from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    PRODUCT_OWNER = "product_owner"
    PROJECT_MANAGER = "project_manager"
    ARCHITECT = "architect"
    QA = "qa"
    DEVOPS = "devops"
    DEVELOPER_BACKEND = "developer_backend"
    DEVELOPER_FRONTEND = "developer_frontend"

class TaskStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    full_name = Column(String)
    role = Column(Enum(UserRole))
    password_hash = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    projects = relationship("Project", back_populates="product_owner")
    team_memberships = relationship("TeamMember", back_populates="user")
    created_tasks = relationship("Task", back_populates="created_by")
    assigned_tasks = relationship("Task", back_populates="assigned_to")

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text)
    product_owner_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    product_owner = relationship("User", back_populates="projects")
    sprints = relationship("Sprint", back_populates="project")
    team_members = relationship("TeamMember", back_populates="project")

class Sprint(Base):
    __tablename__ = "sprints"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    status = Column(String, default="planning")  # planning, active, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="sprints")
    tasks = relationship("Task", back_populates="sprint")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"))
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(TaskStatus), default=TaskStatus.TODO)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    story_points = Column(Integer, nullable=True)
    estimated_hours = Column(Integer, nullable=True)
    actual_hours = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    project = relationship("Project")
    sprint = relationship("Sprint", back_populates="tasks")
    assigned_to = relationship("User", back_populates="assigned_tasks")
    created_by = relationship("User", back_populates="created_tasks")
    comments = relationship("TaskComment", back_populates="task")

class TeamMember(Base):
    __tablename__ = "team_members"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"))
    role = Column(Enum(UserRole))
    is_ai_agent = Column(Boolean, default=False)
    agent_config = Column(Text, nullable=True)  # JSON config for AI agents
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="team_memberships")
    project = relationship("Project", back_populates="team_members")

class TaskComment(Base):
    __tablename__ = "task_comments"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    task = relationship("Task", back_populates="comments")
    user = relationship("User")