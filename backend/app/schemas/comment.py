from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class UserShort(BaseModel):
    id: int
    login: str
    display_name: Optional[str]
    
    class Config:
        from_attributes = True


# ========== Комментарии ==========

class CommentCreate(BaseModel):
    content: str  # HTML контент


class CommentUpdate(BaseModel):
    content: str


class AttachmentResponse(BaseModel):
    id: int
    filename: str
    filepath: str
    file_size: Optional[int]
    mime_type: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    id: int
    content: str
    author: UserShort
    created_at: datetime
    updated_at: Optional[datetime]
    attachments: List[AttachmentResponse] = []
    
    class Config:
        from_attributes = True


# ========== История ==========

class HistoryResponse(BaseModel):
    id: int
    action: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    user: UserShort
    created_at: datetime
    
    class Config:
        from_attributes = True