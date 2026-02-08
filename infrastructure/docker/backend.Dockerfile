# ══════════════════════════════════════════════════════════════
# Backend Dockerfile - FastAPI + Uvicorn
# ══════════════════════════════════════════════════════════════

# Базовый образ
FROM python:3.12-slim AS base

# Не буферизовать вывод Python (сразу видим логи)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# ──────────────────────────────────────────────────────────────
# Этап сборки зависимостей
# ──────────────────────────────────────────────────────────────
FROM base AS builder

# Устанавливаем зависимости для сборки (psycopg2 и др.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements (для кэширования слоя)
COPY requirements.txt .

# Устанавливаем зависимости в отдельную папку
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ──────────────────────────────────────────────────────────────
# Финальный образ (минимальный)
# ──────────────────────────────────────────────────────────────
FROM base AS final

# Библиотеки для PostgreSQL (runtime)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Копируем установленные пакеты из builder
COPY --from=builder /install /usr/local

# Создаём непривилегированного пользователя
RUN useradd --create-home --shell /bin/bash appuser

# Создаём директории для данных
RUN mkdir -p /app/logs /app/uploads && chown -R appuser:appuser /app

# Копируем код приложения
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser alembic/ /app/alembic/
COPY --chown=appuser:appuser alembic.ini /app/

# Переключаемся на непривилегированного пользователя
USER appuser

# Порт приложения
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Запуск
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]