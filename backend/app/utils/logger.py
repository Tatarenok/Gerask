import logging
import sys
from pathlib import Path
from datetime import datetime
from pythonjsonlogger import jsonlogger

from app.config import settings


def setup_logger():
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger('ticket_system')
    logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    if logger.handlers:
        return logger
    
    class CustomJsonFormatter(jsonlogger.JsonFormatter):
        def add_fields(self, log_record, record, message_dict):
            super().add_fields(log_record, record, message_dict)
            log_record['timestamp'] = datetime.utcnow().isoformat()
            log_record['level'] = record.levelname
            log_record['app'] = settings.APP_NAME
    
    json_formatter = CustomJsonFormatter()
    
    file_handler = logging.FileHandler(settings.LOG_FILE, encoding='utf-8')
    file_handler.setFormatter(json_formatter)
    logger.addHandler(file_handler)
    
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()


def log_action(user_id, action, details=None):
    logger.info(
        f"ACTION: {action}",
        extra={
            'user_id': user_id,
            'action': action,
            'details': details or {}
        }
    )
