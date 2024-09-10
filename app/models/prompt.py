from pydantic import BaseModel as PydanticBaseModel


class PromptsConfig(PydanticBaseModel):
    base_system_prompt: str
    fix_grammar_prompt: str
    rephrase_prompt: str
    concise_prompt: str
    one_word_prompt: str
    context_prompt: str
    postscript: str