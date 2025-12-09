from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional
from .MouseEvents import MouseEvent


@dataclass
class MouseResult:
    """Class chứa kết quả phân tích chuột"""
    # Thông tin session
    session_id: str
    start_time: datetime
    end_time: datetime

    # Thống kê cơ bản
    total_events: int
    total_moves: int
    total_clicks: int
    total_scrolls: int

    # Metrics tính toán từ công thức
    total_distance: float  # Công thức (6)
    x_axis_distance: float  # Công thức (7)
    y_axis_distance: float  # Công thức (8)
    x_flips: int  # Công thức (15)
    y_flips: int  # Công thức (17)
    meaningful_clicks: int  # Click có ý nghĩa

    # Thời gian
    duration_seconds: float  # Công thức (2)
    movement_time_span: float  # Công thức (3)
    init_time_avg: float  # Công thức (4) trung bình
    react_time_avg: float  # Công thức (5) trung bình

    # Phát hiện bất thường
    alerts: List[Dict]  # Danh sách cảnh báo
    is_suspicious: bool  # Có đáng ngờ không

    def to_dict(self) -> Dict:
        """Chuyển thành dictionary để ghi Excel"""
        return {
            'SessionID': self.session_id,
            'StartTime': self.start_time,
            'EndTime': self.end_time,
            'Duration(s)': self.duration_seconds,
            'TotalEvents': self.total_events,
            'TotalMoves': self.total_moves,
            'TotalClicks': self.total_clicks,
            'TotalScrolls': self.total_scrolls,
            'TotalDistance': round(self.total_distance, 2),
            'XAxisDistance': round(self.x_axis_distance, 2),
            'YAxisDistance': round(self.y_axis_distance, 2),
            'XFlips': self.x_flips,
            'YFlips': self.y_flips,
            'MeaningfulClicks': self.meaningful_clicks,
            'MovementTimeSpan': round(self.movement_time_span, 2),
            'InitTimeAvg': round(self.init_time_avg, 2),
            'ReactTimeAvg': round(self.react_time_avg, 2),
            'IsSuspicious': 'YES' if self.is_suspicious else 'NO',
            'AlertCount': len(self.alerts)
        }

    def print_summary(self):
        """In summary ra console"""
        print("\n" + "=" * 50)
        print("MOUSE ANALYSIS RESULT")
        print("=" * 50)
        print(f"Session: {self.session_id}")
        print(f"Duration: {self.duration_seconds:.1f}s")
        print(f"Events: {self.total_events} (Moves: {self.total_moves}, Clicks: {self.total_clicks})")
        print(f"Distance: {self.total_distance:.1f}px (X: {self.x_axis_distance:.1f}, Y: {self.y_axis_distance:.1f})")
        print(f"Flips: X={self.x_flips}, Y={self.y_flips}")
        print(f"Meaningful Clicks: {self.meaningful_clicks}")
        print(f"Suspicious: {'YES ⚠️' if self.is_suspicious else 'NO ✅'}")

        if self.alerts:
            print(f"\nAlerts ({len(self.alerts)}):")
            for i, alert in enumerate(self.alerts[:3], 1):  # Hiển thị 3 alerts đầu
                print(f"  {i}. [{alert['level']}] {alert['type']}: {alert['message']}")
            if len(self.alerts) > 3:
                print(f"  ... and {len(self.alerts) - 3} more alerts")
        print("=" * 50)