from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User, Role
from app.routers.auth import get_current_user, require_admin
from app.utils.logger import log_action


router = APIRouter()


# ============ Схемы ============

class RoleInfo(BaseModel):
    id: int
    name: str
    display_name: str
    prefix: str | None
    is_admin: bool
    
    class Config:
        from_attributes = True


class UserInfo(BaseModel):
    id: int
    login: str
    display_name: str | None
    role: RoleInfo
    is_active: bool
    
    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    role_id: int


class UserStatusUpdate(BaseModel):
    is_active: bool


# ============ Эндпоинты для всех ============

@router.get("/roles", response_model=List[RoleInfo])
def get_all_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список всех ролей"""
    roles = db.query(Role).all()
    return roles


# ============ Админские эндпоинты ============

@router.get("", response_model=List[UserInfo])
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Получить список всех пользователей"""
    users = db.query(User).all()
    return users


@router.get("/{user_id}", response_model=UserInfo)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Получить пользователя по ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}/role", response_model=UserInfo)
def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Изменить роль пользователя"""
    
    # Нельзя менять свою роль
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")
    
    old_role = user.role.name
    user.role_id = role.id
    db.commit()
    db.refresh(user)
    
    log_action(admin.id, "USER_ROLE_CHANGED", {
        "target_user": user.login,
        "old_role": old_role,
        "new_role": role.name
    })
    
    return user


@router.patch("/{user_id}/status", response_model=UserInfo)
def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Активировать/деактивировать пользователя"""
    
    # Нельзя деактивировать себя
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    
    action = "USER_ACTIVATED" if data.is_active else "USER_DEACTIVATED"
    log_action(admin.id, action, {"target_user": user.login})
    
    return user


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Удалить пользователя"""
    
    # Нельзя удалить себя
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    login = user.login
    db.delete(user)
    db.commit()
    
    log_action(admin.id, "USER_DELETED", {"deleted_user": login})
    
    return {"message": f"User '{login}' deleted successfully"}


# ============ Создание пользователя админом ============

class AdminUserCreate(BaseModel):
    login: str
    password: str
    display_name: str | None = None
    role_id: int


@router.post("", response_model=UserInfo, status_code=status.HTTP_201_CREATED)
def create_user_by_admin(
    data: AdminUserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """[ADMIN] Создать пользователя с любой ролью"""
    from app.utils.security import hash_password
    
    # Проверяем, что логин не занят
    existing = db.query(User).filter(User.login == data.login).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Проверяем роль
    role = db.query(Role).filter(Role.id == data.role_id).first()
    if not role:
        raise HTTPException(status_code=400, detail="Role not found")
    
    user = User(
        login=data.login,
        password_hash=hash_password(data.password),
        display_name=data.display_name or data.login,
        role_id=role.id,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_action(admin.id, "USER_CREATED_BY_ADMIN", {
        "new_user": data.login,
        "role": role.name
    })
    
    return user