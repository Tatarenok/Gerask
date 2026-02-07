from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models.user import User, Role
from app.models.ticket import Ticket, TicketStatus
from app.models.comment import TicketHistory
from app.schemas.ticket import TicketCreate, TicketUpdate, TicketStatusUpdate, TicketResponse, TicketList
from app.routers.auth import get_current_user
from app.utils.logger import log_action


router = APIRouter()


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


def get_user_display(db: Session, user_id: int) -> str:
    """Получить имя пользователя для истории"""
    if not user_id:
        return "Не назначен"
    user = db.query(User).filter(User.id == user_id).first()
    return user.display_name if user else "Неизвестный"


@router.get("/roles")
def get_available_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role.is_admin:
        roles = db.query(Role).filter(Role.prefix != None).all()
    elif current_user.role.prefix:
        roles = [current_user.role]
    else:
        roles = []
    
    return [{"id": r.id, "name": r.name, "prefix": r.prefix, "display_name": r.display_name} for r in roles]


@router.get("/users")
def get_users_for_assign(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    users = db.query(User).filter(User.is_active == True).all()
    return [{"id": u.id, "login": u.login, "display_name": u.display_name} for u in users]


@router.get("/my", response_model=List[TicketList])
def get_my_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    tickets = db.query(Ticket).filter(
        and_(
            Ticket.assignee_id == current_user.id,
            Ticket.status.in_([TicketStatus.OPEN.value, TicketStatus.IN_PROGRESS.value])
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
        if not current_user.role.is_admin and current_user.role.id != role.id:
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
        time_spent=0,  # ⭐ Начинаем с 0
        timer_started_at=None
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    # Добавляем в историю
    add_history(db, ticket.id, current_user.id, "CREATED", None, None, f"Заявка {key} создана")
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
    """Обновить заявку — ВСЕ пользователи (кроме читателей) могут менять"""
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
        
        # Записываем в историю если значение изменилось
        if old_value != new_value:
            if field == "assignee_id":
                old_name = get_user_display(db, old_value)
                new_name = get_user_display(db, new_value)
                add_history(db, ticket.id, current_user.id, "ASSIGNEE_CHANGED", 
                           "Исполнитель", old_name, new_name)
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
    ticket.time_spent = 0  # ⭐ Обнуляем таймер
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
        ticket.time_spent = int(elapsed)  # ⭐ Записываем время
        ticket.timer_started_at = None
    
    ticket.status = TicketStatus.DONE.value
    ticket.resolved_at = now
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "В работе", "Выполнен")
    
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
    
    ticket.time_spent = 0  # ⭐ Обнуляем
    ticket.timer_started_at = datetime.utcnow()
    ticket.status = TicketStatus.IN_PROGRESS.value
    ticket.resolved_at = None
    
    add_history(db, ticket.id, current_user.id, "STATUS_CHANGED",
               "Статус", "Выполнен", "В работе (возвращено)")
    
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_REOPENED", {"key": ticket_key})
    return ticket