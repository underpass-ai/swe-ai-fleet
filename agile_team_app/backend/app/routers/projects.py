from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Project, User, TeamMember
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectDashboard
from app.routers.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Only Product Owners can create projects
    if current_user.role.value != "product_owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Product Owners can create projects"
        )
    
    db_project = Project(
        name=project.name,
        description=project.description,
        product_owner_id=current_user.id
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # Add the product owner as a team member
    team_member = TeamMember(
        user_id=current_user.id,
        project_id=db_project.id,
        role=current_user.role,
        is_ai_agent=False
    )
    db.add(team_member)
    db.commit()
    
    return db_project

@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get projects where user is a team member
    team_memberships = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id
    ).all()
    
    project_ids = [tm.project_id for tm in team_memberships]
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    
    return projects

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is the product owner of this project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.product_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Product Owner can update this project"
        )
    
    # Update project fields
    for field, value in project_update.dict(exclude_unset=True).items():
        setattr(project, field, value)
    
    db.commit()
    db.refresh(project)
    return project

@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is the product owner of this project
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.product_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Product Owner can delete this project"
        )
    
    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}

@router.get("/{project_id}/dashboard", response_model=ProjectDashboard)
async def get_project_dashboard(
    project_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get team members
    team_members = db.query(TeamMember).filter(
        TeamMember.project_id == project_id
    ).all()
    
    # Get current active sprint
    from app.models import Sprint
    current_sprint = db.query(Sprint).filter(
        Sprint.project_id == project_id,
        Sprint.status == "active"
    ).first()
    
    # Get tasks summary
    from app.models import Task, TaskStatus
    tasks_summary = {
        "total": db.query(Task).filter(Task.project_id == project_id).count(),
        "todo": db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.TODO
        ).count(),
        "in_progress": db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.IN_PROGRESS
        ).count(),
        "done": db.query(Task).filter(
            Task.project_id == project_id,
            Task.status == TaskStatus.DONE
        ).count(),
    }
    
    # Mock sprint burndown data
    sprint_burndown = [
        {"day": 1, "remaining_points": 20},
        {"day": 2, "remaining_points": 18},
        {"day": 3, "remaining_points": 15},
        {"day": 4, "remaining_points": 12},
        {"day": 5, "remaining_points": 8},
    ]
    
    return ProjectDashboard(
        project=project,
        team_members=team_members,
        current_sprint=current_sprint,
        tasks_summary=tasks_summary,
        sprint_burndown=sprint_burndown
    )