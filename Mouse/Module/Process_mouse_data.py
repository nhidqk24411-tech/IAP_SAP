"""
Xử lý log file → trả về MouseResult object
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict
from Mouse.Models.MouseEvents import MouseEvent, EventType
from Mouse.Models.MouseResult import MouseResult
import math


class LogProcessor:
    """Xử lý file log mouse_events.log"""

    def __init__(self, log_file_path):
        self.log_file = log_file_path
        self.events: List[MouseEvent] = []

    def read_log_file(self) -> List[MouseEvent]:
        """Đọc file log và parse thành list MouseEvent"""
        events = []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        event = MouseEvent.from_log_line(line.strip())
                        if event:
                            events.append(event)

            self.events = events
            print(f"✓ Đã đọc {len(events)} events từ {self.log_file}")
            return events

        except FileNotFoundError:
            print(f"✗ File log không tồn tại: {self.log_file}")
            return []
        except Exception as e:
            print(f"✗ Lỗi đọc file: {e}")
            return []

    def calculate_metrics(self, events: List[MouseEvent]) -> Dict:
        """Tính toán tất cả metrics từ danh sách events"""
        if not events:
            return {}

        # Lọc theo loại event
        move_events = [e for e in events if e.event_type == EventType.MOVE]
        click_events = [e for e in events if 'CLICK' in e.event_type.value]
        scroll_events = [e for e in events if e.event_type == EventType.SCROLL]

        # 1. Tính khoảng cách - Công thức (6), (7), (8)
        total_distance = 0
        x_distance = 0
        y_distance = 0

        for i in range(len(move_events) - 1):
            x1, y1 = move_events[i].x, move_events[i].y
            x2, y2 = move_events[i + 1].x, move_events[i + 1].y

            # Euclidean distance - Công thức (6)
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            total_distance += dist

            # X-axis distance - Công thức (7)
            x_distance += abs(x2 - x1)

            # Y-axis distance - Công thức (8)
            y_distance += abs(y2 - y1)

        # 2. Tính flips - Công thức (15), (17)
        x_flips, y_flips = self._calculate_flips(move_events)

        # 3. Tính thời gian - Công thức (2), (3)
        duration = (events[-1].timestamp - events[0].timestamp).total_seconds()

        # Tìm thời gian movement span - Công thức (3)
        if move_events:
            movement_span = (move_events[-1].timestamp - move_events[0].timestamp).total_seconds()
        else:
            movement_span = 0

        # 4. Tính click có ý nghĩa (trong vùng làm việc)
        meaningful_clicks = 0
        for event in click_events:
            if event.event_type == EventType.CLICK_PRESS:
                # Kiểm tra có trong vùng làm việc không (tùy chỉnh)
                if self._is_in_work_area(event.x, event.y):
                    meaningful_clicks += 1

        # 5. Phát hiện bất thường
        alerts = self._detect_anomalies(
            total_distance, x_flips, y_flips,
            duration, movement_span, len(click_events), meaningful_clicks
        )

        return {
            'total_events': len(events),
            'total_moves': len(move_events),
            'total_clicks': len([e for e in click_events if e.event_type == EventType.CLICK_PRESS]),
            'total_scrolls': len(scroll_events),
            'total_distance': total_distance,
            'x_axis_distance': x_distance,
            'y_axis_distance': y_distance,
            'x_flips': x_flips,
            'y_flips': y_flips,
            'duration': duration,
            'movement_span': movement_span,
            'meaningful_clicks': meaningful_clicks,
            'alerts': alerts,
            'is_suspicious': len(alerts) > 2  # Nếu có >2 alerts thì đáng ngờ
        }

    def _calculate_flips(self, move_events: List[MouseEvent]) -> tuple:
        """Tính số lần đổi hướng - Công thức (15), (17)"""
        if len(move_events) < 3:
            return 0, 0

        x_flips, y_flips = 0, 0
        prev_x_dir, prev_y_dir = 0, 0

        for i in range(1, len(move_events)):
            x_curr, y_curr = move_events[i].x, move_events[i].y
            x_prev, y_prev = move_events[i - 1].x, move_events[i - 1].y

            # X direction
            if x_curr > x_prev:
                x_dir = 1
            elif x_curr < x_prev:
                x_dir = -1
            else:
                x_dir = 0

            # Y direction
            if y_curr > y_prev:
                y_dir = 1
            elif y_curr < y_prev:
                y_dir = -1
            else:
                y_dir = 0

            # Check flips
            if prev_x_dir != 0 and x_dir != 0 and prev_x_dir != x_dir:
                x_flips += 1
            if prev_y_dir != 0 and y_dir != 0 and prev_y_dir != y_dir:
                y_flips += 1

            prev_x_dir = x_dir
            prev_y_dir = y_dir

        return x_flips, y_flips

    def _is_in_work_area(self, x: int, y: int) -> bool:
        """Kiểm tra có trong vùng làm việc không"""
        # Tùy chỉnh theo ứng dụng của bạn
        work_areas = [
            (50, 100, 500, 400),  # Vùng chính
            (600, 50, 800, 150),  # Vùng nút
        ]

        for (x1, y1, x2, y2) in work_areas:
            if x1 <= x <= x2 and y1 <= y <= y2:
                return True
        return False

    def _detect_anomalies(self, total_distance, x_flips, y_flips,
                          duration, movement_span, total_clicks, meaningful_clicks) -> List[Dict]:
        """Phát hiện các bất thường"""
        alerts = []

        # 1. Kiểm tra không hoạt động
        if duration > 60 and movement_span < 5:  # 1 phút nhưng chỉ di chuột 5s
            alerts.append({
                'level': 'HIGH',
                'type': 'LOW_ACTIVITY',
                'message': f'Thời gian không hoạt động cao: {duration - movement_span:.1f}s'
            })

        # 2. Kiểm tra flips quá thấp (bot đơn giản)
        total_flips = x_flips + y_flips
        if total_flips == 0 and total_distance > 100:
            alerts.append({
                'level': 'MEDIUM',
                'type': 'NO_FLIPS',
                'message': 'Di chuyển không có đổi hướng - có thể là bot'
            })

        # 3. Kiểm tra click vô nghĩa
        if total_clicks > 0:
            meaningful_ratio = meaningful_clicks / total_clicks
            if meaningful_ratio < 0.2:  # Dưới 20% click có ý nghĩa
                alerts.append({
                    'level': 'MEDIUM',
                    'type': 'MEANINGLESS_CLICKS',
                    'message': f'Chỉ {meaningful_ratio:.1%} click có ý nghĩa'
                })

        # 4. Kiểm tra di chuyển quá ít
        if duration > 300 and total_distance < 500:  # 5 phút nhưng di chuyển < 500px
            alerts.append({
                'level': 'HIGH',
                'type': 'MINIMAL_MOVEMENT',
                'message': f'Di chuyển rất ít: {total_distance:.1f}px trong {duration:.1f}s'
            })

        return alerts

    def process(self, session_id="default_session") -> MouseResult:
        """Xử lý toàn bộ và trả về MouseResult"""
        # 1. Đọc log
        events = self.read_log_file()
        if not events:
            print("✗ Không có dữ liệu để xử lý")
            return None

        # 2. Tính metrics
        metrics = self.calculate_metrics(events)

        # 3. Tạo MouseResult
        result = MouseResult(
            session_id=session_id,
            start_time=events[0].timestamp,
            end_time=events[-1].timestamp,
            total_events=metrics['total_events'],
            total_moves=metrics['total_moves'],
            total_clicks=metrics['total_clicks'],
            total_scrolls=metrics['total_scrolls'],
            total_distance=metrics['total_distance'],
            x_axis_distance=metrics['x_axis_distance'],
            y_axis_distance=metrics['y_axis_distance'],
            x_flips=metrics['x_flips'],
            y_flips=metrics['y_flips'],
            meaningful_clicks=metrics['meaningful_clicks'],
            duration_seconds=metrics['duration'],
            movement_time_span=metrics['movement_span'],
            init_time_avg=0,  # Cần thêm tính toán
            react_time_avg=0,  # Cần thêm tính toán
            alerts=metrics['alerts'],
            is_suspicious=metrics['is_suspicious']
        )

        return result
