import time
import signal
import sys
import pandas as pd
from datetime import datetime

from Mouse.Module.real_time_tracker import RealTimeTracker
from Mouse.Module.real_time_processor import RealTimeProcessor
from Mouse.Module.Process_Excel import MouseExcelHandler
from ML_models.xgboost_anomaly import BehaviorModel
from Mouse.Models.MouseResult import MouseResult


class MouseAnalysisSystem:
    SESSION_DURATION = 60
    ANOMALY_THRESHOLD = 0.75

    def __init__(self):
        self.tracker = RealTimeTracker()
        self.processor = RealTimeProcessor()
        self.excel_handler = MouseExcelHandler()
        self.ai_model = BehaviorModel()

        self.all_results = []
        self.session_count = 0
        self.auto_save = True

        signal.signal(signal.SIGTERM, self._handle_exit)
        signal.signal(signal.SIGINT, self._handle_exit)

        # Khởi tạo model
        self._init_model()

    def _init_model(self):
        """Khởi tạo và train model từ dữ liệu lịch sử"""
        print("\n🔍 Initializing AI Model...")

        # Kiểm tra nếu model đã được load
        if self.ai_model.xgb_model is not None:
            print(f"✅ Model already loaded with {len(self.ai_model.selected_features)} features")
            return

        # Tải dữ liệu training
        print("📚 Loading training data from Excel files...")
        df_history = self.excel_handler.load_training_data()

        if df_history is not None:
            print(f"📊 Training data shape: {df_history.shape}")

            # Train model
            print("🧠 Training AI model with historical data...")
            success = self.ai_model.train(df_history)

            if success:
                print(f"✅ Model trained successfully!")
                print(f"✅ Selected features: {self.ai_model.selected_features}")
                print(f"✅ Training samples: {len(df_history)}")
            else:
                print("⚠️ Model training failed. Will use default model.")
        else:
            print("⚠️ No historical data found. Model will learn from new sessions.")

    # =========================
    # MAIN LOOP
    # =========================
    def run_continuous_analysis(self, stop_event, pause_event, command_queue, alert_queue):
        print("=" * 60)
        print("🛡️  MOUSE ANALYSIS SYSTEM STARTED")
        print(f"✅ Model status: {'TRAINED' if self.ai_model.xgb_model else 'NOT TRAINED'}")
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

                    # Kiểm tra nếu là anomaly
                    if result.is_suspicious:
                        print(f"🚨 ALERT: Anomaly detected (score: {result.anomaly_score:.3f})")

                        # Gửi alert đến browser (sẽ pause cả timer và mouse tracking)
                        try:
                            alert_data = {
                                'session_id': result.session_id,
                                'score': result.anomaly_score,
                                'timestamp': datetime.now().strftime("%H:%M:%S")
                            }
                            alert_queue.put(alert_data)
                            print("📨 Alert sent to browser")

                            # Đợi lệnh từ browser (người dùng ấn OK)
                            print("⏳ Waiting for user confirmation...")
                            while pause_event.is_set() and not stop_event.is_set():
                                time.sleep(0.5)

                        except Exception as e:
                            print(f"⚠️ Error sending alert: {e}")
                    else:
                        # Hiển thị thông tin bình thường
                        print(f"📊 Session {self.session_count}: Normal (score: {result.anomaly_score:.3f})")

                    # Auto save mỗi 5 session
                    if self.auto_save and len(self.all_results) >= 5:
                        self.excel_handler.export_multiple_sessions(self.all_results)
                        print(f"💾 Auto-saved {len(self.all_results)} sessions")
                        self.all_results = []

        finally:
            self._stop_and_save()

    # =========================
    # SINGLE SESSION
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
    # RESULT BUILD
    # =========================
    def _create_result(self, metrics, score):
        alerts = []

        # CHỈ THÊM ALERT KHI CÓ ANOMALY
        if score > self.ANOMALY_THRESHOLD:
            alerts.append({'level': 'HIGH', 'msg': f'Anomaly Behavior (score: {score:.2f})'})

        return MouseResult(
            session_id=f"S_{datetime.now():%H%M%S}_{self.session_count}",
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

    # =========================
    # SAFE EXIT
    # =========================
    def _handle_exit(self, *args):
        print("⚠️ Forced exit detected.")
        self._stop_and_save()
        sys.exit(0)

    def _stop_and_save(self):
        if not self.all_results:
            print("ℹ️ No data to save.")
            return

        print("\n💾 Saving mouse session data...")
        path = self.excel_handler.export_multiple_sessions(self.all_results)
        if path:
            print(f"✅ Data saved to: {path}")
        else:
            print("❌ Failed to save data.")