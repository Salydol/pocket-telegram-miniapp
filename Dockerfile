# ---- 1. Сборка Mini App ----
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ---- 2. Python: API + бот + напоминания ----
FROM python:3.12-slim
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1 STATIC_DIR=/app/frontend/dist DATABASE_URL=sqlite+aiosqlite:////data/pocket.db
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY --from=web /web/dist /app/frontend/dist
VOLUME /data
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
