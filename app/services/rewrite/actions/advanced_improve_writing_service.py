from typing import AsyncGenerator, Optional, List

from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import Runnable, RunnableParallel, RunnableLambda
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.models.actions.advanced_improve import ChainInputs
from app.models.sse import SSEEvent
from app.services.rewrite.actions.base import BaseRephraseAction
from app.settings import LLMProvider, settings


class AdvancedImproveAction(BaseRephraseAction):
    _analyze_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.analyze_prompt)
    _rewrite_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.rewrite_prompt)
    _humanize_prompt = PromptTemplate.from_template(settings.prompts.advanced_improve_prompt.humanize_prompt)

    _analyze_temp = 0.5
    _rewrite_temp = 0.5
    _humanize_temp = 0.5

    _inputs = RunnableParallel({
        "original_message": lambda inputs: inputs.get("original_message"),
        "writing_style": lambda inputs: inputs.get("writing_style"),
        "profession": lambda inputs: inputs.get("profession"),
        "app_name": lambda inputs: inputs.get("app_name"),
        "prompt": _analyze_prompt,
    }).with_types(input_type=ChainInputs)

    _analysis = RunnableParallel({
        "original_message": lambda x: x.get('original_message'),
        "profession": lambda x: x.get('profession'),
        "app_name": lambda x: x.get('app_name'),
        "writing_style": lambda x: x.get('writing_style'),
        "analysis": lambda x: AdvancedImproveAction.get_llm(
            AdvancedImproveAction._analyze_temp,
            name="Analysis",
            structure=...
        ).invoke(x.get("prompt"))
    })
    _analysis.name = "Analysis"

    _rewrite = RunnableParallel({
        "prompt": RunnableLambda(
            lambda x: AdvancedImproveAction._rewrite_prompt.invoke({**(x.pop("analysis")), **x})
        ),
        "original_message": lambda x: x.get("original_message")
    } )
    _rewrite.name = "Rewrite"

    _improve = RunnableParallel({
        "original_message": lambda x: x.get("original_message"),
        "improved_message": lambda x: AdvancedImproveAction.get_llm(
            AdvancedImproveAction._rewrite_temp
        ).invoke(x.get("prompt"))
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
    def get_llm(cls, temp: float, name: Optional[str] = None, structure: Optional[BaseModel] = None) -> ChatOpenAI:
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

    async def _perform(
            self,
            original_message: str,
            prev_rewrites: List[str] | None,
            application: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        chain = self.get_chain()
        async for event in chain.astream_events({
            "original_message": original_message,
            "profession": "startup founder",
            "app_name": application,
            "writing_style": "simple, direct and clear"
        }, version="v2"):
            if event['event'] == 'on_chat_model_stream' and event['name'] == 'Humanize':
                yield SSEEvent.DATA,  event['data']['chunk'].content
            elif event['event'] == 'on_chat_model_end' and event['name'] == 'Analysis':
                yield SSEEvent.EXTRA, event['data']['output'].content