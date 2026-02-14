# backend/app/routers/tickets.py
from typing import List, Optional
from datetime import datetime
import re
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models.user import User, Role
from app.models.ticket import Ticket, TicketStatus
from app.models.comment import Comment, TicketHistory, Attachment, Notification
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketStatusUpdate, TicketResponse, TicketList
from app.routers.auth import get_current_user
from app.utils.logger import log_action
from app.models.delete_request import DeleteRequest
from app.models.ticket_link import TicketLink

import os
import uuid

router = APIRouter()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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


def check_can_edit(user: User):
    """Проверяет, может ли пользователь редактировать (не читатель)"""
    if user.role.name == "reader":
        raise HTTPException(status_code=403, detail="Читатели не могут редактировать")


def check_can_create(user: User):
    """Проверяет, может ли пользователь создавать заявки"""
    # Только читатели не могут создавать заявки
    if user.role.name == "reader":
        raise HTTPException(status_code=403, detail="Читатели не могут создавать заявки")


def generate_ticket_key(db: Session, role: Role) -> str:
    """Генерирует ключ заявки: PREFIX-NUMBER"""
    prefix = role.prefix
    number = role.next_ticket_number
    role.next_ticket_number = number + 1
    db.commit()
    return f"{prefix}-{number}"


def get_user_display(db: Session, user_id: int) -> str:
    """Получить имя пользователя для истории"""
    if not user_id:
        return "Не назначен"
    user = db.query(User).filter(User.id == user_id).first()
    return user.display_name if user else "Неизвестный"


def create_notification(db: Session, user_id: int, ticket_id: int, 
                        notif_type: str, message: str, comment_id: int = None):
    """Создать уведомление"""
    notification = Notification(
        user_id=user_id,
        ticket_id=ticket_id,
        comment_id=comment_id,
        type=notif_type,
        message=message,
        is_read=False
    )
    db.add(notification)


# ============ УВЕДОМЛЕНИЯ ============

@router.get("/notifications", response_model=List[dict])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить уведомления текущего пользователя"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id
    ).order_by(Notification.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": n.id,
            "type": n.type,
            "message": n.message,
            "ticket_id": n.ticket_id,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None
        }
        for n in notifications
    ]


