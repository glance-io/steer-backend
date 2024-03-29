import structlog

from app.models.completion import RephraseTaskType, RephraseRequest
from app.models.message import SystemMessage, UserMessage, AssistantMessage
from app.services.openai_service import AsyncOpenAIService
from app.services.prompt_service import PromptService
from app.services.usage_service import LemonSqueezyUsageService, BaseUsageService


logger = structlog.get_logger(__name__)


class RewriteService:
    prompt_service = PromptService()
    openai_service = AsyncOpenAIService()

    def __init__(self, rewrite_request: RephraseRequest):
        self.rewrite_request = rewrite_request
        self.usage_service = LemonSqueezyUsageService(rewrite_request.ls_order_product_id)

    async def rewrite(self):
        logger.info("Rewriting started", task=self.rewrite_request.completion_task_type)
        prompt = self.prompt_service.get_prompt(
            self.rewrite_request.completion_task_type,
            len(self.rewrite_request.text.split(" ")) == 1,
            self.rewrite_request.prev_rewrites
        )
        conversation_messages = [
            SystemMessage(content=prompt),
            UserMessage(content=self.rewrite_request.text)
        ]
        response_generator = self.openai_service.stream_completions(
            messages = conversation_messages
        )
        rewrite = ""
        async for response_delta in response_generator:
            if response_delta:
                rewrite += response_delta
                yield response_delta
        logger.info("Rewrite completed", rewrite=rewrite, original_text=self.rewrite_request.text)
        conversation_messages.append(AssistantMessage(content=rewrite))
        try:
            await self.usage_service.update_user_usage(conversation_messages)
        except Exception as e:
            logger.error("Failed to update user usage", error=str(e))
            pass
