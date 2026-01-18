import sys
import os
import cv2
import time
import multiprocessing
from datetime import datetime, timedelta
import traceback
import pandas as pd
import subprocess

# Add project root to path for imports
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import ctypes
from ctypes import wintypes

# Định nghĩa các hằng số WinAPI
SW_HIDE = 0
SW_SHOW = 5


class TaskbarController:
    """Điều khiển ẩn/hiện thanh Taskbar của Windows"""

    @staticmethod
    def set_visibility(visible=True):
        try:
            hwnd = ctypes.windll.user32.FindWindowW("Shell_TrayWnd", None)
            hwnd_start = ctypes.windll.user32.FindWindowW("Button", "Start")
            show_cmd = SW_SHOW if visible else SW_HIDE
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, show_cmd)
            if hwnd_start:
                ctypes.windll.user32.ShowWindow(hwnd_start, show_cmd)
        except Exception as e:
            print(f"⚠️ Taskbar error: {e}")


# =========================
# CONFIGURATION
import sys
import os

# Lấy đường dẫn thư mục chứa main_emp.py
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(current_dir)  # MainApp
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # PythonProject

SAVED_FILE_DIR = os.path.join(PROJECT_ROOT, "Saved_file")
UI_DIR = os.path.join(BASE_DIR, "UI")
IMAGES_DIR = os.path.join(UI_DIR, "images")

# Thêm các đường dẫn cần thiết
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Face"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Workspace"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Mouse"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Chatbot"))

print(f"✅ PROJECT_ROOT: {PROJECT_ROOT}")
print(f"✅ SAVED_FILE_DIR: {SAVED_FILE_DIR}")
# FIX LỖI DEBUG TENSORFLOW
if 'pydevd' in sys.modules:
    os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
    print("⚠️ Debug mode active - applied TensorFlow fixes")


# =========================
# PATH UTILITIES
# =========================
def setup_user_directories(user_name):
    """Tạo thư mục cần thiết cho user - CHỈ TẠO THƯ MỤC THÁNG"""
    user_base_dir = os.path.join(SAVED_FILE_DIR, user_name)
    os.makedirs(user_base_dir, exist_ok=True)

    current_date = datetime.now()
    year_month = current_date.strftime("%Y_%m")
    monthly_dir = os.path.join(user_base_dir, year_month)
    os.makedirs(monthly_dir, exist_ok=True)

    face_captures_dir = os.path.join(monthly_dir, "face_captures")
    os.makedirs(face_captures_dir, exist_ok=True)

    paths = {
        'user_base': user_base_dir,
        'monthly': monthly_dir,
        'face_captures': face_captures_dir,
        'ui_images': IMAGES_DIR,
        'background2': os.path.join(IMAGES_DIR, "background2.jpg"),
        'background5': os.path.join(IMAGES_DIR, "background5.jpg"),
        'faceid_icon': os.path.join(IMAGES_DIR, "faceid_icon.jpg"),
    }

    print(f"📁 Created directory: {monthly_dir}")
    print(f"📁 Created directory: {face_captures_dir}")
    return paths


