from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Task, Project, TeamMember, TaskComment
from app.schemas import TaskCreate, TaskUpdate, TaskResponse, TaskCommentCreate, TaskCommentResponse
from app.routers.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Check if project exists
    project = db.query(Project).filter(Project.id == task.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if sprint exists if provided
    if task.sprint_id:
        from app.models import Sprint
        sprint = db.query(Sprint).filter(Sprint.id == task.sprint_id).first()
        if not sprint:
            raise HTTPException(status_code=404, detail="Sprint not found")
        if sprint.project_id != task.project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sprint does not belong to this project"
            )
    
    # Check if assigned user exists and is a team member
    if task.assigned_to_id:
        assigned_team_member = db.query(TeamMember).filter(
            TeamMember.user_id == task.assigned_to_id,
            TeamMember.project_id == task.project_id
        ).first()
        if not assigned_team_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not a member of this project"
            )
    
    db_task = Task(
        title=task.title,
        description=task.description,
        project_id=task.project_id,
        sprint_id=task.sprint_id,
        assigned_to_id=task.assigned_to_id,
        created_by_id=current_user.id,
        priority=task.priority,
        story_points=task.story_points,
        estimated_hours=task.estimated_hours
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    return db_task

@router.get("/project/{project_id}", response_model=List[TaskResponse])
async def get_project_tasks(
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
    
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    return tasks

@router.get("/sprint/{sprint_id}", response_model=List[TaskResponse])
async def get_sprint_tasks(
    sprint_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Get sprint and check if user is a team member
    from app.models import Sprint
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == sprint.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    tasks = db.query(Task).filter(Task.sprint_id == sprint_id).all()
    return tasks

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    return task

@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Update task fields
    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(task, field, value)
    
    db.commit()
    db.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Check if user is a team member of this project
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    # Only task creator or assigned user can delete
    if task.created_by_id != current_user.id and task.assigned_to_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only task creator or assigned user can delete this task"
        )
    
    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully"}

# Task Comments
@router.post("/{task_id}/comments", response_model=TaskCommentResponse)
async def create_task_comment(
    task_id: int,
    comment: TaskCommentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if task exists and user has access
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    db_comment = TaskComment(
        task_id=task_id,
        user_id=current_user.id,
        content=comment.content
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    
    return db_comment

@router.get("/{task_id}/comments", response_model=List[TaskCommentResponse])
async def get_task_comments(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if task exists and user has access
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    team_member = db.query(TeamMember).filter(
        TeamMember.user_id == current_user.id,
        TeamMember.project_id == task.project_id
    ).first()
    
    if not team_member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project"
        )
    
    comments = db.query(TaskComment).filter(TaskComment.task_id == task_id).all()
    return comments