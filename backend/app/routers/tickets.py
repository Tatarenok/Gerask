from typing import List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

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
    # Админ может всё
    if user.role.is_admin:
        return
    # Роль с префиксом может создавать свои заявки
    if user.role.prefix:
        return
    # Остальные (reader) не могут
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
        # Админ видит все роли с префиксами
        roles = db.query(Role).filter(Role.prefix != None).all()
    elif current_user.role.prefix:
        # Пользователь видит только свою роль
        roles = [current_user.role]
    else:
        # Reader не видит ролей для создания
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


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    ticket_data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Создать новую заявку"""
    check_can_create(current_user)
    
    # Определяем роль для заявки
    if ticket_data.role_id:
        role = db.query(Role).filter(Role.id == ticket_data.role_id).first()
        if not role or not role.prefix:
            raise HTTPException(status_code=400, detail="Invalid role")
        # Проверка прав: админ может всё, остальные только свою роль
        if not current_user.role.is_admin:
            if current_user.role.id != role.id:
                raise HTTPException(status_code=403, detail="Нельзя создавать заявки для другой роли")
    else:
        # Если роль не указана, используем роль пользователя
        if not current_user.role.prefix:
            raise HTTPException(status_code=400, detail="Укажите роль для заявки")
        role = current_user.role
    
    # Генерируем ключ
    key = generate_ticket_key(db, role)
    
    # Создаём заявку
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


@router.get("", response_model=List[TicketList])
def get_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Получить список заявок"""
    # Админ и читатель видят все заявки
    if current_user.role.is_admin or current_user.role.name == "reader":
        tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    else:
        # Остальные видят только свои (автор или исполнитель)
        tickets = db.query(Ticket).filter(
            or_(
                Ticket.author_id == current_user.id,
                Ticket.assignee_id == current_user.id
            )
        ).order_by(Ticket.created_at.desc()).all()
    return tickets


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
    
    # Обновляем только переданные поля
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
        # Начинаем работу — запускаем таймер
        if ticket.timer_started_at is None:
            ticket.timer_started_at = now
    elif old_status == TicketStatus.IN_PROGRESS.value:
        # Заканчиваем работу — останавливаем таймер и считаем время
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