from app.models.completion import RephraseTaskType
from app.services.rewrite.actions.llm import BaseLLMAction
from app.settings import settings


class ConciseAction(BaseLLMAction):
    action_prompt = settings.prompts.concise_prompt
    task_type = RephraseTaskType.CONCISE
    base_temperature = settings.rephrase_temperature
    max_rewrite_temp = 1
    _is_creative_rewrite = True
