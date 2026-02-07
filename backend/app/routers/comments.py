from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
import os
import uuid
import re

from app.database import get_db
from app.models.user import User
from app.models.ticket import Ticket
from app.models.comment import Comment, TicketHistory, Attachment, Notification
from app.schemas.comment import CommentCreate, CommentUpdate, CommentResponse, HistoryResponse, NotificationResponse
from app.routers.auth import get_current_user


router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def parse_mentions(content: str, db: Session) -> List[User]:
    """Находит @упоминания в тексте и возвращает список пользователей"""
    # Ищем паттерны @Имя или @[Имя Фамилия]
    pattern = r'@\[([^\]]+)\]|@(\w+)'
    matches = re.findall(pattern, content)
    
    mentioned_users = []
    for match in matches:
        name = match[0] or match[1]  # Берём то, что нашлось
        # Ищем пользователя по display_name или login
        user = db.query(User).filter(
            (User.display_name.ilike(f"%{name}%")) | (User.login.ilike(f"%{name}%"))
        ).first()
        if user:
            mentioned_users.append(user)
    
    return mentioned_users


def create_notification(db: Session, user_id: int, ticket_id: int, 
                       comment_id: int = None, notif_type: str = "MENTION", 
                       message: str = ""):
    """Создать уведомление для пользователя"""
    notification = Notification(
        user_id=user_id,
        ticket_id=ticket_id,
        comment_id=comment_id,
        type=notif_type,
        message=message
    )
    db.add(notification)


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
    """Добавить комментарий к заявке (с поддержкой @упоминаний)"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        content=data.content
    )
    db.add(comment)
    db.flush()  # Чтобы получить ID комментария
    
    # Ищем @упоминания и создаём уведомления
    mentioned_users = parse_mentions(data.content, db)
    for mentioned_user in mentioned_users:
        if mentioned_user.id != current_user.id:  # Не уведомляем самого себя
            create_notification(
                db=db,
                user_id=mentioned_user.id,
                ticket_id=ticket.id,
                comment_id=comment.id,
                notif_type="MENTION",
                message=f"{current_user.display_name} упомянул вас в комментарии к заявке {ticket.key}"
            )
    
    # Добавляем в историю
    add_history(db, ticket.id, current_user.id, "COMMENT_ADDED", None, None, f"Комментарий добавлен")
    
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
    
    if comment.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")
    
    # Проверяем новые упоминания
    old_mentions = set(u.id for u in parse_mentions(comment.content, db))
    new_mentions = set(u.id for u in parse_mentions(data.content, db))
    
    # Уведомляем только новых упомянутых
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    for user_id in new_mentions - old_mentions:
        if user_id != current_user.id:
            create_notification(
                db=db,
                user_id=user_id,
                ticket_id=ticket.id,
                comment_id=comment.id,
                notif_type="MENTION",
                message=f"{current_user.display_name} упомянул вас в комментарии к заявке {ticket.key}"
            )
    
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
    
    if comment.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")
    
    db.delete(comment)
    db.commit()
    
    return {"message": "Комментарий удалён"}


# ========== Загрузка файлов ==========

@router.post("/{ticket_key}/upload")
async def upload_file(
    ticket_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузить файл/изображение к заявке"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Проверяем тип файла
    allowed_types = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "application/pdf", "text/plain",
        "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Недопустимый тип файла: {file.content_type}")
    
    # Ограничение размера (10 MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Файл слишком большой (макс. 10 MB)")
    
    # Генерируем уникальное имя
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_name)
    
    # Сохраняем файл
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Создаём запись в БД
    attachment = Attachment(
        ticket_id=ticket.id,
        filename=file.filename,
        filepath=unique_name,
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
        "url": f"/uploads/{unique_name}",
        "mime_type": attachment.mime_type,
        "size": attachment.file_size
    }


@router.get("/{ticket_key}/attachments")
def get_attachments(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить все вложения заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    attachments = db.query(Attachment).filter(Attachment.ticket_id == ticket.id).all()
    
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "url": f"/uploads/{a.filepath}",
            "mime_type": a.mime_type,
            "size": a.file_size,
            "created_at": a.created_at
        }
        for a in attachments
    ]


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


# ========== Уведомления ==========

@router.get("/notifications", response_model=List[NotificationResponse])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить мои уведомления"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    return notifications


@router.get("/notifications/unread/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить количество непрочитанных уведомлений"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"count": count}


@router.post("/notifications/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отметить уведомление как прочитанное"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if notification:
        notification.is_read = True
        db.commit()
    
    return {"success": True}


@router.post("/notifications/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отметить все уведомления как прочитанные"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    
    return {"success": True}