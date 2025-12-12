"""
Module định nghĩa sự kiện chuột - CHỈ CÒN MOVE
"""
from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    MOVE = "move"


@dataclass
class MouseEvent:
    """Class đại diện cho một sự kiện chuột - CHỈ DI CHUYỂN"""
    timestamp: datetime
    event_type: EventType  # Luôn là EventType.MOVE
    x: int
    y: int

    def __str__(self):
        return f"Move: ({self.x}, {self.y}) at {self.timestamp.strftime('%H:%M:%S.%f')[:-3]}"

    @classmethod
    def create_move_event(cls, x: int, y: int):
        """Tạo sự kiện di chuyển"""
        return cls(
            timestamp=datetime.now(),
            event_type=EventType.MOVE,
            x=x,
            y=y
        )

    @classmethod
    def from_log_line(cls, log_line: str):
        """
        Parse từ log line (tương thích ngược)
        CHỈ XỬ LÝ MOVE, BỎ CLICK VÀ SCROLL
        """
        try:
            parts = log_line.split(" - ", 1)
            if len(parts) != 2:
                return None

            timestamp_str, message = parts
            timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S,%f")

            # CHỈ parse MOVE events
            if "Move:" in message:
                coords = message.split("(")[1].split(")")[0]
                x, y = map(int, coords.split(","))
                return cls(timestamp, EventType.MOVE, x, y)

            # BỎ QUA tất cả CLICK và SCROLL events
            return None

        except Exception as e:
            print(f"Error parsing log line: {e}")
            return None