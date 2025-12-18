from datetime import datetime, timedelta
from pynput.mouse import Listener
import threading
import time
from typing import List
from Mouse.Models.MouseEvents import MouseEvent, EventType


class RealTimeTracker:
    """Thu thập sự kiện chuột real-time với hỗ trợ pause"""

    def __init__(self):
        self.events: List[MouseEvent] = []
        self.listener = None
        self.is_tracking = False

    def collect_events(self, duration_seconds: int, stop_event=None, pause_event=None) -> List[MouseEvent]:
        self.events = []
        self.is_tracking = True

        print(f"🔍 Tracking mouse movement for {duration_seconds}s...")

        def on_move(x, y):
            if self.is_tracking and (pause_event is None or not pause_event.is_set()):
                self.events.append(MouseEvent.create_move_event(x, y))
            return self.is_tracking

        self.listener = Listener(on_move=on_move)
        listener_thread = threading.Thread(target=self.listener.start)
        listener_thread.daemon = True
        listener_thread.start()

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        try:
            while datetime.now() < end_time and self.is_tracking:
                time.sleep(0.5)

                # Kiểm tra stop event
                if stop_event and stop_event.is_set():
                    self.is_tracking = False
                    break

                # Kiểm tra pause event - nếu đang pause thì đợi
                while pause_event and pause_event.is_set() and self.is_tracking:
                    if stop_event and stop_event.is_set():
                        self.is_tracking = False
                        break
                    time.sleep(0.5)

        except KeyboardInterrupt:
            pass
        finally:
            self.is_tracking = False
            if self.listener:
                self.listener.stop()

        print(f"✅ Completed: {len(self.events)} moves")
        return self.events