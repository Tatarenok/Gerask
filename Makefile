# ══════════════════════════════════════════════════════════════
# Makefile для Gerask
# ══════════════════════════════════════════════════════════════

.PHONY: help dev prod logs clean

# Цвета для вывода
YELLOW := \033[33m
GREEN := \033[32m
RESET := \033[0m

# Compose команды
DC := docker compose -f infrastructure/docker-compose.yml
DC_DEV := $(DC) -f infrastructure/docker-compose.dev.yml
DC_PROD := $(DC) -f infrastructure/docker-compose.prod.yml

# ────────────────────────────────────────────────────────────
# Справка (по умолчанию)
# ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "$(GREEN)═══════════════════════════════════════════════════$(RESET)"
	@echo "$(GREEN)           Gerask - Команды управления             $(RESET)"
	@echo "$(GREEN)═══════════════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(YELLOW)Разработка:$(RESET)"
	@echo "  make dev          - Запустить в режиме разработки"
	@echo "  make dev-build    - Пересобрать и запустить"
	@echo "  make dev-down     - Остановить dev-окружение"
	@echo "  make logs         - Смотреть логи (все сервисы)"
	@echo "  make logs-back    - Логи только backend"
	@echo ""
	@echo "$(YELLOW)Продакшн:$(RESET)"
	@echo "  make prod         - Запустить в production"
	@echo "  make prod-down    - Остановить production"
	@echo "  make prod-restart - Перезапустить production"
	@echo ""
	@echo "$(YELLOW)База данных:$(RESET)"
	@echo "  make db-shell     - Войти в psql"
	@echo "  make db-backup    - Создать бэкап"
	@echo "  make migrate      - Применить миграции"
	@echo ""
	@echo "$(YELLOW)Утилиты:$(RESET)"
	@echo "  make shell-back   - Войти в контейнер backend"
	@echo "  make health       - Проверить health endpoints"
	@echo "  make clean        - Очистить Docker (осторожно!)"
	@echo ""

# ────────────────────────────────────────────────────────────
# Разработка
# ────────────────────────────────────────────────────────────
dev:
	$(DC_DEV) up

dev-build:
	$(DC_DEV) up --build

dev-down:
	$(DC_DEV) down

dev-d:
	$(DC_DEV) up -d

# ────────────────────────────────────────────────────────────
# Продакшн
# ────────────────────────────────────────────────────────────
prod:
	$(DC_PROD) up -d

prod-build:
	$(DC_PROD) up -d --build

prod-down:
	$(DC_PROD) down

prod-restart:
	$(DC_PROD) restart

prod-pull:
	$(DC_PROD) pull

# ────────────────────────────────────────────────────────────
# Логи
# ────────────────────────────────────────────────────────────
logs:
	$(DC_DEV) logs -f

logs-back:
	$(DC_DEV) logs -f backend

logs-front:
	$(DC_DEV) logs -f frontend

logs-db:
	$(DC_DEV) logs -f db

# ────────────────────────────────────────────────────────────
# База данных
# ────────────────────────────────────────────────────────────
db-shell:
	$(DC_DEV) exec db psql -U postgres -d gerask

db-backup:
	@mkdir -p backups
	@echo "Создаю бэкап..."
	$(DC_PROD) exec db pg_dump -U postgres gerask > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✓ Бэкап создан в backups/$(RESET)"

migrate:
	$(DC_DEV) exec backend alembic upgrade head

migrate-new:
	@read -p "Название миграции: " name; \
	$(DC_DEV) exec backend alembic revision --autogenerate -m "$$name"

# ────────────────────────────────────────────────────────────
# Утилиты
# ────────────────────────────────────────────────────────────
shell-back:
	$(DC_DEV) exec backend /bin/bash

shell-front:
	$(DC_DEV) exec frontend /bin/sh

health:
	@echo "$(YELLOW)Backend:$(RESET)"
	@curl -s http://localhost:8000/health | python3 -m json.tool 2>/dev/null || echo "Недоступен"
	@echo ""
	@echo "$(YELLOW)Frontend:$(RESET)"
	@curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:5173 2>/dev/null || echo "Недоступен"

clean:
	@echo "$(YELLOW)Это удалит все контейнеры и образы!$(RESET)"
	@read -p "Продолжить? [y/N] " confirm; \
	if [ "$$confirm" = "y" ]; then \
		docker system prune -af; \
		echo "$(GREEN)Очищено$(RESET)"; \
	fi

# ────────────────────────────────────────────────────────────
# Инициализация проекта
# ────────────────────────────────────────────────────────────
init:
	@echo "$(YELLOW)Инициализация проекта...$(RESET)"
	@cp -n .env.example .env 2>/dev/null || true
	@echo "$(GREEN)✓ Создан .env (заполни переменные!)$(RESET)"
	@mkdir -p backups
	@echo "$(GREEN)✓ Создана папка backups/$(RESET)"
	@echo ""
	@echo "Следующие шаги:"
	@echo "  1. Отредактируй .env"
	@echo "  2. Запусти: make dev"