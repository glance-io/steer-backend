import abc
from typing import List, Optional, AsyncGenerator, Tuple

from app.models.message import SystemMessage, UserMessage
from app.models.sse import SSEEvent
from app.services.llm.llm_service import LLMServiceBase
from app.services.rewrite.actions.base import BaseRephraseAction
from app.settings import settings

import structlog


class BaseLLMAction(BaseRephraseAction):
    base_temperature: float
    max_rewrite_temp: float
    action_prompt: str
    _is_creative_rewrite: bool = False

    def __init__(self, llm_service: LLMServiceBase):
        self.llm_service = llm_service

    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None,
            locale: Optional[str] = None
    ) -> AsyncGenerator[Tuple[SSEEvent, str], None]:
        temperature = self._get_temperature(prev_rewrites)
        messages = self._get_messages(original_message, prev_rewrites, application, locale)
        response_generator = self.llm_service.generate_stream(
            messages=messages,
            temperature=temperature
        )
        async for response in response_generator:
            yield SSEEvent.DATA,  response

    def _get_temperature(self, prev_rewrites: List[str] | None) -> float:
        base_temperature = self.base_temperature
        base_temperature *= 1 + 0.1 * len(prev_rewrites) if prev_rewrites else 0
        return min(base_temperature, self.max_rewrite_temp)

    def _get_prompt(
            self,
            original_message: str,
            prev_rewrites: List[str] = None,
            application: Optional[str] = None
    ):
        is_one_word = len(original_message.split()) == 1
        if is_one_word:
            return f"""
            {settings.prompts.one_word_prompt}
            
            original word:
            {original_message}
            """

        action = self.action_prompt
        if application and self._is_creative_rewrite:
            action += "\n" + settings.context_prompt.format(application)

        if prev_rewrites:
            action += (
                    "\n" +
                    "These were the previously revised texts which user wasn't happy with, generate different rewrites with similar meaning: " +
                    "\n".join(prev_rewrites)
            )

        return f"""
        {action}
        
        original message:
        {original_message}
        """

    def _get_messages(self, original_message: str, prev_rewrites: List[str], app: str, locale: Optional[str] = None):
        base_prompt = settings.prompts.base_system_prompt
        
        # Add locale instruction if provided
        if locale:
            mapped_locale = self._get_locale_mapping(locale)
            structlog.get_logger().info(f"Mapped locale: {mapped_locale}")
            locale_instruction = settings.prompts.locale_instructions.get(
                mapped_locale,
                settings.prompts.locale_instructions["en_US"]  # Default to US English
            )
            base_prompt = f"{base_prompt}\n\n{locale_instruction}"
        
        return [
            SystemMessage(content=base_prompt),
            UserMessage(content=self._get_prompt(original_message, prev_rewrites, app))
        ]