def load_image(image_name):
    """Load ảnh từ thư mục images"""
    image_path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(image_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            print(f"✅ Loaded image: {image_name}")
            return pixmap
        else:
            print(f"❌ Failed to load image: {image_name}")
    else:
        print(f"⚠️ Image not found: {image_path}")
    return None


# =========================
# MULTIPROCESS ENTRY
# =========================
def mouse_process_entry(stop_event, pause_event, command_queue, alert_queue, delay_minutes, user_name, global_logger):
    """Hàm chạy trong process riêng - Dùng global logger"""
    try:
        from Mouse.Main_mouse import MouseAnalysisSystem
        print(f"🖱️ Mouse tracking started for user: {user_name}")

        if delay_minutes > 0:
            for _ in range(delay_minutes * 60):
                if stop_event.is_set():
                    return
                time.sleep(1)

        system = MouseAnalysisSystem(global_logger)
        system.run_continuous_analysis(
            stop_event,
            pause_event,
            command_queue,
            alert_queue,
            user_name,
            global_logger
        )
    except Exception as e:
        print("❌ Mouse process crashed:", e)
        traceback.print_exc()


# Import UI
from MainApp.UI.UI_HOME import Ui_MainWindow as Ui_HomeWindow

# Import systems
from Face.main_face import FaceSingleCheck
from Workspace.SafeWorkingBrowser import ProfessionalWorkBrowser


# ============================================
# GLOBAL EXCEL LOGGER - TẤT CẢ MODULE DÙNG CHUNG
# ============================================
class GlobalExcelLogger:
    """Logger toàn cục cho tất cả module - CHỈ LƯU GIAN LẬN"""

    def __init__(self, user_name):
        self.user_name = user_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.PATHS = setup_user_directories(user_name)
        current_date = datetime.now()
        self.current_year_month = current_date.strftime("%Y_%m")

        self.excel_path = os.path.join(
            self.PATHS['monthly'],
            f"work_logs_{user_name}_{self.current_year_month}.xlsx"
        )

        self.fraud_events = []
        self.mouse_details = []
        self.last_save_time = time.time()
        self.save_interval = 60

        print(f"🌐 Global logger initialized: {self.excel_path}")

    def log_alert(self, module, event_type, details="", severity="INFO", is_fraud=False):
        """Ghi log cảnh báo - CHỈ LƯU NẾU LÀ GIAN LẬN (is_fraud=True)"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_entry = {
            "Timestamp": timestamp,
            "Event_Type": event_type,
            "Details": details,
            "User": self.user_name,
            "Session_ID": self.session_id,
            "Severity": severity,
            "IsFraud": 1 if is_fraud else 0,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Module": module
        }

        if is_fraud:
            self.fraud_events.append(event_entry)
            print(f"🚨 [FRAUD] [{module}] {event_type} - {details}")
        else:
            print(f"ℹ️  [{module}] {event_type} - {details}")

    def log_mouse_details(self, event_type, details="", severity="INFO", is_fraud=False, **mouse_data):
        """Ghi chi tiết chuột vào sheet riêng"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mouse_entry = {
            "Timestamp": timestamp,
            "Event_Type": event_type,
            "Details": details,
            "User": self.user_name,
            "Session_ID": self.session_id,
            "Severity": severity,
            "IsFraud": 1 if is_fraud else 0,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Module": "Mouse"
        }
        mouse_entry.update(mouse_data)
        self.mouse_details.append(mouse_data)

        if is_fraud:
            self.log_alert("Mouse", event_type, details, severity, is_fraud)

    def log_face_alert(self, event_type, details="", severity="INFO", is_fraud=False, **face_data):
        """Ghi log face - CHỈ LƯU NẾU GIAN LẬN"""
        if is_fraud:
            self.log_alert("Face", event_type, details, severity, is_fraud)
        else:
            print(f"ℹ️  [Face] {event_type} - {details}")

    def log_browser_alert(self, event_type, details="", severity="INFO", is_fraud=False):
        """Ghi log browser - CHỈ LƯU NẾU GIAN LẬN"""
        if is_fraud:
            self.log_alert("Browser", event_type, details, severity, is_fraud)
        else:
            print(f"ℹ️  [Browser] {event_type} - {details}")

    def save_to_excel(self):
        """Lưu vào file Excel với 2 sheet"""
        try:
            df_fraud = pd.DataFrame(self.fraud_events) if self.fraud_events else pd.DataFrame(columns=[
                "Timestamp", "Event_Type", "Details", "User", "Session_ID",
                "Severity", "IsFraud", "Date", "Time", "Module"
            ])

            df_mouse = pd.DataFrame(self.mouse_details) if self.mouse_details else pd.DataFrame(columns=[
                "Timestamp", "Event_Type", "Details", "User", "Session_ID",
                "Severity", "IsFraud", "Date", "Time", "Module",
                "TotalEvents", "TotalMoves", "TotalDistance", "XAxisDistance",
                "YAxisDistance", "XFlips", "YFlips", "MovementTimeSpan",
                "Velocity", "Acceleration", "XVelocity", "YVelocity",
                "XAcceleration", "YAcceleration", "DurationSeconds", "AnomalyScore"
            ])

            if os.path.exists(self.excel_path):
                try:
                    old_fraud = pd.read_excel(self.excel_path, sheet_name='Fraud_Events')
                    old_mouse = pd.read_excel(self.excel_path, sheet_name='Mouse_Details')
                    df_fraud = pd.concat([old_fraud, df_fraud], ignore_index=True)
                    df_mouse = pd.concat([old_mouse, df_mouse], ignore_index=True)
                    df_fraud = df_fraud.drop_duplicates(subset=['Timestamp', 'Event_Type', 'Session_ID'])
                    df_mouse = df_mouse.drop_duplicates(subset=['Timestamp', 'Event_Type', 'Session_ID'])
                except Exception as e:
                    print(f"⚠️ Error reading existing file: {e}")

            with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
                df_fraud.to_excel(writer, sheet_name='Fraud_Events', index=False)
                df_mouse.to_excel(writer, sheet_name='Mouse_Details', index=False)

            print(f"💾 Global log saved: {self.excel_path}")
            return True
        except Exception as e:
            print(f"❌ Error saving global log: {e}")
            traceback.print_exc()
            return False

    def save_final_data(self):
        """Lưu dữ liệu cuối cùng"""
        self.save_to_excel()
        print(f"✅ Final data saved for user: {self.user_name}")

    def get_session_summary(self):
        """Lấy thông tin tổng hợp session"""
        return {
            "user": self.user_name,
            "session_id": self.session_id,
            "total_alerts": len(self.fraud_events),
            "mouse_entries": len(self.mouse_details),
            "excel_file": os.path.basename(self.excel_path)
        }

    def open_log_file(self):
        """Mở file log"""
        try:
            if os.path.exists(self.excel_path):
                os.startfile(self.excel_path)
                return True
            else:
                print(f"⚠️ Log file not found: {self.excel_path}")
                return False
        except Exception as e:
            print(f"❌ Error opening log file: {e}")
            return False


# ============================================
class FaceCheckWorker(QThread):
    finished = pyqtSignal(dict)

    def __init__(self, face_system):
        super().__init__()
        self.face_system = face_system

    def run(self):
        try:
            result = self.face_system.check_from_camera()
            self.finished.emit(result)
        except Exception as e:
            self.finished.emit({"success": False, "message": str(e)})


