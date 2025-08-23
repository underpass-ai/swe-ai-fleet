from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import TeamMember, User, Project
from app.schemas import TeamMemberCreate, TeamMemberResponse
from app.routers.auth import get_current_active_user

router = APIRouter()

@router.post("/", response_model=TeamMemberResponse)
async def add_team_member(
    team_member: TeamMemberCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    # Check if user is the product owner of this project
    project = db.query(Project).filter(Project.id == team_member.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.product_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Product Owner can add team members"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == team_member.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is already a team member
    existing_member = db.query(TeamMember).filter(
        TeamMember.user_id == team_member.user_id,
        TeamMember.project_id == team_member.project_id
    ).first()
    
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a team member of this project"
        )
    
    db_team_member = TeamMember(
        user_id=team_member.user_id,
        project_id=team_member.project_id,
        role=team_member.role,
        is_ai_agent=team_member.is_ai_agent,
        agent_config=team_member.agent_config
    )
    db.add(db_team_member)
    db.commit()
    db.refresh(db_team_member)
    
    return db_team_member

@router.get("/project/{project_id}", response_model=List[TeamMemberResponse])
async def get_project_team(
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
    
    team_members = db.query(TeamMember).filter(
        TeamMember.project_id == project_id
    ).all()
    
    return team_members

@router.delete("/{team_member_id}")
async def remove_team_member(
    team_member_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    team_member = db.query(TeamMember).filter(TeamMember.id == team_member_id).first()
    if not team_member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    # Check if user is the product owner of this project
    project = db.query(Project).filter(Project.id == team_member.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.product_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Product Owner can remove team members"
        )
    
    # Cannot remove the product owner
    if team_member.user_id == project.product_owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the Product Owner from the team"
        )
    
    db.delete(team_member)
    db.commit()
    return {"message": "Team member removed successfully"}

@router.put("/{team_member_id}/role")
async def update_team_member_role(
    team_member_id: int,
    new_role: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    team_member = db.query(TeamMember).filter(TeamMember.id == team_member_id).first()
    if not team_member:
        raise HTTPException(status_code=404, detail="Team member not found")
    
    # Check if user is the product owner of this project
    project = db.query(Project).filter(Project.id == team_member.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.product_owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the Product Owner can update team member roles"
        )
    
    # Validate role
    from app.models import UserRole
    try:
        role_enum = UserRole(new_role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    team_member.role = role_enum
    db.commit()
    db.refresh(team_member)
    
    return {"message": "Team member role updated successfully", "team_member": team_member}

# AI Agent Management
@router.post("/ai-agent")
async def create_ai_agent(
    project_id: int,
    role: str,
    agent_config: str,
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
            detail="Only the Product Owner can create AI agents"
        )
    
    # Validate role
    from app.models import UserRole
    try:
        role_enum = UserRole(role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    # Create AI agent user
    ai_username = f"ai_{role}_{project_id}"
    ai_user = User(
        username=ai_username,
        email=f"{ai_username}@ai.local",
        full_name=f"AI {role.replace('_', ' ').title()}",
        role=role_enum,
        password_hash="",  # AI agents don't need passwords
        is_active=True
    )
    db.add(ai_user)
    db.commit()
    db.refresh(ai_user)
    
    # Add AI agent to team
    team_member = TeamMember(
        user_id=ai_user.id,
        project_id=project_id,
        role=role_enum,
        is_ai_agent=True,
        agent_config=agent_config
    )
    db.add(team_member)
    db.commit()
    
    return {
        "message": "AI agent created successfully",
        "ai_user": ai_user,
        "team_member": team_member
    }

@router.get("/ai-agents/project/{project_id}")
async def get_project_ai_agents(
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
    
    ai_agents = db.query(TeamMember).filter(
        TeamMember.project_id == project_id,
        TeamMember.is_ai_agent == True
    ).all()
    
    return ai_agents