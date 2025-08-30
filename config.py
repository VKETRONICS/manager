from pydantic import BaseModel
import os

class Config(BaseModel):
    VK_GROUP_ID: str
    VK_SERVICE_TOKEN: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_CHAT_ID: str
    DATABASE_URL: str
    OPENAI_API_KEY: str | None = None
    TZ: str = os.getenv("TZ", "Europe/Amsterdam")
    PUBLIC_BASE_URL: str | None = os.getenv("PUBLIC_BASE_URL")
    WEBHOOK_SECRET: str | None = os.getenv("WEBHOOK_SECRET")
    ALERTS_ENABLED: bool = os.getenv("ALERTS_ENABLED","true").lower() == "true"

def load_config() -> "Config":
    return Config(
        VK_GROUP_ID=os.environ["VK_GROUP_ID"],
        VK_SERVICE_TOKEN=os.environ["VK_SERVICE_TOKEN"],
        TELEGRAM_BOT_TOKEN=os.environ["TELEGRAM_BOT_TOKEN"],
        TELEGRAM_ADMIN_CHAT_ID=os.environ["TELEGRAM_ADMIN_CHAT_ID"],
        DATABASE_URL=os.environ["DATABASE_URL"],
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
    )
