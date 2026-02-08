# Task Tracker (Gerask)

Личный проект — система управления задачами (аналог Jira в минимально жизнеспособном виде). Цель: отработать архитектуру, DevOps‑практики и подготовить систему к продакшн‑деплою.

---

## 1. Описание проекта

- Система позволяет создавать, назначать и вести задачи, комментировать, загружать файлы, отслеживать статусы и историю.
- Создана для практики: архитектура FE/BE, работа с БД, контейнеризация, наблюдаемость, CI/CD и деплой.
- Решает базовые потребности командного трекинга заявок без избыточной сложности.
- В отличие от типовых туториалов:
  - полноценные сущности с ролями, правами и историей;
  - загрузка файлов и раздача из сервиса;
  - продуманная структура логирования и health‑эндпоинт;
  - ориентация на реальный деплой через Docker Compose с reverse proxy.

---

## 2. Общая архитектура

- Frontend: SPA на Vue 3 + Vite. В дев‑режиме — порт 5173. В проде — собранные статики обслуживаются Nginx (или через Traefik+статик).
- Backend: FastAPI (Uvicorn) — REST API и раздача загруженных файлов. В деве — порт 8001. В проде — за reverse proxy.
- Database: PostgreSQL — основное хранилище данных задач, пользователей, комментариев, истории.
- Сервисные каталоги:
  - uploads — загруженные файлы пользователей;
  - logs — JSON‑логи приложения.
- Взаимодействие:
  - FE общается с BE по HTTP: `/api/...`;
  - CORS настроен на локальные адреса Vite‑dev (`http://localhost:5173`).
- Контейнеризация:
  - Docker для каждого сервиса (frontend, backend, db);
  - Docker Compose — оркестрация локально и на сервере, volumes для данных.
- Reverse proxy:
  - Прод: Traefik (рекомендовано) или Nginx. Проксирует 80/443 на FE/BE, занимается TLS/ACME, маршрутизацией, заголовками.

---

## 3. Структура репозитория

- `frontend/` — Vue + Vite SPA, роутер, UI (Vuetify), HTTP‑клиент.
- `backend/` — FastAPI приложение: модели, схемы, роутеры, конфиг, БД, логирование.
  - `backend/app/main.py` — создание FastAPI, CORS, роуты, `/health`, монтирование `/uploads`.
  - `backend/app/config.py` — Pydantic Settings, чтение `.env`.
  - `backend/app/database.py` — engine, SessionLocal, init_db.
  - `backend/app/models/` — SQLAlchemy модели (пользователи, роли, задачи, комментарии, вложения).
  - `backend/app/routers/` — эндпоинты: auth, tickets, users, comments.
  - `backend/app/schemas/` — pydantic‑схемы входа/выхода.
  - `backend/utils/logger.py` — JSON‑логирование в файл и консоль.
  - `backend/uploads/` — пользовательские файлы (volume в проде).
  - `backend/logs/` — логи (volume в проде).
  - `backend/.env` — переменные окружения бэкенда.
- `LICENSE`, `.gitattributes` — служебные файлы.

---

## 4. Технологический стек

- Vue 3 + Vite — современный SPA, быстрый дев‑сервер, понятный билд.
- Vuetify — UI‑компоненты для быстрых интерфейсов.
- Pinia — состояние на клиенте.
- Axios — HTTP‑клиент к API.
- FastAPI + Uvicorn — быстрый, типобезопасный бэкенд с удобной валидацией.
- SQLAlchemy — ORM для PostgreSQL.
- Pydantic / pydantic‑settings — схемы и конфиг из `.env`.
- Alembic — миграции БД (библиотека подключена; миграции в процессе стандартизации).
- PostgreSQL — надёжное хранилище.
- Docker + Docker Compose — упаковка и оркестрация.
- Traefik / Nginx — reverse proxy и TLS на проде.

Выбор обусловлен балансом простоты, производительности и готовности к продакшну. Все инструменты широко известны и поддерживаются.

---

## 5. Переменные окружения

Хранятся в `backend/.env`. Обязательные:

- `DATABASE_URL` — строка подключения к Postgres (пример ниже).
- `SECRET_KEY` — ключ для JWT. Менять в продакшне.

Опциональные:

- `DEBUG` — режим отладки (True/False).
- `LOG_LEVEL` — уровень логирования (`INFO`, `DEBUG`, `ERROR`).
- `LOG_FILE` — путь к лог‑файлу (по умолчанию `logs/app.log`).

Пример `backend/.env` (без секретов):

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/ticket_system
SECRET_KEY=change-me-in-prod-very-long-random
DEBUG=False
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

Замечание: сейчас CORS‑origins заданы жестко на локальные адреса в коде. Для продакшна требуется вынести их в `.env` (см. TODO).

---

## 6. Запуск проекта локально

Требования:

- Docker и Docker Compose установлены.
- Свободные порты: 5173 (FE dev), 8001 (BE), 5432 (DB — при публикации).

Быстрый старт без контейнеров (для разработки):

- Backend:
  - создать/проверить `backend/.env` (см. пример выше);
  - из каталога `backend` активировать venv и запустить:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
    ```
- Frontend:
  - из каталога `frontend`:
    ```bash
    npm install
    npm run dev
    ```
- Доступ:
  - FE: http://localhost:5173
  - BE: http://localhost:8001 (API на `/api/...`, health: `/health`)

Локально через Docker Compose (рекомендовано):

1. Создайте файл `docker-compose.yml` в корне проекта (пример ниже).
2. Запустите:
   ```bash
   docker compose up -d --build
   ```
3. Доступ:
   - FE: http://localhost (если через Nginx/Traefik) или http://localhost:5173 в dev‑варианте;
   - BE: http://localhost:8001;
   - Postgres: по внутренней сети `db:5432` (внешний порт публикуйте только при необходимости).

Пример `docker-compose.yml` (локальная разработка, без TLS):

```yaml
version: "3.9"

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: ticket_system
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432" # можно убрать публикацию в проде

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile # см. пример ниже
    env_file:
      - ./backend/.env
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/logs:/app/logs
    depends_on:
      - db
    ports:
      - "8001:8001"

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile # см. пример ниже
    depends_on:
      - backend
    ports:
      - "5173:5173" # dev‑сервер Vite
    environment:
      VITE_API_BASE_URL: http://localhost:8001/api
    command: ["npm", "run", "dev"]

