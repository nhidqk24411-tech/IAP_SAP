from datetime import datetime
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    MOVE = "move"

@dataclass
class MouseEvent:
    """Class đại diện cho sự kiện di chuyển chuột"""
    timestamp: datetime
    event_type: EventType
    x: int
    y: int

    @classmethod
    def create_move_event(cls, x: int, y: int):
        return cls(timestamp=datetime.now(), event_type=EventType.MOVE, x=x, y=y)