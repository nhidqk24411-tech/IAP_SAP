# App.py - FILE CHÍNH KHỞI ĐỘNG HỆ THỐNG
"""
FILE CHÍNH - Bắt đầu bằng màn hình Login (UI_LOGIN)
Sau khi click nút FaceID, chuyển sang quét mặt
Sau khi quét mặt thành công, tự động phân biệt quản lý/nhân viên và chạy ứng dụng phù hợp
"""

import sys
import os
import cv2
import subprocess
import traceback
import ctypes
from datetime import datetime
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# =========================
# CẤU HÌNH ĐƯỜNG DẪN
# =========================
# Lấy đường dẫn thư mục chứa App.py
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(current_dir)  # MainApp
PROJECT_ROOT = os.path.dirname(BASE_DIR)  # PythonProject

IMAGES_DIR = os.path.join(BASE_DIR, "UI", "images")
SAVED_FILE_DIR = os.path.join(PROJECT_ROOT, "Saved_file")
UI_DIR = os.path.join(BASE_DIR, "UI")

# Thêm các đường dẫn cần thiết vào sys.path
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, "Face"))
sys.path.insert(0, os.path.join(PROJECT_ROOT, "MainApp"))

# Kiểm tra và tạo thư mục
if not os.path.exists(SAVED_FILE_DIR):
    os.makedirs(SAVED_FILE_DIR, exist_ok=True)


# =========================
# TASKBAR CONTROLLER
# =========================
class TaskbarController:
    """Điều khiển ẩn/hiện thanh Taskbar của Windows"""

    @staticmethod
    def set_visibility(visible=True):
        try:
            SW_HIDE = 0
            SW_SHOW = 5
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
# UTILITY FUNCTIONS
# =========================
def load_image(image_name):
    """Load ảnh từ thư mục images"""
    image_path = os.path.join(IMAGES_DIR, image_name)
    if os.path.exists(image_path):
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            return pixmap
    return None


def write_login_info(user_name, user_type):
    """Ghi thông tin đăng nhập vào file tạm"""
    temp_file = os.path.join(PROJECT_ROOT, "temp_login.txt")
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(f"{user_type}:{user_name}")
        print(f"💾 Đã lưu thông tin đăng nhập: {user_name} ({user_type})")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi lưu file đăng nhập: {e}")
        return False


def clean_login_info():
    """Xóa file đăng nhập tạm"""
    temp_file = os.path.join(PROJECT_ROOT, "temp_login.txt")
    if os.path.exists(temp_file):
        try:
            os.remove(temp_file)
            print("🧹 Đã xóa file đăng nhập tạm")
        except:
            pass


