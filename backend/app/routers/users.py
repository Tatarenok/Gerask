from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, Role
from app.schemas.user import UserResponse, RoleResponse
from app.routers.auth import get_current_user
from app.utils.logger import log_action


router = APIRouter()


class ChangeRoleRequest(BaseModel):
    role_id: int


@router.get("", response_model=List[UserResponse])
def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    return db.query(User).all()


@router.get("/roles", response_model=List[RoleResponse])
def get_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Role).all()


@router.patch("/{user_id}/role", response_model=UserResponse)
def change_user_role(
    user_id: int,
    data: ChangeRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    old_role = user.role.name
    user.role_id = role.id
    db.commit()
    db.refresh(user)
    
    log_action(current_user.id, "USER_ROLE_CHANGED", {"user_id": user_id, "old_role": old_role, "new_role": role.name})
    return user
