from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional


# KHÔNG import MouseEvents nếu không cần


@dataclass
class MouseResult:
    """Class chứa kết quả phân tích chuột - CHỈ DI CHUYỂN"""
    # Thông tin session
    session_id: str
    start_time: datetime
    end_time: datetime

    # Thống kê cơ bản - CHỈ CÒN MOVE
    total_events: int  # Tổng số sự kiện (chỉ MOVE)
    total_moves: int  # Số lần di chuyển
    # ĐÃ XÓA: total_clicks, total_scrolls, meaningful_clicks

    # Metrics tính toán từ công thức
    total_distance: float
    x_axis_distance: float
    y_axis_distance: float
    x_flips: int
    y_flips: int
    # ĐÃ XÓA: meaningful_clicks

    # Metrics mới từ công thức
    velocity_ui: float
    x_axis_velocity_ui: float
    y_axis_velocity_ui: float
    acceleration_ui: float
    x_axis_acceleration_ui: float
    y_axis_acceleration_ui: float
    #max_deviation_ui: float

    # Thời gian
    duration_seconds: float
    movement_time_span: float
    init_time_avg: float
    react_time_avg: float

    # Phát hiện bất thường
    alerts: List[Dict]  # Danh sách cảnh báo
    is_suspicious: bool  # Có đáng ngờ không
    anomaly_score: float = 0.0  # Điểm bất thường từ XGBoost

    def to_dict(self) -> Dict:
        """Chuyển thành dictionary để ghi Excel - ĐÃ CẬP NHẬT"""
        return {
            'SessionID': self.session_id,
            'StartTime': self.start_time,
            'EndTime': self.end_time,
            'Duration(s)': self.duration_seconds,
            'TotalEvents': self.total_events,
            'TotalMoves': self.total_moves,
            # ĐÃ XÓA: TotalClicks, TotalScrolls, MeaningfulClicks
            'TotalDistance': round(self.total_distance, 2),
            'XAxisDistance': round(self.x_axis_distance, 2),
            'YAxisDistance': round(self.y_axis_distance, 2),
            'XFlips': self.x_flips,
            'YFlips': self.y_flips,
            'MovementTimeSpan': round(self.movement_time_span, 2),
            'InitTimeAvg': round(self.init_time_avg, 2),
            'ReactTimeAvg': round(self.react_time_avg, 2),
            'Velocity': round(self.velocity_ui, 2),
            'Acceleration': round(self.acceleration_ui, 2),
            #'MaxDeviation': round(self.max_deviation_ui, 2),
            'AnomalyScore': round(self.anomaly_score, 3),
            'IsSuspicious': 'YES' if self.is_suspicious else 'NO',
            'AlertCount': len(self.alerts)
        }
