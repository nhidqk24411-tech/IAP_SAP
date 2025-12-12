"""
Module thu thập dữ liệu chuột real-time - CHỈ DI CHUYỂN
"""
from datetime import datetime, timedelta
from pynput.mouse import Listener
import threading
import time
from typing import List, Tuple
from Mouse.Models.MouseEvents import MouseEvent, EventType


class RealTimeTracker:
    """Thu thập sự kiện chuột real-time - CHỈ DI CHUYỂN"""

    def __init__(self):
        self.events = []
        self.listener = None
        self.is_tracking = False
        self.next_button_position = None

    def collect_events(self, duration_seconds: int, next_button_position: Tuple[int, int]) -> List[MouseEvent]:
        """
        Thu thập CHỈ MOVE events trong khoảng thời gian nhất định

        Args:
            duration_seconds: Thời gian thu thập
            next_button_position: Vị trí nút Next để tính toán đường đi lý tưởng

        Returns:
            List[MouseEvent]: Danh sách sự kiện MOVE
        """
        self.events = []
        self.next_button_position = next_button_position
        self.is_tracking = True

        print(f"🔍 Bắt đầu tracking CHỈ DI CHUYỂN ({duration_seconds}s)...")

        # Callback function CHỈ CÒN on_move
        def on_move(x, y):
            if self.is_tracking:
                event = MouseEvent(
                    timestamp=datetime.now(),
                    event_type=EventType.MOVE,
                    x=x,
                    y=y
                )
                self.events.append(event)
            return self.is_tracking

        # Tạo listener CHỈ với on_move
        self.listener = Listener(on_move=on_move)
        # KHÔNG CÓ on_click và on_scroll

        # Chạy listener trong thread riêng
        listener_thread = threading.Thread(target=self.listener.start)
        listener_thread.daemon = True
        listener_thread.start()

        # Đếm thời gian
        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        # Hiển thị tiến trình
        try:
            while datetime.now() < end_time:
                elapsed = (datetime.now() - start_time).seconds
                remaining = duration_seconds - elapsed

                if elapsed % 5 == 0:  # Cập nhật mỗi 5 giây
                    print(f"⏳ Đang tracking... {elapsed}/{duration_seconds}s ({len(self.events)} moves)")

                time.sleep(1)

        except KeyboardInterrupt:
            print("\n⏹️ Dừng tracking do người dùng")

        # Dừng tracking
        self.is_tracking = False
        if self.listener:
            self.listener.stop()

        print(f"✅ Hoàn thành tracking: {len(self.events)} move events")
        return self.events

    def get_live_metrics(self, window_seconds=5):
        """
        Lấy metrics real-time cho cửa sổ thời gian

        Args:
            window_seconds: Cửa sổ thời gian tính metrics

        Returns:
            dict: Metrics trong cửa sổ thời gian
        """
        if not self.events:
            return {}

        # Lấy events trong khoảng thời gian gần nhất
        cutoff_time = datetime.now() - timedelta(seconds=window_seconds)
        recent_events = [e for e in self.events if e.timestamp >= cutoff_time]

        if len(recent_events) < 2:
            return {}

        # Tính toán đơn giản CHỈ CHO MOVE
        distances = []
        velocities = []

        for i in range(len(recent_events) - 1):
            x1, y1 = recent_events[i].x, recent_events[i].y
            x2, y2 = recent_events[i + 1].x, recent_events[i + 1].y

            # Khoảng cách
            dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            distances.append(dist)

            # Thời gian
            dt = (recent_events[i + 1].timestamp - recent_events[i].timestamp).total_seconds()
            if dt > 0:
                velocities.append(dist / dt)

        return {
            'move_count': len(recent_events),
            'move_rate': len(recent_events) / window_seconds,
            'avg_distance': sum(distances) / len(distances) if distances else 0,
            'avg_velocity': sum(velocities) / len(velocities) if velocities else 0,
            'last_position': (recent_events[-1].x, recent_events[-1].y),
            'time_since_last': (datetime.now() - recent_events[-1].timestamp).total_seconds()
        }