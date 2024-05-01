from typing import Optional, List

import structlog

from app.models.completion import RephraseTaskType
from app.settings import settings

logger = structlog.get_logger(__name__)


class PromptService:
    _prompts = settings.prompts
    _action_mapping = {
        RephraseTaskType.REPHRASE: _prompts.rephrase_prompt,
        RephraseTaskType.FIX_GRAMMAR: _prompts.fix_grammar_prompt,
    }

    def get_prompt(
            self,
            task_type: RephraseTaskType,
            is_one_word: Optional[bool] = False,
            prev_rewrites: List[str] = None,
            application: Optional[str] = None
    ) -> str:
        if is_one_word:
            return "\n\n".join([self._prompts.base_system_prompt, self._prompts.one_word_prompt])
        action = self._action_mapping.get(task_type)
        if application and task_type == RephraseTaskType.REPHRASE:
            action += "\n" + self._prompts.context_prompt.format(application)
        if prev_rewrites:
            logger.info("Adding previous rewrites to the prompt", prev_rewrites=prev_rewrites)
            action = (
                    action + "\n" +
                    "These were the previously revised texts which user wasn't happy with, generate different rewrites with similar meaning: "
                    + "\n".join(prev_rewrites)
            )

        return "\n\n".join([self._prompts.base_system_prompt, action or "", self._prompts.postscript])