# ============================================
# ENHANCED SAFE BROWSER
# ============================================
class EnhancedSafeBrowser(ProfessionalWorkBrowser):
    """Safe Browser chuyên nghiệp tích hợp bảo mật cao"""

    def __init__(self, user_name, global_logger, parent_window=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name = user_name
        self.global_logger = global_logger
        self.parent_window = parent_window
        self.is_closing = False
        self.is_dialog_active = False
        self.fraud_alert_shown = False
        self.current_tab_name = "Home"
        self.current_tab_start_time = time.time()
        self.actual_work_time = 0  # Thời gian làm việc thực tế
        self.last_timer_update = time.time()  # Thời điểm cập nhật timer cuối cùng
        self.timer_paused_time = 0  # Thời gian timer bị pause

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint
        )

        TaskbarController.set_visibility(False)

        # Import face system
        try:
            # Tìm và import main_face.py
            face_main_path = os.path.join(PROJECT_ROOT, "Face", "main_face.py")
            if os.path.exists(face_main_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("main_face", face_main_path)
                face_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(face_module)

                self.face_system = face_module.FaceSingleCheck(
                    user_name=self.user_name,
                    global_logger=self.global_logger
                )
                print(f"✅ Face system loaded for random check (user: {user_name})")
            else:
                print(f"❌ Không tìm thấy main_face.py tại: {face_main_path}")
                self.face_system = None
        except Exception as e:
            print(f"❌ Failed to load face system: {e}")
            traceback.print_exc()
            self.face_system = None

        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setup_random_check()

        self.global_logger.log_browser_alert(
            event_type="BROWSER_OPEN",
            details="Professional Workspace Browser started",
            severity="INFO",
            is_fraud=False
        )

        # Ghi nhận thời điểm bắt đầu
        self.session_start_time = time.time()

    def show_secure(self):
        """Kích hoạt chế độ toàn màn hình bảo mật"""
        self.showFullScreen()
        self.activateWindow()
        self.raise_()

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow() and not self.is_dialog_active and not self.is_closing:
                QTimer.singleShot(300, self.activate_and_raise)
        super().changeEvent(event)

    def activate_and_raise(self):
        if not self.is_closing and not self.is_dialog_active:
            self.raise_()
            self.activateWindow()

    def setup_random_check(self):
        import random
        self.next_check_time = time.time() + random.randint(60, 120)
        self.check_interval_range = (180, 420)

        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_random_face)
        self.check_timer.start(10000)

    def check_random_face(self):
        current_time = time.time()

        if current_time >= self.next_check_time:
            print(f"⏰ Time for random face check!")
            self.check_timer.stop()
            success = self.perform_face_check()

            if success:
                import random
                next_interval = random.randint(*self.check_interval_range)
                self.next_check_time = time.time() + next_interval
                print(f"✅ Next check in {next_interval // 60} minutes")
            else:
                self.next_check_time = time.time() + 30
                print(f"🔄 Retry check in 30 seconds")

            self.check_timer.start(10000)
            print(f"🔁 Timer restarted")

    def perform_face_check(self):
        """Thực hiện face check"""
        try:
            print("🔄 Starting random face check (Full Logic)...")
            self.is_dialog_active = True

            self.global_logger.log_browser_alert(
                event_type="FACE_CHECK_START",
                details="Random face verification started",
                severity="INFO",
                is_fraud=False
            )

            # Pause timer thực tế
            self.pause_actual_timer()

            self.was_paused_by_user = False
            if hasattr(self, 'timer_widget') and self.timer_widget:
                self.was_paused_by_user = not self.timer_widget.is_running
                self.timer_widget.pause_timer()

            if self.pause_event: self.pause_event.set()
            if self.command_queue: self.command_queue.put("PAUSE")

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Random Face Verification")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(
                f"🔐 RANDOM IDENTITY CHECK\n\nUser: {self.user_name}\nPlease look straight at the camera.\n\nClick OK to start verification.")
            msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            msg_box.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            msg_box.exec()

            if self.face_system is None:
                print("🎭 Using demo mode...")
                QMessageBox.information(self, "DEMO Mode",
                                        f"DEMO: Verified as {self.user_name}\n\nYou may continue working.")
                self.global_logger.log_browser_alert("FACE_CHECK_DEMO", "Demo mode - Verification passed",
                                                     is_fraud=False)
                self.on_face_check_finished(
                    {"success": True, "matched": True, "name": self.user_name, "similarity": 0.99})
                return

            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            self.face_worker = FaceCheckWorker(self.face_system)
            self.face_worker.finished.connect(self.on_face_check_finished)
            self.face_worker.start()

        except Exception as e:
            print(f"❌ Error during face check: {e}")
            traceback.print_exc()
            self.on_face_check_finished({"success": False, "message": str(e)})

    def on_face_check_finished(self, result):
        """Xử lý kết quả trả về"""
        QApplication.restoreOverrideCursor()

        try:
            if result.get("success") and result.get("matched"):
                detected_user = result.get("name")
                similarity = result.get("similarity", 0)

                if detected_user == self.user_name:
                    print(f"✅ User verified: {detected_user}")
                    self.global_logger.log_browser_alert("FACE_CHECK_SUCCESS", f"Confidence: {similarity:.1%}",
                                                         is_fraud=False)
                    QMessageBox.information(self, "Verification Successful",
                                            f"✅ Verified: {detected_user}\nConfidence: {similarity:.1%}")
                    self.resume_after_check_logic(True)
                else:
                    print(f"❌ User mismatch")
                    self.global_logger.log_browser_alert("FACE_CHECK_MISMATCH", f"Detected: {detected_user}",
                                                         is_fraud=True)
                    QMessageBox.critical(self, "🚨 UNAUTHORIZED",
                                         f"❌ User mismatch!\nExpected: {self.user_name}\nDetected: {detected_user}")
                    self.resume_after_check_logic(True)
            else:
                error_msg = result.get("message", "Unknown error")
                self.global_logger.log_browser_alert("FACE_CHECK_FAILED", error_msg, is_fraud=False)
                QMessageBox.warning(self, "Verification Failed", f"❌ {error_msg}\n\nPlease try again.")
                self.resume_after_check_logic(False)

        except Exception as e:
            print(f"❌ Error in finished callback: {e}")
            self.is_dialog_active = False
            self.resume_after_check_logic(False)

    def pause_actual_timer(self):
        """Tạm dừng timer thực tế"""
        current_time = time.time()
        if hasattr(self, 'timer_widget') and self.timer_widget and self.timer_widget.is_running:
            self.actual_work_time += (current_time - self.last_timer_update)
        self.last_timer_update = current_time

    def resume_actual_timer(self):
        """Tiếp tục timer thực tế"""
        self.last_timer_update = time.time()

    def resume_after_check_logic(self, is_success):
        """Khôi phục hệ thống"""
        print("▶️ Resuming session...")

        # Resume timer thực tế
        self.resume_actual_timer()

        if not self.was_paused_by_user:
            if hasattr(self, 'timer_widget'): self.timer_widget.resume_timer()
            if self.pause_event: self.pause_event.clear()
            if self.command_queue: self.command_queue.put("RESUME")

        import random
        next_interval = random.randint(*self.check_interval_range) if is_success else 30
        self.next_check_time = time.time() + next_interval
        self.check_timer.start(10000)

        QTimer.singleShot(500, self._finalize_dialog_state)

    def _finalize_dialog_state(self):
        self.is_dialog_active = False
        self.activateWindow()
        self.raise_()
        print("🔓 Focus unlocked, Browser is back on top.")

    def check_rapid_pause(self):
        """Kiểm tra pause nhanh liên tiếp"""
        current_time = datetime.now()

        if not hasattr(self, 'last_pause_time'):
            self.last_pause_time = current_time
            self.rapid_pause_count = 0

        time_diff = (current_time - self.last_pause_time).total_seconds()

        if time_diff < 10:
            self.rapid_pause_count += 1
            if self.rapid_pause_count >= 3:
                return True
        else:
            self.rapid_pause_count = 0

        self.last_pause_time = current_time
        return False

    def show_fraud_alert(self):
        """Hiển thị cảnh báo gian lận"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("⚠️ SUSPICIOUS BEHAVIOR DETECTED")
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setText(
            "🚨 MULTIPLE RAPID PAUSES DETECTED!\n\n"
            "System has detected multiple rapid pauses in a short time.\n"
            "This behavior may indicate:\n"
            "- Attempt to bypass monitoring\n"
            "- Unauthorized breaks\n"
            "- Potential cheating\n\n"
            "This incident has been logged.\n"
            "Continue at your own risk."
        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def confirm_exit(self):
        """Hộp thoại xác nhận thoát"""
        self.is_dialog_active = True
        TaskbarController.set_visibility(True)

        # Tính thời gian làm việc thực tế
        current_time = time.time()
        if hasattr(self, 'timer_widget') and self.timer_widget and self.timer_widget.is_running:
            self.actual_work_time += (current_time - self.last_timer_update)

        total_hours = int(self.actual_work_time // 3600)
        total_minutes = int((self.actual_work_time % 3600) // 60)
        total_seconds = int(self.actual_work_time % 60)

        reply = QMessageBox.question(
            self, "Exit Workspace Browser",
            "Are you sure you want to exit the Professional Workspace Browser?\n\n"
            f"Total actual working time: {total_hours}h {total_minutes}m {total_seconds}s\n"
            "All unsaved work might be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.is_closing = True
            self.close()
        else:
            self.is_dialog_active = False
            TaskbarController.set_visibility(False)
            self.show_secure()

    def closeEvent(self, event):
        """Dọn dẹp tài nguyên khi đóng hẳn"""
        if self.is_closing:
            print("🛑 Closing browser and restoring system...")
            TaskbarController.set_visibility(True)

            # Tính thời gian làm việc thực tế cuối cùng
            current_time = time.time()
            if hasattr(self, 'timer_widget') and self.timer_widget and self.timer_widget.is_running:
                self.actual_work_time += (current_time - self.last_timer_update)

            total_hours = int(self.actual_work_time // 3600)
            total_minutes = int((self.actual_work_time % 3600) // 60)
            total_seconds = int(self.actual_work_time % 60)

            self.global_logger.log_browser_alert(
                event_type="BROWSER_CLOSED",
                details=f"Secure session ended by user. Actual work time: {total_hours}h {total_minutes}m {total_seconds}s",
                severity="INFO",
                is_fraud=False
            )

            if hasattr(self, 'check_timer'): self.check_timer.stop()

            if self.parent_window and hasattr(self.parent_window, 'on_browser_closed'):
                self.parent_window.on_browser_closed()

            event.accept()
        else:
            event.ignore()
            self.confirm_exit()

    def on_tab_changed(self, index):
        """Xử lý khi chuyển tab"""
        if self.current_tab_start_time and self.current_tab_name:
            duration = time.time() - self.current_tab_start_time

        self.current_tab_name = self.tab_widget.tabText(index).strip()
        self.current_tab_start_time = time.time()

    def setup_timer_with_logging(self):
        """Thiết lập timer với logging"""
        try:
            if self.timer_widget and self.timer_widget.pause_btn:
                self.timer_widget.pause_btn.clicked.disconnect()
        except:
            pass

        if self.timer_widget and self.timer_widget.pause_btn:
            self.timer_widget.pause_btn.clicked.connect(self.toggle_timer_with_logging)
            print("✅ Timer button connected with logging")

    def toggle_timer_with_logging(self):
        """Điều khiển Pause/Resume timer và Mouse Tracking"""
        tw = self.timer_widget
        if tw.is_running:
            # Pause - dừng timer thực tế
            tw.is_running = False
            tw.timer.stop()
            tw.pause_btn.setText("▶ Resume")

            # Cập nhật thời gian làm việc thực tế
            current_time = time.time()
            self.actual_work_time += (current_time - self.last_timer_update)

            if self.pause_event: self.pause_event.set()
            if self.command_queue: self.command_queue.put("PAUSE")

            if self.check_rapid_pause():
                self.show_fraud_alert()
                self.global_logger.log_browser_alert("RAPID_PAUSE", "Detected multiple rapid pauses", is_fraud=True)
        else:
            # Resume - tiếp tục timer thực tế
            tw.is_running = True
            tw.timer.start(1000)
            tw.pause_btn.setText("⏸ Pause")

            # Cập nhật thời điểm bắt đầu lại
            self.last_timer_update = time.time()

            if self.pause_event: self.pause_event.clear()
            if self.command_queue: self.command_queue.put("RESUME")


# ============================================
# FIX IMPORT MODULES - THÊM ĐƯỜNG DẪN ĐÚNG
# ============================================
# Thêm đường dẫn cho các module
sys.path.append(os.path.join(BASE_DIR, "Chatbot"))
sys.path.append(os.path.join(BASE_DIR, "Dashboard"))

try:
    from Chatbot.employee_chatbot import EmployeeChatbotGUI

    print("✅ Employee chatbot imported successfully")
except ImportError as e:
    print(f"⚠️ Cannot import EmployeeChatbotGUI: {e}")
    print("⚠️ Trying alternative import...")
    try:
        # Thử import từ đường dẫn trực tiếp
        chatbot_path = os.path.join(BASE_DIR, "employee_chatbot.py")
        if os.path.exists(chatbot_path):
            import importlib.util

            spec = importlib.util.spec_from_file_location("employee_chatbot", chatbot_path)
            chatbot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(chatbot_module)
            EmployeeChatbotGUI = chatbot_module.EmployeeChatbotGUI
            print("✅ Employee chatbot imported from direct path")
        else:
            EmployeeChatbotGUI = None
            print("❌ Chatbot file not found")
    except Exception as e2:
        print(f"❌ Alternative import also failed: {e2}")
        EmployeeChatbotGUI = None

try:
    from Chatbot.dashboard import PerformanceDashboard

    print("✅ Performance dashboard imported successfully")
except ImportError as e:
    print(f"⚠️ Cannot import PerformanceDashboard: {e}")
    print("⚠️ Trying alternative import...")
    try:
        # Thử import từ đường dẫn trực tiếp
        dashboard_path = os.path.join(BASE_DIR, "dashboard.py")
        if os.path.exists(dashboard_path):
            import importlib.util

            spec = importlib.util.spec_from_file_location("dashboard", dashboard_path)
            dashboard_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(dashboard_module)
            PerformanceDashboard = dashboard_module.PerformanceDashboard
            print("✅ Performance dashboard imported from direct path")
        else:
            PerformanceDashboard = None
            print("❌ Dashboard file not found")
    except Exception as e2:
        print(f"❌ Alternative import also failed: {e2}")
        PerformanceDashboard = None


# ============================================
# HOME WINDOW - CHÍNH SỬA QUAN TRỌNG
# ============================================
class HomeWindow(QMainWindow):
    def __init__(self, user_name="User"):
        super().__init__()
        self.user_name = user_name
        self.ui = Ui_HomeWindow()
        self.ui.setupUi(self)

        # DISABLE PHÓNG TO và không cho thay đổi kích thước
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(self.size())

        # KHỞI TẠO GLOBAL LOGGER
        self.global_logger = GlobalExcelLogger(user_name)

        # Biến hệ thống
        self.mouse_process = None
        self.stop_event = None
        self.pause_event = None
        self.command_queue = None
        self.alert_queue = None
        self.browser_window = None
        self.chatbot_window = None
        self.dashboard_window = None
        self.is_working = False
        self.active_window = None  # Track which window is active

        # Cập nhật tên user
        self.update_user_name(user_name)

        # SETUP STYLE CHO TAB HIỆN TẠI
        self.setup_tab_styles()

        # Kết nối nút HOME (pushButton_5) - TAB HIỆN TẠI
        if hasattr(self.ui, 'pushButton_5'):
            self.ui.pushButton_5.clicked.connect(self.on_home_clicked)
            self.ui.pushButton_5.setEnabled(False)  # Home là tab hiện tại
            print("✅ Connected pushButton_5 (HOME)")

        # Kết nối nút CHATBOT (pushButton_7)
        if hasattr(self.ui, 'pushButton_7'):
            self.ui.pushButton_7.clicked.connect(self.open_chatbot)
            print("✅ Connected pushButton_7 (CHATBOT)")

        # Kết nối nút DASHBOARD (pushButton_10)
        if hasattr(self.ui, 'pushButton_10'):
            self.ui.pushButton_10.clicked.connect(self.open_dashboard)
            print("✅ Connected pushButton_10 (DASHBOARD)")

        # Kết nối các nút khác
        self.ui.pushButton_8.clicked.connect(self.start_work_session)
        self.ui.pushButton_6.clicked.connect(self.view_logs)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.setWindowTitle(f"PowerSight - {user_name}")
        self.setWindowFlag(Qt.WindowType.Window, True)
        print(f"🏠 HomeWindow created for {user_name}")

    def setup_tab_styles(self):
        """Setup màu sắc cho các tab - tab hiện tại màu xanh dương nhạt"""
        if hasattr(self.ui, 'pushButton_5'):  # HOME - tab hiện tại
            self.ui.pushButton_5.setStyleSheet("""
                QPushButton {
                    background-color: #87CEEB;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                }
                QPushButton:disabled {
                    background-color: #87CEEB;
                    color: white;
                }
            """)

        if hasattr(self.ui, 'pushButton_7'):  # CHATBOT
            self.ui.pushButton_7.setStyleSheet("""
                QPushButton {
                    background-color: #4A4D52;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5A5D62;
                }
            """)

        if hasattr(self.ui, 'pushButton_10'):  # DASHBOARD
            self.ui.pushButton_10.setStyleSheet("""
                QPushButton {
                    background-color: #4A4D52;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 10px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #5A5D62;
                }
            """)

    def on_home_clicked(self):
        """Khi click vào HOME tab"""
        print("🏠 Home tab clicked - Already on home")
        # Không làm gì vì đang ở home

    def update_tab_state(self, active_tab):
        """Cập nhật trạng thái tab khi chuyển đổi"""
        # Reset tất cả các tab về màu mặc định
        tabs = {
            'home': self.ui.pushButton_5,
            'chatbot': self.ui.pushButton_7,
            'dashboard': self.ui.pushButton_10
        }

        for tab_name, tab_button in tabs.items():
            if tab_button:
                if tab_name == active_tab:
                    # Tab active - xanh dương nhạt và disabled
                    tab_button.setStyleSheet("""
                        QPushButton {
                            background-color: #87CEEB;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            padding: 10px;
                            font-weight: bold;
                        }
                        QPushButton:disabled {
                            background-color: #87CEEB;
                            color: white;
                        }
                    """)
                    tab_button.setEnabled(False)
                else:
                    # Tab không active - màu xám và enabled
                    tab_button.setStyleSheet("""
                        QPushButton {
                            background-color: #4A4D52;
                            color: white;
                            border: none;
                            border-radius: 8px;
                            padding: 10px;
                            font-weight: bold;
                        }
                        QPushButton:hover {
                            background-color: #5A5D62;
                        }
                    """)
                    tab_button.setEnabled(True)

    def open_chatbot(self):
        """Mở chatbot"""
        print(f"\n{'=' * 50}")
        print(f"🚀 OPENING CHATBOT for {self.user_name}")
        print(f"{'=' * 50}")

        if EmployeeChatbotGUI is None:
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 "Không thể tải chatbot system.\n\n"
                                 )
            return

        # Đảm bảo lưu dữ liệu trước
        if hasattr(self, 'global_logger'):
            try:
                self.global_logger.save_to_excel()
                print("💾 Work log saved successfully")
            except Exception as e:
                print(f"⚠️ Could not save work log: {e}")

        # Đóng chatbot cũ nếu có
        if self.chatbot_window:
            try:
                self.chatbot_window.close()
                self.chatbot_window = None
                print("🛑 Closed previous chatbot window")
            except:
                pass

        try:
            # Tạo và hiển thị chatbot
            self.chatbot_window = EmployeeChatbotGUI(self.user_name, self)
            self.chatbot_window.showFullScreen()
            self.active_window = 'chatbot'

            # Cập nhật tab state
            self.update_tab_state('chatbot')

            # Home window minimize
            self.showMinimized()
            print("🏠 Home window minimized")

            print(f"✅ Chatbot opened successfully for {self.user_name}")

        except Exception as e:
            print(f"❌ CRITICAL ERROR opening chatbot: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 f"Lỗi nghiêm trọng khi mở chatbot:\n\n{str(e)[:100]}...\n\n"
                                 "Vui lòng kiểm tra file employee_chatbot.py")

    def open_dashboard(self):
        """Mở dashboard"""
        print(f"\n{'=' * 50}")
        print(f"📊 OPENING DASHBOARD for {self.user_name}")
        print(f"{'=' * 50}")

        if PerformanceDashboard is None:
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 "Không thể tải dashboard system.\n\n"
                                 "Vui lòng kiểm tra:\n"
                                 "1. File dashboard.py có tồn tại không?\n"
                                 "2. Đường dẫn đúng: C:\\PythonProject (1)\\PythonProject\\dashboard.py")
            return

        # Đảm bảo lưu dữ liệu trước
        if hasattr(self, 'global_logger'):
            try:
                self.global_logger.save_to_excel()
                print("💾 Work log saved successfully")
            except Exception as e:
                print(f"⚠️ Could not save work log: {e}")

        # Đóng dashboard cũ nếu có
        if self.dashboard_window:
            try:
                self.dashboard_window.close()
                self.dashboard_window = None
                print("🛑 Closed previous dashboard window")
            except:
                pass

        try:
            # Tạo và hiển thị dashboard
            self.dashboard_window = PerformanceDashboard(self.user_name, self)
            self.dashboard_window.showFullScreen()
            self.active_window = 'dashboard'

            # Cập nhật tab state
            self.update_tab_state('dashboard')

            # Home window minimize
            self.showMinimized()
            print("🏠 Home window minimized")

            print(f"✅ Dashboard opened successfully for {self.user_name}")

        except Exception as e:
            print(f"❌ CRITICAL ERROR opening dashboard: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 f"Lỗi nghiêm trọng khi mở dashboard:\n\n{str(e)[:100]}...\n\n"
                                 "Vui lòng kiểm tra file dashboard.py")

    def update_user_name(self, user_name):
        """Cập nhật tên user trên UI"""
        if hasattr(self.ui, 'label_7'):
            self.ui.label_7.setText(f"{user_name}!")

    def update_time(self):
        """Cập nhật thời gian hiện tại"""
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        if hasattr(self.ui, 'label_3'):
            self.ui.label_3.setText(f"Time: {current_time}")
        if hasattr(self.ui, 'label_4'):
            self.ui.label_4.setText(f"Date: {current_date}")

    def start_work_session(self):
        if self.is_working:
            QMessageBox.information(self, "Session Active", "Work session is already running!")
            return

        reply = QMessageBox.question(
            self, "Start Work Session",
            f"Start secure work session for {self.user_name}?\n\n"
            "Features included:\n"
            "✓ Safe Browser (Gmail + SAP)\n"
            "✓ Mouse Behavior Analysis\n"
            "✓ Random Face Verification\n"
            "✓ Stranger Detection\n"
            "✓ Activity Logging\n"
            "✓ Fraud Detection\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            self.is_working = True
            self.ui.pushButton_8.setText("Working...")
            self.ui.pushButton_8.setEnabled(False)
            self.ui.pushButton_5.setEnabled(True)
            self.ui.pushButton_6.setEnabled(True)
            if hasattr(self.ui, 'khichle'):
                self.ui.khichle.setText("🔐 Secure work session active")

            self.global_logger.log_browser_alert(
                event_type="SESSION_START",
                details=f"Session started for {self.user_name}",
                severity="INFO",
                is_fraud=False
            )

            self.stop_event = multiprocessing.Event()
            self.pause_event = multiprocessing.Event()
            self.command_queue = multiprocessing.Queue()
            self.alert_queue = multiprocessing.Queue()

            self.mouse_process = multiprocessing.Process(
                target=mouse_process_entry,
                args=(
                    self.stop_event,
                    self.pause_event,
                    self.command_queue,
                    self.alert_queue,
                    0,
                    self.user_name,
                    self.global_logger
                ),
                daemon=True
            )
            self.mouse_process.start()
            print("✅ Mouse process started:", self.mouse_process.pid)

            self.global_logger.log_browser_alert(
                event_type="MOUSE_TRACKING_START",
                details="Mouse analysis system started",
                severity="INFO",
                is_fraud=False
            )

            self.browser_window = EnhancedSafeBrowser(
                user_name=self.user_name,
                global_logger=self.global_logger,
                parent_window=self,
                pause_event=self.pause_event,
                command_queue=self.command_queue,
                alert_queue=self.alert_queue
            )

            QTimer.singleShot(100, self.browser_window.setup_timer_with_logging)

            self.browser_window.show_secure()
            self.showMinimized()
            self.active_window = 'browser'

            self.global_logger.log_browser_alert(
                event_type="SESSION_START_FULLSCREEN",
                details="Work session started in fullscreen mode",
                severity="INFO",
                is_fraud=False
            )

        except Exception as e:
            print(f"❌ Error starting work session: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to start work session: {str(e)}")
            self.reset_ui()

    def show_browser(self):
        """Hiển thị browser nếu đang chạy"""
        if self.browser_window and self.is_working:
            self.browser_window.showFullScreen()
            self.browser_window.activateWindow()
            self.showMinimized()
        else:
            QMessageBox.information(self, "No Active Session", "No active work session found.")

    def view_logs(self):
        """Hiển thị logs từ global logger"""
        summary = self.global_logger.get_session_summary()

        msg = QMessageBox(self)
        msg.setWindowTitle("Session Summary")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            f"📊 SESSION SUMMARY\n\n"
            f"User: {summary['user']}\n"
            f"Session ID: {summary['session_id']}\n"
            f"Total Alerts: {summary['total_alerts']}\n"
            f"Mouse Entries: {summary['mouse_entries']}\n"
            f"Log File: {summary['excel_file']}"
        )

        open_btn = msg.addButton("Open Log File", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Close", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        if msg.clickedButton() == open_btn:
            self.global_logger.open_log_file()

    def on_browser_closed(self):
        """Xử lý khi browser đóng"""
        print("\n🛑 Browser closed by user")

        self.global_logger.log_browser_alert(
            event_type="SESSION_END",
            details=f"Session ended for {self.user_name}",
            severity="INFO",
            is_fraud=False
        )

        self.global_logger.save_final_data()

        if self.stop_event:
            self.stop_event.set()

        if self.mouse_process:
            print("⏳ Waiting for mouse process to save data...")
            self.mouse_process.join(timeout=10)

            if self.mouse_process.is_alive():
                print("⚠️ Mouse process not responding, terminating...")
                self.mouse_process.terminate()
                self.mouse_process.join(timeout=2)

        print("✅ Mouse data saved successfully!")
        self.reset_ui()
        self.mouse_process = None
        self.stop_event = None
        self.pause_event = None
        self.command_queue = None
        self.alert_queue = None
        self.browser_window = None
        print("✅ Session cleanup completed.")
        self.showNormal()
        self.activateWindow()

    def reset_ui(self):
        """Reset UI về trạng thái ban đầu"""
        self.is_working = False
        self.ui.pushButton_8.setText("Start")
        self.ui.pushButton_8.setEnabled(True)
        self.ui.pushButton_5.setEnabled(False)
        self.ui.pushButton_6.setEnabled(False)
        if hasattr(self.ui, 'khichle'):
            self.ui.khichle.setText("Session ended. Ready for next session.")

    def on_chatbot_closed(self):
        """Khi chatbot đóng"""
        print("\n🛑 Chatbot window closed")
        self.chatbot_window = None
        self.active_window = 'home'
        self.update_tab_state('home')
        self.showNormal()
        self.raise_()
        self.activateWindow()

        if hasattr(self.ui, 'khichle'):
            self.ui.khichle.setText("Sẵn sàng")

    def on_dashboard_closed(self):
        """Khi dashboard đóng"""
        print("\n🛑 Dashboard window closed")
        self.dashboard_window = None
        self.active_window = 'home'
        self.update_tab_state('home')
        self.showNormal()
        self.raise_()
        self.activateWindow()

        if hasattr(self.ui, 'khichle'):
            self.ui.khichle.setText("Sẵn sàng")

    def closeEvent(self, event):
        """Xử lý khi đóng HomeWindow"""
        print("\n🛑 HomeWindow close event")
        TaskbarController.set_visibility(True)

        # Đóng chatbot nếu đang mở
        if self.chatbot_window:
            try:
                print("   Closing chatbot window...")
                self.chatbot_window.close()
                self.chatbot_window = None
            except:
                pass

        # Đóng dashboard nếu đang mở
        if self.dashboard_window:
            try:
                print("   Closing dashboard window...")
                self.dashboard_window.close()
                self.dashboard_window = None
            except:
                pass

        # Kiểm tra work session
        if self.is_working and self.browser_window:
            self.browser_window.show()
            self.browser_window.activateWindow()
            QMessageBox.warning(self, "Không thể đóng",
                                "Không thể đóng Home khi session đang chạy.\nVui lòng đóng browser trước.")
            event.ignore()
            return

        event.accept()
        print("✅ HomeWindow closed successfully")


# ============================================
# HÀM MAIN HOÀN CHỈNH
# ============================================
def main():
    # 1. Kiểm tra môi trường hệ thống
    if not os.path.exists(SAVED_FILE_DIR):
        os.makedirs(SAVED_FILE_DIR, exist_ok=True)
        print(f"📁 Created main directory: {SAVED_FILE_DIR}")

    print("\n🔍 Kiểm tra các file ảnh:")
    for image_name in ["background2.jpg", "background5.jpg", "faceid_icon.jpg"]:
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            print(f"✅ Found: {image_name}")
        else:
            print(f"❌ Missing: {image_path}")

    # Kiểm tra các file module quan trọng
    print("\n🔍 Kiểm tra các file module:")
    important_files = [
        "employee_chatbot.py",
        "dashboard.py",
        "Face/main_face.py",
        "Workspace/SafeWorkingBrowser.py",
        "Mouse/Main_mouse.py"
    ]

    for file in important_files:
        file_path = os.path.join(BASE_DIR, file)
        if os.path.exists(file_path):
            print(f"✅ Found: {file}")
        else:
            print(f"❌ Missing: {file}")

    # 2. Hỗ trợ đa tiến trình
    multiprocessing.freeze_support()

    # 3. Khởi tạo ứng dụng PyQt6
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("PowerSight")

    # 4. CHỐT CHẶN AN TOÀN: Khi app sắp tắt, phải hiện lại Taskbar ngay
    app.aboutToQuit.connect(lambda: TaskbarController.set_visibility(True))

    # 5. Đọc thông tin đăng nhập từ file tạm
    login_file = os.path.join(PROJECT_ROOT, "temp_login.txt")
    user_name = None
    user_type = None

    if os.path.exists(login_file):
        try:
            with open(login_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"📄 Nội dung file login: {content}")
                parts = content.split(":")
                if len(parts) == 2:
                    user_type = parts[0]
                    user_name = parts[1]

                    if user_type == "employee":
                        print(f"✅ Đã đăng nhập với tư cách NHÂN VIÊN: {user_name}")
                        # Xóa file tạm
                        os.remove(login_file)
                    else:
                        print(f"❌ Người dùng không phải nhân viên: {user_type}")
                        user_name = None
                else:
                    print("❌ Thông tin đăng nhập không hợp lệ")
        except Exception as e:
            print(f"❌ Lỗi đọc file đăng nhập: {e}")

    if not user_name:
        print("❌ Không tìm thấy thông tin đăng nhập hợp lệ cho nhân viên")
        QMessageBox.critical(None, "Lỗi đăng nhập",
                             "Không tìm thấy thông tin đăng nhập hợp lệ cho nhân viên.\nVui lòng chạy App.py để đăng nhập.")
        sys.exit(1)

    # 6. Tạo và hiển thị HomeWindow
    try:
        window = HomeWindow(user_name)
        window.show()
        exit_code = app.exec()
        sys.exit(exit_code)

    except Exception as e:
        print(f"\n❌ ỨNG DỤNG BỊ LỖI NGHIÊM TRỌNG:")
        traceback.print_exc()

    finally:
        # 7. CÁNH CỬA CUỐI CÙNG: Khôi phục thanh công cụ
        print("\n🛡️ Final safety check: Khôi phục thanh công cụ hệ thống...")
        TaskbarController.set_visibility(True)


if __name__ == "__main__":
    main()