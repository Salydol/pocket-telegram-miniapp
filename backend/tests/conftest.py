import os

# Тесты не должны зависеть от локального backend/.env: переменные окружения важнее .env
os.environ["ALLOWED_USERS"] = ""
os.environ["TUNNEL_METRICS_URL"] = ""
os.environ["WEBAPP_URL"] = ""
os.environ.pop("DEV_USER_ID", None)
