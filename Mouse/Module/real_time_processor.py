import math
import numpy as np
from typing import List, Tuple
from Mouse.Models.MouseEvents import MouseEvent


class RealTimeProcessor:
    """Xử lý và tính toán metrics real-time"""

    def calculate_all_metrics(self, events: List[MouseEvent]) -> dict:
        if len(events) < 2:
            return {}

        # 1. Tính toán cơ bản
        total_dist = self._calculate_distance(events)
        x_dist = sum(abs(events[i + 1].x - events[i].x) for i in range(len(events) - 1))
        y_dist = sum(abs(events[i + 1].y - events[i].y) for i in range(len(events) - 1))

        # 2. Thời gian
        time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()
        duration = time_span  # Trong ngữ cảnh này coi như bằng nhau

        # 3. Flips (Đổi hướng)
        x_flips, y_flips = self._calculate_flips(events)

        # 4. Vận tốc & Gia tốc
        vel_acc_metrics = self._calculate_dynamics(events)

        return {
            'total_events': len(events),
            'total_moves': len(events),
            'distance_ui': total_dist,
            'x_axis_distance_ui': x_dist,
            'y_axis_distance_ui': y_dist,
            'movement_time_span_ui': time_span,
            'duration_ui': duration,
            'x_flips_ui': x_flips,
            'y_flips_ui': y_flips,
            **vel_acc_metrics
        }

    def _calculate_distance(self, events: List[MouseEvent]) -> float:
        return sum(math.sqrt((events[i + 1].x - events[i].x) ** 2 +
                             (events[i + 1].y - events[i].y) ** 2)
                   for i in range(len(events) - 1))

    def _calculate_flips(self, events: List[MouseEvent]) -> Tuple[int, int]:
        if len(events) < 3: return 0, 0
        x_flips, y_flips = 0, 0

        # Lấy diff để xác định hướng: +1 tăng, -1 giảm
        dx = np.diff([e.x for e in events])
        dy = np.diff([e.y for e in events])

        # Sign bit: chuyển thành dấu (-1, 0, 1)
        x_signs = np.sign(dx)
        y_signs = np.sign(dy)

        # Loại bỏ các đoạn đứng yên (0) để tính flip chính xác hơn
        x_signs = x_signs[x_signs != 0]
        y_signs = y_signs[y_signs != 0]

        # Đếm số lần đổi dấu
        if len(x_signs) > 1:
            x_flips = np.sum(np.diff(x_signs) != 0)
        if len(y_signs) > 1:
            y_flips = np.sum(np.diff(y_signs) != 0)

        return int(x_flips), int(y_flips)

    def _calculate_dynamics(self, events: List[MouseEvent]) -> dict:
        velocities = []
        x_vels, y_vels = [], []

        for i in range(len(events) - 1):
            dt = (events[i + 1].timestamp - events[i].timestamp).total_seconds()
            if dt <= 0: continue

            dx = events[i + 1].x - events[i].x
            dy = events[i + 1].y - events[i].y
            dist = math.sqrt(dx ** 2 + dy ** 2)

            velocities.append(dist / dt)
            x_vels.append(abs(dx) / dt)
            y_vels.append(abs(dy) / dt)

        # Tính trung bình vận tốc
        avg_v = np.mean(velocities) if velocities else 0
        avg_vx = np.mean(x_vels) if x_vels else 0
        avg_vy = np.mean(y_vels) if y_vels else 0

        # Tính gia tốc từ mảng vận tốc
        accels = np.diff(velocities) if len(velocities) > 1 else []
        # Lưu ý: cần chia cho dt tương ứng, ở đây lấy trung bình giản lược cho UI
        avg_a = np.mean(np.abs(accels)) if len(accels) > 0 else 0

        return {
            'velocity_ui': avg_v,
            'x_axis_velocity_ui': avg_vx,
            'y_axis_velocity_ui': avg_vy,
            'acceleration_ui': avg_a,  # Simplified
            'x_axis_acceleration_ui': 0,  # Placeholder nếu cần chi tiết
            'y_axis_acceleration_ui': 0  # Placeholder
        }