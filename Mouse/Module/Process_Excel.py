import pandas as pd
import os
import glob
from datetime import datetime
from typing import Optional, List
from Mouse.Models.MouseResult import MouseResult


class MouseExcelHandler:
    """Xử lý Mouse data với Global Logger"""

    def __init__(self, user_name, global_logger=None):
        self.user_name = user_name
        self.global_logger = global_logger
        print(f"🖱️ Mouse handler for user: {user_name}")
        print(f"✅ Global logger in handler: {'ACTIVE' if self.global_logger else 'INACTIVE'}")

    def log_session_data(self, sessions):
        """Ghi log dữ liệu sessions - hỗ trợ cả list, dict và object"""
        if not sessions:
            print("⚠️ No mouse sessions to log")
            return

        # Chuyển đổi sessions thành list nếu cần
        if not isinstance(sessions, list):
            sessions = [sessions]

        print(f"📊 Processing {len(sessions)} mouse sessions...")

        processed_count = 0
        for i, session in enumerate(sessions):
            try:
                session_data = {}
                is_fraud = False
                anomaly_score = 0.0

                # Xử lý nếu session là MouseResult object
                if hasattr(session, 'total_events'):
                    session_data = self._extract_from_object(session)
                    is_fraud = session.is_suspicious
                    anomaly_score = session.anomaly_score

                # Xử lý nếu session là dict
                elif isinstance(session, dict):
                    session_data = self._extract_from_dict(session)
                    is_fraud = session.get('is_suspicious', False)
                    anomaly_score = session.get('anomaly_score', 0.0)

                else:
                    print(f"⚠️ Unknown session type {i + 1}: {type(session)}")
                    continue

                # Xác định severity
                if is_fraud:
                    severity = "CRITICAL" if anomaly_score > 0.8 else "WARNING"
                else:
                    severity = "INFO"

                # Ghi vào global logger - LUÔN GHI CẢ BÌNH THƯỜNG LẪN GIAN LẬN
                if self.global_logger and session_data:
                    self.global_logger.log_mouse_details(
                        event_type="MOUSE_SESSION",
                        details=f"Mouse session {i + 1} - Score: {anomaly_score:.3f}",
                        severity=severity,
                        is_fraud=is_fraud,
                        **session_data
                    )
                    processed_count += 1
                    print(f"✅ Logged mouse session {i + 1} (Fraud: {is_fraud}, Score: {anomaly_score:.3f})")

                    # NẾU LÀ GIAN LẬN, THÌ LOG THÊM VÀO FRAUD EVENTS
                    if is_fraud:
                        self.global_logger.log_alert(
                            "Mouse",
                            "ANOMALY_DETECTED",
                            f"Mouse anomaly detected - Score: {anomaly_score:.3f}",
                            severity,
                            is_fraud=True
                        )

            except Exception as e:
                print(f"❌ Error processing session {i + 1}: {e}")
                import traceback
                traceback.print_exc()
                continue

        print(f"✅ Successfully processed {processed_count}/{len(sessions)} mouse sessions")

        # LƯU NGAY SAU KHI LOG
        if self.global_logger and processed_count > 0:
            self.global_logger.save_to_excel()

        return processed_count

    def _extract_from_object(self, session) -> dict:
        """Trích xuất dữ liệu từ MouseResult object"""
        return {
            "TotalEvents": session.total_events,
            "TotalMoves": session.total_moves,
            "TotalDistance": round(session.total_distance, 2),
            "XAxisDistance": round(session.x_axis_distance, 2),
            "YAxisDistance": round(session.y_axis_distance, 2),
            "XFlips": session.x_flips,
            "YFlips": session.y_flips,
            "MovementTimeSpan": round(session.movement_time_span, 2),
            "Velocity": round(session.velocity_ui, 2),
            "Acceleration": round(session.acceleration_ui, 2),
            "XVelocity": round(session.x_axis_velocity_ui, 2),
            "YVelocity": round(session.y_axis_velocity_ui, 2),
            "XAcceleration": round(session.x_axis_acceleration_ui, 2),
            "YAcceleration": round(session.y_axis_acceleration_ui, 2),
            "DurationSeconds": round(session.duration_seconds, 2),
            "AnomalyScore": round(session.anomaly_score, 3)
        }

    def _extract_from_dict(self, session: dict) -> dict:
        """Trích xuất dữ liệu từ dict"""
        session_data = {}
        keys = [
            'TotalEvents', 'TotalMoves', 'TotalDistance', 'XAxisDistance',
            'YAxisDistance', 'XFlips', 'YFlips', 'MovementTimeSpan',
            'Velocity', 'Acceleration', 'XVelocity', 'YVelocity',
            'XAcceleration', 'YAcceleration', 'DurationSeconds', 'AnomalyScore'
        ]

        for key in keys:
            if key in session:
                value = session[key]
                # Làm tròn số nếu là float
                if isinstance(value, (int, float)):
                    session_data[key] = round(float(value), 2) if key != 'AnomalyScore' else round(float(value), 3)
                else:
                    session_data[key] = value

        return session_data

    @classmethod
    def load_training_data(cls, user_name) -> Optional[pd.DataFrame]:
        """Đọc dữ liệu training từ file Excel"""
        BASE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Saved_file"
        user_dir = os.path.join(BASE_DIR, user_name)

        if not os.path.exists(user_dir):
            print(f"❌ User directory not found: {user_dir}")
            return None

        # Tìm tất cả thư mục tháng
        month_dirs = []
        for item in os.listdir(user_dir):
            full_path = os.path.join(user_dir, item)
            if os.path.isdir(full_path) and item.count('_') == 1:
                try:
                    year, month = item.split('_')
                    int(year), int(month)
                    month_dirs.append(full_path)
                except:
                    continue

        if not month_dirs:
            print(f"⚠️ No monthly directories found")
            return None

        print(f"📚 Found {len(month_dirs)} monthly directories")

        df_list = []

        # Đọc từ tất cả thư mục tháng
        for month_dir in month_dirs:
            excel_files = glob.glob(os.path.join(month_dir, f"work_logs_{user_name}_*.xlsx"))

            for file in excel_files:
                try:
                    # Đọc sheet Mouse_Details
                    df = pd.read_excel(file, sheet_name='Mouse_Details')

                    # Chỉ lấy các cột cần thiết
                    mouse_features = [
                        'Velocity', 'Acceleration', 'XFlips', 'YFlips',
                        'TotalDistance', 'MovementTimeSpan', 'XVelocity', 'YVelocity',
                        'XAxisDistance', 'YAxisDistance', 'AnomalyScore'
                    ]

                    available_cols = [col for col in mouse_features if col in df.columns]
                    if available_cols:
                        df = df[available_cols].dropna()
                        if not df.empty:
                            df_list.append(df)
                except Exception as e:
                    print(f"⚠️ Error reading {file}: {e}")
                    continue

        if not df_list:
            print("⚠️ No mouse training data found")
            return None

        final_df = pd.concat(df_list, ignore_index=True)
        print(f"✅ Loaded {len(final_df)} rows of mouse data from {len(df_list)} files")

        # Loại bỏ idle sessions
        if 'TotalDistance' in final_df.columns:
            final_df = final_df[final_df['TotalDistance'] > 10]
            print(f"✅ After filtering idle sessions: {len(final_df)} rows")

        return final_df

    def save_final_data(self):
        """Lưu dữ liệu cuối cùng"""
        if self.global_logger:
            self.global_logger.save_final_data()
        print(f"✅ Final mouse data saved for user: {self.user_name}")