from datetime import datetime
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    MOVE = "move"
    CLICK_PRESS = "click_press"
    CLICK_RELEASE = "click_release"
    SCROLL = "scroll"


@dataclass
class MouseEvent:
    """Class đại diện cho một sự kiện chuột"""
    timestamp: datetime
    event_type: EventType
    x: int
    y: int
    button: str = None  # Chỉ cho click
    dx: int = None  # Chỉ cho scroll
    dy: int = None  # Chỉ cho scroll

    def __str__(self):
        if self.event_type == EventType.MOVE:
            return f"Move: ({self.x}, {self.y})"
        elif self.event_type in [EventType.CLICK_PRESS, EventType.CLICK_RELEASE]:
            action = "Pressed" if self.event_type == EventType.CLICK_PRESS else "Released"
            return f"{action} at ({self.x}, {self.y})"
        elif self.event_type == EventType.SCROLL:
            return f"Scroll at ({self.x}, {self.y}) dx={self.dx}, dy={self.dy}"
        return f"Unknown event at ({self.x}, {self.y})"

    @classmethod
    def from_log_line(cls, log_line: str):
        try:
            # Tách timestamp và message
            parts = log_line.split(" - ", 1)
            if len(parts) != 2:
                return None

            timestamp_str, message = parts
            timestamp = datetime.strptime(timestamp_str.strip(), "%Y-%m-%d %H:%M:%S,%f")

            # Parse message
            if "Move:" in message:
                coords = message.split("(")[1].split(")")[0]
                x, y = map(int, coords.split(","))
                return cls(timestamp, EventType.MOVE, x, y)

            elif "Pressed" in message or "Released" in message:
                action = "Pressed" if "Pressed" in message else "Released"
                coords = message.split("(")[1].split(")")[0]
                x, y = map(int, coords.split(","))
                event_type = EventType.CLICK_PRESS if action == "Pressed" else EventType.CLICK_RELEASE
                return cls(timestamp, event_type, x, y)

            elif "Scroll" in message:

                import re
                coords_match = re.search(r'\((\d+),\s*(\d+)\)', message)
                dx_match = re.search(r'dx=(-?\d+)', message)
                dy_match = re.search(r'dy=(-?\d+)', message)

                if coords_match and dx_match and dy_match:
                    x, y = int(coords_match.group(1)), int(coords_match.group(2))
                    dx, dy = int(dx_match.group(1)), int(dy_match.group(1))
                    return cls(timestamp, EventType.SCROLL, x, y, dx=dx, dy=dy)

        except Exception as e:
            print(f"Error parsing log line: {e}")
        return None