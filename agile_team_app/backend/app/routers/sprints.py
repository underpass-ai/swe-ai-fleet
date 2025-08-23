from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Sprint, Project, TeamMember
from app.schemas import SprintCreate, SprintUpdate, SprintResponse, SprintDashboard
from app.routers.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=SprintResponse)
async def create_sprint(
    sprint: SprintCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Check if project exists
    project = db.query(Project).filter(Project.id == sprint.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for overlapping sprints
    overlapping_sprint = db.query(Sprint).filter(
        Sprint.project_id == sprint.project_id,
        Sprint.status.in_(["planning", "active"]),
        Sprint.start_date <= sprint.end_date,
        Sprint.end_date >= sprint.start_date
    ).first()
    
    if overlapping_sprint:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sprint dates overlap with existing sprint"
        )
    
    db_sprint = Sprint(
        name=sprint.name,
        project_id=sprint.project_id,
        start_date=sprint.start_date,
        end_date=sprint.end_date
    )
    db.add(db_sprint)
    db.commit()
    db.refresh(db_sprint)
    
    return db_sprint

@router.get("/project/{project_id}", response_model=List[SprintResponse])
async def get_project_sprints(
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
    
    sprints = db.query(Sprint).filter(Sprint.project_id == project_id).all()
    return sprints

@router.get("/{sprint_id}", response_model=SprintResponse)
async def get_sprint(
    sprint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    return sprint

@router.put("/{sprint_id}", response_model=SprintResponse)
async def update_sprint(
    sprint_id: int,
    sprint_update: SprintUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Update sprint fields
    for field, value in sprint_update.dict(exclude_unset=True).items():
        setattr(sprint, field, value)
    
    db.commit()
    db.refresh(sprint)
    return sprint

@router.delete("/{sprint_id}")
async def delete_sprint(
    sprint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Check if sprint has tasks
    from app.models import Task
    tasks_count = db.query(Task).filter(Task.sprint_id == sprint_id).count()
    if tasks_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete sprint with assigned tasks"
        )
    
    db.delete(sprint)
    db.commit()
    return {"message": "Sprint deleted successfully"}

@router.get("/{sprint_id}/dashboard", response_model=SprintDashboard)
async def get_sprint_dashboard(
    sprint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Get sprint tasks
    from app.models import Task
    tasks = db.query(Task).filter(Task.sprint_id == sprint_id).all()
    
    # Calculate metrics
    total_story_points = sum(task.story_points or 0 for task in tasks)
    completed_story_points = sum(
        task.story_points or 0 for task in tasks 
        if task.status.value == "done"
    )
    
    team_velocity = completed_story_points / max(len(tasks), 1)
    completion_percentage = (completed_story_points / max(total_story_points, 1)) * 100
    
    return SprintDashboard(
        sprint=sprint,
        tasks=tasks,
        team_velocity=team_velocity,
        completion_percentage=completion_percentage
    )