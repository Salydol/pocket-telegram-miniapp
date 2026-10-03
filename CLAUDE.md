# Pocket — контекст для Claude Code

Telegram-бот + Mini App для учёта трат и задач с напоминаниями. Портфолио-проект, пользуются двое (автор и его девушка), данные у каждого раздельные. Общаемся на русском.

## Стек
- backend/: Python 3.12, aiogram 3.15 (long polling), FastAPI, SQLAlchemy 2 async, pydantic-settings. SQLite по умолчанию, Postgres через DATABASE_URL.
- frontend/: React 18 + TypeScript + Vite, Recharts, Telegram WebApp SDK (script tag в index.html).
- Один процесс: FastAPI (lifespan) запускает бота, цикл напоминаний и watcher адреса cloudflared-туннеля; он же раздаёт собранный frontend/dist.
- Цикл напоминаний спит до ближайшего remind_at (максимум 6 ч) и не опрашивает БД по таймеру: бесплатный Neon должен засыпать. Любое изменение времени задачи → `services.reminders_changed()`.
- Docker multi-stage + docker-compose (профиль `tunnel` = cloudflared quick tunnel).
- Прод: Render free (render.yaml, Docker, Frankfurt) + Neon Postgres + UptimeRobot пингует /health. WEBAPP_URL берётся из RENDER_EXTERNAL_URL. К Postgres — NullPool, строку Neon с `sslmode` понимает `db.normalize_db_url`.

## Команды
- Тесты: `cd backend && pip install -r requirements.txt pytest httpx && pytest -q` (13 тестов; tests/conftest.py изолирует их от backend/.env). На Windows venv уже есть: `backend\.venv\Scripts\python.exe -m pytest -q`.
- API без Telegram: `cd backend && DEV_USER_ID=1 RUN_BOT=false uvicorn app.main:app --reload`
- Фронт: `cd frontend && npm install && npm run dev` (проксирует /api на :8000), сборка `npm run build`.
- Всё вместе: `cp .env.example .env` → заполнить → `docker compose --profile tunnel up -d --build`.

## Устройство
- auth.py: проверка initData (HMAC, заголовок `Authorization: tma <initData>`), таймзона из `X-Timezone`. DEV_USER_ID — обход только для разработки.
- Все даты в БД хранятся в UTC (services.to_db / as_utc: SQLite теряет tzinfo). Периоды и группировка по дням считаются в таймзоне пользователя.
- parser.py: «500 кофе», «такси 1.5к», «2 500 продукты» → сумма + заметка; guess_category по имени категории и ключевым словам.
- bot.py: /start, /today, /week, /month, /task, /tasks, быстрый ввод траты текстом, callback-и undo/done/snooze, send_due_reminders.
- Фронт: Expenses.tsx (ввод, итоги, история; графики показываются только когда окно развёрнуто — useExpanded/viewportChanged), Tasks.tsx, Charts.tsx, tg.ts (MainButton, haptics, confirm).
- Категории не удаляются, а архивируются (archived=True), чтобы старые траты сохраняли категорию.
- Схема создаётся через create_all, миграций пока нет.

## Правила
- Не коммитить .env и data/.
- Любая новая выборка — только с фильтром по user_id (изоляция данных покрыта тестом).
- Новые даты — через to_db()/as_utc().
- Не добавлять фоновые задачи, которые трогают БД по таймеру (съедят лимит Neon).
- После изменений бэка — pytest; после фронта — `npm run build` (там же tsc).

## Бэклог
1. Общий бюджет на двоих (пространства + приглашение по ссылке)
2. Лимиты по категориям и предупреждения в боте
3. Регулярные траты/задачи
4. Редактирование траты (сейчас только удаление)
5. Экспорт CSV/Excel
6. Alembic-миграции, GitHub Actions (pytest + build)
