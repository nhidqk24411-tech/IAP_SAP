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
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage
import ctypes
from ctypes import wintypes
import requests
# Định nghĩa các hằng số WinAPI
SW_HIDE = 0
SW_SHOW = 5
CUSTOMER_FEEDBACK_WEBHOOK_URL = "https://gain1109.app.n8n.cloud/webhook/349efadb-fad2-4589-9827-f99d94e3ac31"


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
# IMPORT SAP AUTOMATION
# =========================
try:
    from SAP.SAP_automation import SAPDataCollector
    print("✅ SAP automation imported successfully")
except ImportError as e:
    print(f"⚠️ Cannot import SAPDataCollector: {e}")
    SAPDataCollector = None

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
# UIPATH SAP LOGIN AUTOMATION - ĐÃ TÍCH HỢP
# =========================

class UiPathSAPLoginAutomation(QObject):
    """UiPath automation cho SAP login TRỰC TIẾP trên browser hiện tại"""

    automation_started = pyqtSignal(str)
    automation_completed = pyqtSignal(bool, str)
    automation_error = pyqtSignal(str)

    def __init__(self, user_name, global_logger):
        super().__init__()
        self.user_name = user_name  # Mã nhân viên (EM001, EM002, EM001)
        self.global_logger = global_logger
        self.credentials = {}
        self.uipath_process = None
        self.is_running = False

        print(f"🤖 UiPath SAP Automation initialized for {user_name}")

    def load_sap_credentials(self):
        """Load credentials từ employee_ids.xlsx dựa trên mã nhân viên"""
        try:
            excel_path = os.path.join(PROJECT_ROOT, "MG", "employee_ids.xlsx")
            print(f"🔍 Đang đọc file Excel: {excel_path}")

            if not os.path.exists(excel_path):
                print(f"❌ Excel file not found: {excel_path}")
                return self.get_default_credentials()

            df = pd.read_excel(excel_path)
            print(f"\n📊 Excel loaded: {len(df)} rows")
            print(f"Columns: {list(df.columns)}")

            if df.empty:
                print("⚠️ Excel file is empty")
                return self.get_default_credentials()

            # Chuẩn hóa tên cột
            df.columns = [str(col).strip().lower() for col in df.columns]
            print(f"Cleaned columns: {list(df.columns)}")

            # Tìm cột ID (đã đổi tên từ Employee_ID)
            id_column = None
            for col in df.columns:
                if col == 'id' or 'employee' in col or 'mã' in col:
                    id_column = col
                    print(f"✅ Found ID column: '{id_column}'")
                    break

            if not id_column:
                print("⚠️ No ID column found, checking all columns...")
                print("\n🔍 ALL DATA IN EXCEL:")
                print(df.to_string())
                return self.get_default_credentials()

            # Tìm user theo mã nhân viên (self.user_name)
            user_code = self.user_name.strip().upper()
            print(f"\n🔍 Looking for employee ID: '{user_code}'")

            # Chuyển tất cả về string và strip
            df[id_column] = df[id_column].astype(str).str.strip().str.upper()

            # Tìm chính xác
            user_row = df[df[id_column] == user_code]

            if user_row.empty:
                print(f"❌ Employee ID '{user_code}' not found in column '{id_column}'")
                print(f"Available IDs: {df[id_column].tolist()}")
                return self.get_default_credentials()

            if not user_row.empty:
                row = user_row.iloc[0]
                print(f"✅ Found match for {user_code}")

                # Lấy thông tin đăng nhập từ các cột
                credentials = {
                    "username": self.get_column_value(row, ['sap', 'sap_username', 'username', 'user'], ''),
                    "password": self.get_column_value(row, ['pwd', 'sap_password', 'password', 'pass'], ''),
                    "client": self.get_column_value(row, ['client', 'sap_client', 'mandt'], '312'),
                    "language": "EN",
                    "system": "SAP_ECC",
                    "employee_code": str(row.get(id_column, user_code)).strip(),
                    "employee_name": self.get_column_value(row, ['full_name', 'fullname', 'name', 'employee_name'],
                                                           user_code),
                    "email": self.get_column_value(row, ['email'], '')
                }

                print(f"\n🔐 CREDENTIALS FOR {user_code}:")
                print(f"   SAP Username: {credentials['username']}")
                print(f"   SAP Password: {'*' * len(credentials['password']) if credentials['password'] else 'EMPTY'}")
                print(f"   SAP Client: {credentials['client']}")
                print(f"   Employee: {credentials['employee_name']}")

                # Kiểm tra nếu thiếu thông tin
                if not credentials['username'] or not credentials['password']:
                    print(f"⚠️ Missing SAP credentials for {user_code}")
                    return self.get_default_credentials()

                return credentials

            return self.get_default_credentials()

        except Exception as e:
            print(f"❌ Error loading credentials: {e}")
            traceback.print_exc()
            return self.get_default_credentials()

    def get_column_value(self, row, possible_columns, default_value):
        """Lấy giá trị từ row dựa trên các tên cột có thể"""
        for col in possible_columns:
            if col in row:
                value = str(row[col]).strip()
                if value and value.lower() != 'nan' and value != '0':
                    return value

        # Nếu không tìm thấy, thử tìm không phân biệt hoa thường
        for actual_col in row.index:
            if any(target in str(actual_col).lower() for target in possible_columns):
                value = str(row[actual_col]).strip()
                if value and value.lower() != 'nan' and value != '0':
                    return value

        return default_value

    def get_default_credentials(self):
        """Default credentials"""
        return {
            "username": "LEARN-724",
            "password": "DTKUEL@123",
            "client": "312",
            "language": "EN",
            "system": "SAP_ECC",
            "employee_code": self.user_name,
            "employee_name": self.user_name,
            "email": ""
        }

    def execute_on_existing_browser(self, webview):
        """Thực thi tự động đăng nhập TRÊN BROWSER HIỆN TẠI"""
        try:
            if not webview:
                print("❌ No webview available")
                return False

            self.is_running = True
            self.automation_started.emit(f"Starting SAP auto-login for {self.user_name}")

            # 1. Load credentials
            credentials = self.load_sap_credentials()
            print(f"🔑 Credentials loaded: {credentials['username']}")

            # 2. Lấy URL hiện tại để kiểm tra
            current_url = webview.url().toString()
            print(f"🌐 Current URL: {current_url}")

            # 3. Kiểm tra nếu đang ở trang login SAP
            if not self.is_sap_login_page(current_url):
                print("ℹ️ Not on SAP login page, waiting for redirection...")
                # Chờ 3 giây rồi kiểm tra lại
                QTimer.singleShot(3000, lambda: self.retry_login_check(webview))
                return True

            # 4. Sử dụng JavaScript để tự động điền form
            self.execute_javascript_login(webview, credentials)

            return True

        except Exception as e:
            error_msg = f"UiPath automation error: {str(e)}"
            print(f"❌ {error_msg}")
            self.automation_error.emit(error_msg)
            self.is_running = False
            return False

    def is_sap_login_page(self, url):
        """Kiểm tra xem có phải trang login SAP không"""
        sap_login_indicators = [
            '/sap/bc/ui2/flp',
            '/sap/bc/webdynpro/sap/',
            '/sap/bc/logon',
            '/sap/public/bc/icf/logon',
            'sap-system-login',
            'sap-client'
        ]

        url_lower = url.lower()
        return any(indicator in url_lower for indicator in sap_login_indicators)

    def retry_login_check(self, webview):
        """Thử lại kiểm tra login page"""
        current_url = webview.url().toString()
        print(f"🔄 Retry check URL: {current_url}")

        if self.is_sap_login_page(current_url):
            credentials = self.load_sap_credentials()
            self.execute_javascript_login(webview, credentials)
        else:
            print("⚠️ Still not on SAP login page")
            self.automation_completed.emit(False, "Could not detect SAP login page")

    def execute_javascript_login(self, webview, credentials):
        """Thực hiện login bằng JavaScript"""
        print("🎯 Executing JavaScript login...")

        js_code = self.create_enhanced_javascript(credentials)

        def on_js_result(result):
            print(f"📊 JavaScript result: {result}")
            if result:
                self.automation_completed.emit(True, "Auto-login successful via JavaScript")
                self.inject_success_notification(webview)
            else:
                self.automation_completed.emit(False, "JavaScript login failed")
                self.show_fallback_instructions(webview)

        # Chạy JavaScript
        webview.page().runJavaScript(js_code, on_js_result)

    def create_enhanced_javascript(self, credentials):
        """Tạo JavaScript tự đăng nhập"""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        client = credentials.get("client", "312")
        language = credentials.get("language", "EN")

        return f"""
        (function() {{
            console.log('🤖 Auto-login SAP...');

            // Tìm tất cả input fields
            const allInputs = document.querySelectorAll('input');

            // Map credentials to field types
            const fieldMappings = [
                {{types: ['sap-client', 'client', 'MANDT'], value: '{client}'}},
                {{types: ['sap-user', 'user', 'username', 'txtUser'], value: '{username}'}},
                {{types: ['sap-password', 'password', 'pwd', 'txtPassword'], value: '{password}'}},
                {{types: ['sap-language', 'language', 'lang'], value: '{language}'}}
            ];

            let filledCount = 0;

            // Tìm và điền từng field
            fieldMappings.forEach(mapping => {{
                let found = false;

                for (const input of allInputs) {{
                    if (!input || input.type === 'hidden') continue;

                    const name = (input.name || '').toLowerCase();
                    const id = (input.id || '').toLowerCase();
                    const placeholder = (input.placeholder || '').toLowerCase();
                    const className = (input.className || '').toLowerCase();

                    for (const fieldType of mapping.types) {{
                        const typeLower = fieldType.toLowerCase();

                        if (name.includes(typeLower) || 
                            id.includes(typeLower) || 
                            placeholder.includes(typeLower) ||
                            className.includes(typeLower)) {{

                            console.log('✅ Found field:', fieldType);
                            input.value = mapping.value;

                            // Kích hoạt events để SAP nhận biết
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));

                            filledCount++;
                            found = true;
                            break;
                        }}
                    }}

                    if (found) break;
                }}
            }});

            console.log('📊 Fields filled:', filledCount);

            if (filledCount > 0) {{
                // Đợi 0.5 giây rồi tìm nút login
                setTimeout(() => {{
                    // Tìm nút login
                    const allButtons = document.querySelectorAll('button, input[type="submit"], input[type="button"]');

                    const loginKeywords = ['log on', 'login', 'anmelden', 'enter', 'ok', 'submit', 'sign in'];

                    for (const btn of allButtons) {{
                        if (!btn) continue;

                        const btnText = (btn.textContent || btn.value || btn.innerText || '').toLowerCase().trim();
                        const btnType = (btn.type || '').toLowerCase();
                        const btnName = (btn.name || '').toLowerCase();

                        if (btnType === 'submit' || 
                            loginKeywords.some(keyword => btnText.includes(keyword)) ||
                            loginKeywords.some(keyword => btnName.includes(keyword))) {{

                            console.log('🎯 Clicking login button');
                            btn.click();
                            return true;
                        }}
                    }}

                    // Thử submit form nếu không tìm thấy button
                    const forms = document.querySelectorAll('form');
                    if (forms.length > 0) {{
                        console.log('📤 Submitting form');
                        forms[0].submit();
                        return true;
                    }}

                    console.log('⚠️ No login button found');
                    return false;

                }}, 500);  // Chờ 0.5s

                return true;
            }} else {{
                console.log('❌ No fields to fill');
                return false;
            }}
        }})();
        """

    def show_fallback_instructions(self, webview):
        """VÔ HIỆU HÓA HOÀN TOÀN - KHÔNG HIỆN GÌ CẢ"""
        print("⚠️ Fallback disabled - not showing any notification")
        # KHÔNG CHẠY JAVASCRIPT GÌ CẢ

    def inject_success_notification(self, webview):
        """Inject JavaScript success notification"""
        js_code = """
        console.log('✅ SAP auto-login successful!');

        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            z-index: 99999;
            font-family: Arial, sans-serif;
            font-size: 14px;
            animation: slideIn 0.5s ease;
        `;
        notification.innerHTML = `
            <strong>✅ SAP Auto-Login Successful!</strong><br>
            <small>System completed the login automatically</small>
        `;
        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);

        // Thêm animation style
        if (!document.getElementById('sap-notification-style')) {
            const style = document.createElement('style');
            style.id = 'sap-notification-style';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `;
            document.head.appendChild(style);
        }
        """

        if webview:
            QTimer.singleShot(1000, lambda: webview.page().runJavaScript(js_code))

    def stop(self):
        """Dừng automation"""
        print("🛑 Stopping UiPath automation...")
        self.is_running = False

        if self.uipath_process:
            try:
                self.uipath_process.terminate()
                print("✅ UiPath process terminated")
            except:
                pass


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


