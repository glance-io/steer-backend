from app.models.completion import RephraseTaskType
from app.services.rewrite.actions.llm import BaseLLMAction
from app.settings import settings


class ImproveWritingAction(BaseLLMAction):
    task_type = RephraseTaskType.REPHRASE_OLD
    action_prompt = settings.prompts.rephrase_prompt
    base_temperature = settings.rephrase_temperature
    max_rewrite_temp = 1
    _is_creative_rewrite = True