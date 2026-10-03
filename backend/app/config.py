from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    # Публичный HTTPS-адрес, где открыт Mini App (например, https://xxx.trycloudflare.com).
    # На Render подставляется сам из RENDER_EXTERNAL_URL.
    webapp_url: str = Field("", validation_alias=AliasChoices("WEBAPP_URL", "RENDER_EXTERNAL_URL"))
    # Если задан — адрес берётся автоматически из cloudflared quick tunnel
    # (например, http://tunnel:2000). Тогда WEBAPP_URL можно не указывать.
    tunnel_metrics_url: str = ""
    # sqlite+aiosqlite:///./data/pocket.db  или  postgresql+asyncpg://user:pass@host/db
    database_url: str = "sqlite+aiosqlite:///./data/pocket.db"
    # Список Telegram ID через запятую, кому разрешён доступ. Пусто = всем.
    allowed_users: str = ""
    # Только для локальной разработки в браузере без Telegram: подставляет этого пользователя
    dev_user_id: int | None = None
    default_tz: str = "Asia/Almaty"
    currency: str = "₸"
    # Запускать бота (polling) внутри того же процесса
    run_bot: bool = True
    # Где лежит собранный фронт (frontend/dist)
    static_dir: str = "../frontend/dist"

    @property
    def allowed_ids(self) -> set[int]:
        return {int(x) for x in self.allowed_users.replace(" ", "").split(",") if x}


settings = Settings()
