from pydantic import BaseModel


class ChainInputs(BaseModel):
    original_message: str
    profession: str
    app_name: str
    writing_style: str


class AnalyzeOutput(BaseModel):
    tone: str
    vocabulary: str
    formality: str
    goal: str