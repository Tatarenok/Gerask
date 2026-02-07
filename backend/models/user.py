"""
Модели пользователей и ролей.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Role(Base):
    """
    Роль пользователя.
    
    Примеры:
        - admin (prefix=None, is_admin=True)
        - engineer (prefix="ASU")
        - developer (prefix="DEVASU")
        - frontend (prefix="FRONTASU")
        - tester (prefix="TESTASU")
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # engineer, developer...
    display_name = Column(String(100), nullable=False)       # Инженер, Разработчик...
    prefix = Column(String(20), unique=True, nullable=True)  # ASU, DEVASU... (None для админа)
    next_ticket_number = Column(Integer, default=1)          # Следующий номер заявки
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    users = relationship("User", back_populates="role")


class User(Base):
    """
    Пользователь системы.
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    display_name = Column(String(100), nullable=True)  # Отображаемое имя
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Связи
    role = relationship("Role", back_populates="users")