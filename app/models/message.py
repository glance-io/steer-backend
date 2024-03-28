from enum import Enum

from pydantic import BaseModel as PydanticBaseModel


class ChatMessageRole(str, Enum):
    USER = "user"
    SYSTEM = "system"
    ASSISTANT = "assistant"


class BaseChatMessage(PydanticBaseModel):
    content: str
    role: ChatMessageRole


class UserMessage(BaseChatMessage):
    role: ChatMessageRole = ChatMessageRole.USER


class SystemMessage(BaseChatMessage):
    role: ChatMessageRole = ChatMessageRole.SYSTEM


class AssistantMessage(BaseChatMessage):
    role: ChatMessageRole    = ChatMessageRole.ASSISTANT
