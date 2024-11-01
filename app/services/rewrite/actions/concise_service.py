from typing import List, Optional, AsyncGenerator

from app.services.rewrite.actions.llm import BaseLLMAction
from app.settings import settings


class ConciseService(BaseLLMAction):
    action_prompt = settings.prompts.concise_prompt
    task_type = settings.rephrase_task_type.CONCISE
    base_temperature = settings.rephrase_temperature
    max_rewrite_temp = 1
    _is_creative_rewrite = True