volumes:
  postgres_data:
```

Пример `backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app /app/app
COPY .env /app/.env
ENV PYTHONUNBUFFERED=1
EXPOSE 8001
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8001"]
```

Пример `frontend/Dockerfile` (dev):

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* /app/
RUN npm install
COPY . /app
EXPOSE 5173
CMD ["npm","run","dev"]
```

Пример `frontend` Dockerfile (prod, multi‑stage + Nginx):

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* /app/
RUN npm ci
COPY . /app
# при необходимости пробросить VITE_* env перед сборкой
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx","-g","daemon off;"]
```

---

## 7. Запуск на сервере (production‑ready)

Подготовка сервера:

- Docker + Docker Compose.
- Открытые порты: 80/443 для reverse proxy; внутренние сервисы без публичной экспозиции.
- Настроить firewall (пропустить 80/443; закрыть 5432 наружу, если не нужно).
- Директории (persist):
  - `backend/uploads` — файлы пользователей;
  - `backend/logs` — логи;
  - volume `postgres_data` — данные БД.

Reverse proxy (Traefik — рекомендовано):

- Поднимаем Traefik отдельным сервисом, настраиваем ACME (Let's Encrypt), точки входа 80/443.
- Правила:
  - `Host(api.example.com)` → backend:8001
  - `Host(app.example.com)` → frontend:80 (собранные статики)
- Добавить заголовки безопасности (HSTS, X‑Frame‑Options, CSP по необходимости), gzip.

Деплой:

- Собираем и пушим образы в регистр (см. CI/CD).
- На сервере выполняем:
  ```bash
  docker compose pull
  docker compose up -d
  ```
- Проверяем health `/health`, логи, миграции БД (см. Ограничения/TODO).

Что нельзя потерять:

- `postgres_data` — база данных.
- `backend/uploads` — вложения пользователей.
- Резервное копирование: ежедневный dump БД (+ проверка восстановления), архивирование загрузок.

---

## 8. Мониторинг и наблюдаемость

- Health‑эндпоинт: `GET /health` — базовая проверка живости приложения.
- Логи:
  - JSON‑логи в `backend/logs/app.log` и в stdout (агрегация через Loki/ELK — по желанию).
  - Критично отслеживать уровни `ERROR` и частоту 5xx.
- Базовые проверки (критичные):
  - 2xx на `/health` (через reverse proxy).
  - Успешное подключение к Postgres.
  - Доступность volumes (`uploads`, `postgres_data`).
  - Размер логов и файлов (дисковая квота).
- Интеграция с Zabbix/Prometheus — по месту; для начала достаточно HTTP‑проверок и логов.

---

## 9. CI/CD (концептуально)

- Текущее состояние: ручной деплой через `docker compose up -d`.
- План:
  - GitHub Actions:
    - job сборки фронта и бэка, пуш образов в реестр (GHCR/Docker Hub).
    - job деплоя: SSH на сервер, `docker compose pull && docker compose up -d`.
  - Secrets: хранить `REGISTRY_TOKEN`, `SSH_PRIVATE_KEY` в GitHub Secrets.
  - Безопасный деплой:
    - деплой‑пользователь с ограниченными правами;
    - обновление через pull/up, без публикации внутренних портов наружу;
    - проверка `/health` после релиза, возможность быстрого rollback (хранить предыдущий тег).

---

## 10. Ограничения и TODO

- Миграции Alembic:
  - библиотека подключена; необходимо оформить полноценный `alembic.ini`, окружение и pipeline миграций.
  - сейчас создание таблиц делается через `Base.metadata.create_all` — временное решение.
- CORS:
  - значения origins заданы в коде для дев‑режима; вынести в `.env` для продакшна.
- Frontend:
  - `baseURL` для API сейчас фиксирован (`http://localhost:8001/api`); требуется параметризация через `VITE_API_BASE_URL` и настройка для prod build.
- Безопасность:
  - секреты — только из `.env`; убрать любые дефолты в продакшне.
  - ограничить размер загрузок и типы файлов (частично реализовано), добавить антивирус/скан при необходимости.
- Наблюдаемость:
  - добавить метрики (Prometheus), подробные health‑проверки компонентов (DB, диски).
- Бэкапы:
  - настроить крон для ежедневных дампов БД и архивирования `uploads`.
- Документация API:
  - автогенерация через FastAPI docs доступна на `/docs`; за reverse proxy защитить доступ.

---

## Приложение: ссылки на ключевые файлы

- Backend:
  - `backend/app/main.py` — точка входа и маршруты.
  - `backend/app/config.py` — переменные окружения.
  - `backend/app/database.py` — инициализация БД.
  - `backend/utils/logger.py` — настройка логирования.
- Frontend:
  - `frontend/src/api/index.js` — HTTP‑клиент.
  - `frontend/src/router/index.js` — роутер.

---

## Быстрые команды

```bash
# Локальный дев (без контейнеров)
cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
cd frontend && npm install && npm run dev

# Docker Compose
docker compose up -d --build
docker compose logs -f backend
docker compose logs -f frontend
```
