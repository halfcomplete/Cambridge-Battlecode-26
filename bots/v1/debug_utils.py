from enum import Enum

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller # type: ignore


class DebugMessageType(Enum):
    """
    Enum to represent different types of debug messages.
    """
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

def print_debug_msg(ct: Controller, msg: str, msg_type: DebugMessageType = DebugMessageType.INFO) -> None:
    """
    Utility function to print debug messages in a consistent format.
    """
    print(f"[{msg_type.value}] {msg} (Round {ct.get_current_round()})")