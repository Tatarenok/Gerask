"""
Схемы для пользователей и авторизации.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# === Роли ===

class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    prefix: Optional[str]
    is_admin: bool
    
    class Config:
        from_attributes = True


# === Пользователи ===

class UserCreate(BaseModel):
    """Схема для регистрации пользователя."""
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    password_confirm: str = Field(..., min_length=4, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Схема для входа."""
    login: str
    password: str


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""
    id: int
    login: str
    display_name: Optional[str]
    role: RoleResponse
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWT токен."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Данные из токена."""
    user_id: Optional[int] = None