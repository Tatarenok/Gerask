"""
Настройка логирования.

DevOps-заметка:
- Логи пишем в JSON формате — легко парсить (ELK, Loki)
- Дублируем в файл и в консоль
- Каждый лог содержит: время, уровень, сообщение, доп. данные
- Это основа для мониторинга и отладки на проде
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from pythonjsonlogger import jsonlogger

from app.config import settings


def setup_logger() -> logging.Logger:
    """Создаём и настраиваем логгер приложения."""
    
    # Создаём папку для логов если нет
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Создаём логгер
    logger = logging.getLogger("ticket_system")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Формат для JSON логов
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record['timestamp'] = datetime.utcnow().isoformat()
            log_record['level'] = record.levelname
            log_record['app'] = settings.APP_NAME
    
    json_formatter = CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    
    # Хендлер для файла (JSON)
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    # Хендлер для консоли (человекочитаемый)
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


# Глобальный логгер
logger = setup_logger()


def log_action(user_id: int | None, action: str, details: dict = None):
    """
    Логирование действий пользователей.
    
    Примеры:
        log_action(1, "LOGIN_SUCCESS", {"ip": "192.168.1.1"})
        log_action(1, "TICKET_CREATED", {"ticket_key": "ASU-15"})
        log_action(None, "LOGIN_FAILED", {"login": "admin", "reason": "wrong_password"})
    """
    logger.info(
        f"ACTION: {action}",
        extra={
            "user_id": user_id,
            "action": action,
            "details": details or {}
        }
    )