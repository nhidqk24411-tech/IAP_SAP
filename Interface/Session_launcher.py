import sys
import os
import time
import multiprocessing
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer
from Workspace.SafeWorkingBrowser import ProfessionalWorkBrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_mouse_process(stop_event, pause_event, command_queue, alert_queue, start_delay_minutes=1):
    """Chạy mouse analysis với khả năng pause/resume"""
    try:
        if start_delay_minutes > 0:
            print(f"⏳ Mouse tracking starts in {start_delay_minutes} minutes...")

            for i in range(start_delay_minutes * 60):
                if stop_event.is_set():
                    return
                time.sleep(1)

        print("🖱️ Starting mouse tracking...")
        from Mouse.Main_mouse import MouseAnalysisSystem
        system = MouseAnalysisSystem()
        system.run_continuous_analysis(stop_event, pause_event, command_queue, alert_queue)

    except Exception as e:
        print(f"❌ Mouse process error: {e}")
        import traceback
        traceback.print_exc()


def main():
    # Tạo các events và queues để giao tiếp
    stop_event = multiprocessing.Event()
    pause_event = multiprocessing.Event()
    command_queue = multiprocessing.Queue()  # Browser -> Mouse commands
    alert_queue = multiprocessing.Queue()  # Mouse -> Browser alerts

    # Tạo và bắt đầu mouse process
    mouse_process = multiprocessing.Process(
        target=run_mouse_process,
        args=(stop_event, pause_event, command_queue, alert_queue, 1)  # 1 phút delay
    )
    mouse_process.start()

    print(f"✅ Mouse process started (PID: {mouse_process.pid})")

    # Tạo và chạy browser
    app = QApplication(sys.argv)

    # Truyền pause_event và command_queue vào browser
    browser = ProfessionalWorkBrowser(
        pause_event=pause_event,
        command_queue=command_queue,
        alert_queue=alert_queue
    )
    browser.setWindowTitle("PowerSight - Safe Browser")

    # Biến để lưu popup đang hiển thị
    current_alert_box = None

    def on_browser_closed():
        """Callback khi browser đóng"""
        print("\n🛑 Browser closing...")

        # Đóng popup alert nếu đang hiển thị
        nonlocal current_alert_box
        if current_alert_box:
            current_alert_box.accept()

        # Gửi lệnh STOP cho mouse process
        command_queue.put("STOP")
        stop_event.set()
        pause_event.clear()

        # Đợi mouse process kết thúc
        print("⏳ Waiting for mouse process to save data...")
        mouse_process.join(timeout=10)

        if mouse_process.is_alive():
            print("⚠️ Mouse process not responding, forcing termination...")
            mouse_process.terminate()
            mouse_process.join(timeout=2)

        print("✅ Session cleanup completed.")
        print("✅ Mouse data saved successfully.")

    # Kết nối sự kiện đóng browser
    app.aboutToQuit.connect(on_browser_closed)

    # Hàm hiển thị alert
    def show_alert_popup(alert_data):
        nonlocal current_alert_box

        # Tạo message box
        msg_box = QMessageBox()
        msg_box.setWindowTitle("⚠️ Anomaly Detected")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText("SUSPICIOUS MOUSE BEHAVIOR DETECTED!")
        msg_box.setInformativeText(
            f"Anomaly Score: {alert_data.get('score', 0):.3f}\n"
            f"Session: {alert_data.get('session_id', 'Unknown')}\n\n"
            f"Timestamp: {alert_data.get('timestamp', 'N/A')}\n\n"
            "Mouse tracking and timer have been PAUSED.\n"
            "Click OK to resume tracking."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)

        # Đặt style cho popup
        msg_box.setStyleSheet("""
            QMessageBox {
                background-color: #2b2b2b;
                color: white;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 8px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)

        current_alert_box = msg_box

        # Tạm dừng mouse tracking (nếu chưa pause)
        pause_event.set()

        # Hiển thị popup
        msg_box.exec()

        # Resume sau khi người dùng OK
        pause_event.clear()
        command_queue.put("RESUME")
        current_alert_box = None

        print("✅ User acknowledged alert, resuming tracking...")

    # Timer kiểm tra alert mỗi 0.5 giây
    alert_timer = QTimer()
    alert_timer.timeout.connect(lambda: check_alerts())
    alert_timer.start(500)

    def check_alerts():
        if not alert_queue.empty():
            try:
                alert_data = alert_queue.get_nowait()
                if alert_data:
                    show_alert_popup(alert_data)
            except Exception as e:
                print(f"⚠️ Error processing alert: {e}")

    # Hiển thị browser
    browser.show()

    # Chạy application
    return app.exec()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())