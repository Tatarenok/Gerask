from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RoleResponse(BaseModel):
    id: int
    name: str
    display_name: str
    prefix: Optional[str]
    is_admin: bool
    
    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    login: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4, max_length=100)
    password_confirm: str = Field(..., min_length=4, max_length=100)
    display_name: Optional[str] = Field(None, max_length=100)


class UserLogin(BaseModel):
    login: str
    password: str


class UserResponse(BaseModel):
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
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None
