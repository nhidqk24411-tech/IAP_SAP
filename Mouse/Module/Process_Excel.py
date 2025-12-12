"""
Đọc/ghi file Excel với metrics mới - CHỈ DI CHUYỂN
"""
import pandas as pd
from typing import List, Dict, Any
from Mouse.Models.MouseResult import MouseResult
import os


class MouseExcelHandler:
    """Xử lý Excel cho dữ liệu chuột - CHỈ DI CHUYỂN"""

    @staticmethod
    def export_multiple_sessions(sessions: List[MouseResult], filename_prefix: str = "mouse_analysis"):
        """
        Xuất nhiều sessions vào một file Excel

        Args:
            sessions: Danh sách MouseResult
            filename_prefix: Tiền tố tên file

        Returns:
            str: Đường dẫn file đã lưu, hoặc None nếu lỗi
        """
        try:
            # Tạo thư mục nếu chưa có
            saved_dir = "Saved_file"
            os.makedirs(saved_dir, exist_ok=True)

            # Tạo tên file với timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.xlsx"
            filepath = os.path.join(saved_dir, filename)

            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # 1. Sheet tất cả sessions
                all_data = []
                for session in sessions:
                    data = session.to_dict()
                    data['AlertCount'] = len(session.alerts)
                    data['HasCriticalAlert'] = any(a['level'] in ['CRITICAL', 'HIGH'] for a in session.alerts)
                    all_data.append(data)

                df_all = pd.DataFrame(all_data)
                df_all.to_excel(writer, sheet_name='All_Sessions', index=False)

                # 2. Sheet summary
                MouseExcelHandler._write_summary_sheet(writer, sessions)

                # 3. Sheet alerts (nếu có)
                alert_sessions = [s for s in sessions if s.alerts]
                if alert_sessions:
                    MouseExcelHandler._write_alerts_sheet(writer, alert_sessions)

                # 4. Sheet metrics mẫu (session đầu tiên)
                if sessions:
                    MouseExcelHandler._write_detailed_metrics(writer, sessions[0])

            print(f"✅ Đã xuất {len(sessions)} sessions vào: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Lỗi xuất nhiều sessions: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def _write_summary_sheet(writer, sessions: List[MouseResult]):
        """Viết sheet summary"""
        try:
            if not sessions:
                return

            total = len(sessions)
            anomaly_sessions = sum(1 for r in sessions if r.anomaly_score > 0.7)  # Ngưỡng mặc định
            alert_sessions = sum(1 for r in sessions if r.alerts)

            summary_data = {
                'Metric': [
                    'Tổng số phiên',
                    'Tổng thời gian (phút)',
                    'Phiên bất thường',
                    'Phiên có cảnh báo',
                    'Tổng số events',
                    'Tổng quãng đường (px)',
                    'Vận tốc trung bình (px/s)',
                    'Tỉ lệ bất thường'
                ],
                'Value': [
                    total,
                    sum(r.duration_seconds for r in sessions) / 60,
                    anomaly_sessions,
                    alert_sessions,
                    sum(r.total_events for r in sessions),
                    sum(r.total_distance for r in sessions),
                    sum(r.velocity_ui for r in sessions) / max(total, 1),
                    f"{anomaly_sessions / max(total, 1) * 100:.1f}%"
                ]
            }

            df_summary = pd.DataFrame(summary_data)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)

        except Exception as e:
            print(f"⚠️ Lỗi viết summary sheet: {e}")

    @staticmethod
    def _write_alerts_sheet(writer, sessions: List[MouseResult]):
        """Viết sheet alerts"""
        try:
            alert_rows = []
            for session in sessions:
                for alert in session.alerts:
                    alert_rows.append({
                        'Session_ID': session.session_id,
                        'Alert_Level': alert.get('level', 'UNKNOWN'),
                        'Alert_Type': alert.get('type', 'UNKNOWN'),
                        'Message': alert.get('message', ''),
                        'Anomaly_Score': session.anomaly_score,
                        'Timestamp': session.start_time.strftime('%Y-%m-%d %H:%M:%S')
                    })

            if alert_rows:
                df_alerts = pd.DataFrame(alert_rows)
                df_alerts.to_excel(writer, sheet_name='Alerts', index=False)

        except Exception as e:
            print(f"⚠️ Lỗi viết alerts sheet: {e}")

    @staticmethod
    def _write_detailed_metrics(writer, session: MouseResult):
        """Viết sheet metrics chi tiết (mẫu từ 1 session)"""
        try:
            metrics_data = {
                'Metric': [
                    'Total Distance', 'X Distance', 'Y Distance',
                    'Movement Time Span', 'Total Duration',
                    'X Flips', 'Y Flips', 'Max Deviation',
                    'Average Velocity', 'Average Acceleration',
                    'X Axis Velocity', 'Y Axis Velocity',
                    'X Axis Acceleration', 'Y Axis Acceleration'
                ],
                'Value': [
                    session.total_distance,
                    session.x_axis_distance,
                    session.y_axis_distance,
                    session.movement_time_span,
                    session.duration_seconds,
                    session.x_flips,
                    session.y_flips,
                    session.max_deviation_ui,
                    session.velocity_ui,
                    session.acceleration_ui,
                    getattr(session, 'x_axis_velocity_ui', 0),
                    getattr(session, 'y_axis_velocity_ui', 0),
                    getattr(session, 'x_axis_acceleration_ui', 0),
                    getattr(session, 'y_axis_acceleration_ui', 0)
                ],
                'Description': [
                    'Tổng quãng đường di chuyển (px)',
                    'Quãng đường trục X (px)',
                    'Quãng đường trục Y (px)',
                    'Thời gian di chuyển (s)',
                    'Tổng thời gian session (s)',
                    'Số lần đổi hướng trục X',
                    'Số lần đổi hướng trục Y',
                    'Độ lệch tối đa so với đường thẳng (px)',
                    'Vận tốc trung bình (px/s)',
                    'Gia tốc trung bình (px/s²)',
                    'Vận tốc trung bình trục X (px/s)',
                    'Vận tốc trung bình trục Y (px/s)',
                    'Gia tốc trung bình trục X (px/s²)',
                    'Gia tốc trung bình trục Y (px/s²)'
                ]
            }

            df_metrics = pd.DataFrame(metrics_data)
            df_metrics.to_excel(writer, sheet_name='Metrics_Detail', index=False)

        except Exception as e:
            print(f"⚠️ Lỗi viết metrics sheet: {e}")