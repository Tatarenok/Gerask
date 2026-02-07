from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models.user import User, Role
from app.models.ticket import Ticket, TicketStatus
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketStatusUpdate, TicketResponse, TicketList
from app.routers.auth import get_current_user
from app.utils.logger import log_action


router = APIRouter()


def check_can_edit(user: User):
    """Проверяет, может ли пользователь редактировать (не читатель)"""
    if user.role.name == "reader":
        raise HTTPException(status_code=403, detail="Читатели не могут редактировать")


def check_can_create(user: User):
    """Проверяет, может ли пользователь создавать заявки"""
    if user.role.is_admin:
        return
    if user.role.prefix:
        return
    raise HTTPException(status_code=403, detail="Нет прав на создание заявок")


def generate_ticket_key(db: Session, role: Role) -> str:
    """Генерирует ключ заявки: PREFIX-NUMBER"""
    prefix = role.prefix
    number = role.next_ticket_number
    role.next_ticket_number = number + 1
    db.commit()
    return f"{prefix}-{number}"


@router.get("/roles")
def get_available_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список ролей, для которых можно создавать заявки"""
    if current_user.role.is_admin:
        roles = db.query(Role).filter(Role.prefix != None).all()
    elif current_user.role.prefix:
        roles = [current_user.role]
    else:
        roles = []
    
    return [
        {
            "id": r.id, 
            "name": r.name, 
            "prefix": r.prefix, 
            "display_name": r.display_name
        } 
        for r in roles
    ]


@router.get("/users")
def get_users_for_assign(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список пользователей для назначения исполнителем"""
    users = db.query(User).filter(User.is_active == True).all()
    return [
        {
            "id": u.id,
            "login": u.login, 
            "display_name": u.display_name
        } 
        for u in users
    ]


# ⭐ МОИ ЗАЯВКИ — где я ИСПОЛНИТЕЛЬ и статус open/in_progress
@router.get("/my", response_model=List[TicketList])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить мои заявки (где я исполнитель, только открытые и в работе)"""
    tickets = db.query(Ticket).filter(
        and_(
            Ticket.assignee_id == current_user.id,  # Только где я исполнитель
            Ticket.status.in_([
                TicketStatus.OPEN.value,        # Открыта
                TicketStatus.IN_PROGRESS.value  # В работе
            ])
        )
    ).order_by(Ticket.created_at.desc()).all()
    
    return tickets


# ⭐ ВСЕ ЗАЯВКИ — с поиском и фильтрами
@router.get("", response_model=List[TicketList])
def get_all_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    search: Optional[str] = Query(None, description="Поиск по ключу или названию"),
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    priority: Optional[str] = Query(None, description="Фильтр по приоритету"),
    assignee_id: Optional[int] = Query(None, description="Фильтр по исполнителю"),
    role_id: Optional[int] = Query(None, description="Фильтр по типу (роли)")
):
    """Получить все заявки с фильтрами"""
    
    query = db.query(Ticket)
    
    # Поиск по ключу или названию
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                Ticket.key.ilike(search_pattern),
                Ticket.title.ilike(search_pattern)
            )
        )
    
    # Фильтр по статусу
    if status:
        query = query.filter(Ticket.status == status)
    
    # Фильтр по приоритету
    if priority:
        query = query.filter(Ticket.priority == priority)
    
    # Фильтр по исполнителю
    if assignee_id:
        query = query.filter(Ticket.assignee_id == assignee_id)
    
    # Фильтр по типу заявки (роли)
    if role_id:
        query = query.filter(Ticket.role_id == role_id)
    
    tickets = query.order_by(Ticket.created_at.desc()).all()
    return tickets


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новую заявку"""
    check_can_create(current_user)
    
    if ticket_data.role_id:
        role = db.query(Role).filter(Role.id == ticket_data.role_id).first()
        if not role or not role.prefix:
            raise HTTPException(status_code=400, detail="Invalid role")
        if not current_user.role.is_admin:
            if current_user.role.id != role.id:
                raise HTTPException(status_code=403, detail="Нельзя создавать заявки для другой роли")
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
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_CREATED", {"key": key, "title": ticket_data.title})
    return ticket


@router.get("/{ticket_key}", response_model=TicketResponse)
def get_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить заявку по ключу"""
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
        if hasattr(value, 'value'):
            setattr(ticket, field, value.value)
        else:
            setattr(ticket, field, value)
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_UPDATED", {"key": ticket_key})
    return ticket


@router.patch("/{ticket_key}/status", response_model=TicketResponse)
def update_ticket_status(
    ticket_key: str,
    status_data: TicketStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Изменить статус заявки (с учётом таймера)"""
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    
    old_status = ticket.status
    new_status = status_data.status.value if hasattr(status_data.status, 'value') else status_data.status
    now = datetime.utcnow()
    
    # Логика таймера
    if new_status == TicketStatus.IN_PROGRESS.value:
        if ticket.timer_started_at is None:
            ticket.timer_started_at = now
    elif old_status == TicketStatus.IN_PROGRESS.value:
        if ticket.timer_started_at:
            elapsed = (now - ticket.timer_started_at).total_seconds()
            ticket.time_spent = (ticket.time_spent or 0) + int(elapsed)
            ticket.timer_started_at = None
    
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_STATUS_CHANGED", {
        "key": ticket_key, 
        "old_status": old_status, 
        "new_status": new_status
    })
    return ticket