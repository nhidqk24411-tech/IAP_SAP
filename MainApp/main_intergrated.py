# main_integrated.py - HOÀN CHỈNH VỚI BROWSER TIME LOGGING
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

from Chatbot.chatbot_launcher import ChatbotLauncher

# =========================
# CONFIGURATION
# =========================
BASE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject"
SAVED_FILE_DIR = os.path.join(BASE_DIR, "Saved_file")
UI_DIR = os.path.join(BASE_DIR, "MainApp", "UI")
IMAGES_DIR = os.path.join(UI_DIR, "images")
sys.path.insert(0, BASE_DIR)
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

    # Lấy thông tin tháng hiện tại
    current_date = datetime.now()
    year_month = current_date.strftime("%Y_%m")

    # Tạo thư mục năm_tháng chính
    monthly_dir = os.path.join(user_base_dir, year_month)
    os.makedirs(monthly_dir, exist_ok=True)

    # Tạo thư mục face_captures bên trong thư mục tháng
    face_captures_dir = os.path.join(monthly_dir, "face_captures")
    os.makedirs(face_captures_dir, exist_ok=True)

    paths = {
        'user_base': user_base_dir,
        'monthly': monthly_dir,  # Thư mục chính
        'face_captures': face_captures_dir,  # Thư mục ảnh capture
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
        from Mouse.Module.Process_Excel import MouseExcelHandler

        print(f"🖱️ Mouse tracking started for user: {user_name}")
        print(f"✅ Global logger passed to mouse process: {'YES' if global_logger else 'NO'}")

        if delay_minutes > 0:
            for _ in range(delay_minutes * 60):
                if stop_event.is_set():
                    return
                time.sleep(1)

        # TRUYỀN global_logger VÀO MouseAnalysisSystem
        system = MouseAnalysisSystem(global_logger)
        system.run_continuous_analysis(
            stop_event,
            pause_event,
            command_queue,
            alert_queue,
            user_name,
            global_logger  # THÊM global_logger VÀO ĐÂY
        )

    except Exception as e:
        print("❌ Mouse process crashed:", e)
        traceback.print_exc()


# Import UI
from UI.UI_LOGIN import Ui_MainWindow as Ui_LoginWindow
from UI.UI_FACEID import Ui_MainWindow as Ui_FaceIDWindow
from UI.UI_HOME import Ui_MainWindow as Ui_HomeWindow

# Import systems
from Face.main_face import FaceSingleCheck
from Workspace.SafeWorkingBrowser import ProfessionalWorkBrowser


# ============================================
# GLOBAL EXCEL LOGGER - CẬP NHẬT THÊM BROWSER TIME LOGGING
# ============================================
class GlobalExcelLogger:
    """Logger toàn cục cho tất cả module - CHỈ LƯU GIAN LẬN + THÊM BROWSER TIME"""

    def __init__(self, user_name):
        self.user_name = user_name
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Setup directories for user
        self.PATHS = setup_user_directories(user_name)

        # Lấy thông tin tháng hiện tại
        current_date = datetime.now()
        self.current_year_month = current_date.strftime("%Y_%m")

        # Đường dẫn file Excel duy nhất
        self.excel_path = os.path.join(
            self.PATHS['monthly'],
            f"work_logs_{user_name}_{self.current_year_month}.xlsx"
        )

        # Data storage
        self.fraud_events = []  # Sheet 1: CHỈ sự kiện gian lận (IsFraud = 1)
        self.mouse_details = []  # Sheet 2: Chi tiết chuột (có cả bình thường và gian lận)
        self.browser_time_logs = []  # Sheet 3: Thời gian làm việc trên browser MỚI

        self.last_save_time = time.time()
        self.save_interval = 60

        print(f"🌐 Global logger initialized: {self.excel_path}")
        print(f"   Mode: Only fraud events saved to All_Events sheet")
        print(f"   Added: Browser Time Logging sheet")

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

        # CHỈ LƯU NẾU LÀ GIAN LẬN (IsFraud = 1)
        if is_fraud:
            self.fraud_events.append(event_entry)
            print(f"🚨 [FRAUD] [{module}] {event_type} - {details}")
        else:
            # Chỉ hiển thị log, không lưu vào sheet All_Events
            print(f"ℹ️  [{module}] {event_type} - {details}")

    def log_mouse_details(self, event_type, details="", severity="INFO", is_fraud=False, **mouse_data):
        """Ghi chi tiết chuột vào sheet riêng - VẪN LƯU TẤT CẢ"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Các cột cơ bản
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

        # Thêm dữ liệu chuột chi tiết
        mouse_entry.update(mouse_data)
        self.mouse_details.append(mouse_entry)

        # Ghi log cảnh báo vào sheet chung NẾU CÓ GIAN LẬN
        if is_fraud:
            self.log_alert("Mouse", event_type, details, severity, is_fraud)

    def log_face_alert(self, event_type, details="", severity="INFO", is_fraud=False, **face_data):
        """Ghi log face - CHỈ LƯU NẾU GIAN LẬN"""
        # CHỈ log nếu là gian lận
        if is_fraud:
            self.log_alert("Face", event_type, details, severity, is_fraud)
        else:
            print(f"ℹ️  [Face] {event_type} - {details}")

    def log_browser_alert(self, event_type, details="", severity="INFO", is_fraud=False):
        """Ghi log browser - CHỈ LƯU NẾU GIAN LẬN"""
        # CHỈ log nếu là gian lận
        if is_fraud:
            self.log_alert("Browser", event_type, details, severity, is_fraud)
        else:
            print(f"ℹ️  [Browser] {event_type} - {details}")

    def log_browser_time(self, event_type, url="", tab_name="", start_time=None, end_time=None, duration_seconds=0):
        """Ghi log thời gian làm việc trên browser - MỚI"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if start_time is None:
            start_time = timestamp
        if end_time is None:
            end_time = timestamp

        # Tính duration nếu chưa có
        if duration_seconds == 0 and isinstance(start_time, str) and isinstance(end_time, str):
            try:
                start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
                duration_seconds = (end_dt - start_dt).total_seconds()
            except:
                duration_seconds = 0

        browser_entry = {
            "Timestamp": timestamp,
            "Event_Type": event_type,
            "URL": url[:200] if url else "",  # Giới hạn độ dài URL
            "Tab_Name": tab_name[:100] if tab_name else "",
            "Start_Time": start_time,
            "End_Time": end_time,
            "Duration_Seconds": duration_seconds,
            "Duration_Formatted": self.format_duration(duration_seconds),
            "User": self.user_name,
            "Session_ID": self.session_id,
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Time": datetime.now().strftime("%H:%M:%S"),
            "Module": "Browser_Time"
        }

        self.browser_time_logs.append(browser_entry)
        print(f"⏱️  [Browser Time] {event_type} - {tab_name} - {self.format_duration(duration_seconds)}")

    def format_duration(self, seconds):
        """Format thời gian từ seconds sang HH:MM:SS"""
        if seconds == 0:
            return "00:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def save_to_excel(self):
        """Lưu vào file Excel với 3 sheets"""
        try:
            # Sheet 1: CHỈ sự kiện gian lận
            df_fraud = pd.DataFrame(self.fraud_events) if self.fraud_events else pd.DataFrame(columns=[
                "Timestamp", "Event_Type", "Details", "User", "Session_ID",
                "Severity", "IsFraud", "Date", "Time", "Module"
            ])

            # Sheet 2: Chi tiết chuột (VẪN LƯU TẤT CẢ)
            df_mouse = pd.DataFrame(self.mouse_details) if self.mouse_details else pd.DataFrame(columns=[
                "Timestamp", "Event_Type", "Details", "User", "Session_ID",
                "Severity", "IsFraud", "Date", "Time", "Module",
                "TotalEvents", "TotalMoves", "TotalDistance", "XAxisDistance",
                "YAxisDistance", "XFlips", "YFlips", "MovementTimeSpan",
                "Velocity", "Acceleration", "XVelocity", "YVelocity",
                "XAcceleration", "YAcceleration", "DurationSeconds", "AnomalyScore"
            ])

            # Sheet 3: Thời gian làm việc trên Browser - MỚI
            df_browser_time = pd.DataFrame(self.browser_time_logs) if self.browser_time_logs else pd.DataFrame(columns=[
                "Timestamp", "Event_Type", "URL", "Tab_Name", "Start_Time", "End_Time",
                "Duration_Seconds", "Duration_Formatted", "User", "Session_ID",
                "Date", "Time", "Module"
            ])

            # Kiểm tra nếu file đã tồn tại
            if os.path.exists(self.excel_path):
                try:
                    # Đọc dữ liệu cũ từ tất cả sheets
                    old_fraud = pd.read_excel(self.excel_path, sheet_name='Fraud_Events')
                    old_mouse = pd.read_excel(self.excel_path, sheet_name='Mouse_Details')

                    # Kiểm tra nếu có sheet Browser_Time cũ
                    try:
                        old_browser_time = pd.read_excel(self.excel_path, sheet_name='Browser_Time')
                    except:
                        old_browser_time = pd.DataFrame()

                    # Kết hợp dữ liệu
                    df_fraud = pd.concat([old_fraud, df_fraud], ignore_index=True)
                    df_mouse = pd.concat([old_mouse, df_mouse], ignore_index=True)
                    df_browser_time = pd.concat([old_browser_time, df_browser_time], ignore_index=True)

                    # Xóa trùng lặp
                    df_fraud = df_fraud.drop_duplicates(subset=['Timestamp', 'Event_Type', 'Session_ID'])
                    df_mouse = df_mouse.drop_duplicates(subset=['Timestamp', 'Event_Type', 'Session_ID'])
                    df_browser_time = df_browser_time.drop_duplicates(subset=['Timestamp', 'Event_Type', 'Session_ID'])

                except Exception as e:
                    print(f"⚠️ Error reading existing file: {e}")

            # Lưu vào Excel với 3 sheets
            with pd.ExcelWriter(self.excel_path, engine='openpyxl') as writer:
                # Sheet 1: CHỈ sự kiện gian lận
                df_fraud.to_excel(writer, sheet_name='Fraud_Events', index=False)

                # Sheet 2: Chi tiết chuột
                df_mouse.to_excel(writer, sheet_name='Mouse_Details', index=False)

                # Sheet 3: Thời gian browser - MỚI
                df_browser_time.to_excel(writer, sheet_name='Browser_Time', index=False)

            print(f"💾 Global log saved: {self.excel_path}")
            print(f"   Fraud events: {len(df_fraud)}")
            print(f"   Mouse entries: {len(df_mouse)}")
            print(f"   Browser time entries: {len(df_browser_time)}")
            return True

        except Exception as e:
            print(f"❌ Error saving global log: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_final_data(self):
        """Lưu dữ liệu cuối cùng"""
        self.save_to_excel()
        print(f"✅ Final data saved for user: {self.user_name}")

    def get_session_summary(self):
        """Lấy thông tin tổng hợp session - FIX: dùng self.fraud_events thay vì self.all_events"""
        return {
            "user": self.user_name,
            "session_id": self.session_id,
            "total_alerts": len(self.fraud_events),  # SỬA TỪ self.all_events -> self.fraud_events
            "mouse_entries": len(self.mouse_details),
            "browser_time_entries": len(self.browser_time_logs),
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
# LOGIN WINDOW
# ============================================
class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_LoginWindow()
        self.ui.setupUi(self)
        self.setWindowTitle("PowerSight - Login")
        self.faceid_window = None

        # LOAD ẢNH NỀN
        background_pixmap = load_image("background2.jpg")
        if background_pixmap:
            self.ui.label_3.setPixmap(background_pixmap)

        # LOAD ICON CHO NÚT FACEID
        faceid_icon = load_image("faceid_icon.jpg")
        if faceid_icon:
            self.ui.pushButton_faceid.setIcon(QIcon(faceid_icon))
            self.ui.pushButton_faceid.setIconSize(QSize(25, 25))

        print(f"🔍 Kiểm tra nút FaceID: pushButton_faceid = {hasattr(self.ui, 'pushButton_faceid')}")

        if hasattr(self.ui, 'pushButton_faceid'):
            self.ui.pushButton_faceid.clicked.connect(self.open_faceid)
            print("✅ Đã kết nối nút FaceID")
        else:
            print("❌ KHÔNG TÌM THẤY NÚT pushButton_faceid trong UI!")
            self.create_fallback_button()

    def create_fallback_button(self):
        """Tạo nút fallback nếu nút trong UI không tồn tại"""
        fallback_btn = QPushButton("Face ID Login", self)
        fallback_btn.setGeometry(100, 100, 200, 50)
        fallback_btn.clicked.connect(self.open_faceid)
        fallback_btn.show()
        print("⚠️ Đã tạo nút FaceID fallback")

    def open_faceid(self):
        print("🔄 Mở cửa sổ FaceID...")
        try:
            # Đóng cửa sổ FaceID cũ nếu có
            if self.faceid_window:
                try:
                    self.faceid_window.close()
                except:
                    pass

            self.hide()
            self.faceid_window = FaceIDWindow(self)
            self.faceid_window.show()
            print("✅ Đã mở cửa sổ FaceID")
        except Exception as e:
            print(f"❌ Lỗi khi mở FaceID: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể mở cửa sổ FaceID: {str(e)}")
            self.show()  # Hiển thị lại login window

    def show(self):
        """Override show để đảm bảo hiển thị đúng"""
        super().show()
        self.activateWindow()
        self.raise_()
        print("✅ LoginWindow hiển thị")


# ============================================
# FACE ID WINDOW - SỬA LỖI TỰ THOÁT
# ============================================
class FaceIDWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_FaceIDWindow()
        self.ui.setupUi(self)

        # LOAD ẢNH NỀN
        background_pixmap = load_image("background5.jpg")
        if background_pixmap:
            self.ui.label.setPixmap(background_pixmap)

        self.parent_window = parent
        self.recognized_user = None
        self.attempt_count = 0
        self.max_attempts = 3
        self.cap = None
        self.recognition_complete = False

        print("🔍 Kiểm tra webcam...")
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("❌ Không thể mở webcam, thử camera index 1...")
                self.cap = cv2.VideoCapture(1)

            if not self.cap.isOpened():
                QMessageBox.critical(self, "Lỗi", "Không thể mở webcam. Vui lòng kiểm tra camera.")
                print("❌ Không thể mở webcam")
                self.return_to_login()
                return

            print("✅ Camera mở thành công")
        except Exception as e:
            print(f"❌ Lỗi mở camera: {e}")
            QMessageBox.critical(self, "Lỗi", f"Lỗi mở camera: {str(e)}")
            self.return_to_login()
            return

        # Load face system
        print("🔍 Tải hệ thống nhận diện...")
        try:
            self.face_system = FaceSingleCheck(user_name="")
            print("✅ Hệ thống FaceSingleCheck đã tải")
        except Exception as e:
            print(f"❌ Lỗi tải FaceSingleCheck: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể tải hệ thống nhận diện: {str(e)}")
            self.return_to_login()
            return

        # Setup timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.start_time = datetime.now()
        self.recognition_started = False

        self.setWindowTitle("PowerSight - Face Login")
        print("✅ Cửa sổ FaceID đã sẵn sàng")

    def update_frame(self):
        if self.recognition_complete:
            return

        try:
            ret, frame = self.cap.read()
            if not ret:
                print("⚠️ Không đọc được frame từ webcam")
                return

            frame = cv2.flip(frame, 1)
            self.display_frame(frame)

            elapsed = (datetime.now() - self.start_time).total_seconds()
            if elapsed > 3 and not self.recognition_started:
                self.recognition_started = True
                self.process_recognition(frame)
        except Exception as e:
            print(f"❌ Lỗi update frame: {e}")

    def display_frame(self, frame):
        """Hiển thị frame từ camera - FIXED for PyQt6"""
        try:
            label_w = self.ui.labelCamera.width()
            label_h = self.ui.labelCamera.height()

            if label_w <= 0 or label_h <= 0:
                return

            # Resize frame cho vừa label
            frame = cv2.resize(frame, (label_w, label_h))

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Get dimensions
            h, w, ch = frame_rgb.shape

            # Tạo QImage với strides đúng
            qimg = QImage(frame.data, w, h, w * 3, QImage.Format.Format_RGB888)
            # Tạo QPixmap với transparency
            pixmap = QPixmap(label_w, label_h)
            pixmap.fill(Qt.GlobalColor.transparent)

            # Vẽ hình tròn
            painter = QPainter(pixmap)
            path = QPainterPath()
            path.addEllipse(0, 0, label_w, label_h)
            painter.setClipPath(path)

            # Vẽ ảnh
            painter.drawImage(0, 0, qimg)
            painter.end()

            # Hiển thị lên label
            self.ui.labelCamera.setPixmap(pixmap)

        except Exception as e:
            print(f"❌ Lỗi hiển thị frame: {e}")
            import traceback
            traceback.print_exc()

    def process_recognition(self, frame):
        try:
            print("🔍 Đang nhận diện khuôn mặt...")
            result = self.face_system.check_single_face(frame)

            if result["success"] and result["matched"]:
                user_name = result["name"]
                similarity = result["similarity"]
                print(f"✅ Đăng nhập thành công: {user_name} ({similarity:.2%})")

                self.ui.label_2.setText(f"WELCOME {user_name}!")
                self.recognized_user = user_name

                # Dừng timer và camera
                self.cleanup_camera()
                self.recognition_complete = True

                # Mở HomeWindow sau 1 giây
                QTimer.singleShot(1000, self.open_home)
            else:
                self.attempt_count += 1

                if self.attempt_count >= self.max_attempts:
                    # Quá 3 lần, quay lại login
                    self.cleanup_camera()
                    self.recognition_complete = True
                    QMessageBox.warning(
                        self, "Quá nhiều lần thử",
                        f"Không nhận diện được khuôn mặt sau {self.max_attempts} lần thử.\n"
                        "Quay lại màn hình đăng nhập."
                    )
                    QTimer.singleShot(500, self.return_to_login)
                else:
                    # Hiển thị số lần thử còn lại
                    remaining = self.max_attempts - self.attempt_count
                    self.ui.label_2.setText(f"FACE VERIFICATION FAILED - {remaining} ATTEMPT(S) REMAINING")
                    self.recognition_started = False
                    self.start_time = datetime.now()

        except Exception as e:
            print("❌ Lỗi nhận diện:", e)
            traceback.print_exc()
            self.attempt_count += 1

            if self.attempt_count >= self.max_attempts:
                self.cleanup_camera()
                self.recognition_complete = True
                QTimer.singleShot(500, self.return_to_login)
            else:
                self.ui.label_2.setText(f"SYSTEM ERROR ({self.max_attempts - self.attempt_count} ATTEMPTS REMAINING)")
                self.recognition_started = False
                self.start_time = datetime.now()

    def cleanup_camera(self):
        """Dọn dẹp camera an toàn"""
        try:
            if self.cap and self.cap.isOpened():
                self.cap.release()
                print("✅ Camera released")
            if hasattr(self, 'timer') and self.timer:
                self.timer.stop()
                print("✅ Timer stopped")
        except Exception as e:
            print(f"⚠️ Lỗi khi cleanup camera: {e}")

    def return_to_login(self):
        """Quay lại màn hình login"""
        print("🔙 Quay lại màn hình login...")
        self.cleanup_camera()

        if self.parent_window:
            self.parent_window.show()

        self.close()

    def open_home(self):
        """Mở màn hình Home"""
        print("🏠 Mở màn hình Home...")

        # Tạo HomeWindow
        self.home_window = HomeWindow(self.recognized_user)

        # Đảm bảo camera đã được giải phóng
        self.cleanup_camera()

        # Hiển thị HomeWindow
        self.home_window.show()

        # Đóng cửa sổ FaceID và parent
        if self.parent_window:
            self.parent_window.close()
        self.close()

    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        print("🛑 Đóng cửa sổ FaceID...")
        self.cleanup_camera()
        event.accept()


# ============================================
# ENHANCED SAFE BROWSER - CẬP NHẬT THÊM TIME TRACKING
# ============================================
class EnhancedSafeBrowser(ProfessionalWorkBrowser):
    """Safe Browser dùng global logger - THÊM TIME TRACKING"""

    def __init__(self, user_name, global_logger, parent_window=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name = user_name
        self.global_logger = global_logger
        self.parent_window = parent_window
        self.current_tab_start_time = None
        self.current_tab_name = None
        self.current_tab_url = None
        self.browser_start_time = datetime.now()
        self.tab_timers = {}
        self.fraud_alert_shown = False
        self.is_closing = False
        self.tab_history = []  # Lưu lịch sử các tab

        # Timer tự động save mỗi phút
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save_tab_time)
        self.auto_save_timer.start(60000)  # 1 phút

        # Thiết lập random face check
        self.setup_random_check()

        # Khởi tạo face system
        try:
            from Face.main_face import FaceSingleCheck
            self.face_system = FaceSingleCheck(user_name=self.user_name, global_logger=self.global_logger)
            print(f"✅ Face system loaded for random check (user: {user_name})")
        except Exception as e:
            print(f"❌ Failed to load face system: {e}")
            self.face_system = None

        # Kết nối sự kiện tab changed
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        # Ghi log mở browser
        self.global_logger.log_browser_alert(
            event_type="BROWSER_OPEN",
            details="Professional Workspace Browser started",
            severity="INFO",
            is_fraud=False
        )

        # Ghi log thời gian bắt đầu browser
        self.global_logger.log_browser_time(
            event_type="BROWSER_START",
            url="",
            tab_name="Browser Session",
            start_time=self.browser_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=self.browser_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds=0
        )

    def on_tab_changed(self, index):
        """Xử lý khi chuyển tab - THÊM TIME TRACKING"""
        # Lưu thời gian tab cũ
        if self.current_tab_start_time and self.current_tab_name:
            end_time = datetime.now()
            duration = (end_time - self.current_tab_start_time).total_seconds()

            if duration > 1:  # Chỉ lưu nếu thời gian > 1 giây
                self.global_logger.log_browser_time(
                    event_type="TAB_CLOSE",
                    url=self.current_tab_url,
                    tab_name=self.current_tab_name,
                    start_time=self.current_tab_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                    duration_seconds=duration
                )

                # Thêm vào lịch sử
                self.tab_history.append({
                    'tab_name': self.current_tab_name,
                    'url': self.current_tab_url,
                    'duration': duration,
                    'start': self.current_tab_start_time,
                    'end': end_time
                })

        # Bắt đầu tracking tab mới
        self.current_tab_name = self.tab_widget.tabText(index).strip()
        self.current_tab_url = self.tab_widget.currentWidget().url().toString() if hasattr(
            self.tab_widget.currentWidget(), 'url') else ""
        self.current_tab_start_time = datetime.now()

        # Ghi log mở tab mới
        self.global_logger.log_browser_time(
            event_type="TAB_OPEN",
            url=self.current_tab_url,
            tab_name=self.current_tab_name,
            start_time=self.current_tab_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            end_time=self.current_tab_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds=0
        )

        print(f"📁 Tab changed to: {self.current_tab_name}")

    def auto_save_tab_time(self):
        """Tự động save thời gian hiện tại mỗi phút"""
        if self.current_tab_start_time and self.current_tab_name:
            current_time = datetime.now()
            duration = (current_time - self.current_tab_start_time).total_seconds()

            # Chỉ save nếu có thời gian đáng kể
            if duration >= 60:  # Ít nhất 1 phút
                self.global_logger.log_browser_time(
                    event_type="TAB_ACTIVE",
                    url=self.current_tab_url,
                    tab_name=self.current_tab_name,
                    start_time=self.current_tab_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                    end_time=current_time.strftime("%Y-%m-%d %H:%M:%S"),
                    duration_seconds=duration
                )

    def setup_random_check(self):
        """Thiết lập random check - FIXED"""
        # TEST MODE: Random check trong khoảng 1-5 phút
        import random

        # Lần check đầu tiên sau 1-2 phút
        self.next_check_time = time.time() + random.randint(60, 120)
        # Khoảng cách giữa các check: 3-7 phút
        self.check_interval_range = (180, 420)  # 3-7 phút

        print(f"⏰ Random check mode:")
        print(f"   First check in: {(self.next_check_time - time.time()) // 60} minutes")
        print(f"   Interval: {self.check_interval_range[0] // 60}-{self.check_interval_range[1] // 60} minutes")

        # Timer kiểm tra mỗi 10 giây (thay vì 30 giây)
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self.check_random_face)
        self.check_timer.start(10000)  # 10 giây

    def check_random_face(self):
        """Kiểm tra xem đã đến giờ random check chưa - FIXED"""
        current_time = time.time()

        if current_time >= self.next_check_time:
            print(f"⏰ Time for random face check!")

            # Dừng timer check tạm thời
            self.check_timer.stop()

            # Thực hiện face check
            success = self.perform_face_check()

            if success:
                # Nếu check thành công, lên lịch check tiếp theo với khoảng random
                import random
                next_interval = random.randint(*self.check_interval_range)
                self.next_check_time = time.time() + next_interval
                print(f"✅ Next check in {next_interval // 60} minutes")
            else:
                # Nếu check thất bại, lên lịch check lại sau 30 giây
                self.next_check_time = time.time() + 30
                print(f"🔄 Retry check in 30 seconds")

            # Khởi động lại timer
            self.check_timer.start(10000)
            print(f"🔁 Timer restarted")

    def perform_face_check(self):
        """Thực hiện face check - FIXED"""
        try:
            print("🔄 Starting random face check...")

            # Ghi log bắt đầu check
            self.global_logger.log_browser_alert(
                event_type="FACE_CHECK_START",
                details="Random face verification started",
                severity="INFO",
                is_fraud=False
            )

            # Pause timer và tracking
            was_paused = False
            if hasattr(self, 'timer_widget') and self.timer_widget:
                was_paused = self.timer_widget.pause_timer()
                print(f"⏸ Timer paused: {was_paused}")

            if self.pause_event:
                self.pause_event.set()
                print("⏸ Mouse tracking paused")

            if self.command_queue:
                self.command_queue.put("PAUSE")
                print("⏸ Command PAUSE sent")

            # Hiển thị thông báo - CHỈ CÓ NÚT OK, KHÔNG CÓ CANCEL
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Random Face Verification")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(
                f"🔐 RANDOM IDENTITY CHECK\n\n"
                f"User: {self.user_name}\n"
                "Please look straight at the camera.\n\n"
                "Click OK to start verification."
            )

            # CHỈ THÊM NÚT OK, KHÔNG CÓ CANCEL
            ok_button = msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            msg_box.setDefaultButton(ok_button)

            # Tắt nút close (X) trên cửa sổ
            msg_box.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            # Chặn đóng cửa sổ
            msg_box.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, False)

            print("📢 Showing verification dialog...")
            msg_box.exec()
            print("✅ User clicked OK")

            print("📸 Capturing face for verification...")
            self.global_logger.log_browser_alert(
                event_type="FACE_CHECK_CAPTURE",
                details="Capturing face image",
                severity="INFO",
                is_fraud=False
            )

            if self.face_system is None:
                # Demo mode
                print("🎭 Using demo mode...")
                QMessageBox.information(
                    self, "DEMO Mode",
                    f"DEMO: Verified as {self.user_name}\n\nYou may continue working."
                )
                self.global_logger.log_browser_alert(
                    event_type="FACE_CHECK_DEMO",
                    details="Demo mode - Verification passed",
                    severity="INFO",
                    is_fraud=False
                )
                self.resume_after_check(was_paused)
                return True

            # Check face từ camera
            print("🔍 Checking face from camera...")
            result = self.face_system.check_from_camera()
            print(f"✅ Face check result: {result.get('message')}")

            if result["success"] and result["matched"]:
                detected_user = result["name"]
                similarity = result["similarity"]

                if detected_user == self.user_name:
                    print(f"✅ User verified: {detected_user} ({similarity:.1%})")
                    QMessageBox.information(
                        self, "Verification Successful",
                        f"✅ Verified: {detected_user}\nConfidence: {similarity:.1%}"
                    )
                    self.global_logger.log_browser_alert(
                        event_type="FACE_CHECK_SUCCESS",
                        details=f"Verification successful - {similarity:.1%} confidence",
                        severity="INFO",
                        is_fraud=False
                    )
                    self.resume_after_check(was_paused)
                    return True
                else:
                    print(f"❌ User mismatch: Expected {self.user_name}, Got {detected_user}")
                    QMessageBox.critical(
                        self, "🚨 UNAUTHORIZED",
                        f"❌ User mismatch!\nExpected: {self.user_name}\nDetected: {detected_user}"
                    )
                    self.global_logger.log_browser_alert(
                        event_type="FACE_CHECK_MISMATCH",
                        details=f"User mismatch! Expected: {self.user_name}, Detected: {detected_user}",
                        severity="CRITICAL",
                        is_fraud=True
                    )
                    # KHÔNG đóng browser ngay, chỉ ghi log
                    print("⚠️ User mismatch logged, continuing session...")
                    self.resume_after_check(was_paused)
                    return False  # Trả về False để lên lịch check lại
            else:
                error_msg = result.get("message", "Verification failed")
                print(f"❌ Verification failed: {error_msg}")
                QMessageBox.warning(
                    self, "Verification Failed",
                    f"❌ {error_msg}\n\nPlease try again."
                )
                self.global_logger.log_browser_alert(
                    event_type="FACE_CHECK_FAILED",
                    details=f"Verification failed: {error_msg}",
                    severity="WARNING",
                    is_fraud=False
                )

                self.resume_after_check(was_paused)
                return False  # Trả về False để lên lịch check lại

        except Exception as e:
            print(f"❌ Error during face check: {e}")
            traceback.print_exc()
            self.global_logger.log_browser_alert(
                event_type="FACE_CHECK_ERROR",
                details=str(e),
                severity="WARNING",
                is_fraud=False
            )

            QMessageBox.warning(
                self, "System Error",
                "Face verification system error.\nSession will resume."
            )

            self.resume_after_check(False)
            return False  # Trả về False để lên lịch check lại

    def resume_after_check(self, was_paused):
        """Resume sau khi check xong - FIXED"""
        print("▶️ Resuming session...")

        try:
            if was_paused and hasattr(self, 'timer_widget') and self.timer_widget:
                self.timer_widget.resume_timer()
                print("▶ Timer resumed")

            if self.pause_event:
                self.pause_event.clear()
                print("▶ Mouse tracking resumed")

            if self.command_queue:
                self.command_queue.put("RESUME")
                print("▶ Command RESUME sent")

        except Exception as e:
            print(f"⚠️ Error resuming session: {e}")

    def get_browser_summary(self):
        """Lấy tổng kết thời gian làm việc"""
        total_seconds = sum(item['duration'] for item in self.tab_history)

        # Thêm thời gian tab hiện tại
        if self.current_tab_start_time:
            current_duration = (datetime.now() - self.current_tab_start_time).total_seconds()
            total_seconds += current_duration

        return {
            'total_time': total_seconds,
            'total_formatted': self.format_time(total_seconds),
            'tab_count': len(self.tab_history) + (1 if self.current_tab_start_time else 0),
            'browser_start': self.browser_start_time,
            'tab_history': self.tab_history
        }

    def format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}h {minutes:02d}m {secs:02d}s"

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
        """Toggle timer với logging"""
        try:
            if self.timer_widget.is_running:
                # Pause timer
                self.timer_widget.is_running = False
                self.timer_widget.timer.stop()
                self.timer_widget.pause_btn.setText("▶ Resume")
                self.timer_widget.pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #34A853;
                        color: white;
                        border: none;
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #2E8B47;
                    }
                    QPushButton:pressed {
                        background-color: #1E7B37;
                    }
                """)

                # Pause mouse tracking
                if self.pause_event:
                    self.pause_event.set()
                if self.command_queue:
                    self.command_queue.put("PAUSE")

                print("⏸ Timer and mouse tracking PAUSED")

                # Kiểm tra pause nhiều lần
                fraud_detected = self.check_rapid_pause()

                if fraud_detected and not self.fraud_alert_shown:
                    self.fraud_alert_shown = True
                    self.show_fraud_alert()

                    self.global_logger.log_browser_alert(
                        event_type="RAPID_PAUSE_DETECTED",
                        details=f"Multiple rapid pauses detected - Count: {self.rapid_pause_count}",
                        severity="WARNING",
                        is_fraud=True
                    )
            else:
                # Resume timer
                self.timer_widget.start_time = time.time() - self.timer_widget.elapsed_time
                self.timer_widget.is_running = True
                self.timer_widget.timer.start(1000)
                self.timer_widget.pause_btn.setText("⏸ Pause")
                self.timer_widget.pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #EA4335;
                        color: white;
                        border: none;
                        padding: 8px 12px;
                        border-radius: 6px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #D23A2D;
                    }
                    QPushButton:pressed {
                        background-color: #B3261E;
                    }
                """)

                # Resume mouse tracking
                if self.pause_event:
                    self.pause_event.clear()
                if self.command_queue:
                    self.command_queue.put("RESUME")

                print("▶ Timer and mouse tracking RESUMED")
                self.fraud_alert_shown = False

        except Exception as e:
            print(f"❌ Error in toggle_timer_with_logging: {e}")
            traceback.print_exc()

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
        """Xác nhận thoát"""
        reply = QMessageBox.question(
            self, "Exit Workspace Browser",
            "Are you sure you want to exit the Professional Workspace Browser?\n\n"
            f"Total working time: {self.timer_widget.elapsed_time // 3600}h "
            f"{(self.timer_widget.elapsed_time % 3600) // 60}m\n"
            "All unsaved work might be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.is_closing = True
            self.close()

    def closeEvent(self, event):
        """Xử lý khi đóng browser - THÊM LƯU THỜI GIAN CUỐI"""
        if self.is_closing:
            print("🛑 Closing browser...")

            # Lưu thời gian tab cuối cùng
            if self.current_tab_start_time and self.current_tab_name:
                end_time = datetime.now()
                duration = (end_time - self.current_tab_start_time).total_seconds()

                if duration > 1:
                    self.global_logger.log_browser_time(
                        event_type="TAB_CLOSE",
                        url=self.current_tab_url,
                        tab_name=self.current_tab_name,
                        start_time=self.current_tab_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        end_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                        duration_seconds=duration
                    )

            # Lưu thời gian kết thúc browser
            browser_end_time = datetime.now()
            browser_duration = (browser_end_time - self.browser_start_time).total_seconds()

            self.global_logger.log_browser_time(
                event_type="BROWSER_END",
                url="",
                tab_name="Browser Session",
                start_time=self.browser_start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time=browser_end_time.strftime("%Y-%m-%d %H:%M:%S"),
                duration_seconds=browser_duration
            )

            # Lấy summary
            summary = self.get_browser_summary()

            # Ghi log kết thúc
            self.global_logger.log_browser_alert(
                event_type="BROWSER_CLOSED",
                details=f"Professional Workspace Browser closed. Total time: {summary['total_formatted']}",
                severity="INFO",
                is_fraud=False
            )

            # Dừng timer auto save
            if hasattr(self, 'auto_save_timer'):
                self.auto_save_timer.stop()

            # Thông báo cho parent_window
            if self.parent_window and hasattr(self.parent_window, 'on_browser_closed'):
                self.parent_window.on_browser_closed(summary)

            event.accept()
        else:
            self.confirm_exit()
            event.ignore()


# ============================================
# FULL CHATBOT SYSTEM INTEGRATION - FIXED
# ============================================
try:
    from Chatbot.chatbot_launcher import ChatbotLauncher

    print("✅ Chatbot launcher imported successfully")
except ImportError as e:
    print(f"⚠️ Cannot import ChatbotLauncher: {e}")


    # Tạo placeholder cho ChatbotLauncher
    class ChatbotLauncherPlaceholder:
        @staticmethod
        def show_chatbot_fullscreen(user_name, parent=None):
            QMessageBox.warning(parent, "Chatbot không khả dụng",
                                f"Không thể khởi động chatbot cho {user_name}")
            return None


    ChatbotLauncher = ChatbotLauncherPlaceholder


class HomeWindow(QMainWindow):
    def __init__(self, user_name="User"):
        super().__init__()
        self.user_name = user_name
        self.ui = Ui_HomeWindow()
        self.ui.setupUi(self)

        # KHỞI TẠO GLOBAL LOGGER
        self.global_logger = GlobalExcelLogger(user_name)

        # Biến hệ thống
        self.mouse_process = None
        self.stop_event = None
        self.pause_event = None
        self.command_queue = None
        self.alert_queue = None
        self.browser_window = None
        self.chatbot_window = None  # Chatbot window
        self.is_working = False

        # Cập nhật tên user
        self.update_user_name(user_name)

        # Kết nối nút chatbot (pushButton_7)
        if hasattr(self.ui, 'pushButton_7'):
            self.ui.pushButton_7.clicked.connect(self.open_full_chatbot)
            print("✅ Connected pushButton_7 to full chatbot")
        else:
            print("❌ pushButton_7 not found in UI")
            # Tạo nút fallback
            self.create_chatbot_button_fallback()

        # Kết nối các nút khác
        self.ui.pushButton_8.clicked.connect(self.start_work_session)
        self.ui.pushButton_5.clicked.connect(self.show_browser)
        self.ui.pushButton_6.clicked.connect(self.view_logs)

        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time)
        self.timer.start(1000)

        self.setWindowTitle(f"PowerSight - {user_name}")
        self.setWindowFlag(Qt.WindowType.Window, True)
        print(f"🏠 HomeWindow created for {user_name}")

    def create_chatbot_button_fallback(self):
        """Tạo nút chatbot fallback"""
        try:
            self.chatbot_btn = QPushButton("🤖 AI Assistant", self)
            self.chatbot_btn.setGeometry(50, 200, 200, 60)
            self.chatbot_btn.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    border-radius: 10px;
                    padding: 15px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #764ba2, stop:1 #667eea);
                    border: 2px solid #3b82f6;
                }
            """)
            self.chatbot_btn.clicked.connect(self.open_full_chatbot)
            self.chatbot_btn.show()
            print("✅ Created fallback chatbot button")
        except Exception as e:
            print(f"⚠️ Error creating fallback button: {e}")

    def open_full_chatbot(self):
        """Mở toàn bộ chatbot system"""
        print(f"\n{'=' * 50}")
        print(f"🚀 OPENING FULL CHATBOT SYSTEM for {self.user_name}")
        print(f"{'=' * 50}")

        # Kiểm tra launcher
        if ChatbotLauncher is None:
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 "Không thể tải chatbot system.\n\n"
                                 "Cần các file:\n"
                                 "- employee_chatbot.py\n"
                                 "- config.py\n"
                                 "- data_processor.py\n"
                                 "- gemini_analyzer.py\n"
                                 "- dashboard.py")
            return

        try:
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

            # Khởi chạy toàn bộ chatbot system
            print("\n🔧 Launching full chatbot system...")
            self.chatbot_window = ChatbotLauncher.show_chatbot_fullscreen(
                self.user_name, self)

            if self.chatbot_window:
                print("\n✅ FULL CHATBOT SYSTEM LAUNCHED SUCCESSFULLY!")
                print(f"   User: {self.user_name}")
                print(f"   Window: {self.chatbot_window.windowTitle()}")

                # Cập nhật status trong home
                if hasattr(self.ui, 'khichle'):
                    self.ui.khichle.setText("🤖 AI Assistant đang chạy...")

                # Home window minimize
                self.showMinimized()
                print("🏠 Home window minimized")

                # Kết nối sự kiện đóng chatbot
                self.chatbot_window.destroyed.connect(self.on_chatbot_closed)

            else:
                QMessageBox.warning(self, "Lỗi khởi động",
                                    "Không thể khởi động chatbot system.\n"
                                    "Vui lòng kiểm tra console log.")

        except Exception as e:
            print(f"❌ CRITICAL ERROR opening chatbot: {e}")
            import traceback
            traceback.print_exc()

            QMessageBox.critical(self, "Lỗi hệ thống",
                                 f"Lỗi nghiêm trọng khi mở chatbot:\n\n"
                                 f"{str(e)[:100]}...\n\n"
                                 f"Vui lòng kiểm tra các file module.")

    def show(self):
        """Override show để đảm bảo hiển thị đúng"""
        try:
            super().show()
            self.activateWindow()
            self.raise_()
            print("✅ HomeWindow hiển thị thành công")
        except Exception as e:
            print(f"❌ Lỗi khi hiển thị HomeWindow: {e}")
            traceback.print_exc()

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

        # Xác nhận bắt đầu session
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

            # Ghi log bắt đầu session
            self.global_logger.log_browser_alert(
                event_type="SESSION_START",
                details=f"Session started for {self.user_name}",
                severity="INFO",
                is_fraud=False
            )

            # Tạo các event và queue
            self.stop_event = multiprocessing.Event()
            self.pause_event = multiprocessing.Event()
            self.command_queue = multiprocessing.Queue()
            self.alert_queue = multiprocessing.Queue()

            # Khởi chạy mouse process
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

            # Ghi log mouse tracking
            self.global_logger.log_browser_alert(
                event_type="MOUSE_TRACKING_START",
                details="Mouse analysis system started",
                severity="INFO",
                is_fraud=False
            )

            # Tạo Enhanced Safe Browser
            self.browser_window = EnhancedSafeBrowser(
                user_name=self.user_name,
                global_logger=self.global_logger,
                parent_window=self,
                pause_event=self.pause_event,
                command_queue=self.command_queue,
                alert_queue=self.alert_queue
            )

            # Thiết lập timer với logging
            QTimer.singleShot(100, self.browser_window.setup_timer_with_logging)

            # HomeWindow minimized, browser fullscreen
            self.showMinimized()
            self.browser_window.showFullScreen()

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
            f"Browser Time Entries: {summary['browser_time_entries']}\n"
            f"Log File: {summary['excel_file']}"
        )

        # Thêm nút Open Log File
        open_btn = msg.addButton("Open Log File", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Close", QMessageBox.ButtonRole.RejectRole)

        msg.exec()

        if msg.clickedButton() == open_btn:
            self.global_logger.open_log_file()

    def on_browser_closed(self, browser_summary=None):
        """Xử lý khi browser đóng - THÊM HIỂN THỊ SUMMARY"""
        print("\n🛑 Browser closed by user")

        # Hiển thị summary nếu có
        if browser_summary:
            print(f"\n📊 Browser Session Summary:")
            print(f"   Total Working Time: {browser_summary['total_formatted']}")
            print(f"   Total Tabs Opened: {browser_summary['tab_count']}")

            # Có thể hiển thị dialog summary
            QMessageBox.information(
                self,
                "Session Summary",
                f"📊 Work Session Completed\n\n"
                f"Total Working Time: {browser_summary['total_formatted']}\n"
                f"Total Tabs Opened: {browser_summary['tab_count']}\n\n"
                f"Detailed log saved to Excel file."
            )

        # Ghi log kết thúc session
        self.global_logger.log_browser_alert(
            event_type="SESSION_END",
            details=f"Session ended for {self.user_name}",
            severity="INFO",
            is_fraud=False
        )

        # Lưu dữ liệu cuối cùng
        self.global_logger.save_final_data()

        # Dừng mouse process
        if self.stop_event:
            self.stop_event.set()

        # Đợi mouse process lưu dữ liệu
        if self.mouse_process:
            print("⏳ Waiting for mouse process to save data...")
            self.mouse_process.join(timeout=10)

            if self.mouse_process.is_alive():
                print("⚠️ Mouse process not responding, terminating...")
                self.mouse_process.terminate()
                self.mouse_process.join(timeout=2)

        print("✅ Mouse data saved successfully!")

        # Reset UI
        self.reset_ui()

        # Dọn dẹp
        self.mouse_process = None
        self.stop_event = None
        self.pause_event = None
        self.command_queue = None
        self.alert_queue = None
        self.browser_window = None

        print("✅ Session cleanup completed.")

        # Hiển thị lại home window
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

    def logout(self):
        """Đăng xuất"""
        if self.is_working:
            reply = QMessageBox.question(
                self, "Logout",
                "Work session is running. Stop and logout?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            # Đóng browser nếu đang mở
            if self.browser_window:
                self.browser_window.is_closing = True
                self.browser_window.close()
                QTimer.singleShot(500, lambda: self.logout_cleanup())
            else:
                self.logout_cleanup()
        else:
            self.logout_cleanup()

    def logout_cleanup(self):
        """Dọn dẹp sau khi logout"""
        self.close()
        login_window = LoginWindow()
        login_window.show()

    def on_chatbot_closed(self):
        """Khi chatbot đóng"""
        print("\n🛑 Chatbot window closed")
        self.chatbot_window = None

        # Khôi phục home window
        self.showNormal()
        self.raise_()
        self.activateWindow()

        # Cập nhật status
        if hasattr(self.ui, 'khichle'):
            self.ui.khichle.setText("Sẵn sàng")

    def closeEvent(self, event):
        """Xử lý khi đóng HomeWindow"""
        print("\n🛑 HomeWindow close event")

        # Đóng chatbot nếu đang mở
        if self.chatbot_window:
            try:
                print("   Closing chatbot window...")
                self.chatbot_window.close()
                self.chatbot_window = None
            except:
                pass

        # Kiểm tra work session
        if self.is_working and self.browser_window:
            self.browser_window.show()
            self.browser_window.activateWindow()

            QMessageBox.warning(self, "Không thể đóng",
                                "Không thể đóng Home khi session đang chạy.\n"
                                "Vui lòng đóng browser trước.")
            event.ignore()
            return

        # Đóng bình thường
        event.accept()
        print("✅ HomeWindow closed successfully")


# ============================================
# MAIN
# ============================================
def main():
    # Kiểm tra thư mục Saved_file tồn tại
    if not os.path.exists(SAVED_FILE_DIR):
        os.makedirs(SAVED_FILE_DIR, exist_ok=True)
        print(f"📁 Created main directory: {SAVED_FILE_DIR}")

    # Kiểm tra ảnh có tồn tại không
    print("\n🔍 Kiểm tra các file ảnh:")
    for image_name in ["background2.jpg", "background5.jpg", "faceid_icon.jpg"]:
        image_path = os.path.join(IMAGES_DIR, image_name)
        if os.path.exists(image_path):
            print(f"✅ Found: {image_name}")
        else:
            print(f"❌ Missing: {image_name}")

    multiprocessing.freeze_support()

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("PowerSight")

    window = LoginWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()