# =========================
# LOGIN WINDOW - CỬA SỔ ĐẦU TIÊN
# =========================
class LoginWindow(QMainWindow):
    """Cửa sổ đăng nhập đầu tiên - Sử dụng UI_LOGIN"""

    def __init__(self):
        super().__init__()

        # Import UI từ module
        try:
            # Import UI_LOGIN từ đúng vị trí
            ui_login_path = os.path.join(UI_DIR, "UI_LOGIN.py")
            if os.path.exists(ui_login_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("UI_LOGIN", ui_login_path)
                ui_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ui_module)
                Ui_LoginWindow = ui_module.Ui_MainWindow
                self.ui = Ui_LoginWindow()
                self.ui.setupUi(self)
                print("✅ Loaded Login UI successfully")
            else:
                raise ImportError(f"Không tìm thấy file UI_LOGIN.py tại: {ui_login_path}")
        except ImportError as e:
            print(f"❌ Failed to load Login UI: {e}")
            traceback.print_exc()
            self.show_fatal_error("Không thể tải giao diện Login")
            return

        # Setup window properties
        self.setWindowTitle("PowerSight - Login")

        # DISABLE PHÓNG TO và không cho thay đổi kích thước
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(self.size())

        # LOAD ẢNH NỀN
        background_pixmap = load_image("background2.jpg")
        if background_pixmap:
            self.ui.label_3.setPixmap(background_pixmap.scaled(
                self.ui.label_3.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        # Kết nối nút FaceID và load icon
        if hasattr(self.ui, 'pushButton_faceid'):
            self.ui.pushButton_faceid.clicked.connect(self.open_faceid)
            print("✅ Connected FaceID button")

            # LOAD ICON CHO NÚT FACEID
            icon_path = os.path.join(IMAGES_DIR, "faceid_icon.jpg")
            if os.path.exists(icon_path):
                icon_pixmap = QPixmap(icon_path)
                if not icon_pixmap.isNull():
                    # Resize icon cho vừa với nút
                    icon_pixmap = icon_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)
                    self.ui.pushButton_faceid.setIcon(QIcon(icon_pixmap))
                    self.ui.pushButton_faceid.setIconSize(QSize(60, 60))
                    print("✅ Loaded FaceID icon")
                else:
                    print("⚠️ Không thể load icon FaceID")
            else:
                print(f"⚠️ Không tìm thấy icon: {icon_path}")
        else:
            print("❌ KHÔNG TÌM THẤY NÚT pushButton_faceid trong UI!")
            self.create_fallback_button()

        print("🚀 Login Window đã sẵn sàng!")

    def create_fallback_button(self):
        """Tạo nút fallback nếu nút trong UI không tồn tại"""
        fallback_btn = QPushButton("Face ID Login", self)
        fallback_btn.setGeometry(100, 100, 200, 50)
        fallback_btn.clicked.connect(self.open_faceid)
        fallback_btn.show()
        print("⚠️ Đã tạo nút FaceID fallback")

    def open_faceid(self):
        """Mở cửa sổ FaceID"""
        print("🔄 Mở cửa sổ FaceID...")
        try:
            self.hide()  # Ẩn cửa sổ login
            self.faceid_window = FaceIDWindow(self)
            self.faceid_window.show()
            print("✅ Đã mở cửa sổ FaceID")
        except Exception as e:
            print(f"❌ Lỗi khi mở FaceID: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể mở cửa sổ FaceID: {str(e)}")
            self.show()

    def show_fatal_error(self, message):
        """Hiển thị lỗi nghiêm trọng và thoát"""
        QMessageBox.critical(self, "Lỗi hệ thống", f"{message}\n\nỨng dụng sẽ thoát.")
        self.close()
        sys.exit(1)

    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        TaskbarController.set_visibility(True)
        event.accept()


# =========================
# FACE ID WINDOW
# =========================
class FaceIDWindow(QMainWindow):
    """Cửa sổ quét mặt - Sử dụng UI_FACEID"""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Import UI từ module
        try:
            # Import UI_FACEID từ đúng vị trí
            ui_faceid_path = os.path.join(UI_DIR, "UI_FACEID.py")
            if os.path.exists(ui_faceid_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("UI_FACEID", ui_faceid_path)
                ui_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(ui_module)
                Ui_FaceIDWindow = ui_module.Ui_MainWindow
                self.ui = Ui_FaceIDWindow()
                self.ui.setupUi(self)
                print("✅ Loaded FaceID UI successfully")
            else:
                raise ImportError(f"Không tìm thấy file UI_FACEID.py tại: {ui_faceid_path}")
        except ImportError as e:
            print(f"❌ Failed to load FaceID UI: {e}")
            traceback.print_exc()
            self.return_to_login()
            return

        # Setup window properties
        self.setWindowTitle("PowerSight - Face Login")

        # DISABLE PHÓNG TO và không cho thay đổi kích thước
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(self.size())


        # LOAD ẢNH NỀN
        background_pixmap = load_image("background5.jpg")
        if background_pixmap:
            self.ui.label.setPixmap(background_pixmap.scaled(
                self.ui.label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        self.parent_window = parent
        self.recognized_user = None
        self.attempt_count = 0
        self.max_attempts = 3
        self.cap = None
        self.recognition_complete = False

        # Ẩn taskbar khi mở FaceID
        TaskbarController.set_visibility(False)

        # Setup camera
        self.setup_camera()

        # Load face system
        self.load_face_system()

        print("🚀 FaceID Window đã sẵn sàng!")

    def setup_camera(self):
        """Thiết lập camera"""
        print("🔍 Kiểm tra webcam...")
        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(1)

            if not self.cap.isOpened():
                QMessageBox.critical(self, "Lỗi", "Không thể mở webcam. Vui lòng kiểm tra camera.")
                self.return_to_login()
                return

            print("✅ Camera mở thành công")

            # Setup timer
            self.start_time = datetime.now()
            self.recognition_started = False

            self.timer = QTimer()
            self.timer.timeout.connect(self.update_frame)
            self.timer.start(30)

        except Exception as e:
            print(f"❌ Lỗi mở camera: {e}")
            self.return_to_login()

    def load_face_system(self):
        """Load hệ thống nhận diện khuôn mặt"""
        print("🔍 Tải hệ thống nhận diện...")
        try:
            # Tìm và import main_face.py từ thư mục Face
            face_main_path = os.path.join(PROJECT_ROOT, "Face", "main_face.py")
            print(f"🔍 Đang tìm main_face.py tại: {face_main_path}")

            # KIỂM TRA THƯ MỤC FACE
            face_dir = os.path.join(PROJECT_ROOT, "Face")
            if os.path.exists(face_dir):
                print(f"📁 Thư mục Face tồn tại")

                # Kiểm tra thư mục ảnh
                anh_dir = os.path.join(face_dir, "anh")
                if os.path.exists(anh_dir):
                    print(f"📸 Thư mục anh chứa: {os.listdir(anh_dir)}")
                    # Kiểm tra folder Giang_MG
                    giang_mg_path = os.path.join(anh_dir, "Giang_MG")
                    if os.path.exists(giang_mg_path):
                        print(f"✅ Tìm thấy folder Giang_MG, chứa: {os.listdir(giang_mg_path)}")
                    else:
                        print(f"❌ KHÔNG tìm thấy folder Giang_MG")

            if os.path.exists(face_main_path):
                import importlib.util
                spec = importlib.util.spec_from_file_location("main_face", face_main_path)
                face_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(face_module)

                self.face_system = face_module.FaceSingleCheck(user_name="")
                print("✅ Hệ thống FaceSingleCheck đã tải")
            else:
                print(f"❌ Không tìm thấy main_face.py tại: {face_main_path}")
                raise ImportError(f"File không tồn tại: {face_main_path}")
        except Exception as e:
            print(f"❌ Lỗi tải FaceSingleCheck: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", "Không thể tải hệ thống nhận diện khuôn mặt")
            self.return_to_login()

    def update_frame(self):
        """Cập nhật frame từ camera"""
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
        """Hiển thị frame từ camera"""
        try:
            label_w = self.ui.labelCamera.width()
            label_h = self.ui.labelCamera.height()

            if label_w <= 0 or label_h <= 0:
                return

            frame = cv2.resize(frame, (label_w, label_h))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = frame_rgb.shape

            qimg = QImage(
                frame.data,
                w,
                h,
                w * 3,
                QImage.Format.Format_BGR888
            )
            pixmap = QPixmap(label_w, label_h)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            path = QPainterPath()
            path.addEllipse(0, 0, label_w, label_h)
            painter.setClipPath(path)
            painter.drawImage(0, 0, qimg)
            painter.end()

            self.ui.labelCamera.setPixmap(pixmap)
        except Exception as e:
            print(f"❌ Lỗi hiển thị frame: {e}")

    def process_recognition(self, frame):
        """Xử lý nhận diện khuôn mặt"""
        try:
            print("🔍 Đang nhận diện khuôn mặt...")
            result = self.face_system.check_single_face(frame)
            print(f"DEBUG - Kết quả nhận diện: {result}")
            print(f"DEBUG - Tên user từ hệ thống: {result.get('name')}")

            if result["success"] and result["matched"]:
                user_name = result["name"]
                similarity = result["similarity"]
                print(f"✅ Đăng nhập thành công: {user_name} ({similarity:.2%})")

                # KIỂM TRA TRONG THƯ MỤC ANH ĐỂ XÁC ĐỊNH LOẠI USER
                face_anh_dir = os.path.join(PROJECT_ROOT, "Face", "anh")
                user_type = "employee"  # Mặc định là nhân viên
                display_name = user_name

                if os.path.exists(face_anh_dir):
                    # Kiểm tra tất cả các thư mục trong anh
                    for folder in os.listdir(face_anh_dir):
                        folder_path = os.path.join(face_anh_dir, folder)
                        if os.path.isdir(folder_path):
                            # So sánh tên folder với tên user
                            # Nếu folder là "Giang_MG" và user_name là "Giang_MG"
                            if folder == user_name:
                                if "_MG" in folder.upper():
                                    user_type = "manager"
                                    display_name = folder.replace("_MG", "").replace("_mg", "")
                                    print(f"👨‍💼 Phát hiện QUẢN LÝ từ folder trùng khớp: {folder}")
                                    break
                                else:
                                    user_type = "employee"
                                    display_name = folder
                                    print(f"👤 Phát hiện NHÂN VIÊN từ folder trùng khớp: {folder}")
                                    break
                            # Nếu folder là "Giang_MG" và user_name chỉ là "Giang"
                            elif user_name in folder and "_MG" in folder.upper():
                                user_type = "manager"
                                display_name = folder.replace("_MG", "").replace("_mg", "")
                                print(f"👨‍💼 Phát hiện QUẢN LÝ từ folder chứa: {folder}")
                                break
                            # Nếu folder không có _MG và trùng hoặc chứa user_name
                            elif user_name in folder and "_MG" not in folder.upper():
                                user_type = "employee"
                                display_name = folder
                                print(f"👤 Phát hiện NHÂN VIÊN từ folder: {folder}")
                                break

                self.recognized_user = user_name

                self.cleanup_camera()
                self.recognition_complete = True

                # Lưu thông tin đăng nhập
                write_login_info(user_name, user_type)

                # Chạy ứng dụng phù hợp
                self.launch_app(user_type, user_name, display_name)

                # Đóng cửa sổ sau 0.5 giây
                QTimer.singleShot(500, self.close)
            else:
                self.attempt_count += 1

                if self.attempt_count >= self.max_attempts:
                    self.cleanup_camera()
                    self.recognition_complete = True
                    QMessageBox.warning(
                        self, "Quá nhiều lần thử",
                        f"Không nhận diện được khuôn mặt sau {self.max_attempts} lần thử.\n"
                        "Quay lại màn hình đăng nhập."
                    )
                    QTimer.singleShot(500, self.return_to_login)
                else:
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

    def launch_app(self, user_type, user_name, display_name):
        """Khởi chạy ứng dụng phù hợp"""
        try:
            if user_type == "manager":
                print(f"👨‍💼 Khởi chạy ứng dụng quản lý cho: {display_name}")
                self.run_manager_app(user_name)
            else:
                print(f"👤 Khởi chạy ứng dụng nhân viên cho: {display_name}")
                self.run_employee_app(user_name)
        except Exception as e:
            print(f"❌ Lỗi khi khởi chạy ứng dụng: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 f"Không thể khởi chạy ứng dụng:\n{str(e)}")

    def run_manager_app(self, user_name):
        """Chạy ứng dụng quản lý"""
        # Thử các đường dẫn khác nhau cho main_manager.py
        possible_paths = [
            os.path.join(PROJECT_ROOT, "MainApp", "Run", "main_manager.py"),
            os.path.join(PROJECT_ROOT, "main_manager.py"),
            os.path.join(BASE_DIR, "Run", "main_manager.py"),
        ]

        manager_app = None
        for path in possible_paths:
            if os.path.exists(path):
                manager_app = path
                print(f"✅ Tìm thấy ứng dụng quản lý tại: {manager_app}")
                break

        if not manager_app:
            QMessageBox.critical(self, "Lỗi",
                                 "Không tìm thấy ứng dụng quản lý!\n"
                                 f"Đã tìm tại:\n- {possible_paths[0]}\n- {possible_paths[1]}")
            return

        print(f"🚀 Khởi chạy ứng dụng quản lý cho user: {user_name}")

        # Kiểm tra xem có file login tạm không
        temp_login = os.path.join(PROJECT_ROOT, "temp_login.txt")
        if os.path.exists(temp_login):
            with open(temp_login, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"📄 Nội dung temp_login: {content}")
                # Kiểm tra lại xem có đúng là manager không
                if ":manager:" not in content and not content.startswith("manager:"):
                    print(f"⚠️ CẢNH BÁO: File login không chứa 'manager:'")

        # Khởi chạy ứng dụng quản lý
        try:
            python_exe = sys.executable
            print(f"🐍 Python executable: {python_exe}")

            # Tạo process mới
            subprocess.Popen([python_exe, manager_app],
                             cwd=PROJECT_ROOT)
            print("✅ Đã khởi chạy ứng dụng quản lý")
        except Exception as e:
            print(f"❌ Lỗi khi chạy ứng dụng quản lý: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể chạy ứng dụng quản lý:\n{str(e)}")

    def run_employee_app(self, user_name):
        """Chạy ứng dụng nhân viên"""
        # Thử các đường dẫn khác nhau cho main_emp.py
        possible_paths = [
            os.path.join(PROJECT_ROOT, "MainApp", "Run", "main_emp.py"),
            os.path.join(PROJECT_ROOT, "main_emp.py"),
            os.path.join(BASE_DIR, "Run", "main_emp.py"),
        ]

        employee_app = None
        for path in possible_paths:
            if os.path.exists(path):
                employee_app = path
                print(f"✅ Tìm thấy ứng dụng nhân viên tại: {employee_app}")
                break

        if not employee_app:
            QMessageBox.critical(self, "Lỗi",
                                 "Không tìm thấy ứng dụng nhân viên!\n"
                                 f"Đã tìm tại:\n- {possible_paths[0]}\n- {possible_paths[1]}")
            return

        print(f"🚀 Khởi chạy ứng dụng nhân viên cho user: {user_name}")

        # Khởi chạy ứng dụng nhân viên
        try:
            python_exe = sys.executable
            print(f"🐍 Python executable: {python_exe}")

            subprocess.Popen([python_exe, employee_app],
                             cwd=PROJECT_ROOT)
            print("✅ Đã khởi chạy ứng dụng nhân viên")
        except Exception as e:
            print(f"❌ Lỗi khi chạy ứng dụng nhân viên: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể chạy ứng dụng nhân viên: {str(e)}")

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
        TaskbarController.set_visibility(True)
        if self.parent_window:
            self.parent_window.show()
        self.close()

    def exit_application(self):
        """Thoát ứng dụng"""
        print("🛑 Thoát ứng dụng...")
        self.cleanup_camera()
        TaskbarController.set_visibility(True)
        self.close()

    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        print("🛑 Đóng cửa sổ FaceID...")
        self.cleanup_camera()
        TaskbarController.set_visibility(True)
        if self.parent_window and not self.recognition_complete:
            self.parent_window.show()
        event.accept()


# =========================
# MAIN FUNCTION
# =========================
def main():
    """Hàm main - Điểm bắt đầu của hệ thống"""

    print("\n" + "=" * 60)
    print("🚀 KHỞI ĐỘNG HỆ THỐNG POWER SIGHT")
    print("=" * 60)

    # Kiểm tra hệ thống
    print("🔍 Kiểm tra hệ thống...")

    # Kiểm tra file Face/main_face.py
    required_files = [
        os.path.join("Face", "main_face.py")
    ]

    missing_files = []
    for file in required_files:
        file_path = os.path.join(PROJECT_ROOT, file)
        if not os.path.exists(file_path):
            missing_files.append(file)

    if missing_files:
        print("❌ Thiếu file quan trọng:")
        for file in missing_files:
            print(f"   - {file}")

        reply = QMessageBox.critical(None, "Lỗi hệ thống",
                                     f"Thiếu file quan trọng:\n{', '.join(missing_files)}\n\n"
                                     "Bạn có muốn tiếp tục không?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            sys.exit(1)

    # KIỂM TRA THƯ MỤC FACE VÀ DỮ LIỆU
    print("\n🔍 Kiểm tra dữ liệu Face...")
    face_anh_dir = os.path.join(PROJECT_ROOT, "Face", "anh")
    if os.path.exists(face_anh_dir):
        print(f"📁 Thư mục Face/anh tồn tại")
        subfolders = [f for f in os.listdir(face_anh_dir)
                      if os.path.isdir(os.path.join(face_anh_dir, f))]
        print(f"📁 Số lượng user được đăng ký: {len(subfolders)}")
        for folder in subfolders:
            print(f"   - {folder}")
            # Kiểm tra xem có ảnh trong folder không
            folder_path = os.path.join(face_anh_dir, folder)
            files = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            print(f"     📸 Số ảnh: {len(files)}")
    else:
        print(f"⚠️ Không tìm thấy thư mục Face/anh")

    # Kiểm tra thư mục ảnh UI
    print("\n🔍 Kiểm tra ảnh UI...")
    required_images = ["background2.jpg", "background5.jpg", "faceid_icon.jpg"]
    for img in required_images:
        img_path = os.path.join(IMAGES_DIR, img)
        if os.path.exists(img_path):
            print(f"✅ Found: {img}")
        else:
            print(f"❌ Missing: {img_path}")

    # Kiểm tra thư mục ảnh
    if not os.path.exists(IMAGES_DIR):
        print(f"⚠️ Thư mục images không tồn tại: {IMAGES_DIR}")
        os.makedirs(IMAGES_DIR, exist_ok=True)
        print(f"📁 Đã tạo thư mục: {IMAGES_DIR}")

    # Khởi tạo ứng dụng
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("PowerSight - Login System")

    # Dọn dẹp file đăng nhập cũ (nếu có)
    clean_login_info()

    # Khởi tạo và hiển thị cửa sổ Login
    window = LoginWindow()
    window.show()

    # Khôi phục taskbar khi thoát
    def restore_system():
        TaskbarController.set_visibility(True)
        clean_login_info()
        print("✅ Đã khôi phục hệ thống")

    app.aboutToQuit.connect(restore_system)

    # Xử lý thoát ứng dụng
    def handle_quit():
        restore_system()
        app.quit()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()