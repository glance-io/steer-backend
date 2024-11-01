from app.services.rewrite.actions.llm import BaseLLMAction
from app.settings import settings


class ImproveWritingAction(BaseLLMAction):
    task_type = settings.rephrase_task_type.IMPROVE_WRITING
    action_prompt = settings.prompts.improve_writing_prompt
    base_temperature = settings.rephrase_temperature
    max_rewrite_temp = 1
    _is_creative_rewrite = True