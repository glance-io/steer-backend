from typing import AsyncGenerator, List, Optional

from app.models.completion import RephraseTaskType
from app.services.rewrite.actions.llm import BaseLLMAction
from app.settings import settings


class ProofreadAction(BaseLLMAction):
    task_type = RephraseTaskType.FIX_GRAMMAR
    action_prompt = settings.prompts.fix_grammar_prompt
    base_temperature = settings.fix_grammar_temperature
    max_rewrite_temp = base_temperature
