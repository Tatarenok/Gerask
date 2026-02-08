# ══════════════════════════════════════════════════════════════
# Frontend Dockerfile - Vue 3 + Vite (Multi-stage build)
# ══════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# Этап 1: Сборка
# ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Копируем файлы зависимостей
COPY package.json package-lock.json* ./

# Устанавливаем зависимости
RUN npm ci

# Копируем исходный код
COPY . .

# Аргумент для API URL (передаётся при сборке)
ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Собираем продакшн-билд
RUN npm run build

# ──────────────────────────────────────────────────────────────
# Этап 2: Nginx для раздачи статики
# ──────────────────────────────────────────────────────────────
FROM nginx:alpine AS final

# Удаляем дефолтную конфигурацию
RUN rm /etc/nginx/conf.d/default.conf

# Копируем нашу конфигурацию Nginx
COPY infrastructure/docker/nginx.conf /etc/nginx/conf.d/default.conf

# Копируем собранные файлы из builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Nginx работает на 80 порту
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost/health || exit 1

CMD ["nginx", "-g", "daemon off;"]