from app.models.config import DBConfig, ThrottlingConfig
from app.models.prompt import PromptsConfig
from app.utils.filesystem import get_project_root
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource
from enum import Enum


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Settings(BaseSettings):
    debug: bool = True
    llm_api_key: str
    llm_model: str
    llm_provider: LLMProvider = LLMProvider.OPENAI
    lemonsqueezy_api_key: str
    lemonsqueezy_webhook_secret: str = 'test123'   # TODO: change to real secret
    lemonsqueezy_product_id: int
    lemonsqueezy_store_id: str
    lemonsqueezy_default_variant_id: str
    redis_host: str = "localhost"
    redis_port: int = 6379
    sentry_dsn: str
    rephrase_temperature: float = 1
    fix_grammar_temperature: float = 1
    mixpanel_api_key: str
    prompts: PromptsConfig
    db_config: DBConfig
    throttling_config: ThrottlingConfig

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        yaml_file=[get_project_root() / "config.yaml", get_project_root() / "prompts.yaml"]
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, env_settings, dotenv_settings, YamlConfigSettingsSource(settings_cls)


settings = Settings()