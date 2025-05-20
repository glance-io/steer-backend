from pydantic import BaseModel as PydanticBaseModel
from typing import Dict


class AdvancedImprovePrompts(PydanticBaseModel):
    analyze_prompt: str
    rewrite_prompt: str
    humanize_prompt: str


class PromptsConfig(PydanticBaseModel):
    base_system_prompt: str
    fix_grammar_prompt: str
    rephrase_prompt: str
    concise_prompt: str
    one_word_prompt: str
    context_prompt: str
    postscript: str
    advanced_improve_prompt: AdvancedImprovePrompts
    locale_instructions: Dict[str, str]
