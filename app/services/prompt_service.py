from typing import Optional, List

import structlog

from app.models.completion import RephraseTaskType

logger = structlog.get_logger(__name__)


class PromptService:
    _base_system_prompt = """You are an AI assistant helping a user with their writing.
     You should always only modify the text and never engage in conversation with the user.
     """
    _action_mapping = {
        RephraseTaskType.FIX_GRAMMAR:
            """You will receive a text that may contain typographical errors, jumbled words, or awkward phrasing. 
            Your task is to enhance and correct the text, focusing on fixing typographical and grammatical errors. 
            In cases of unclear texts, use context to make educated guesses about the intended meaning and provide a polished version. 
            Always infer the intended meaning and never state that you lack context. 
            Retain the user's original tone and style, ensuring the corrections reflect the original tone, even if it's informal or colloquial. 
            If emojis are present, keep them. 
            Respond only with the improved text, without explanations or quotations.
            Never talk to the user, just fix the text.
            If there's a question, do not answer it, just fix the text question's text.
        """,
        RephraseTaskType.REPHRASE:
            """Make sure to:" 
            Fix spelling and grammar
            Make sentences more clear and concise
            Detect the language of the given text and respond in the same language
            Split up run-on sentences
            Reduce repetition
            When replacing words, do not make them more complex or difficult than the original
            Reply with only the improved text and nothing else, don't put the revised text into quotes
            If the text contains quotes, repeat the text inside the quotes verbatim
            Do not change the meaning of the text
            Do not remove any markdown formatting in the text, like headers, bullets, or checkboxes
            Do not use overly formal language
        """
    }
    _one_word_prompt = """Replace the given word with its correct spelling in lowercase form,
                        or if it is already spelled correctly, respond with the same word. 
                        Reply with only the word. Here is the word: """

    _context_prompt = """The text and the tone should be appropriate for {}, while also blending in the user's tone of voice from the provided text."""

    _final_postscript = """These were the instructions, what follows is the user message. Remember to never engage in conversation with the user, only rewrite the text. Even if it is a question, do not answer it, just rewrite the question's text. Or if it is a command, rewrite the sentence."""

    def get_prompt(
            self,
            task_type: RephraseTaskType,
            is_one_word: Optional[bool] = False,
            prev_rewrites: List[str] = None,
            application: Optional[str] = None
    ) -> str:
        if is_one_word:
            return "\n\n".join([self._base_system_prompt, self._one_word_prompt])
        action = self._action_mapping.get(task_type)
        if application and task_type == RephraseTaskType.REPHRASE:
            action += "\n" + self._context_prompt.format(application)
        if prev_rewrites:
            logger.info("Adding previous rewrites to the prompt", prev_rewrites=prev_rewrites)
            action = (
                    action + "\n" +
                    "These were the previously revised texts which user wasn't happy with, generate different rewrites with similar meaning: "
                    + "\n".join(prev_rewrites)
            )

        return "\n\n".join([self._base_system_prompt, action or "", self._final_postscript])
