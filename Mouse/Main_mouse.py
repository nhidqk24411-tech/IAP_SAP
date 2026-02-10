import time
import signal
import sys
import pandas as pd
from datetime import datetime
import os

from Mouse.Module.real_time_tracker import RealTimeTracker
from Mouse.Module.real_time_processor import RealTimeProcessor
from Mouse.Module.Process_Excel import MouseExcelHandler
from ML_models.xgboost_anomaly import BehaviorModel
from Mouse.Models.MouseResult import MouseResult


class MouseAnalysisSystem:
    SESSION_DURATION = 60
    ANOMALY_THRESHOLD = 0.75

    def __init__(self, global_logger=None):  # THÊM THAM SỐ global_logger
        self.tracker = RealTimeTracker()
        self.processor = RealTimeProcessor()
        self.user_name = None
        self.global_logger = global_logger  # LƯU global_logger
        self.excel_handler = None
        self.ai_model = BehaviorModel()

        self.all_results = []
        self.fraud_sessions = []
        self.session_count = 0
        self.auto_save = True

        signal.signal(signal.SIGTERM, self._handle_exit)
        signal.signal(signal.SIGINT, self._handle_exit)

    def setup_user(self, user_name):
        """Thiết lập user cho mouse system - DÙNG global_logger"""
        self.user_name = user_name
        # TRUYỀN global_logger vào MouseExcelHandler
        self.excel_handler = MouseExcelHandler(user_name, self.global_logger)
        print(f"🖱️ Mouse system setup for user: {user_name}")

        # Khởi tạo model với user_name
        self._init_model()

    def _init_model(self):
        """Chỉ load model từ .pkl, KHÔNG train lại nếu đã có model"""
        print(f"\n🔍 Initializing AI Model for user: {self.user_name}")

        # Kiểm tra xem model đã được load từ .pkl chưa
        if self.ai_model.xgb_model is not None:
            print(f"✅ Model loaded from .pkl with {len(self.ai_model.selected_features)} features")
            print(f"✅ Features: {self.ai_model.selected_features}")
            return  # ĐÃ CÓ MODEL, KHÔNG CẦN TRAIN LẠI

        # Nếu không có model (file .pkl không tồn tại hoặc hỏng)
        print("⚠️ No model found in .pkl, loading training data...")

        # Chỉ load Excel để train khi KHÔNG có .pkl
        df_history = self.excel_handler.load_training_data(self.user_name)

        if df_history is not None and len(df_history) >= self.ai_model.MIN_TRAIN_SAMPLES:
            print(f"📊 Training with {len(df_history)} samples from Excel...")
            success = self.ai_model.train(df_history)
            if success:
                print("✅ Model trained from Excel data")
        else:
            print("⚠️ Insufficient Excel data. Model will learn from new sessions.")

    def run_continuous_analysis(self, stop_event, pause_event, command_queue, alert_queue, user_name=None,
                                global_logger=None):
        """Chạy phân tích liên tục với user_name - NHẬN global_logger"""

        # Thiết lập global_logger nếu được truyền vào
        if global_logger is not None:
            self.global_logger = global_logger

        # Thiết lập user nếu chưa được thiết lập
        if user_name and not self.user_name:
            self.setup_user(user_name)

        print("=" * 60)
        print(f"🛡️ MOUSE ANALYSIS SYSTEM STARTED for user: {self.user_name}")
        print(f"✅ Model status: {'TRAINED' if self.ai_model.xgb_model else 'NOT TRAINED'}")
        print(f"✅ Global logger: {'ACTIVE' if self.global_logger else 'INACTIVE'}")
        print("=" * 60)

        try:
            while not stop_event.is_set():
                # Kiểm tra pause
                if pause_event.is_set():
                    print("⏸️ Mouse tracking PAUSED (by timer)...")
                    while pause_event.is_set() and not stop_event.is_set():
                        time.sleep(0.5)
                    if stop_event.is_set():
                        break
                    print("▶️ Mouse tracking RESUMED (timer resumed)...")

                self.session_count += 1
                result = self._run_single_session(stop_event, pause_event)

                if result:
                    self.all_results.append(result)

                    # LOG SESSION VÀO GLOBAL LOGGER NGAY LẬP TỨC
                    if self.excel_handler:
                        self.excel_handler.log_session_data(result)
                        print(f"📝 Session {self.session_count} logged to global logger")

                    # Thêm vào fraud_sessions nếu có gian lận
                    if result.is_suspicious:
                        self.fraud_sessions.append(result)
                        print(f"🚨 ALERT: Anomaly detected (score: {result.anomaly_score:.3f})")

                        # LOG CẢNH BÁO GIAN LẬN
                        if self.global_logger:
                            self.global_logger.log_alert(
                                "Mouse",
                                "ANOMALY_DETECTED",
                                f"Mouse anomaly detected - Score: {result.anomaly_score:.3f}",
                                "CRITICAL",
                                is_fraud=True
                            )

                        # Gửi alert đến browser
                        try:
                            alert_data = {
                                'session_id': result.session_id,
                                'score': result.anomaly_score,
                                'timestamp': datetime.now().strftime("%H:%M:%S"),
                                'user': self.user_name
                            }
                            alert_queue.put(alert_data)
                            print("📨 Alert sent to browser")

                            # Đợi lệnh từ browser
                            print("⏳ Waiting for user confirmation...")
                            while pause_event.is_set() and not stop_event.is_set():
                                time.sleep(0.5)

                        except Exception as e:
                            print(f"⚠️ Error sending alert: {e}")
                    else:
                        # Hiển thị thông tin bình thường
                        print(f"📊 Session {self.session_count}: Normal (score: {result.anomaly_score:.3f})")

                    # Auto save mỗi 3 session (giảm từ 5 xuống 3 để lưu thường xuyên hơn)
                    if self.auto_save and len(self.all_results) >= 3:
                        self._save_sessions()
                        self.all_results = []
                        self.fraud_sessions = []

        finally:
            self._stop_and_save()
    # =========================
    # SINGLE SESSION (GIỮ NGUYÊN)
    # =========================
    def _run_single_session(self, stop_event, pause_event):
        events = self.tracker.collect_events(self.SESSION_DURATION, stop_event=stop_event, pause_event=pause_event)

        if not events:
            return None

        # Bỏ qua nếu quá ít sự kiện
        if len(events) < 5:
            print(f"⚠️ Not enough mouse events ({len(events)}), skipping session.")
            return None

        metrics = self.processor.calculate_all_metrics(events)
        metrics['raw_count'] = len(events)

        score = self.ai_model.predict(metrics)

        return self._create_result(metrics, score)

    # =========================
    # RESULT BUILD (GIỮ NGUYÊN)
    # =========================
    def _create_result(self, metrics, score):
        alerts = []

        # CHỈ THÊM ALERT KHI CÓ ANOMALY
        if score > self.ANOMALY_THRESHOLD:
            alerts.append({
                'type': 'ANOMALY',
                'message': f'Anomaly Behavior (score: {score:.2f})',
                'severity': 'HIGH'
            })

        return MouseResult(
            session_id=f"S_{datetime.now().strftime('%H%M%S')}_{self.session_count}",
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_events=metrics.get('raw_count', 0),
            total_moves=metrics.get('total_moves', 0),
            total_distance=metrics.get('distance_ui', 0),
            x_axis_distance=metrics.get('x_axis_distance_ui', 0),
            y_axis_distance=metrics.get('y_axis_distance_ui', 0),
            x_flips=metrics.get('x_flips_ui', 0),
            y_flips=metrics.get('y_flips_ui', 0),
            velocity_ui=metrics.get('velocity_ui', 0),
            acceleration_ui=metrics.get('acceleration_ui', 0),
            x_axis_velocity_ui=metrics.get('x_axis_velocity_ui', 0),
            y_axis_velocity_ui=metrics.get('y_axis_velocity_ui', 0),
            x_axis_acceleration_ui=metrics.get('x_axis_acceleration_ui', 0),
            y_axis_acceleration_ui=metrics.get('y_axis_acceleration_ui', 0),
            duration_seconds=metrics.get('duration_ui', self.SESSION_DURATION),
            movement_time_span=metrics.get('movement_time_span_ui', 0),
            alerts=alerts,
            is_suspicious=len(alerts) > 0,
            anomaly_score=score
        )

    def _save_sessions(self):
        """Lưu session data và fraud alerts"""
        print(f"\n💾 Auto-saving mouse data for user: {self.user_name}")

        # Lưu qua global logger
        if self.global_logger:
            self.global_logger.save_to_excel()
            print(f"✅ Data saved to global logger")

    # =========================
    # SAFE EXIT (ĐÃ SỬA)
    # =========================
    def _handle_exit(self, *args):
        print("⚠️ Forced exit detected.")
        self._stop_and_save()
        sys.exit(0)

    def _stop_and_save(self):
        """Lưu dữ liệu khi kết thúc - ƯU TIÊN GLOBAL LOGGER"""
        try:
            print(f"\n💾 Saving FINAL mouse data for user: {self.user_name}...")

            # LƯU TẤT CẢ SESSION CUỐI CÙNG
            if self.all_results and self.excel_handler:
                self.excel_handler.log_session_data(self.all_results)
                print(f"✅ Logged {len(self.all_results)} final sessions")

            # LƯU DỮ LIỆU CUỐI CÙNG VÀO GLOBAL LOGGER
            if self.global_logger:
                self.global_logger.save_final_data()
                print(f"✅ Final data saved to global logger")

            # LƯU QUA EXCEL HANDLER (BACKUP)
            if self.excel_handler:
                self.excel_handler.save_final_data()

            print(f"✅ All mouse data saved successfully for user: {self.user_name}")

        except Exception as e:
            print(f"❌ Error saving mouse data: {e}")
            import traceback
            traceback.print_exc()