@router.get("/notifications/unread/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Количество непрочитанных уведомлений"""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    return {"count": count}


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Пометить уведомление как прочитанное"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if notification:
        notification.is_read = True
        db.commit()
    
    return {"status": "ok"}


@router.post("/notifications/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Пометить все уведомления как прочитанные"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"status": "ok"}


# ============ РОЛИ И ПОЛЬЗОВАТЕЛИ ============

@router.get("/roles")
def get_available_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить доступные роли для создания заявок"""
    # Читатели не могут создавать заявки
    if current_user.role.name == "reader":
        return []
    
    # Все остальные видят все роли с prefix
    roles = db.query(Role).filter(Role.prefix != None).all()
    return [{"id": r.id, "name": r.name, "prefix": r.prefix, "display_name": r.display_name} for r in roles]

@router.get("/users")
def get_users_for_assign(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).filter(User.is_active == True).all()
    return [{"id": u.id, "login": u.login, "display_name": u.display_name} for u in users]



# ============ ЗАПРОСЫ НА УДАЛЕНИЕ ============

@router.get("/delete-requests")
def get_delete_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить запросы на удаление (для автора и админов)"""
    if current_user.role.is_admin:
        requests = db.query(DeleteRequest).filter(
            DeleteRequest.status == "pending"
        ).all()
    else:
        requests = db.query(DeleteRequest).join(Ticket).filter(
            Ticket.author_id == current_user.id,
            DeleteRequest.status == "pending"
        ).all()
    
    return [
        {
            "id": req.id,
            "ticket": {
                "id": req.ticket.id,
                "key": req.ticket.key,
                "title": req.ticket.title,
                "status": req.ticket.status
            },
            "requester": {
                "id": req.requester.id,
                "display_name": req.requester.display_name
            },
            "created_at": req.created_at.isoformat() if req.created_at else None
        }
        for req in requests
    ]


@router.post("/delete-requests/{request_id}/approve")
def approve_delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Одобрить запрос на удаление"""
    delete_req = db.query(DeleteRequest).filter(DeleteRequest.id == request_id).first()
    if not delete_req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    
    ticket = delete_req.ticket
    
    if ticket.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав")
    
    ticket_key = ticket.key
    requester_id = delete_req.requested_by
    
    # Удаляем заявку
    db.query(Comment).filter(Comment.ticket_id == ticket.id).delete()
    db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket.id).delete()
    db.query(Attachment).filter(Attachment.ticket_id == ticket.id).delete()
    db.query(Notification).filter(Notification.ticket_id == ticket.id).delete()
    db.query(DeleteRequest).filter(DeleteRequest.ticket_id == ticket.id).delete()
    db.delete(ticket)
    db.commit()
    
    # Уведомляем запросившего
    create_notification(
        db, requester_id, None, "DELETE_APPROVED",
        f"Запрос на удаление заявки {ticket_key} одобрен"
    )
    db.commit()
    
    log_action(current_user.id, "DELETE_REQUEST_APPROVED", {"key": ticket_key})
    return {"status": "ok", "message": f"Заявка {ticket_key} удалена"}


@router.post("/delete-requests/{request_id}/reject")
def reject_delete_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Отклонить запрос на удаление"""
    delete_req = db.query(DeleteRequest).filter(DeleteRequest.id == request_id).first()
    if not delete_req:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    
    ticket = delete_req.ticket
    
    if ticket.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав")
    
    delete_req.status = "rejected"
    delete_req.resolved_at = datetime.utcnow()
    delete_req.resolved_by = current_user.id
    db.commit()
    
    create_notification(
        db, delete_req.requested_by, ticket.id, "DELETE_REJECTED",
        f"Запрос на удаление заявки {ticket.key} отклонён"
    )
    db.commit()
    
    log_action(current_user.id, "DELETE_REQUEST_REJECTED", {"key": ticket.key})
    return {"status": "ok", "message": "Запрос отклонён"}

# ============ СВЯЗИ МЕЖДУ ЗАЯВКАМИ ============

@router.get("/{ticket_key}/links")
def get_ticket_links(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить связи заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Связи где текущая заявка — источник
    outgoing = db.query(TicketLink).filter(TicketLink.source_ticket_id == ticket.id).all()
    # Связи где текущая заявка — цель
    incoming = db.query(TicketLink).filter(TicketLink.target_ticket_id == ticket.id).all()
    
    links = []
    
    for link in outgoing:
        links.append({
            "id": link.id,
            "type": link.link_type,
            "direction": "outgoing",
            "ticket": {
                "id": link.target_ticket.id,
                "key": link.target_ticket.key,
                "title": link.target_ticket.title,
                "status": link.target_ticket.status
            },
            "created_by": link.creator.display_name if link.creator else None,
            "created_at": link.created_at.isoformat() if link.created_at else None
        })
    
    for link in incoming:
        # Инвертируем тип для входящих связей
        inverted_type = {
            "blocks": "blocked_by",
            "blocked_by": "blocks",
            "parent": "child",
            "child": "parent",
            "duplicates": "duplicated_by",
            "duplicated_by": "duplicates",
        }.get(link.link_type, link.link_type)
        
        links.append({
            "id": link.id,
            "type": inverted_type,
            "direction": "incoming",
            "ticket": {
                "id": link.source_ticket.id,
                "key": link.source_ticket.key,
                "title": link.source_ticket.title,
                "status": link.source_ticket.status
            },
            "created_by": link.creator.display_name if link.creator else None,
            "created_at": link.created_at.isoformat() if link.created_at else None
        })
    
    return links


@router.post("/{ticket_key}/links")
def create_ticket_link(
    ticket_key: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать связь между заявками"""
    check_can_edit(current_user)
    
    source_ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not source_ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    target_key = data.get("target_key")
    link_type = data.get("link_type", "related")
    
    target_ticket = db.query(Ticket).filter(Ticket.key == target_key).first()
    if not target_ticket:
        raise HTTPException(status_code=404, detail=f"Заявка {target_key} не найдена")
    
    if source_ticket.id == target_ticket.id:
        raise HTTPException(status_code=400, detail="Нельзя связать заявку с самой собой")
    
    # Проверяем, нет ли уже такой связи
    existing = db.query(TicketLink).filter(
        ((TicketLink.source_ticket_id == source_ticket.id) & (TicketLink.target_ticket_id == target_ticket.id)) |
        ((TicketLink.source_ticket_id == target_ticket.id) & (TicketLink.target_ticket_id == source_ticket.id))
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Связь уже существует")
    
    link = TicketLink(
        source_ticket_id=source_ticket.id,
        target_ticket_id=target_ticket.id,
        link_type=link_type,
        created_by=current_user.id
    )
    db.add(link)
    
    add_history(db, source_ticket.id, current_user.id, "LINK_ADDED",
               "Связь", None, f"{link_type} → {target_key}")
    
    db.commit()
    db.refresh(link)
    
    return {
        "id": link.id,
        "type": link.link_type,
        "ticket": {
            "id": target_ticket.id,
            "key": target_ticket.key,
            "title": target_ticket.title,
            "status": target_ticket.status
        }
    }


@router.delete("/{ticket_key}/links/{link_id}")
def delete_ticket_link(
    ticket_key: str,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить связь"""
    check_can_edit(current_user)
    
    link = db.query(TicketLink).filter(TicketLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Связь не найдена")
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Проверяем что связь относится к этой заявке
    if link.source_ticket_id != ticket.id and link.target_ticket_id != ticket.id:
        raise HTTPException(status_code=400, detail="Связь не относится к этой заявке")
    
    target_key = link.target_ticket.key if link.source_ticket_id == ticket.id else link.source_ticket.key
    
    add_history(db, ticket.id, current_user.id, "LINK_REMOVED",
               "Связь", f"{link.link_type} → {target_key}", None)
    
    db.delete(link)
    db.commit()
    
    return {"status": "ok"}

# ============ ЗАЯВКИ ============

@router.get("/my", response_model=List[TicketList])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить заявки текущего пользователя"""
    tickets = db.query(Ticket).filter(
        and_(
            Ticket.assignee_id == current_user.id,
            Ticket.status.in_([
                TicketStatus.OPEN.value, 
                TicketStatus.IN_PROGRESS.value,
                TicketStatus.WAITING.value  # Добавляем ожидание
            ])
        )
    ).order_by(Ticket.created_at.desc()).all()
    return tickets

@router.get("", response_model=List[TicketList])
def get_all_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[int] = Query(None),
    role_id: Optional[int] = Query(None)
):
    query = db.query(Ticket)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(Ticket.key.ilike(search_pattern), Ticket.title.ilike(search_pattern)))
    if status:
        query = query.filter(Ticket.status == status)
    if priority:
        query = query.filter(Ticket.priority == priority)
    if assignee_id:
        query = query.filter(Ticket.assignee_id == assignee_id)
    if role_id:
        query = query.filter(Ticket.role_id == role_id)
    
    return query.order_by(Ticket.created_at.desc()).all()


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_can_create(current_user)
    
    if ticket_data.role_id:
        role = db.query(Role).filter(Role.id == ticket_data.role_id).first()
        if not role or not role.prefix:
            raise HTTPException(status_code=400, detail="Invalid role")
        # Убрано: теперь все (кроме читателей) могут создавать заявки любого типа
        # if not current_user.role.is_admin and current_user.role.id != role.id:
        #     raise HTTPException(status_code=403, detail="Нельзя создавать заявки для другой роли")
    else:
        if not current_user.role.prefix:
            raise HTTPException(status_code=400, detail="Укажите роль для заявки")
        role = current_user.role
    
    key = generate_ticket_key(db, role)
    
    ticket = Ticket(
        key=key,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority.value if hasattr(ticket_data.priority, 'value') else ticket_data.priority,
        author_id=current_user.id,
        assignee_id=ticket_data.assignee_id,
        role_id=role.id,
        deadline=ticket_data.deadline,
        time_spent=0,
        timer_started_at=None
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    add_history(db, ticket.id, current_user.id, "CREATED", None, None, f"Заявка {key} создана")
    
    # Уведомляем исполнителя о назначении
    if ticket.assignee_id and ticket.assignee_id != current_user.id:
        create_notification(
            db, ticket.assignee_id, ticket.id, "ASSIGNED",
            f"Вам назначена заявка {key}: {ticket.title}"
        )
    
    db.commit()
    
    log_action(current_user.id, "TICKET_CREATED", {"key": key, "title": ticket_data.title})
    return ticket


@router.get("/{ticket_key}", response_model=TicketResponse)
def get_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return ticket


@router.patch("/{ticket_key}", response_model=TicketResponse)
def update_ticket(
    ticket_key: str,
    ticket_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Обновить заявку"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    data = ticket_data.model_dump(exclude_unset=True)
    
    for field, value in data.items():
        old_value = getattr(ticket, field)
        
        if hasattr(value, 'value'):
            new_value = value.value
        else:
            new_value = value
        
        if old_value != new_value:
            if field == "assignee_id":
                old_name = get_user_display(db, old_value)
                new_name = get_user_display(db, new_value)
                add_history(db, ticket.id, current_user.id, "ASSIGNEE_CHANGED", 
                           "Исполнитель", old_name, new_name)
                # Уведомляем нового исполнителя
                if new_value and new_value != current_user.id:
                    create_notification(
                        db, new_value, ticket.id, "ASSIGNED",
                        f"Вам назначена заявка {ticket.key}: {ticket.title}"
                    )
            elif field == "title":
                add_history(db, ticket.id, current_user.id, "TITLE_CHANGED",
                           "Название", str(old_value), str(new_value))
            elif field == "description":
                add_history(db, ticket.id, current_user.id, "DESCRIPTION_CHANGED",
                           "Описание", "Изменено", "Изменено")
            elif field == "priority":
                add_history(db, ticket.id, current_user.id, "PRIORITY_CHANGED",
                           "Приоритет", str(old_value), str(new_value))
        
        setattr(ticket, field, new_value)
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_UPDATED", {"key": ticket_key})
    return ticket

@router.post("/{ticket_key}/request-delete")
def request_delete_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Запросить удаление заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Автор и админ могут удалить сразу
    if ticket.author_id == current_user.id or current_user.role.is_admin:
        return {"can_delete": True}
    
    # Проверяем, есть ли уже активный запрос от этого пользователя
    existing = db.query(DeleteRequest).filter(
        DeleteRequest.ticket_id == ticket.id,
        DeleteRequest.requested_by == current_user.id,
        DeleteRequest.status == "pending"
    ).first()
    
    if existing:
        return {
            "can_delete": False, 
            "message": "Вы уже отправили запрос на удаление этой заявки"
        }
    
    # Создаём запрос на удаление
    delete_request = DeleteRequest(
        ticket_id=ticket.id,
        requested_by=current_user.id,
        status="pending"
    )
    db.add(delete_request)
    
    # Уведомляем автора
    if ticket.author_id != current_user.id:
        create_notification(
            db, ticket.author_id, ticket.id, "DELETE_REQUEST",
            f"{current_user.display_name} запросил удаление заявки {ticket.key}"
        )
    
    # Уведомляем всех админов
    admins = db.query(User).join(Role).filter(Role.is_admin == True).all()
    for admin in admins:
        if admin.id != current_user.id and admin.id != ticket.author_id:
            create_notification(
                db, admin.id, ticket.id, "DELETE_REQUEST",
                f"{current_user.display_name} запросил удаление заявки {ticket.key}"
            )
    
    add_history(db, ticket.id, current_user.id, "DELETE_REQUESTED", 
               None, None, f"{current_user.display_name} запросил удаление")
    
    db.commit()
    
    log_action(current_user.id, "TICKET_DELETE_REQUESTED", {"key": ticket_key})
    return {
        "can_delete": False, 
        "message": "Запрос на удаление отправлен автору и администраторам"
    }

@router.delete("/{ticket_key}")
def delete_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Удалить заявку (только автор или админ)"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Проверка прав: только автор или админ
    if ticket.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на удаление заявки")
    
    # Удаляем связанные данные
    db.query(Comment).filter(Comment.ticket_id == ticket.id).delete()
    db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket.id).delete()
    db.query(Attachment).filter(Attachment.ticket_id == ticket.id).delete()
    db.query(Notification).filter(Notification.ticket_id == ticket.id).delete()
    
    # Удаляем заявку
    db.delete(ticket)
    db.commit()
    
    log_action(current_user.id, "TICKET_DELETED", {"key": ticket_key})
    return {"status": "ok", "message": f"Заявка {ticket_key} удалена"}

# ============ ЗАПРОСЫ НА УДАЛЕНИЕ ============



@router.post("/{ticket_key}/start", response_model=TicketResponse)
def start_work(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Взять заявку в работу"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if ticket.assignee_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Вы не являетесь исполнителем")
    
    if ticket.status != TicketStatus.OPEN.value:
        raise HTTPException(status_code=400, detail="Можно взять в работу только открытую заявку")
    
    ticket.status = TicketStatus.IN_PROGRESS.value
    ticket.time_spent = 0
    ticket.timer_started_at = datetime.utcnow()
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED", 
               "Статус", "Открыта", "В работе")
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_STARTED", {"key": ticket_key})
    return ticket


@router.post("/{ticket_key}/resolve", response_model=TicketResponse)
def resolve_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Решить заявку"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if ticket.assignee_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Вы не являетесь исполнителем")
    
    if ticket.status != TicketStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=400, detail="Можно решить только заявку в работе")
    
    now = datetime.utcnow()
    if ticket.timer_started_at:
        elapsed = (now - ticket.timer_started_at).total_seconds()
        ticket.time_spent = (ticket.time_spent or 0) + int(elapsed)
        ticket.timer_started_at = None
    
    ticket.status = TicketStatus.DONE.value
    ticket.resolved_at = now
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "В работе", "Выполнен")
    
    # Уведомляем автора
    if ticket.author_id and ticket.author_id != current_user.id:
        create_notification(
            db, ticket.author_id, ticket.id, "STATUS_CHANGED",
            f"Заявка {ticket.key} выполнена"
        )
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_RESOLVED", {"key": ticket_key, "time_spent": ticket.time_spent})
    return ticket


@router.post("/{ticket_key}/reopen", response_model=TicketResponse)
def reopen_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Вернуть заявку в работу"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if ticket.assignee_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Вы не являетесь исполнителем")
    
    if ticket.status != TicketStatus.DONE.value:
        raise HTTPException(status_code=400, detail="Можно вернуть только выполненную заявку")
    
    # НЕ обнуляем time_spent, продолжаем накапливать
    ticket.timer_started_at = datetime.utcnow()
    ticket.status = TicketStatus.IN_PROGRESS.value
    ticket.resolved_at = None
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "Выполнен", "В работе (возвращено)")
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_REOPENED", {"key": ticket_key})
    return ticket


@router.post("/{ticket_key}/pause", response_model=TicketResponse)
def pause_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Поставить заявку на ожидание (пауза таймера)"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if ticket.assignee_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Вы не являетесь исполнителем")
    
    if ticket.status != TicketStatus.IN_PROGRESS.value:
        raise HTTPException(status_code=400, detail="Можно приостановить только заявку в работе")
    
    # Сохраняем накопленное время
    now = datetime.utcnow()
    if ticket.timer_started_at:
        elapsed = (now - ticket.timer_started_at).total_seconds()
        ticket.time_spent = (ticket.time_spent or 0) + int(elapsed)
        ticket.timer_started_at = None  # Останавливаем таймер
    
    ticket.status = TicketStatus.WAITING.value
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "В работе", "Ожидание")
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_PAUSED", {"key": ticket_key, "time_spent": ticket.time_spent})
    return ticket


@router.post("/{ticket_key}/resume", response_model=TicketResponse)
def resume_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Возобновить работу над заявкой из ожидания"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    if ticket.assignee_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Вы не являетесь исполнителем")
    
    if ticket.status != TicketStatus.WAITING.value:
        raise HTTPException(status_code=400, detail="Можно возобновить только заявку в ожидании")
    
    # Запускаем таймер заново (time_spent сохранён)
    ticket.timer_started_at = datetime.utcnow()
    ticket.status = TicketStatus.IN_PROGRESS.value
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "Ожидание", "В работе")
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_RESUMED", {"key": ticket_key})
    return ticket

# ============ КОММЕНТАРИИ ============

@router.get("/{ticket_key}/comments")
def get_comments(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить комментарии заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    comments = db.query(Comment).filter(Comment.ticket_id == ticket.id).order_by(Comment.created_at.asc()).all()
    
    return [
        {
            "id": c.id,
            "content": c.content,
            "author": {"id": c.author.id, "display_name": c.author.display_name} if c.author else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "updated_at": c.updated_at.isoformat() if c.updated_at else None
        }
        for c in comments
    ]


@router.post("/{ticket_key}/comments")
def add_comment(
    ticket_key: str,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Добавить комментарий с поддержкой @mentions"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    content = data.get("content", "")
    
    comment = Comment(
        ticket_id=ticket.id,
        author_id=current_user.id,
        content=content
    )
    db.add(comment)
    db.flush()  # Получаем ID комментария
    
    # Парсим @mentions из контента: @[Имя Пользователя]
    mentions = re.findall(r'@\[([^\]]+)\]', content)
    mentioned_user_ids = set()
    
    for mention_name in mentions:
        mentioned_user = db.query(User).filter(
            User.display_name == mention_name
        ).first()
        
        if mentioned_user and mentioned_user.id != current_user.id:
            mentioned_user_ids.add(mentioned_user.id)
            create_notification(
                db, mentioned_user.id, ticket.id, "MENTION",
                f"{current_user.display_name} упомянул вас в заявке {ticket.key}",
                comment.id
            )
    
    # Уведомляем автора и исполнителя о новом комментарии
    notify_users = set()
    if ticket.author_id and ticket.author_id != current_user.id:
        notify_users.add(ticket.author_id)
    if ticket.assignee_id and ticket.assignee_id != current_user.id:
        notify_users.add(ticket.assignee_id)
    
    # Исключаем тех, кто уже получил mention
    notify_users -= mentioned_user_ids
    
    for user_id in notify_users:
        create_notification(
            db, user_id, ticket.id, "COMMENT",
            f"{current_user.display_name} добавил комментарий к заявке {ticket.key}",
            comment.id
        )
    
    add_history(db, ticket.id, current_user.id, "COMMENT_ADDED")
    
    db.commit()
    db.refresh(comment)
    
    return {
        "id": comment.id,
        "content": comment.content,
        "author": {"id": current_user.id, "display_name": current_user.display_name},
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None
    }


@router.put("/{ticket_key}/comments/{comment_id}")
def update_comment(
    ticket_key: str,
    comment_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Редактировать комментарий"""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    
    if comment.author_id != current_user.id and not current_user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")
    
    comment.content = data.get("content", comment.content)
    comment.updated_at = datetime.utcnow()
    db.commit()
    
    return {"status": "ok"}


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
    
    return {"status": "ok"}


# ============ ИСТОРИЯ ============

@router.get("/{ticket_key}/history")
def get_history(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить историю заявки"""
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    history = db.query(TicketHistory).filter(
        TicketHistory.ticket_id == ticket.id
    ).order_by(TicketHistory.created_at.desc()).all()
    
    return [
        {
            "id": h.id,
            "action": h.action,
            "field_name": h.field_name,
            "old_value": h.old_value,
            "new_value": h.new_value,
            "user": {"id": h.user.id, "display_name": h.user.display_name} if h.user else None,
            "created_at": h.created_at.isoformat() if h.created_at else None
        }
        for h in history
    ]


# ============ ФАЙЛЫ ============

@router.post("/{ticket_key}/upload")
async def upload_file(
    ticket_key: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Загрузить файл"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    # Генерируем уникальное имя файла
    ext = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Сохраняем файл
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    # Создаём запись в БД
    attachment = Attachment(
        ticket_id=ticket.id,
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
        "url": f"/uploads/{unique_filename}",
        "mime_type": attachment.mime_type
    }