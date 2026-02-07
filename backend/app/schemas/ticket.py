from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.models.ticket import TicketStatus, TicketPriority


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TicketPriority = TicketPriority.MEDIUM
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None
    role_id: Optional[int] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[TicketPriority] = None
    assignee_id: Optional[int] = None
    deadline: Optional[datetime] = None


class TicketStatusUpdate(BaseModel):
    status: TicketStatus


class UserShort(BaseModel):
    id: int
    login: str
    display_name: Optional[str]
    
    class Config:
        from_attributes = True


class RoleShort(BaseModel):
    id: int
    name: str
    prefix: Optional[str]
    display_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class TicketResponse(BaseModel):
    id: int
    key: str
    title: str
    description: Optional[str]
    status: str
    priority: str
    author: UserShort
    assignee: Optional[UserShort]
    role: RoleShort
    deadline: Optional[datetime]
    time_spent: Optional[int] = 0
    timer_started_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class TicketList(BaseModel):
    id: int
    key: str
    title: str
    status: str
    priority: str
    author: Optional[UserShort] = None
    assignee: Optional[UserShort]
    role: Optional[RoleShort] = None
    deadline: Optional[datetime]
    time_spent: Optional[int] = 0
    created_at: datetime
    
    class Config:
        from_attributes = True