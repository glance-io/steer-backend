from typing import AsyncGenerator, Optional, List, Type, Any, Dict

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableParallel, RunnableLambda
from langchain_openai import ChatOpenAI

from app.models.actions.advanced_improve import ChainInputs, AnalyzeOutput
from app.models.completion import RephraseTaskType
from app.models.sse import SSEEvent
from app.services.rewrite.actions.base import BaseRephraseAction
from app.settings import LLMProvider, settings


class AdvancedImproveAction(BaseRephraseAction):
    task_type = RephraseTaskType.ADVANCED_IMPROVE
    base_temperature = 0.5
    max_rewrite_temp = 0.5

    _analyze_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.analyze_prompt)
    _rewrite_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.rewrite_prompt)
    _humanize_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.humanize_prompt)

    _analyze_temp = _rewrite_temp = _humanize_temp = base_temperature

    _default_writing_style = "natural style, direct and clear"

    _inputs = RunnableParallel({
        "original_message": lambda inputs: inputs.get("original_message"),
        "writing_style": lambda inputs: inputs.get("writing_style") or AdvancedImproveAction._default_writing_style,
        "app_name": lambda inputs: inputs.get("app_name"),
        "prompt": _analyze_prompt,
        "prev_rewrites": lambda inputs: inputs.get("prev_rewrites"),
        "locale": lambda inputs: inputs.get("locale")
    }).with_types(input_type=ChainInputs)

    # most inputs from the previous step are just passed through to the next step,
    # analysis doesn't use them
    _analysis = RunnableParallel({
        "original_message": lambda x: x.get('original_message'),
        "app_name": lambda x: x.get('app_name'),
        "writing_style": lambda x: x.get('writing_style'),
        "prev_rewrites": lambda x: x.get('prev_rewrites'),
        "locale": lambda x: x.get('locale'),
        "analysis": lambda x: AdvancedImproveAction.get_llm(
            AdvancedImproveAction._analyze_temp,
            name="Analysis",
            structure=AnalyzeOutput
        ).invoke(x.get("prompt"))
    })
    _analysis.name = "Analysis"

    _rewrite = RunnableParallel({
        "prompt": RunnableLambda(
            lambda x: AdvancedImproveAction._get_rephrase_prompt(
                {**(x.pop("analysis")).dict(), **x}, 
                x.get("prev_rewrites")
            )
        ),
        "original_message": lambda x: x.get("original_message"),
        "locale": lambda x: x.get("locale")
    } )
    _rewrite.name = "Rewrite"

    _improve = RunnableParallel({
        "original_message": lambda x: x.get("original_message"),
        "improved_message": lambda x: AdvancedImproveAction.get_llm(
            AdvancedImproveAction._rewrite_temp
        ).invoke(x.get("prompt")).content,
        "locale_instructions": lambda x: AdvancedImproveAction._get_locale_instructions(x.get("locale"))
    })
    _improve.name = "Improve"

    def get_chain(self) -> Runnable:
        humanize_llm = self.get_llm(self._humanize_temp, name="Humanize")
        chain = (
                self._inputs |
                self._analysis |
                self._rewrite |
                self._improve |
                self._humanize_prompt |
                humanize_llm
        )
        return chain

    @classmethod
    def _get_rephrase_prompt(cls, input: Dict[str, Any], prev_rewrites: List[str] | None) -> str:
        if prev_rewrites:
            prompt = cls._rewrite_prompt + (
                    "\n" +
                    "These were the previously revised texts which user wasn't happy with, generate different rewrites with similar meaning: " +
                    "\n".join(prev_rewrites)
            )
        else:
            prompt = cls._rewrite_prompt
        return prompt.invoke(input).to_string()

    @classmethod
    def get_llm(cls, temp: float, name: Optional[str] = None, structure: Optional[Type] = None) -> ChatOpenAI:
        if settings.llm_provider == LLMProvider.OPENAI:
            model = ChatOpenAI(
                api_key=settings.llm_api_key,
                model=settings.llm_model,
                temperature=temp,
            )
            if name:
                model.name = name
            if structure:
                model = model.with_structured_output(structure, method="json_mode")
            return model
        else:
            raise NotImplementedError(
                f"LLM provider {settings.llm_provider} is not supported for advanced rwerite"
            )

    @classmethod
    def _get_locale_instructions(cls, locale: Optional[str] = None) -> str:
        """Get locale instructions for the humanize step."""
        if locale:
            mapped_locale = cls._get_locale_mapping(locale)
            locale_instruction = settings.prompts.locale_instructions.get(
                mapped_locale,
                settings.prompts.locale_instructions["en_US"]
            )
            return locale_instruction
        else:
            return ""

    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None,
            locale: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        chain = self.get_chain()
        async for event in chain.astream_events({
            "original_message": original_message,
            "app_name": application,
            "writing_style": self._default_writing_style,
            "prev_rewrites": prev_rewrites,
            "locale": locale
        }, version="v2"):
            if event['event'] == 'on_chat_model_stream' and event['name'] == 'Humanize':
                yield SSEEvent.DATA,  event['data']['chunk'].content
            elif event['event'] == 'on_chat_model_end' and event['name'] == 'Analysis':
                yield SSEEvent.ANALYSIS, event['data']['output'].content