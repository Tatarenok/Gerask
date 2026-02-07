from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), default=TicketStatus.OPEN.value)
    priority = Column(String(20), default=TicketPriority.MEDIUM.value)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    # Таймер
    timer_started_at = Column(DateTime, nullable=True)
    time_spent = Column(Integer, default=0)
    
    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # ⭐ ДОБАВЛЕНО
    resolved_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)
    
    # Связи
    author = relationship("User", foreign_keys=[author_id], backref="created_tickets")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_tickets")
    role = relationship("Role")