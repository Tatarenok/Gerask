# ══════════════════════════════════════════════════════════════
# Frontend Dockerfile для РАЗРАБОТКИ (с hot reload)
# ══════════════════════════════════════════════════════════════

FROM node:20-alpine

WORKDIR /app

# Копируем файлы зависимостей
COPY package.json package-lock.json* ./

# Устанавливаем зависимости
RUN npm install

# Копируем остальное
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]