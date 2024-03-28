from typing import Optional

from app.models.completion import RephraseTaskType


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

    def get_prompt(self, task_type: RephraseTaskType, is_one_word: Optional[bool] = False):
        if is_one_word:
            return "\n\n".join([self._base_system_prompt, self._one_word_prompt])
        action = self._action_mapping.get(task_type)
        return "\n\n".join([self._base_system_prompt, action or ""])
