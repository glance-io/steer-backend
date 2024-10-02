from app.services.anthropic_service import AnthropicService
from app.services.llm_service import LLMServiceBase
from app.services.openai_service import AsyncOpenAIService
from app.settings import settings, LLMProvider


def get_llm_service() -> LLMServiceBase:
    if settings.llm_provider == LLMProvider.ANTHROPIC:
        return AnthropicService()
    else:
        return AsyncOpenAIService()
