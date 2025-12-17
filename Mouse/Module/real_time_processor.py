"""
Module xử lý dữ liệu real-time - CHỈ DI CHUYỂN
"""
import math
import numpy as np
from typing import List, Tuple
from Mouse.Models.MouseEvents import MouseEvent, EventType
from datetime import datetime


class RealTimeProcessor:
    """Xử lý và tính toán metrics real-time - CHỈ DI CHUYỂN"""

    def calculate_all_metrics(self, events: List[MouseEvent], next_button_position: Tuple[int, int]) -> dict:
        """
        Tính toán tất cả metrics theo công thức mới - CHỈ DI CHUYỂN

        Args:
            events: Danh sách sự kiện di chuyển (TẤT CẢ ĐỀU LÀ MOVE)
            next_button_position: Vị trí nút Next (x, y)

        Returns:
            dict: Tất cả metrics
        """
        if len(events) < 2:
            return {}

        # TẤT CẢ events đều là move events (đã filter ở tracker)
        move_events = events

        # 1. Công thức (6): Tổng quãng đường di chuyển
        distance_ui = self._calculate_distance_ui(move_events)

        # 2. Công thức (7): Quãng đường trục X
        x_axis_distance_ui = self._calculate_x_axis_distance(move_events)

        # 3. Công thức (8): Quãng đường trục Y
        y_axis_distance_ui = self._calculate_y_axis_distance(move_events)

        # 4. Công thức (3): Thời gian di chuyển
        movement_time_span_ui = self._calculate_movement_time_span(move_events)

        # 5. Công thức (14-17): Số lần đổi hướng
        x_flips_ui, y_flips_ui = self._calculate_direction_flips(move_events)

        # 6. Thời gian tổng
        duration_ui = self._calculate_total_duration(events)

        # 7. Công thức (11-12): Độ lệch tối đa so với đường đi lý tưởng
        # initial_pos = (move_events[0].x, move_events[0].y) if move_events else (0, 0)
        # max_deviation_ui = self._calculate_max_deviation(
        #     move_events,
        #     initial_pos,
        #     next_button_position
        # )

        # 8. Công thức (18-23): Vận tốc và gia tốc
        velocity_metrics = self._calculate_velocity_acceleration(move_events)

        # 9. Độ tin cậy (confidence score)
        confidence = self._calculate_confidence(
            len(move_events),
            distance_ui,
            movement_time_span_ui
        )

        return {
            'total_events': len(events),
            'total_moves': len(move_events),
            'distance_ui': distance_ui,
            'x_axis_distance_ui': x_axis_distance_ui,
            'y_axis_distance_ui': y_axis_distance_ui,
            'movement_time_span_ui': movement_time_span_ui,
            'duration_ui': duration_ui,
            'x_flips_ui': x_flips_ui,
            'y_flips_ui': y_flips_ui,
            # 'max_deviation_ui': max_deviation_ui,
            'confidence': confidence,
            **velocity_metrics
        }

    def _calculate_distance_ui(self, move_events: List[MouseEvent]) -> float:
        """Công thức (6): Tổng quãng đường di chuyển"""
        total_distance = 0
        for i in range(len(move_events) - 1):
            x1, y1 = move_events[i].x, move_events[i].y
            x2, y2 = move_events[i + 1].x, move_events[i + 1].y
            dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            total_distance += dist
        return total_distance

    def _calculate_x_axis_distance(self, move_events: List[MouseEvent]) -> float:
        """Công thức (7): Quãng đường trục X"""
        x_distance = 0
        for i in range(len(move_events) - 1):
            x_distance += abs(move_events[i + 1].x - move_events[i].x)
        return x_distance

    def _calculate_y_axis_distance(self, move_events: List[MouseEvent]) -> float:
        """Công thức (8): Quãng đường trục Y"""
        y_distance = 0
        for i in range(len(move_events) - 1):
            y_distance += abs(move_events[i + 1].y - move_events[i].y)
        return y_distance

    def _calculate_movement_time_span(self, move_events: List[MouseEvent]) -> float:
        """Công thức (3): Thời gian di chuyển"""
        if len(move_events) < 2:
            return 0
        return (move_events[-1].timestamp - move_events[0].timestamp).total_seconds()

    def _calculate_total_duration(self, events: List[MouseEvent]) -> float:
        """Tổng thời gian session"""
        if len(events) < 2:
            return 0
        return (events[-1].timestamp - events[0].timestamp).total_seconds()

    def _calculate_direction_flips(self, move_events: List[MouseEvent]) -> Tuple[int, int]:
        """Công thức (14-17): Số lần đổi hướng"""
        if len(move_events) < 3:
            return 0, 0

        x_flips, y_flips = 0, 0
        prev_x_dir, prev_y_dir = 0, 0

        for i in range(1, len(move_events)):
            x_curr, y_curr = move_events[i].x, move_events[i].y
            x_prev, y_prev = move_events[i - 1].x, move_events[i - 1].y

            # X direction (công thức 14)
            if x_curr > x_prev:
                x_dir = 1
            elif x_curr < x_prev:
                x_dir = -1
            else:
                x_dir = 0

            # Y direction (công thức 16)
            if y_curr > y_prev:
                y_dir = 1
            elif y_curr < y_prev:
                y_dir = -1
            else:
                y_dir = 0

            # Check flips (công thức 15, 17)
            if prev_x_dir != 0 and x_dir != 0 and prev_x_dir != x_dir:
                x_flips += 1
            if prev_y_dir != 0 and y_dir != 0 and prev_y_dir != y_dir:
                y_flips += 1

            prev_x_dir = x_dir
            prev_y_dir = y_dir

        return x_flips, y_flips

    # def _calculate_max_deviation(self, move_events: List[MouseEvent],
    #                              initial_pos: Tuple[int, int],
    #                              target_pos: Tuple[int, int]) -> float:
    #     """Công thức (11-12): Độ lệch tối đa so với đường đi lý tưởng"""
    #     if len(move_events) < 2:
    #         return 0
    #
    #     x_initial, y_initial = initial_pos
    #     x_target, y_target = target_pos
    #
    #     # Vector đường đi lý tưởng
    #     ideal_vector = np.array([x_target - x_initial, y_target - y_initial])
    #     ideal_length = np.linalg.norm(ideal_vector)
    #
    #     if ideal_length == 0:
    #         return 0
    #
    #     max_deviation = 0
    #
    #     for event in move_events:
    #         # Vector từ điểm đầu đến điểm hiện tại
    #         current_vector = np.array([event.x - x_initial, event.y - y_initial])
    #
    #         # Tính khoảng cách vuông góc (công thức 11)
    #         if ideal_length > 0:
    #             # Tính diện tích hình bình hành / độ dài vector lý tưởng
    #             cross_product = abs(
    #                 ideal_vector[0] * current_vector[1] - ideal_vector[1] * current_vector[0]
    #             )
    #             deviation = cross_product / ideal_length
    #             max_deviation = max(max_deviation, deviation)
    #
    #     return max_deviation

    def _calculate_velocity_acceleration(self, move_events: List[MouseEvent]) -> dict:
        """Công thức (18-23): Vận tốc và gia tốc"""
        if len(move_events) < 2:
            return {}

        velocities = []
        x_velocities = []
        y_velocities = []

        for i in range(len(move_events) - 1):
            # Khoảng cách
            dx = move_events[i + 1].x - move_events[i].x
            dy = move_events[i + 1].y - move_events[i].y
            distance = math.sqrt(dx ** 2 + dy ** 2)

            # Thời gian
            dt = (move_events[i + 1].timestamp - move_events[i].timestamp).total_seconds()
            if dt == 0:
                continue

            # Vận tốc (công thức 18-20)
            velocity = distance / dt
            x_velocity = abs(dx) / dt
            y_velocity = abs(dy) / dt

            velocities.append(velocity)
            x_velocities.append(x_velocity)
            y_velocities.append(y_velocity)

        # Tính trung bình
        avg_velocity = np.mean(velocities) if velocities else 0
        avg_x_velocity = np.mean(x_velocities) if x_velocities else 0
        avg_y_velocity = np.mean(y_velocities) if y_velocities else 0

        # Tính gia tốc (công thức 21-23)
        accelerations = []
        x_accelerations = []
        y_accelerations = []

        for i in range(len(velocities) - 1):
            dt_acc = (move_events[i + 2].timestamp - move_events[i + 1].timestamp).total_seconds()
            if dt_acc == 0:
                continue

            dv = velocities[i + 1] - velocities[i]
            dv_x = x_velocities[i + 1] - x_velocities[i] if i + 1 < len(x_velocities) else 0
            dv_y = y_velocities[i + 1] - y_velocities[i] if i + 1 < len(y_velocities) else 0

            accelerations.append(dv / dt_acc)
            x_accelerations.append(dv_x / dt_acc)
            y_accelerations.append(dv_y / dt_acc)

        avg_acceleration = np.mean(accelerations) if accelerations else 0
        avg_x_acceleration = np.mean(x_accelerations) if x_accelerations else 0
        avg_y_acceleration = np.mean(y_accelerations) if y_accelerations else 0

        return {
            'velocity_ui': avg_velocity,
            'x_axis_velocity_ui': avg_x_velocity,
            'y_axis_velocity_ui': avg_y_velocity,
            'acceleration_ui': avg_acceleration,
            'x_axis_acceleration_ui': avg_x_acceleration,
            'y_axis_acceleration_ui': avg_y_acceleration
        }

    def _calculate_confidence(self, num_events: int, distance: float, time_span: float) -> float:
        """Tính độ tin cậy của dữ liệu"""
        if num_events == 0 or time_span == 0:
            return 0

        # Dựa trên mật độ events và quãng đường
        event_density = num_events / time_span if time_span > 0 else 0
        movement_intensity = distance / time_span if time_span > 0 else 0

        # Tính confidence score (0-1)
        confidence = min(1.0,
                         (event_density / 50) * 0.4 +  # Events per second
                         (movement_intensity / 100) * 0.4 +  # Pixels per second
                         (min(num_events, 100) / 100) * 0.2)  # Total events

        return max(0, min(1, confidence))