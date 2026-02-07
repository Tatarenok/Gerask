from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "TicketSystem"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/ticket_system"
    
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"
    
    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
