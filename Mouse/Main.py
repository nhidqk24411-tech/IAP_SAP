"""
Main module - Xử lý real-time CHỈ DI CHUYỂN với cảnh báo chặn
"""
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
import threading
import time
import queue
from Mouse.Module.real_time_tracker import RealTimeTracker
from Mouse.Module.real_time_processor import RealTimeProcessor
from ML_models.xgboost_anomaly import XGBoostAnomalyDetector
from Mouse.Module.Process_Excel import MouseExcelHandler


class MouseAnalysisSystem:
    # ========== CONFIG ==========
    SESSION_DURATION = 5  # 30 giây mỗi phiên
    TOTAL_DURATION_MINUTES = 1  # Tổng 5 phút
    ANOMALY_THRESHOLD = 0.7
    MIN_EVENTS_THRESHOLD = 5  # Dưới 5 events = không hoạt động
    LOW_ACTIVITY_RATIO = 0.2  # Hoạt động <20% thời gian

    def __init__(self):
        self.session_counter = 0
        self.anomaly_sessions = 0
        self.inactive_sessions = 0
        self.all_results = []
        self.is_running = True
        self.waiting_for_user = False
        self.gui_root = None
        self.gui_queue = queue.Queue()

        # Khởi tạo components
        self.tracker = RealTimeTracker()
        self.processor = RealTimeProcessor()
        self.anomaly_detector = XGBoostAnomalyDetector()
        self.excel_handler = MouseExcelHandler()

        # Vị trí nút Next
        screen_width, screen_height = 1920, 1080
        self.next_button_position = (screen_width // 2, screen_height // 2)
        self._start_gui_thread()

    def _start_gui_thread(self):
        """Khởi chạy GUI trong thread riêng"""

        def gui_mainloop():
            if self.gui_root is None:
                self.gui_root = tk.Tk()
                self.gui_root.withdraw()
                self.gui_root.title("Hệ thống phân tích chuột")
            self.gui_root.mainloop()

        gui_thread = threading.Thread(target=gui_mainloop, daemon=True)
        gui_thread.start()
        time.sleep(0.5)  # Đợi GUI khởi động

    # KHÔNG khởi tạo GUI ở đây nữa - sẽ khởi tạo trong main thread

    def init_gui(self):
        """Khởi tạo GUI - phải chạy trong main thread"""
        self.gui_root = tk.Tk()
        self.gui_root.withdraw()  # Ẩn cửa sổ chính
        self.gui_root.title("Hệ thống phân tích chuột")

        # Start the GUI event loop in a thread-safe way
        self.gui_root.after(100, self._process_gui_queue)

        # Bây giờ có thể hiển thị cảnh báo
        return self.gui_root

    def _process_gui_queue(self):
        """Xử lý queue của GUI"""
        try:
            while True:
                func, args, kwargs = self.gui_queue.get_nowait()
                func(*args, **kwargs)
        except queue.Empty:
            pass
        self.gui_root.after(100, self._process_gui_queue)

    def show_blocking_alert(self, title, message, alert_type="warning"):
        """Hiển thị cảnh báo CHẶN - phiên bản đơn giản"""
        try:
            # Tạo root window mới mỗi lần nếu cần
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)

            if alert_type == "warning":
                messagebox.showwarning(title, message, parent=root)
            elif alert_type == "error":
                messagebox.showerror(title, message, parent=root)
            else:
                messagebox.showinfo(title, message, parent=root)

            root.destroy()
            return True
        except Exception as e:
            print(f"❌ Lỗi alert: {e}")
            # Fallback: in ra console
            print(f"⚠️ [ALERT] {title}: {message}")
            return True
    def run_continuous_analysis(self):
        """
        Chạy phân tích liên tục - CẢNH BÁO SẼ CHẶN
        """
        print("=" * 70)
        print("HỆ THỐNG PHÂN TÍCH CHUỘT - REAL-TIME")
        print("=" * 70)
        print(f"📊 Mỗi phiên: {self.SESSION_DURATION} giây")
        print(f"⏱️ Tổng thời gian: {self.TOTAL_DURATION_MINUTES} phút")
        print(f"⚠️ Cảnh báo sẽ DỪNG hệ thống chờ xác nhận")
        print("=" * 70)

        # Thông báo bắt đầu
        self.show_blocking_alert(
            "Bắt đầu phân tích",
            f"Hệ thống sẽ phân tích trong {self.TOTAL_DURATION_MINUTES} phút\n"
            f"Mỗi phiên: {self.SESSION_DURATION} giây\n\n"
            "⚠️ LƯU Ý: Nếu không di chuyển chuột, hệ thống sẽ dừng và yêu cầu bạn quay lại làm việc!",
            "info"
        )

        start_total_time = datetime.now()
        end_total_time = start_total_time + timedelta(minutes=self.TOTAL_DURATION_MINUTES)

        try:
            while datetime.now() < end_total_time and self.is_running:
                # Tạo session ID
                session_id = f"session_{datetime.now().strftime('%H%M%S')}_{self.session_counter:03d}"
                self.session_counter += 1

                # Tính thời gian còn lại
                remaining = (end_total_time - datetime.now()).total_seconds() / 60

                print(f"\n{'=' * 40}")
                print(f"PHIÊN #{self.session_counter}: {session_id}")
                print(f"⏰ Còn lại: {remaining:.1f} phút")
                print(f"{'=' * 40}")

                # Chạy phân tích phiên
                result = self._run_single_session(session_id)

                if result:
                    self.all_results.append(result)

                    # Xử lý cảnh báo (có thể dừng hệ thống)
                    self._handle_session_alerts(result)

                    # Hiển thị kết quả
                    self._display_session_summary(result)

                    # Đánh giá pattern nếu đủ phiên
                    if len(self.all_results) >= 3:
                        self._evaluate_patterns()

                # KHÔNG CÓ THỜI GIAN CHỜ - CHẠY LIÊN TỤC
                # Ngay lập tức bắt đầu phiên tiếp theo

            # Kết thúc
            self._finalize_analysis()

        except KeyboardInterrupt:
            print("\n\n⏹️ Đã dừng hệ thống")
        except Exception as e:
            print(f"\n❌ Lỗi: {e}")
            self.show_blocking_alert("Lỗi hệ thống", f"Đã xảy ra lỗi:\n{str(e)}", "error")

        return self.all_results

    def _run_single_session(self, session_id: str):
        """
        Chạy phân tích một phiên
        """
        try:
            print(f"🎯 Đang thu thập dữ liệu ({self.SESSION_DURATION}s)...")

            # Thu thập events
            events = self.tracker.collect_events(
                duration_seconds=self.SESSION_DURATION,
                next_button_position=self.next_button_position
            )

            print(f"📊 Đã thu thập: {len(events)} events")

            # LUÔN phân tích, không có "không đủ dữ liệu"
            # Tính metrics
            metrics = self.processor.calculate_all_metrics(
                events=events,
                next_button_position=self.next_button_position
            )

            # Thêm số events vào metrics
            metrics['raw_event_count'] = len(events)

            # Phát hiện bất thường
            anomaly_score, _ = self.anomaly_detector.detect_anomaly(metrics)

            # Tạo kết quả
            result = self._create_mouse_result(session_id, metrics, anomaly_score, len(events))

            return result

        except Exception as e:
            print(f"❌ Lỗi phiên {session_id}: {e}")
            return None

    def _create_mouse_result(self, session_id: str, metrics: dict,
                             anomaly_score: float, event_count: int):
        """Tạo MouseResult với alerts chi tiết"""
        from Mouse.Models.MouseResult import MouseResult

        alerts = []

        # 1. Kiểm tra KHÔNG HOẠT ĐỘNG (quan trọng nhất)
        if event_count < self.MIN_EVENTS_THRESHOLD:
            alerts.append({
                'level': 'CRITICAL',
                'type': 'NO_ACTIVITY',
                'message': f'KHÔNG DI CHUYỂN! Chỉ {event_count} events trong {self.SESSION_DURATION}s'
            })

        # 2. Kiểm tra hoạt động thấp
        activity_ratio = metrics.get('movement_time_span_ui', 0) / max(metrics.get('duration_ui', 1), 1)
        if activity_ratio < self.LOW_ACTIVITY_RATIO and event_count >= self.MIN_EVENTS_THRESHOLD:
            alerts.append({
                'level': 'HIGH',
                'type': 'LOW_ACTIVITY',
                'message': f'Hoạt động rất thấp ({activity_ratio:.0%} thời gian)'
            })

        # 3. Kiểm tra bất thường từ XGBoost
        if anomaly_score > self.ANOMALY_THRESHOLD:
            if anomaly_score > 0.85:
                level = 'CRITICAL'
                anomaly_type = 'BOT_SUSPECTED'
            else:
                level = 'HIGH'
                anomaly_type = 'ANOMALY_DETECTED'

            alerts.append({
                'level': level,
                'type': anomaly_type,
                'message': f'Điểm bất thường: {anomaly_score:.3f}'
            })

        # 4. Kiểm tra đường thẳng (bot)
        if metrics.get('max_deviation_ui', 0) < 15 and metrics['distance_ui'] > 200:
            alerts.append({
                'level': 'HIGH',
                'type': 'STRAIGHT_LINE',
                'message': f'Đường đi quá thẳng (deviation: {metrics.get("max_deviation_ui", 0):.1f}px)'
            })

        # Tạo MouseResult
        return MouseResult(
            session_id=session_id,
            start_time=datetime.now(),
            end_time=datetime.now(),
            total_events=metrics.get('total_events', event_count),
            total_moves=metrics.get('total_moves', event_count),
            total_distance=metrics.get('distance_ui', 0),
            x_axis_distance=metrics.get('x_axis_distance_ui', 0),
            y_axis_distance=metrics.get('y_axis_distance_ui', 0),
            x_flips=metrics.get('x_flips_ui', 0),
            y_flips=metrics.get('y_flips_ui', 0),
            velocity_ui=metrics.get('velocity_ui', 0),
            x_axis_velocity_ui=metrics.get('x_axis_velocity_ui', 0),
            y_axis_velocity_ui=metrics.get('y_axis_velocity_ui', 0),
            acceleration_ui=metrics.get('acceleration_ui', 0),
            x_axis_acceleration_ui=metrics.get('x_axis_acceleration_ui', 0),
            y_axis_acceleration_ui=metrics.get('y_axis_acceleration_ui', 0),
            max_deviation_ui=metrics.get('max_deviation_ui', 0),
            duration_seconds=metrics.get('duration_ui', self.SESSION_DURATION),
            movement_time_span=metrics.get('movement_time_span_ui', 0),
            init_time_avg=0,
            react_time_avg=0,
            alerts=alerts,
            is_suspicious=anomaly_score > self.ANOMALY_THRESHOLD or len(alerts) > 0,
            anomaly_score=anomaly_score
        )

    def _handle_session_alerts(self, result):
        """
        Xử lý cảnh báo - CÓ THỂ DỪNG HỆ THỐNG CHỜ USER
        """
        if not result.alerts:
            return

        # Phân loại alerts
        critical_alerts = [a for a in result.alerts if a['level'] in ['CRITICAL', 'HIGH']]
        medium_alerts = [a for a in result.alerts if a['level'] == 'MEDIUM']

        # Xử lý CRITICAL/HIGH alerts (dừng hệ thống)
        if critical_alerts:
            alert_text = "🚨 PHÁT HIỆN VẤN ĐỀ QUAN TRỌNG!\n\n"

            for alert in critical_alerts:
                alert_text += f"• {alert['type']}: {alert['message']}\n"

            alert_text += "\n⚠️ Vui lòng quay lại làm việc và bấm OK để tiếp tục phân tích."

            print(f"\n{'!' * 60}")
            print("CẢNH BÁO QUAN TRỌNG - Hệ thống tạm dừng")
            print(f"{'!' * 60}")

            # HIỂN THỊ CẢNH BÁO CHẶN - đợi user bấm OK
            confirmed = self.show_blocking_alert(
                "CẢNH BÁO HỆ THỐNG",
                alert_text,
                "warning"
            )

            if confirmed:
                print("✅ Người dùng đã xác nhận, tiếp tục phân tích...")
            else:
                print("⚠️ Cảnh báo không được xác nhận")

        # Xử lý MEDIUM alerts (chỉ cảnh báo, không dừng)
        elif medium_alerts:
            alert_text = "📢 Thông báo:\n\n"
            for alert in medium_alerts:
                alert_text += f"• {alert['type']}: {alert['message']}\n"

            # Hiển thị nhưng KHÔNG chặn
            print(f"\n{'~' * 60}")
            print("THÔNG BÁO:")
            for alert in medium_alerts:
                print(f"  • {alert['type']}: {alert['message']}")
            print(f"{'~' * 60}")

            # Có thể hiển thị non-blocking alert
            # self.show_non_blocking_alert("Thông báo", alert_text, "info")

    def _display_session_summary(self, result):
        """Hiển thị tóm tắt phiên"""
        print(f"\n📋 KẾT QUẢ PHIÊN {result.session_id}:")
        print(f"   ⏱️  Thời gian: {result.duration_seconds:.1f}s")
        print(f"   📏 Quãng đường: {result.total_distance:.1f}px")
        print(f"   🎯 Tổng events: {result.total_events}")
        print(f"   🔄 X/Y Flips: {result.x_flips}/{result.y_flips}")
        print(f"   🚀 Vận tốc: {result.velocity_ui:.1f} px/s")
        print(f"   ⚠️  Điểm bất thường: {result.anomaly_score:.3f}")

        if result.alerts:
            print(f"   🚨 Cảnh báo: {len(result.alerts)}")
            for i, alert in enumerate(result.alerts[:2], 1):
                print(f"     {i}. [{alert['level']}] {alert['type']}")

    def _evaluate_patterns(self):
        """Đánh giá pattern nhiều phiên"""
        if len(self.all_results) < 3:
            return

        recent = self.all_results[-3:]  # 3 phiên gần nhất

        # Đếm số phiên có vấn đề
        problem_sessions = 0
        for r in recent:
            if r.alerts or r.anomaly_score > self.ANOMALY_THRESHOLD:
                problem_sessions += 1

        # Nếu 2/3 phiên có vấn đề
        if problem_sessions >= 2:
            alert_text = (
                "⚠️ PHÁT HIỆN MẪU HÀNH VI BẤT THƯỜNG!\n\n"
                f"{problem_sessions}/3 phiên gần nhất có vấn đề.\n"
                "Điều này có thể cho thấy:\n"
                "• Người dùng không tập trung làm việc\n"
                "• Có thể là bot/script tự động\n"
                "• Hành vi không tự nhiên\n\n"
                "Vui lòng kiểm tra và bấm OK để tiếp tục."
            )

            print(f"\n{'⚠️' * 30}")
            print("CẢNH BÁO: Mẫu hành vi bất thường!")
            print(f"{'⚠️' * 30}")

            # Hiển thị cảnh báo chặn
            self.show_blocking_alert(
                "Cảnh báo Pattern",
                alert_text,
                "warning"
            )

    def _finalize_analysis(self):
        """Kết thúc phân tích"""
        print(f"\n{'=' * 70}")
        print("🏁 KẾT THÚC PHÂN TÍCH")
        print(f"{'=' * 70}")

        if not self.all_results:
            print("❌ Không có dữ liệu")
            return

        total = len(self.all_results)
        anomalies = sum(1 for r in self.all_results if r.anomaly_score > self.ANOMALY_THRESHOLD)
        alerts = sum(len(r.alerts) for r in self.all_results)

        print(f"📊 Tổng số phiên: {total}")
        print(f"🚨 Phiên bất thường: {anomalies} ({anomalies / total:.1%})")
        print(f"⚠️ Tổng cảnh báo: {alerts}")

        # Xuất báo cáo
        self._export_report()

        # Hiển thị kết quả cuối
        summary_msg = (
            f"Phân tích hoàn tất!\n\n"
            f"• Tổng phiên: {total}\n"
            f"• Phiên bất thường: {anomalies}\n"
            f"• Tổng cảnh báo: {alerts}\n\n"
            f"Báo cáo đã được lưu vào thư mục Saved_file/"
        )

        self.show_blocking_alert(
            "Phân tích hoàn tất",
            summary_msg,
            "info"
        )

    def _export_report(self):
        """Xuất báo cáo Excel - GỌI Module Excel đã có"""
        try:
            if not self.all_results:
                print("❌ Không có dữ liệu để xuất Excel")
                return None

            print(f"\n📊 Đang xuất báo cáo cho {len(self.all_results)} sessions...")

            # GỌI PHƯƠNG THỨC MỚI CỦA MODULE EXCEL
            file_path = self.excel_handler.export_multiple_sessions(
                sessions=self.all_results,
                filename_prefix="mouse_analysis"
            )

            if file_path:
                print(f"✅ Đã xuất báo cáo thành công: {file_path}")
                return file_path
            else:
                print("❌ Xuất báo cáo thất bại")
                return None

        except Exception as e:
            print(f"❌ Lỗi xuất báo cáo: {e}")
            import traceback
            traceback.print_exc()
            return None
    def stop_analysis(self):
        """Dừng hệ thống"""
        self.is_running = False
        print("\n🛑 Đang dừng hệ thống...")


if __name__ == "__main__":
    print("🚀 KHỞI ĐỘNG HỆ THỐNG PHÂN TÍCH CHUỘT")

    try:
        # Tạo system
        system = MouseAnalysisSystem()
        print("✅ Đã tạo hệ thống")

        # KHÔNG gọi init_gui() ở đây - sẽ dùng fallback alert
        print("⏳ Bắt đầu phân tích trong 5 giây...")
        time.sleep(5)

        # Chạy phân tích
        print("🎬 Bắt đầu run_continuous_analysis...")
        results = system.run_continuous_analysis()

        if results:
            print(f"\n✅ Phân tích hoàn tất: {len(results)} phiên")
        else:
            print("\n❌ Không có kết quả")

    except Exception as e:
        print(f"\n💥 Lỗi nghiêm trọng: {e}")
        import traceback

        traceback.print_exc()