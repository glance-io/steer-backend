import abc
from typing import List, Optional, AsyncGenerator

from app.models.message import SystemMessage, UserMessage
from app.services.llm.llm_service import LLMServiceBase
from app.services.rewrite.actions.base import BaseRephraseAction
from app.settings import settings


class BaseLLMAction(BaseRephraseAction):
    base_temperature: float
    max_rewrite_temp: float
    action_prompt: str
    _is_creative_rewrite: bool = False

    def __innit__(self, llm_service: LLMServiceBase):
        self.llm_service = llm_service

    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        temperature = self._get_temperature(prev_rewrites)
        messages = self._get_messages(original_message, prev_rewrites, application)
        response_generator = self.llm_service.generate_stream(
            messages=messages,
            temperature=temperature
        )
        async for response in response_generator:
            yield response

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
            return "\n\n".join([settings.prompts.base_system_prompt, settings.one_word_prompt])

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

    def _get_messages(self, original_message: str, prev_rewrites: List[str], app: str):
        return [
            SystemMessage(content=settings.prompts.base_system_prompt),
            UserMessage(content=self._get_prompt(original_message, prev_rewrites, app))
        ]
