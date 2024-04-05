from pydantic.v1 import BaseSettings

from app.utils.filesystem import get_project_root


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str
    lemonsqueezy_api_key: str
    sentry_dsn: str
    rephrase_temperature: float = 1
    fix_grammar_temperature: float = 1

    class Config:
        env_file = get_project_root() / ".env"


settings = Settings()