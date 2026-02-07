"""
Роуты авторизации: регистрация, вход, текущий пользователь.
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token
from app.utils.security import hash_password, verify_password, create_access_token, decode_token
from app.utils.logger import logger, log_action


router = APIRouter()
security = HTTPBearer()


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency: получает текущего пользователя из JWT токена.
    
    Использование:
        @router.get("/me")
        def get_me(user: User = Depends(get_current_user)):
            return user
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован",
        )
    
    return user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя.
    
    Новые пользователи создаются без роли (нужно назначить через админку).
    Пока что назначаем роль engineer по умолчанию.
    """
    # Проверяем совпадение паролей
    if user_data.password != user_data.password_confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пароли не совпадают"
        )
    
    # Проверяем, не занят ли логин
    existing_user = db.query(User).filter(User.login == user_data.login).first()
    if existing_user:
        log_action(None, "REGISTER_FAILED", {"login": user_data.login, "reason": "login_exists"})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким логином уже существует"
        )
    
    # Получаем роль по умолчанию (engineer)
    default_role = db.query(Role).filter(Role.name == "engineer").first()
    if not default_role:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Роль по умолчанию не найдена"
        )
    
    # Создаём пользователя
    user = User(
        login=user_data.login,
        password_hash=hash_password(user_data.password),
        display_name=user_data.display_name or user_data.login,
        role_id=default_role.id,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_action(user.id, "USER_REGISTERED", {"login": user.login, "role": default_role.name})
    logger.info(f"New user registered: {user.login}")
    
    return user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Вход в систему."""
    
    # Ищем пользователя
    user = db.query(User).filter(User.login == user_data.login).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        log_action(None, "LOGIN_FAILED", {"login": user_data.login, "reason": "invalid_credentials"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль"
        )
    
    if not user.is_active:
        log_action(user.id, "LOGIN_FAILED", {"reason": "user_inactive"})
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь деактивирован"
        )
    
    # Обновляем время последнего входа
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Создаём токен
    access_token = create_access_token(data={"sub": str(user.id)})
    
    log_action(user.id, "LOGIN_SUCCESS", {"login": user.login})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Получить данные текущего пользователя."""
    return current_user