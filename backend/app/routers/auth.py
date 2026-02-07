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
    """Получить текущего пользователя по токену"""
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User deactivated")
    
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Проверка что пользователь — админ"""
    if not current_user.role.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Регистрация нового пользователя с ролью reader по умолчанию"""
    
    if user_data.password != user_data.password_confirm:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Passwords do not match")
    
    existing = db.query(User).filter(User.login == user_data.login).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")
    
    # Ищем роль reader
    reader_role = db.query(Role).filter(Role.name == "reader").first()
    
    if not reader_role:
        # Если роли нет — создаём её
        logger.warning("Role 'reader' not found, creating...")
        reader_role = Role(
            name="reader",
            display_name="Читатель",
            prefix=None,
            is_admin=False
        )
        db.add(reader_role)
        db.commit()
        db.refresh(reader_role)
    
    user = User(
        login=user_data.login,
        password_hash=hash_password(user_data.password),
        display_name=user_data.display_name or user_data.login,
        role_id=reader_role.id,
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    log_action(user.id, "USER_REGISTERED", {"login": user.login, "role": "reader"})
    return user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Авторизация пользователя"""
    
    user = db.query(User).filter(User.login == user_data.login).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        log_action(None, "LOGIN_FAILED", {"login": user_data.login})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid login or password")
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User deactivated")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = create_access_token(data={"sub": str(user.id)})
    log_action(user.id, "LOGIN_SUCCESS", {"login": user.login})
    
    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Получить данные текущего пользователя"""
    return current_user