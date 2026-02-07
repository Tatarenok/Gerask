from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CLOSED = "closed"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(20), unique=True, nullable=False, index=True)  # ASU-1, DEVASU-1
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    status = Column(String(20), default=TicketStatus.OPEN.value)
    priority = Column(String(20), default=TicketPriority.MEDIUM.value)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)  # Для определения префикса
    
    deadline = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Время работы (в секундах)
    time_spent = Column(Integer, default=0)
    timer_started_at = Column(DateTime, nullable=True)
    
    # Связи
    author = relationship("User", foreign_keys=[author_id], backref="created_tickets")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_tickets")
    role = relationship("Role")