class SAPBackgroundCollector(QThread):
    """Thu thập SAP data trong nền - KHÔNG CHẶN UI"""

    finished = pyqtSignal(bool, str)
    progress = pyqtSignal(str)

    def __init__(self, user_name, save_directory, logger):
        super().__init__()
        self.user_name = user_name
        self.save_directory = save_directory
        self.logger = logger
        self.is_running = True

    def run(self):
        try:
            if not self.is_running:
                return

            self.progress.emit("Starting SAP data collection...")

            # Kiểm tra module SAP có tồn tại không
            if SAPDataCollector is None:
                self.progress.emit("SAP module not available")
                self.finished.emit(False, "SAP module not available")
                return

            # Tạo collector
            collector = SAPDataCollector(
                user_name=self.user_name,
                save_directory=self.save_directory
            )

            if not self.is_running:
                return

            self.progress.emit("Connecting to SAP...")

            # Thu thập dữ liệu
            result = collector.quick_collect()

            if result and os.path.exists(result):
                self.progress.emit(f"✅ SAP data saved: {os.path.basename(result)}")
                self.logger.log_alert(
                    "SAP",
                    "SAP_DATA_COLLECTED_BACKGROUND",
                    f"Data collected in background: {os.path.basename(result)}",
                    "INFO",
                    is_fraud=False
                )
                self.finished.emit(True, result)
            else:
                self.progress.emit("❌ Failed to collect SAP data")
                self.logger.log_alert(
                    "SAP",
                    "SAP_DATA_FAILED_BACKGROUND",
                    "Background collection failed",
                    "WARNING",
                    is_fraud=False
                )
                self.finished.emit(False, "Collection failed")

        except Exception as e:
            error_msg = f"Background collection error: {str(e)[:100]}"
            self.progress.emit(f"❌ {error_msg}")
            self.logger.log_alert(
                "SAP",
                "SAP_DATA_ERROR_BACKGROUND",
                error_msg,
                "ERROR",
                is_fraud=False
            )
            self.finished.emit(False, error_msg)

    def stop(self):
        """Dừng collection"""
        self.is_running = False

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

        # Initialize the lists that were missing
        self.fraud_events = []  # Initialize fraud events list
        self.mouse_details = []  # Initialize mouse details list

        # Đường dẫn file SAP data
        self.sap_data_dir = self.PATHS['monthly']

        # Excel file path
        current_date = datetime.now().strftime("%Y_%m")
        self.excel_path = os.path.join(
            self.PATHS['monthly'],
            f"work_logs_{user_name}_{current_date}.xlsx"
        )

        print(f"🌐 Global logger initialized for: {user_name}")
        print(f"📊 SAP data directory: {self.sap_data_dir}")
        print(f"📄 Excel file path: {self.excel_path}")

        # Kiểm tra .env file
        self.check_env_file()
    def check_env_file(self):
        """Kiểm tra file .env có tồn tại không"""
        env_path = os.path.join(PROJECT_ROOT, "SAP", ".env")
        if os.path.exists(env_path):
            print(f"✅ Found .env file at: {env_path}")

            # Đọc và hiển thị (không hiện password)
            try:
                # Thử nhiều encoding phổ biến
                encodings_to_try = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'gb2312']

                for encoding in encodings_to_try:
                    try:
                        with open(env_path, 'r', encoding=encoding) as f:
                            content = f.read()
                        print(f"✅ Successfully read .env with {encoding} encoding")

                        # Xử lý từng dòng
                        lines = content.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key = line.split('=')[0].strip()
                                if 'PASSWORD' not in key.upper():  # Không hiện password
                                    print(f"   {line}")
                        break  # Thành công thì dừng
                    except UnicodeDecodeError:
                        continue  # Thử encoding tiếp theo

            except Exception as e:
                print(f"⚠️ Cannot read .env file with any encoding: {e}")
                # Chỉ in đường dẫn nếu không đọc được
                print(f"   .env file exists but cannot be read")
        else:
            print(f"⚠️ .env file not found at: {env_path}")
            print("   Please create .env file with SAP_USER and SAP_PASSWORD")

    def collect_sap_data_at_session_end(self):
        """Thu thập dữ liệu SAP khi kết thúc session"""
        try:
            print(f"\n{'=' * 50}")
            print(f"🤖 STARTING SAP DATA COLLECTION")
            print(f"   User: {self.user_name}")
            print(f"   Directory: {self.sap_data_dir}")
            print(f"{'=' * 50}")

            # Tạo collector với credentials từ .env
            sap_collector = SAPDataCollector(
                user_name=self.user_name,
                save_directory=self.sap_data_dir
            )

            # Thu thập dữ liệu
            file_path = sap_collector.quick_collect()

            if file_path and os.path.exists(file_path):
                print(f"✅ SAP data collected: {file_path}")
                self.log_alert(
                    "SAP",
                    "SAP_DATA_COLLECTED",
                    f"Data collected at session end: {os.path.basename(file_path)}",
                    "INFO",
                    is_fraud=False
                )
                return True
            else:
                print(f"❌ Failed to collect SAP data")
                self.log_alert(
                    "SAP",
                    "SAP_DATA_FAILED",
                    "Failed to collect SAP data at session end",
                    "WARNING",
                    is_fraud=False
                )
                return False

        except Exception as e:
            print(f"❌ SAP collection error: {e}")
            traceback.print_exc()
            self.log_alert(
                "SAP",
                "SAP_DATA_ERROR",
                f"Error during SAP collection: {str(e)[:100]}",
                "ERROR",
                is_fraud=False
            )
            return False

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
        self.mouse_details.append(mouse_entry)  # Fixed: append mouse_entry, not mouse_data

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
            # Ensure lists exist
            if not hasattr(self, 'fraud_events'):
                self.fraud_events = []
            if not hasattr(self, 'mouse_details'):
                self.mouse_details = []

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
        """Lưu dữ liệu cuối cùng - BÂY GIỜ CÓ THÊM SAP"""
        print(f"\n💾 SAVING FINAL DATA (WITH SAP COLLECTION)")

        # 1. Lưu log data vào Excel
        log_success = self.save_to_excel()

        # 2. Thu thập dữ liệu SAP (chạy sau để không ảnh hưởng đến log data)
        sap_success = self.collect_sap_data_at_session_end()

        # Summary
        if sap_success:
            print(f"✅ SAP data collected successfully")
        else:
            print(f"⚠️ SAP data collection skipped or failed")

        if log_success:
            print(f"✅ Log data saved: {self.excel_path}")

        print(f"🎉 Final data saved for user: {self.user_name}")
        return sap_success or log_success
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
# ENHANCED SAFE BROWSER VỚI SAP AUTO-LOGIN
# ============================================
class EnhancedSafeBrowser(ProfessionalWorkBrowser):
    """Safe Browser chuyên nghiệp tích hợp SAP auto-login"""

    def __init__(self, user_name, global_logger, parent_window=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_name = user_name  # Mã nhân viên
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

        # Lấy tên hiển thị từ mã nhân viên
        self.display_name = self.get_display_name_from_id(user_name)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint
        )

        TaskbarController.set_visibility(False)

        # Import face system
        try:
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

        # Khởi tạo SAP automation
        self.uipath_automation = UiPathSAPLoginAutomation(user_name, global_logger)

        # Kết nối signals
        self.uipath_automation.automation_started.connect(self.on_automation_started)
        self.uipath_automation.automation_completed.connect(self.on_automation_completed)
        self.uipath_automation.automation_error.connect(self.on_automation_error)

        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        self.setup_random_check()

        self.global_logger.log_browser_alert(
            event_type="BROWSER_OPEN",
            details="Professional Workspace Browser started with SAP auto-login",
            severity="INFO",
            is_fraud=False
        )

        # Ghi nhận thời điểm bắt đầu
        self.session_start_time = time.time()

        # Thêm nút automation sau khi khởi tạo
        QTimer.singleShot(1000, self.add_automation_buttons)

    def get_display_name_from_id(self, employee_id):
        """Lấy tên hiển thị từ mã nhân viên"""
        try:
            excel_path = os.path.join(PROJECT_ROOT, "MG","employee_ids.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
                # Chuẩn hóa tên cột
                df.columns = [str(col).strip().lower() for col in df.columns]

                # Tìm cột ID (đã đổi tên từ Employee_ID)
                id_column = None
                for col in df.columns:
                    if col == 'id' or 'employee' in col or 'mã' in col:
                        id_column = col
                        break

                if id_column:
                    # Tìm cột tên
                    name_column = None
                    for col in df.columns:
                        if 'full' in col or 'name' in col:
                            name_column = col
                            break

                    if name_column:
                        # Tìm hàng có mã trùng
                        for idx, row in df.iterrows():
                            if str(row[id_column]).strip().upper() == employee_id.upper():
                                name = str(row[name_column]).strip()
                                if name and name.lower() != 'nan':
                                    return name
        except Exception as e:
            print(f"⚠️ Error getting display name: {e}")

        return employee_id  # Trả về mã nếu không tìm thấy tên

    def on_automation_started(self, message):
        """Khi automation bắt đầu"""
        print(f"📢 {message}")
        self.show_status_message(f"🤖 {message}", 5000)

    def on_automation_completed(self, success, message):
        """Khi automation hoàn thành"""
        if success:
            print(f"🎉 {message}")
            self.show_status_message(f"✅ {message}", 5000)

            # Log sự kiện thành công
            self.global_logger.log_browser_alert(
                event_type="SAP_AUTO_LOGIN_SUCCESS",
                details=f"Auto-login successful for {self.display_name}",
                severity="INFO",
                is_fraud=False
            )
        else:
            print(f"⚠️ {message}")
            self.show_status_message(f"⚠️ {message}", 5000)

    def on_automation_error(self, error_msg):
        """Khi có lỗi"""
        print(f"❌ {error_msg}")
        self.show_status_message(f"❌ {error_msg}", 5000)

    def show_status_message(self, message, timeout=3000):
        """Hiển thị message trên status bar"""
        try:
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(message, timeout)
            elif hasattr(self, 'statusBar'):
                self.statusBar().showMessage(message, timeout)
        except:
            pass

    def setup_sap_automation(self):
        """Thiết lập SAP automation TRÊN TAB CÓ SẴN"""
        print("🤖 Setting up SAP automation on existing tab...")

        try:
            # Tìm tab SAP có sẵn (không tạo tab mới)
            sap_webview = self.find_sap_webview()

            if sap_webview:
                print(f"✅ Found SAP webview, setting up automation...")

                # Khi trang load xong, chạy automation
                sap_webview.loadFinished.connect(
                    lambda ok: self.on_sap_page_loaded(ok, sap_webview)
                )

                # Thêm nút automation vào toolbar
                self.add_automation_buttons()

                # Kiểm tra và tự động đăng nhập nếu đang ở trang login
                self.check_and_auto_login()
            else:
                print("⚠️ No SAP webview found")
                # Tạo tab SAP mới
                self.create_sap_tab()

        except Exception as e:
            print(f"❌ Error setting up SAP automation: {e}")

    def find_sap_webview(self):
        """Tìm webview SAP có sẵn trong browser"""
        try:
            # Tìm tab có chứa "SAP" trong tiêu đề
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    tab_text = self.tab_widget.tabText(i).lower()
                    if 'sap' in tab_text or 'login' in tab_text:
                        print(f"✅ Found SAP tab: {self.tab_widget.tabText(i)}")

                        # Lấy widget từ tab
                        tab_widget = self.tab_widget.widget(i)

                        # Tìm QWebEngineView trong tab
                        webview = self.find_webengineview_in_widget(tab_widget)
                        if webview:
                            print(f"✅ Found QWebEngineView in SAP tab")
                            return webview

            print("⚠️ No SAP tab found")
            return None

        except Exception as e:
            print(f"❌ Error finding SAP webview: {e}")
            return None

    def find_webengineview_in_widget(self, widget):
        """Tìm QWebEngineView trong widget"""
        try:
            # Nếu widget là QWebEngineView
            if isinstance(widget, QWebEngineView):
                return widget

            # Tìm đệ quy trong children
            for child in widget.children():
                result = self.find_webengineview_in_widget(child)
                if result:
                    return result

            return None
        except:
            return None

    def on_sap_page_loaded(self, ok, webview):
        """Khi trang SAP load xong"""
        if ok:
            current_url = webview.url().toString()
            print(f"✅ Page loaded: {current_url[:100]}")

            # Chạy JavaScript để debug
            debug_js = """
            console.log('=== SAP PAGE DEBUG ===');
            console.log('Title:', document.title);
            console.log('Forms:', document.forms.length);
            document.querySelectorAll('input').forEach((input, i) => {
                console.log(`Input ${i}:`, {
                    name: input.name,
                    id: input.id,
                    type: input.type,
                    placeholder: input.placeholder,
                    className: input.className
                });
            });
            console.log('=====================');
            return document.forms.length;
            """

            webview.page().runJavaScript(debug_js, lambda result:
            print(f"📋 Forms found: {result}"))

            # Kiểm tra và auto-login
            if self.uipath_automation.is_sap_login_page(current_url):
                print("🎯 SAP login page detected, starting auto-login in 2s...")
                QTimer.singleShot(2000, lambda: self.execute_sap_automation(webview))
            else:
                print(f"ℹ️ Already logged in or different page: {current_url[:50]}...")
        else:
            print("❌ Failed to load SAP page")

    def execute_sap_automation(self, webview):
        """Thực thi SAP automation TRÊN WEBVIEW CÓ SẴN"""
        try:
            if webview:
                print("🚀 Executing SAP automation on existing webview...")

                # Hiển thị status message
                self.show_status_message("🤖 Starting SAP auto-login...", 0)

                # Thực thi automation
                success = self.uipath_automation.execute_on_existing_browser(webview)

                if success:
                    print("✅ Automation started")
                else:
                    print("⚠️ Failed to start automation")
                    self.show_status_message("⚠️ Automation failed", 3000)

        except Exception as e:
            print(f"❌ Error executing automation: {e}")
            self.show_status_message(f"❌ Error: {e}", 3000)

    def add_automation_buttons(self, webview=None):
        """Thêm nút automation vào toolbar"""
        try:
            if not hasattr(self, 'toolbar'):
                print("⚠️ Toolbar not found")
                return

            # Xóa các nút cũ nếu có
            for widget in self.toolbar.findChildren(QPushButton):
                if widget.text() in ["🔍 Check & Login", "🚀 Force Login", "🤖 Run UiPath", "⏹️ Stop"]:
                    widget.deleteLater()

            if webview is None:
                webview = self.find_sap_webview()

            # Nút Kiểm tra & Đăng nhập
            check_btn = QPushButton("🔍 Check & Login")
            check_btn.clicked.connect(lambda: self.check_and_auto_login())
            check_btn.setToolTip("Check if on SAP login page and auto-login")

            # Nút Force Login (thủ công)
            force_btn = QPushButton("🚀 Force Login")
            if webview:
                force_btn.clicked.connect(lambda: self.execute_sap_automation(webview))
            force_btn.setToolTip("Force auto-login on current page")

            # Style cho nút
            button_style = """
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #667eea, stop:1 #764ba2);
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 15px;
                    font-weight: bold;
                    margin: 2px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 #764ba2, stop:1 #667eea);
                    border: 1px solid #3b82f6;
                }
                QPushButton:pressed {
                    background: #555;
                }
            """

            check_btn.setStyleSheet(button_style)
            force_btn.setStyleSheet(button_style)

            self.toolbar.addWidget(check_btn)
            self.toolbar.addWidget(force_btn)
            self.toolbar.addSeparator()

            print("✅ Added enhanced automation buttons")

        except Exception as e:
            print(f"❌ Error adding buttons: {e}")

    def check_and_auto_login(self):
        """Kiểm tra và tự động đăng nhập"""
        try:
            sap_webview = self.find_sap_webview()
            if sap_webview:
                # Lấy URL hiện tại
                current_url = sap_webview.url().toString()
                print(f"🔍 Current URL in SAP tab: {current_url}")

                if self.uipath_automation.is_sap_login_page(current_url):
                    print("✅ Detected SAP login page, starting auto-login...")
                    self.execute_sap_automation(sap_webview)
                else:
                    print(f"ℹ️ Not a login page: {current_url[:50]}...")

                    # Thử navigate đến SAP login URL
                    QTimer.singleShot(2000, lambda: self.navigate_to_sap_login(sap_webview))
            else:
                print("⚠️ No SAP webview found")
                # Tạo tab SAP mới nếu không có
                self.create_sap_tab()

        except Exception as e:
            print(f"❌ Error checking login: {e}")

    def navigate_to_sap_login(self, webview):
        """Navigate đến trang login SAP"""
        sap_login_url = "https://s36.gb.ucc.cit.tum.de/sap/bc/ui2/flp"
        webview.setUrl(QUrl(sap_login_url))
        print(f"🌐 Navigating to SAP login: {sap_login_url}")

        # Đợi load xong rồi chạy automation
        def on_navigated(ok):
            if ok:
                print("✅ Navigation successful, waiting for auto-login...")
                QTimer.singleShot(2000, lambda: self.execute_sap_automation(webview))
            else:
                print("❌ Navigation failed")

        webview.loadFinished.connect(on_navigated)

    def create_sap_tab(self):
        """Tạo tab SAP mới nếu chưa có"""
        try:
            print("➕ Creating new SAP tab...")

            # Tạo webview mới
            new_webview = QWebEngineView()
            new_webview.setUrl(QUrl("https://s36.gb.ucc.cit.tum.de/sap/bc/ui2/flp"))

            # Thêm vào tab widget
            if hasattr(self, 'tab_widget'):
                tab_index = self.tab_widget.addTab(new_webview, "SAP System")
                self.tab_widget.setCurrentIndex(tab_index)

                # Đợi load xong
                new_webview.loadFinished.connect(
                    lambda ok: self.on_sap_page_loaded(ok, new_webview)
                )

                # Thêm nút automation mới
                self.add_automation_buttons(new_webview)

                print("✅ New SAP tab created")

        except Exception as e:
            print(f"❌ Error creating SAP tab: {e}")

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
                f"🔐 RANDOM IDENTITY CHECK\n\nUser: {self.display_name}\nPlease look straight at the camera.\n\nClick OK to start verification.")
            msg_box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
            msg_box.setWindowFlags(msg_box.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
            msg_box.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
            msg_box.exec()

            if self.face_system is None:
                print("🎭 Using demo mode...")
                QMessageBox.information(self, "DEMO Mode",
                                        f"DEMO: Verified as {self.display_name}\n\nYou may continue working.")
                self.global_logger.log_browser_alert("FACE_CHECK_DEMO", "Demo mode - Verification passed",
                                                     is_fraud=False)
                self.on_face_check_finished(
                    {"success": True, "matched": True, "name": self.display_name, "similarity": 0.99})
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

                if detected_user == self.user_name or detected_user == self.display_name:
                    print(f"✅ User verified: {detected_user}")
                    self.global_logger.log_browser_alert("FACE_CHECK_SUCCESS", f"Confidence: {similarity:.1%}",
                                                         is_fraud=False)
                    QMessageBox.information(self, "Verification Successful",
                                            f"✅ Verified: {self.display_name}\nConfidence: {similarity:.1%}")
                    self.resume_after_check_logic(True)
                else:
                    print(f"❌ User mismatch")
                    self.global_logger.log_browser_alert("FACE_CHECK_MISMATCH", f"Detected: {detected_user}",
                                                         is_fraud=True)
                    QMessageBox.critical(self, "🚨 UNAUTHORIZED",
                                         f"❌ User mismatch!\nExpected: {self.display_name}\nDetected: {detected_user}")
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
        """Tối ưu quá trình đóng browser - ĐÓNG NHANH"""
        if self.is_closing:
            print("🛑 Fast-closing browser...")

            # 1. Ẩn window ngay lập tức để người dùng thấy nó đã đóng
            self.hide()

            # 2. Ngừng tất cả timers và workers
            if hasattr(self, 'check_timer'):
                self.check_timer.stop()

            if hasattr(self, 'uipath_automation'):
                try:
                    self.uipath_automation.stop()
                except:
                    pass

            # 3. Đóng tất cả webviews
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    widget = self.tab_widget.widget(i)
                    if widget:
                        try:
                            # Gọi deleteLater thay vì đóng trực tiếp
                            widget.deleteLater()
                        except:
                            pass

            # 4. Restore taskbar
            TaskbarController.set_visibility(True)

            # 5. Tính toán thời gian nhanh
            try:
                current_time = time.time()
                if hasattr(self, 'timer_widget') and self.timer_widget and self.timer_widget.is_running:
                    self.actual_work_time += (current_time - self.last_timer_update)

                total_hours = int(self.actual_work_time // 3600)
                total_minutes = int((self.actual_work_time % 3600) // 60)

                self.global_logger.log_browser_alert(
                    event_type="BROWSER_CLOSED",
                    details=f"Session ended. Work time: {total_hours}h {total_minutes}m",
                    severity="INFO",
                    is_fraud=False
                )
            except:
                pass

            # 6. Gọi parent để lưu SAP data (sẽ chạy trong background)
            if self.parent_window and hasattr(self.parent_window, 'on_browser_closed'):
                # Gọi sau 100ms để browser có thể đóng hoàn toàn
                QTimer.singleShot(100, self.parent_window.on_browser_closed)

            print("✅ Browser closed successfully")
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
        self.user_name = user_name  # Mã nhân viên (EM001, EM002, EM001)
        self.display_name = self.get_display_name_from_id(user_name)  # Tên hiển thị
        self.sap=self.get_display_sap_from_id(user_name)

        self.ui = Ui_HomeWindow()
        self.ui.setupUi(self)
        # Thêm biến cho SAP background collector
        self.sap_collector = None

        # Đảm bảo dọn dẹp khi đóng
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # DISABLE PHÓNG TO và không cho thay đổi kích thước
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)
        self.setFixedSize(self.size())

        # KHỞI TẠO GLOBAL LOGGER
        self.global_logger = GlobalExcelLogger(user_name)
        self.uipath_automation = UiPathSAPLoginAutomation(user_name, self.global_logger)

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

        # Cập nhật tên user (hiển thị tên thay vì mã)
        self.update_user_name(self.display_name)

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

        self.setWindowTitle(f"PowerSight - {self.display_name}")
        self.setWindowFlag(Qt.WindowType.Window, True)
        print(f"🏠 HomeWindow created for {self.display_name} ({user_name})")

    def get_display_name_from_id(self, employee_id):
        """Lấy tên hiển thị từ mã nhân viên"""
        try:
            excel_path = os.path.join(PROJECT_ROOT, "MG","employee_ids.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
                # Chuẩn hóa tên cột
                df.columns = [str(col).strip().lower() for col in df.columns]

                # Tìm cột ID (đã đổi tên từ Employee_ID)
                id_column = None
                for col in df.columns:
                    if col == 'id' or 'employee' in col or 'mã' in col:
                        id_column = col
                        break

                if id_column:
                    # Tìm cột tên
                    name_column = None
                    for col in df.columns:
                        if 'full' in col or 'name' in col:
                            name_column = col
                            break

                    if name_column:
                        # Tìm hàng có mã trùng
                        for idx, row in df.iterrows():
                            if str(row[id_column]).strip().upper() == employee_id.upper():
                                name = str(row[name_column]).strip()
                                if name and name.lower() != 'nan':
                                    return name
        except Exception as e:
            print(f"⚠️ Error getting display name: {e}")

        return employee_id  # Trả về mã nếu không tìm thấy tên

    def get_display_sap_from_id(self, employee_id):
        """Lấy tên hiển thị từ mã nhân viên"""
        try:
            excel_path = os.path.join(PROJECT_ROOT, "MG", "employee_ids.xlsx")
            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)
                # Chuẩn hóa tên cột
                df.columns = [str(col).strip().lower() for col in df.columns]

                # Tìm cột ID (đã đổi tên từ Employee_ID)
                id_column = None
                for col in df.columns:
                    if col == 'id' or 'employee' in col or 'mã' in col:
                        id_column = col
                        break

                if id_column:
                    # Tìm cột tên
                    sap_column = None
                    for col in df.columns:
                        if 'SAP' in col:
                            sap_column = col
                            break

                    if sap_column:
                        # Tìm hàng có mã trùng
                        for idx, row in df.iterrows():
                            if str(row[id_column]).strip().upper() == employee_id.upper():
                                sap = str(row[sap_column]).strip()
                                if sap and sap.lower() != 'nan':
                                    return sap
        except Exception as e:
            print(f"⚠️ Error getting display name: {e}")

        return employee_id  # Trả về mã nếu không tìm thấy tên

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
        print(f"🚀 OPENING CHATBOT for {self.display_name}")
        print(f"{'=' * 50}")

        if EmployeeChatbotGUI is None:
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 "Không thể tải chatbot system.\n\n")
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

            print(f"✅ Chatbot opened successfully for {self.display_name}")

        except Exception as e:
            print(f"❌ CRITICAL ERROR opening chatbot: {e}")
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống",
                                 f"Lỗi nghiêm trọng khi mở chatbot:\n\n{str(e)[:100]}...\n\n"
                                 "Vui lòng kiểm tra file employee_chatbot.py")

    def open_dashboard(self):
        """Mở dashboard"""
        print(f"\n{'=' * 50}")
        print(f"📊 OPENING DASHBOARD for {self.display_name}")
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

            print(f"✅ Dashboard opened successfully for {self.display_name}")

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
        """Bắt đầu session làm việc với SAP auto-login"""
        if self.is_working:
            QMessageBox.information(self, "Session Active", "Work session is already running!")
            return

        reply = QMessageBox.question(
            self, "Start Work Session",
            f"Start secure work session for {self.display_name}?\n\n"
            "Features included:\n"
            "✓ Professional Workspace Browser\n"
            "✓ SAP Auto-Login 🤖\n"
            "✓ Mouse Behavior Analysis\n"
            "✓ Random Face Verification\n"
            "✓ Stranger Detection\n"
            "✓ Activity Logging\n"
            "✓ Fraud Detection\n\n"
            "Hệ thống sẽ tự động đăng nhập SAP System trên tab có sẵn.\n\n"
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

            # Log bắt đầu session
            self.global_logger.log_browser_alert(
                event_type="SESSION_START",
                details=f"Session started for {self.display_name} with SAP auto-login",
                severity="INFO",
                is_fraud=False
            )

            # Tạo các event cho mouse tracking
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

            # Log mouse tracking
            self.global_logger.log_browser_alert(
                event_type="MOUSE_TRACKING_START",
                details="Mouse analysis system started",
                severity="INFO",
                is_fraud=False
            )

            # Tạo EnhancedSafeBrowser với SAP auto-login
            self.browser_window = EnhancedSafeBrowser(
                user_name=self.user_name,
                global_logger=self.global_logger,
                parent_window=self,
                pause_event=self.pause_event,
                command_queue=self.command_queue,
                alert_queue=self.alert_queue
            )

            QTimer.singleShot(100, self.browser_window.setup_timer_with_logging)

            # Hiển thị browser fullscreen
            self.browser_window.show_secure()

            # HomeWindow minimized
            self.showMinimized()
            self.active_window = 'browser'

            # Thiết lập SAP automation TRÊN TAB CÓ SẴN
            QTimer.singleShot(2000, self.browser_window.setup_sap_automation)

            # Log thành công
            self.global_logger.log_browser_alert(
                event_type="SESSION_START_FULLSCREEN",
                details="Work session started with SAP automation on existing tab",
                severity="INFO",
                is_fraud=False
            )

            print("✅ Work session started with SAP auto-login on existing tab")

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
            f"User: {self.display_name}\n"
            f"Employee ID: {summary['user']}\n"
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
        """Xử lý khi browser đóng - KHÔNG CHỜ SAP DATA"""
        print("\n🛑 Browser closed - Starting background cleanup...")

        # 1. Log sự kiện
        self.global_logger.log_browser_alert(
            event_type="SESSION_END",
            details=f"Session ended for {self.display_name}",
            severity="INFO",
            is_fraud=False
        )

        # 2. Dừng mouse process (có timeout ngắn)
        if self.stop_event:
            self.stop_event.set()

        if self.mouse_process:
            print("⏳ Stopping mouse process...")
            # Chỉ chờ 3 giây thôi
            self.mouse_process.join(timeout=3)

            if self.mouse_process.is_alive():
                print("⚠️ Mouse process still alive, forcing termination...")
                try:
                    self.mouse_process.terminate()
                    self.mouse_process.join(timeout=1)
                except:
                    pass

        # 3. Lưu log data NGAY LẬP TỨC (không chờ SAP)
        print("\n💾 Saving log data immediately...")
        log_success = self.global_logger.save_to_excel()

        if log_success:
            print("✅ Log data saved")
        else:
            print("⚠️ Failed to save log data")
        print("\n📧 Sending customer feedback email...")
        self.send_customer_feedback_email()

        # 4. Chạy SAP data collection TRONG BACKGROUND (không chờ)
        print("🤖 Starting SAP data collection in background...")
        credentials = self.uipath_automation.load_sap_credentials()
        print(f"🔑 Credentials loaded: {credentials['username']}")

        # Tạo và chạy background collector
        self.sap_collector = SAPBackgroundCollector(
            user_name=str(credentials['username']),
            save_directory=self.global_logger.PATHS['monthly'],
            logger=self.global_logger
        )

        def on_sap_finished(success, message):
            """Callback khi SAP collection hoàn thành"""
            if success:
                print(f"✅ Background SAP collection successful: {message}")
                # Có thể hiển thị thông báo nhỏ ở đây nếu muốn
            else:
                print(f"⚠️ Background SAP collection failed: {message}")

        self.sap_collector.finished.connect(on_sap_finished)
        self.sap_collector.start()

        # 5. Reset UI NGAY LẬP TỨC
        self.reset_ui_immediately()

        # 6. Hiển thị thông báo nhanh
        QMessageBox.information(
            self,
            "Session Ended",
            f"✅ Session ended for {self.display_name}\n\n"
            f"✓ Mouse tracking stopped\n"
            f"✓ Log data saved\n"
            f"✓ SAP data collection started in background\n\n"
            f"You can continue using other features.\n"
            f"SAP data will be saved automatically."
        )

        print("✅ Browser cleanup completed (non-blocking)")
        self.showNormal()
        self.activateWindow()

    def reset_ui_immediately(self):
        """Reset UI ngay lập tức"""
        self.is_working = False
        self.ui.pushButton_8.setText("Start")
        self.ui.pushButton_8.setEnabled(True)
        self.ui.pushButton_5.setEnabled(False)
        self.ui.pushButton_6.setEnabled(False)

        # Clean up references
        self.mouse_process = None
        self.stop_event = None
        self.pause_event = None
        self.command_queue = None
        self.alert_queue = None
        self.browser_window = None

        if hasattr(self.ui, 'khichle'):
            self.ui.khichle.setText("Session ended. Ready for next session.")

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
        """Xử lý khi đóng HomeWindow - Dọn dẹp tất cả"""
        print("\n🛑 HomeWindow closing - Cleaning up everything...")
        TaskbarController.set_visibility(True)

        # Dừng SAP collector nếu đang chạy
        if self.sap_collector and self.sap_collector.isRunning():
            print("   Stopping SAP background collector...")
            self.sap_collector.stop()
            self.sap_collector.quit()
            self.sap_collector.wait(1000)  # Chờ tối đa 1 giây

        # Đóng các cửa sổ con
        if self.chatbot_window:
            try:
                self.chatbot_window.close()
            except:
                pass

        if self.dashboard_window:
            try:
                self.dashboard_window.close()
            except:
                pass

        # Đảm bảo mouse process được dọn dẹp
        if self.mouse_process and self.mouse_process.is_alive():
            try:
                self.mouse_process.terminate()
                self.mouse_process.join(timeout=1)
            except:
                pass

        event.accept()
        print("✅ HomeWindow closed cleanly")

    def send_customer_feedback_email(self):
        """Gửi email phản hồi khách hàng tự động khi kết thúc session"""
        try:
            print(f"\n📧 Đang gửi email phản hồi khách hàng cho {self.display_name}...")

            # Email khách hàng mặc định
            customer_email = "konodio3q@gmail.com"

            # Lấy thông tin nhân viên
            employee_name = self.display_name
            employee_id = self.user_name

            # Import EmailTemplates
            try:
                from MG.email_templates import EmailTemplates

                # Tạo nội dung email
                html_body = EmailTemplates.get_customer_feedback_template(
                    employee_name=employee_name,
                    employee_id=employee_id,
                    customer_email=customer_email
                )

                # Chuẩn bị dữ liệu gửi đến n8n
                email_data = {
                    "test_mode": False,
                    "timestamp": datetime.now().isoformat(),
                    "to_email": customer_email,
                    "subject": f"[PowerSight] Yêu cầu phản hồi về nhân viên {employee_name}",
                    "body": f"""Kính gửi Quý khách hàng,

    Cảm ơn Quý khách đã hợp tác cùng nhân viên {employee_name} (Mã: {employee_id}).

    Để giúp chúng tôi cải thiện chất lượng dịch vụ, Quý khách vui lòng dành vài phút đánh giá nhân viên qua link trong email này.

    Trân trọng,
    Bộ phận Quản lý Chất lượng
    PowerSight""",
                    "html_body": html_body,
                    "cc": "",  # Có thể thêm CC nếu cần
                    "employee_name": employee_name,
                    "employee_id": employee_id,
                    "email_type": "CUSTOMER_FEEDBACK"
                }

                # Gửi request đến n8n
                response = requests.post(
                    CUSTOMER_FEEDBACK_WEBHOOK_URL,
                    json=email_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    print(f"✅ Đã gửi email phản hồi đến {customer_email}")

                    # Log sự kiện
                    self.global_logger.log_browser_alert(
                        event_type="CUSTOMER_FEEDBACK_EMAIL_SENT",
                        details=f"Gửi email đánh giá đến {customer_email} cho nhân viên {employee_name}",
                        severity="INFO",
                        is_fraud=False
                    )

                    return True
                else:
                    print(f"❌ Lỗi gửi email: {response.status_code} - {response.text}")
                    return False

            except ImportError as e:
                print(f"❌ Không thể import EmailTemplates: {e}")
                return False

        except Exception as e:
            print(f"❌ Lỗi khi gửi email phản hồi khách hàng: {e}")
            import traceback
            traceback.print_exc()
            return False

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

    # 5. ĐỌC THÔNG TIN TỪ THAM SỐ DÒNG LỆNH (KHÔNG DÙNG FILE TEMP)
    user_id = None

    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        user_type = sys.argv[2]

        if user_type != "employee":
            print(f"❌ Người dùng không phải nhân viên: {user_type}")
            QMessageBox.critical(None, "Lỗi đăng nhập",
                                 f"Bạn không có quyền truy cập vào hệ thống nhân viên.\nLoại user: {user_type}")
            sys.exit(1)

        print(f"✅ Đã nhận thông tin từ App.py: {user_id} ({user_type})")
    else:
        # Fallback: Thử đọc từ file Excel trực tiếp (cho trường hợp chạy trực tiếp)
        print("⚠️ Không có tham số dòng lệnh, thử tìm user từ hệ thống...")
        QMessageBox.warning(None, "Cảnh báo",
                            "Không tìm thấy thông tin đăng nhập hợp lệ.\nVui lòng chạy App.py để đăng nhập.")
        sys.exit(1)

    # 6. Tạo và hiển thị HomeWindow
    try:
        window = HomeWindow(user_id)
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