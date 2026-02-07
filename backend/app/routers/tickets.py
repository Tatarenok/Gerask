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
    if user.role.r.role.prefix and not user.role.is_admin:
        raise HTTPException(status_code=403, detail="Нет прав на создание заявок")


def generate_ticket_key(db: Session, role: Role) -> str:
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
    return [{"ogin, "display_name": u.display_name} for u in users]


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
        if not current_user.role.is_admin:
            if current_user.role.id != role.id:
                raise HTTPException(status_code=403, detail="Cannot create tickets for this role")
    else:
        if not current_user.role.prefix:
            raise HTTPException(status_code=403, detail="Select a role")
        role = current_user.role
    
    key = generate_ticket_key(db, role)
    
    ticket = Ticket(
        key=key,
        title=ticket_data.title,
        description=ticket_data.description,
        priority=ticket_data.priority.value,
        author_id=current_user.id,
        assignee_id=ticket_data.assignee_id,
        role_id=role.id,
        deadline=ticket_data.deadline,
    )
    
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_CREATED", {"key": key})
    return ticket


@router.get("", response_model=List[TicketList])
def get_tickets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Читатель и админ видят все заявки
    if current_user.role.is_admin or current_user.role.name == "reader":
        tickets = db.query(Ticket).order_by(Ticket.created_at.desc()).all()
    else:
        tickets = db.query(Ticket).filter(
            or_(
                Ticket.author_id == current_user.id,
                Ticket.assignee_id == current_user.id
            )
        ).order_by(Ticket.created_at.desc()).all()
    return tickets}", response_model=TicketResponse)
def get_ticket(
    ticket_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_key}", response_model=TicketResponse)
def update_ticket(
    ticket_key: str,
    ticket_data: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
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
    check_can_edit(current_user)
    
    ticket = db.query(Ticket).filter(Ticket.key == ticket_key).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    old_status = ticket.status
    new_status = status_data.status.value
    now = datetime.utcnow()
    
    if new_status == TicketStatus.IN_PROGRESS.value:
        if ticket.timer_started_at is None:
            ticket.timer_started_at = now
    elif old_status == TicketStatus.IN_PROGRESS.value:
        if ticket.timer_started_at:
            elapsed = (now - ticket.timer_started_at).total_seconds()
            ticket.time_spent += int(elapsed)
            ticket.timer_started_at = None
    
    ticket.status = new_status
    db.commit()
    db.refresh(ticket)
    
    log_action(current_user.id, "TICKET_STATUS_CHANGED", {"key": ticket_key})
    return ticket
