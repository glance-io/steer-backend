from app.models.prompt import PromptsConfig
from app.utils.filesystem import get_project_root
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource


class Settings(BaseSettings):
    openai_api_key: str
    openai_model: str
    lemonsqueezy_api_key: str
    sentry_dsn: str
    rephrase_temperature: float = 1
    fix_grammar_temperature: float = 1
    mixpanel_api_key: str
    prompts: PromptsConfig

    model_config = SettingsConfigDict(
        env_file=get_project_root() / ".env",
        yaml_file=get_project_root() / "config.yaml"
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