import math
import numpy as np
from typing import List, Tuple
from Mouse.Models.MouseEvents import MouseEvent


class RealTimeProcessor:
    """Xử lý và tính toán metrics real-time THEO RESEARCH PAPER"""

    def calculate_all_metrics(self, events: List[MouseEvent]) -> dict:
        if len(events) < 2:
            return {}

        # 1. Tính toán cơ bản (ĐÚNG theo paper)
        total_dist = self._calculate_distance(events)  # Công thức (6)
        x_dist = sum(abs(events[i + 1].x - events[i].x) for i in range(len(events) - 1))  # (7)
        y_dist = sum(abs(events[i + 1].y - events[i].y) for i in range(len(events) - 1))  # (8)

        # 2. Thời gian (ĐÚNG theo paper)
        time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()  # Công thức (3)
        duration = time_span

        # 3. Flips (SỬA theo paper)
        x_flips, y_flips = self._calculate_flips_paper(events)  # Công thức (14)-(17)

        # 4. Velocity (SỬA theo paper)
        velocity_metrics = self._calculate_velocity_paper(events)  # Công thức (18)-(20)

        # 5. Acceleration (SỬA theo paper)
        acceleration_metrics = self._calculate_acceleration_paper(events)  # Công thức (21)-(23)

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
            **velocity_metrics,
            **acceleration_metrics
        }

    def _calculate_distance(self, events: List[MouseEvent]) -> float:
        """Công thức (6): Tổng khoảng cách Euclidean"""
        return sum(math.sqrt((events[i + 1].x - events[i].x) ** 2 +
                             (events[i + 1].y - events[i].y) ** 2)
                   for i in range(len(events) - 1))

    def _calculate_flips_paper(self, events: List[MouseEvent]) -> Tuple[int, int]:
        """
        Công thức (14)-(17): Tính số lần đổi hướng theo paper
        """
        if len(events) < 3:
            return 0, 0

        x_flips, y_flips = 0, 0
        prev_dir_x, prev_dir_y = 0, 0

        for i in range(1, len(events)):
            # Tính direction cho x (công thức 14)
            if events[i].x > events[i - 1].x:
                dir_x = 1
            elif events[i].x < events[i - 1].x:
                dir_x = -1
            else:
                dir_x = 0

            # Tính direction cho y (công thức 16)
            if events[i].y > events[i - 1].y:
                dir_y = 1
            elif events[i].y < events[i - 1].y:
                dir_y = -1
            else:
                dir_y = 0

            # Tính flips (công thức 15, 17)
            if i > 1:  # Cần ít nhất 2 directions để so sánh
                # X-flip: đổi từ +1 sang -1 hoặc -1 sang +1
                if (prev_dir_x == 1 and dir_x == -1) or (prev_dir_x == -1 and dir_x == 1):
                    x_flips += 1

                # Y-flip: đổi từ +1 sang -1 hoặc -1 sang +1
                if (prev_dir_y == 1 and dir_y == -1) or (prev_dir_y == -1 and dir_y == 1):
                    y_flips += 1

            prev_dir_x, prev_dir_y = dir_x, dir_y

        return x_flips, y_flips

    def _calculate_velocity_paper(self, events: List[MouseEvent]) -> dict:
        """
        Công thức (18)-(20): Tính velocity theo paper
        velocity = Δdistance / Δmovement_time_span
        """
        if len(events) < 2:
            return {
                'velocity_ui': 0,
                'x_axis_velocity_ui': 0,
                'y_axis_velocity_ui': 0
            }

        # Tính tổng distance
        total_distance = self._calculate_distance(events)
        x_distance = sum(abs(events[i + 1].x - events[i].x) for i in range(len(events) - 1))
        y_distance = sum(abs(events[i + 1].y - events[i].y) for i in range(len(events) - 1))

        # Tính movement_time_span
        movement_time_span = (events[-1].timestamp - events[0].timestamp).total_seconds()

        if movement_time_span <= 0:
            return {
                'velocity_ui': 0,
                'x_axis_velocity_ui': 0,
                'y_axis_velocity_ui': 0
            }

        # Áp dụng công thức paper
        velocity = total_distance / movement_time_span
        x_axis_velocity = x_distance / movement_time_span
        y_axis_velocity = y_distance / movement_time_span

        return {
            'velocity_ui': velocity,
            'x_axis_velocity_ui': x_axis_velocity,
            'y_axis_velocity_ui': y_axis_velocity
        }

    def _calculate_acceleration_paper(self, events: List[MouseEvent]) -> dict:
        """
        Công thức (21)-(23): Tính acceleration theo paper
        acceleration = Δvelocity / Δmovement_time_span

        Paper không rõ Δvelocity tính thế nào.
        Implementation: Chia làm 2 nửa, tính velocity mỗi nửa
        """
        if len(events) < 3:
            return {
                'acceleration_ui': 0,
                'x_axis_acceleration_ui': 0,
                'y_axis_acceleration_ui': 0
            }

        # Chia events thành 2 nửa
        mid_idx = len(events) // 2

        # Tính velocity cho nửa đầu
        first_half = events[:mid_idx + 1]
        if len(first_half) < 2:
            return {
                'acceleration_ui': 0,
                'x_axis_acceleration_ui': 0,
                'y_axis_acceleration_ui': 0
            }

        v1_metrics = self._calculate_velocity_paper(first_half)
        v1 = v1_metrics['velocity_ui']
        vx1 = v1_metrics['x_axis_velocity_ui']
        vy1 = v1_metrics['y_axis_velocity_ui']

        # Tính velocity cho nửa sau
        second_half = events[mid_idx:]
        if len(second_half) < 2:
            return {
                'acceleration_ui': 0,
                'x_axis_acceleration_ui': 0,
                'y_axis_acceleration_ui': 0
            }

        v2_metrics = self._calculate_velocity_paper(second_half)
        v2 = v2_metrics['velocity_ui']
        vx2 = v2_metrics['x_axis_velocity_ui']
        vy2 = v2_metrics['y_axis_velocity_ui']

        # Tính Δmovement_time_span (khoảng thời gian giữa 2 nửa)
        total_time = (events[-1].timestamp - events[0].timestamp).total_seconds()
        if total_time <= 0:
            return {
                'acceleration_ui': 0,
                'x_axis_acceleration_ui': 0,
                'y_axis_acceleration_ui': 0
            }

        # Thời gian mỗi nửa (xấp xỉ)
        time_first = (first_half[-1].timestamp - first_half[0].timestamp).total_seconds()
        time_second = (second_half[-1].timestamp - second_half[0].timestamp).total_seconds()
        avg_time = (time_first + time_second) / 2

        if avg_time <= 0:
            return {
                'acceleration_ui': 0,
                'x_axis_acceleration_ui': 0,
                'y_axis_acceleration_ui': 0
            }

        # Áp dụng công thức paper (21), (22), (23)
        acceleration = (v2 - v1) / avg_time
        x_acceleration = (vx2 - vx1) / avg_time
        y_acceleration = (vy2 - vy1) / avg_time

        return {
            'acceleration_ui': abs(acceleration),
            'x_axis_acceleration_ui': abs(x_acceleration),
            'y_axis_acceleration_ui': abs(y_acceleration)
        }