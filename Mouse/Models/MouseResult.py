from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict

@dataclass
class MouseResult:
    """Class chứa kết quả phân tích chuột - CHỈ DI CHUYỂN"""
    # Thông tin session
    session_id: str
    start_time: datetime
    end_time: datetime

    # Metrics cơ bản
    total_events: int
    total_moves: int

    # Metrics hình học & vật lý
    total_distance: float
    x_axis_distance: float
    y_axis_distance: float
    x_flips: int
    y_flips: int

    # Metrics động học (Velocity/Acceleration)
    velocity_ui: float
    x_axis_velocity_ui: float
    y_axis_velocity_ui: float
    acceleration_ui: float
    x_axis_acceleration_ui: float
    y_axis_acceleration_ui: float

    # Thời gian
    duration_seconds: float
    movement_time_span: float

    # Kết quả phân tích ML
    alerts: List[Dict]
    is_suspicious: bool
    anomaly_score: float = 0.0

    def to_dict(self) -> Dict:
        """Chuyển thành dictionary để ghi Excel"""
        return {
            'SessionID': self.session_id,
            'StartTime': self.start_time,
            'EndTime': self.end_time,
            'Duration(s)': round(self.duration_seconds, 2),
            'TotalEvents': self.total_events,
            'TotalMoves': self.total_moves,
            'TotalDistance': round(self.total_distance, 2),
            'XAxisDistance': round(self.x_axis_distance, 2),
            'YAxisDistance': round(self.y_axis_distance, 2),
            'XFlips': self.x_flips,
            'YFlips': self.y_flips,
            'MovementTimeSpan': round(self.movement_time_span, 2),
            'Velocity': round(self.velocity_ui, 2),
            'Acceleration': round(self.acceleration_ui, 2),
            'XVelocity': round(self.x_axis_velocity_ui, 2),
            'YVelocity': round(self.y_axis_velocity_ui, 2),
            'AnomalyScore': round(self.anomaly_score, 3),
            'IsSuspicious': 'YES' if self.is_suspicious else 'NO',
            'AlertCount': len(self.alerts)
        }