from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid

from app.database import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment, TicketHistory, Attachment
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, HistoryResponse
from app.routers.auth import get_current_user


router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ========== Комментарии ==========

@router.get("/{ticket_key}/comments", response_model=List[CommentResponse])
def get_comments(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить комментарии к заявке"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    comments = db.query(Comment).filter(
        Comment.ticket_id == ticket.id
    ).order_by(Comment.created_at.asc()).all()
    
    return comments


@router.post("/{ticket_key}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def create_comment(
    ticket_key: str,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить комментарий к заявке"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        content=data.content
    )
    db.add(comment)
    
    # Добавляем в историю
    add_history(db, ticket.id, current_user.id, "COMMENT_ADDED", None, None, f"Комментарий #{comment.id}")
    
    db.commit()
    db.refresh(comment)
    
    return comment


@router.put("/{ticket_key}/comments/{comment_id}", response_model=CommentResponse)
def update_comment(
    ticket_key: str,
    comment_id: int,
    data: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Редактировать комментарий"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    
    # Только автор или админ может редактировать
    if comment.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")
    
    comment.content = data.content
    comment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    
    return comment


@router.delete("/{ticket_key}/comments/{comment_id}")
def delete_comment(
    ticket_key: str,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить комментарий"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    
    # Только автор или админ может удалить
    if comment.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")
    
    db.delete(comment)
    db.commit()
    
    return {"message": "Комментарий удалён"}


# ========== Загрузка файлов ==========

@router.post("/{ticket_key}/comments/{comment_id}/attachments")
async def upload_attachment(
    ticket_key: str,
    comment_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузить файл к комментарию"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    
    # Генерируем уникальное имя файла
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)
    
    # Сохраняем файл
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Создаём запись в БД
    attachment = Attachment(
        comment_id=comment_id,
        ticket_id=comment.ticket_id,
        filename=file.filename,
        filepath=filepath,
        file_size=len(content),
        mime_type=file.content_type,
        uploaded_by=current_user.id
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    
    return {
        "id": attachment.id,
        "filename": attachment.filename,
        "filepath": f"/uploads/{unique_name}"
    }


# ========== История ==========

@router.get("/{ticket_key}/history", response_model=List[HistoryResponse])
def get_history(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить историю изменений заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    history = db.query(TicketHistory).filter(
        TicketHistory.ticket_id == ticket.id
    ).order_by(TicketHistory.created_at.desc()).all()
    
    return history


# ========== Вспомогательные функции ==========

def add_history(db: Session, ticket_id: int, user_id: int, action: str, 
                field_name: str = None, old_value: str = None, new_value: str = None):
    """Добавить запись в историю"""
    history = TicketHistory(
        ticket_id=ticket_id,
        user_id=user_id,
        action=action,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value
    )
    db.add(history)