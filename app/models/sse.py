from enum import Enum


class SSEEvent(str, Enum):
    DATA = "data"
    EOS = "eos"
    THROTTLE = "throttle"
    ANALYSIS = "analysis"
    ERROR = "error"
