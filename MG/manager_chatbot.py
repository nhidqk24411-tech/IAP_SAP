#!/usr/bin/env python3
"""
Manager Chatbot - Chatbot version for manager
Interface synchronized with employee_chatbot
"""
import json
import sys
import os
import requests
from pathlib import Path
from datetime import datetime
import traceback

from MG.email_templates import EmailTemplates

# Add path to import from Chatbot directory
current_dir = os.path.dirname(os.path.abspath(__file__))
chatbot_dir = os.path.join(current_dir, '..', 'Chatbot')
if chatbot_dir not in sys.path:
    sys.path.append(chatbot_dir)

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import modules with try-except
try:
    from Chatbot.config import Config

    config_available = True
except ImportError:
    print("⚠️ Cannot import config.py")
    config_available = False
    Config = None

try:
    from Chatbot.gemini_analyzer import GeminiAnalyzer

    gemini_available = True
except ImportError as e:
    print(f"⚠️ Cannot import gemini_analyzer: {e}")
    gemini_available = False

# Import DataProcessor from MG directory
try:
    from MG.data_processor import DataProcessor

    dataprocessor_available = True
except ImportError as e:
    print(f"⚠️ Cannot import data_processor from MG: {e}")
    dataprocessor_available = False


class ManagerChatbotGUI(QMainWindow):
    """Manager Chatbot with synchronized interface"""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.n8n_webhook_url = "https://gain1109.app.n8n.cloud/webhook-test/349efadb-fad2-4589-9827-f99d94e3ac31"

        print("🤖 Initializing Manager Chatbot...")

        # Set to maximize
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Initialize Gemini Analyzer
        self.gemini = self.initialize_gemini()

        # Initialize Data Processor (no employee_name to manage all)
        self.data_processor = self.initialize_data_processor()

        # Store aggregate data
        self.aggregate_data = None
        self.all_employees_data = []

        # Email request state
        self.email_request_state = {
            'waiting_confirmation': False,
            'original_command': '',
            'email_type': None  # 'specific' or 'all'
        }

        # Application name
        if config_available and Config:
            app_name = Config.APP_NAME
        else:
            app_name = "PowerSight Manager Assistant"

        self.init_ui(app_name)

        # Load initial data
        QTimer.singleShot(1000, self.load_initial_data)

    # ========================== EMAIL CONFIRMATION SYSTEM ==========================

    def check_email_intent(self, user_input):
        """Phát hiện ý định gửi email từ câu nói"""
        user_input_lower = user_input.lower()

        # Các từ khóa phát hiện ý định gửi email
        email_keywords = [
            'gửi mail', 'gửi email', 'send email', 'email',
            'thông báo', 'notify', 'thông báo cho', 'inform',
            'email cho', 'gửi thư', 'mail cho', 'thông báo tới',
            'nhắn cho', 'liên hệ với', 'contact', 'send mail'
        ]

        # Kiểm tra từ khóa
        for keyword in email_keywords:
            if keyword in user_input_lower:
                return True

        # Kiểm tra mẫu câu phổ biến
        email_patterns = [
            'tôi muốn gửi',
            'mình muốn gửi',
            'cần gửi',
            'hãy gửi',
            'gửi cho',
            'thông báo đến',
            'thông báo tới',
            'mail tới',
            'email tới'
        ]

        for pattern in email_patterns:
            if pattern in user_input_lower:
                return True

        return False

    def extract_email_recipients(self, user_input):
        """Trích xuất thông tin người nhận từ câu nói (nếu có)"""
        user_input_lower = user_input.lower()

        # Phát hiện gửi cho tất cả
        all_keywords = ['tất cả', 'mọi người', 'toàn bộ', 'cả team', 'cả phòng', 'all', 'everyone']
        for keyword in all_keywords:
            if keyword in user_input_lower:
                return 'all'

        # Phát hiện gửi cho nhân viên cụ thể
        # Có thể phân tích tên nhân viên nếu có
        return 'specific'

    def handle_email_confirmation(self, user_input):
        """Xử lý phản hồi confirm của người dùng"""
        if not self.email_request_state['waiting_confirmation']:
            return False

        user_input_lower = user_input.lower()
        confirm_keywords = ['có', 'yes', 'y', 'ok', 'oke', 'okay', 'đồng ý', 'chắc chắn', 'được']
        deny_keywords = ['không', 'no', 'n', 'cancel', 'hủy', 'thôi', 'đừng']

        if any(keyword in user_input_lower for keyword in confirm_keywords):
            # Người dùng đồng ý
            self.add_bot_message("✅ Đã xác nhận. Đang mở cửa sổ chọn nhân viên...")
            self.email_request_state['waiting_confirmation'] = False
            QTimer.singleShot(500, self.open_employee_selection_dialog)
            return True
        elif any(keyword in user_input_lower for keyword in deny_keywords):
            # Người dùng từ chối
            self.add_bot_message("❌ Đã hủy yêu cầu gửi email.")
            self.email_request_state['waiting_confirmation'] = False
            self.send_button.setEnabled(True)
            return True

        return False

    def prompt_email_confirmation(self, user_input):
        """Hiển thị prompt xác nhận gửi email"""
        email_type = self.extract_email_recipients(user_input)

        if email_type == 'all':
            confirmation_msg = "⚠️ **XÁC NHẬN GỬI EMAIL**\n\nBạn có chắc chắn muốn gửi email cho TẤT CẢ nhân viên không?\n\nTrả lời: 'Có' hoặc 'Không'"
        else:
            confirmation_msg = "⚠️ **XÁC NHẬN GỬI EMAIL**\n\nBạn có muốn mở cửa sổ chọn nhân viên để gửi email không?\n\nTrả lời: 'Có' hoặc 'Không'"

        self.add_bot_message(confirmation_msg)

        # Lưu trạng thái
        self.email_request_state['waiting_confirmation'] = True
        self.email_request_state['original_command'] = user_input
        self.email_request_state['email_type'] = email_type

    # ========================== EMAIL FUNCTIONALITY ==========================

    def handle_email_request(self, user_input):
        """Xử lý yêu cầu gửi email - CHỈ GỌI KHI ĐÃ CONFIRM"""
        # Kiểm tra dữ liệu nhân viên
        if not self.data_processor:
            self.add_bot_message("❌ **KHÔNG CÓ DATA PROCESSOR**\n\nKhông thể truy cập dữ liệu nhân viên.")
            self.send_button.setEnabled(True)
            return

        employees = self.data_processor.get_employee_contact_info()
        if not employees:
            self.add_bot_message(
                "❌ **KHÔNG CÓ DỮ LIỆU NHÂN VIÊN**\n\nKhông thể tìm thấy thông tin nhân viên. Vui lòng kiểm tra file employee_ids.xlsx")
            self.send_button.setEnabled(True)
            return

        # Hiển thị dialog chọn nhân viên
        self.open_employee_selection_dialog()

    def open_employee_selection_dialog(self):
        """Mở dialog chọn nhân viên để gửi email"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📧 Gửi Email Cải Thiện Hiệu Suất")
        dialog.setFixedSize(700, 600)

        layout = QVBoxLayout(dialog)

        # Title
        title_label = QLabel("GỬI EMAIL CHO NHÂN VIÊN")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #1e40af;
            padding: 10px;
            background-color: #f0f9ff;
            border-radius: 8px;
            text-align: center;
        """)
        layout.addWidget(title_label)

        # Employee list
        employee_list_label = QLabel("📋 Chọn nhân viên nhận email:")
        employee_list_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(employee_list_label)

        self.employee_list_widget = QListWidget()
        self.employee_list_widget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.employee_list_widget.setStyleSheet("""
            QListWidget {
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #f1f5f9;
            }
            QListWidget::item:selected {
                background-color: #dbeafe;
                color: #1e40af;
            }
        """)

        # Load employees từ DataProcessor
        employees = self.data_processor.get_employee_contact_info()
        self.employee_data = {}  # Lưu trữ dữ liệu nhân viên

        for emp in employees:
            item_text = f"👤 {emp['name']}"
            if emp['id']:
                item_text += f" (ID: {emp['id']})"
            if emp['email']:
                item_text += f"\n   📧 {emp['email']}"
            if emp.get('department'):
                item_text += f" | {emp['department']}"

            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, emp['id'])
            self.employee_list_widget.addItem(item)
            self.employee_data[emp['id']] = emp

        # Select all button
        select_all_btn = QPushButton("✅ Chọn tất cả")
        select_all_btn.clicked.connect(lambda: self.employee_list_widget.selectAll())
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 5px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        layout.addWidget(select_all_btn)

        layout.addWidget(self.employee_list_widget)

        # Email subject
        subject_label = QLabel("✏️ Tiêu đề email:")
        subject_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(subject_label)

        self.email_subject = QLineEdit()
        self.email_subject.setText("Kế hoạch cải thiện hiệu suất công việc")
        self.email_subject.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #e2e8f0;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.email_subject)

        # Email content
        content_label = QLabel("📝 Nội dung email (có thể chỉnh sửa):")
        content_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        layout.addWidget(content_label)

        self.email_content = QTextEdit()

        # Nội dung mẫu dựa trên dữ liệu thực tế
        sample_content = """Kính gửi Anh/Chị,

Dựa trên phân tích hiệu suất công việc, chúng tôi đề xuất kế hoạch cải thiện sau:

🎯 TRỌNG TÂM CẢI THIỆN:
1. Tối ưu hóa quy trình làm việc
2. Nâng cao hiệu suất xử lý đơn hàng
3. Giảm thiểu lỗi và gian lận
4. Cải thiện tỷ suất lợi nhuận

📊 CHỈ SỐ MỤC TIÊU:
- Tăng hiệu suất: 15-20%
- Giảm lỗi: 30%
- Cải thiện tỷ lệ hoàn thành: 95%+

🛠️ BIỆN PHÁP:
• Tham gia đào tạo chuyên môn
• Áp dụng công cụ mới
• Tăng cường báo cáo và phản hồi
• Đánh giá định kỳ hàng tuần

📅 THỜI GIAN: 30 ngày tới
• Tuần 1-2: Triển khai và đào tạo
• Tuần 3-4: Thực hành và điều chỉnh
• Tuần 5: Đánh giá tổng kết

Chúng tôi sẽ hỗ trợ bạn trong suốt quá trình này. Vui lòng liên hệ nếu có bất kỳ thắc mắc nào.

Trân trọng,
Quản lý"""
        self.email_content.setPlainText(sample_content)
        self.email_content.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 5px;
                padding: 5px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.email_content)

        # Buttons
        button_layout = QHBoxLayout()

        test_btn = QPushButton("🧪 Gửi Test")
        test_btn.setToolTip("Gửi email test đến chính bạn để kiểm tra")
        test_btn.clicked.connect(lambda: self.send_test_email(dialog))
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #f59e0b;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #d97706;
            }
        """)

        send_btn = QPushButton("📤 Gửi Email")
        send_btn.clicked.connect(lambda: self.send_selected_emails(dialog))
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(dialog.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)

        button_layout.addWidget(test_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(send_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def send_test_email(self, dialog):
        """Gửi email test đến chính manager"""
        test_email = "gameyuno123@gmail.com"  # THAY ĐỔI THÀNH EMAIL CỦA BẠN

        # Tạo dữ liệu đơn giản hơn cho n8n
        test_data = {
            "test_mode": True,
            "timestamp": datetime.now().isoformat(),
            "to_email": test_email,
            "subject": f"TEST: {self.email_subject.text()}",
            "body": self.email_content.toPlainText(),
            "html_body": EmailTemplates.get_improvement_email_template(
                employee_name="Test User (Manager)",
                manager_name="Manager",
                recommendations=self.email_content.toPlainText(),
                employee_id="TEST001"
            )
        }

        # Gửi request đến n8n
        self.send_to_n8n(test_data, dialog, is_test=True)

    def send_selected_emails(self, dialog):
        """Gửi email cho nhân viên được chọn"""
        # Lấy danh sách ID nhân viên được chọn
        selected_ids = []
        for i in range(self.employee_list_widget.count()):
            item = self.employee_list_widget.item(i)
            if item.isSelected():
                emp_id = item.data(Qt.ItemDataRole.UserRole)
                selected_ids.append(emp_id)

        if not selected_ids:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một nhân viên!")
            return

        # Lấy thông tin chi tiết của nhân viên được chọn
        employees_info = self.data_processor.get_employee_contact_info(selected_ids)

        # Chuẩn bị dữ liệu gửi đến n8n - Dạng đơn giản cho từng email
        email_data = {
            "test_mode": False,
            "timestamp": datetime.now().isoformat(),
            "emails": []
        }

        for emp in employees_info:
            if not emp.get('email'):
                print(f"⚠️ Nhân viên {emp['name']} không có email, bỏ qua")
                continue

            email_data["emails"].append({
                "to_email": emp['email'],
                "subject": self.email_subject.text(),
                "body": self.email_content.toPlainText(),
                "cc": "legalgiang@gmai.com",
                "employee_name": emp['name'],
                "employee_id": emp['id'],
                "html_body": EmailTemplates.get_improvement_email_template(
                    employee_name=emp['name'],
                    manager_name="Manager",
                    recommendations=self.email_content.toPlainText(),
                    employee_id=emp['id']
                )
            })

        if not email_data["emails"]:
            QMessageBox.warning(self, "Cảnh báo", "Không có nhân viên nào có địa chỉ email hợp lệ!")
            return

        # Gửi request đến n8n
        self.send_to_n8n(email_data, dialog, is_test=False)

    def send_to_n8n(self, email_data, dialog, is_test=False):
        """Gửi dữ liệu đến n8n webhook với cấu trúc đơn giản"""
        try:
            self.status_bar.setText("📤 Đang gửi email...")

            # Gửi từng email riêng biệt để n8n xử lý dễ dàng hơn
            if is_test:
                # Test mode - gửi 1 email
                response = requests.post(
                    self.n8n_webhook_url,
                    json=email_data,
                    headers={'Content-Type': 'application/json'},
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    self.add_bot_message("✅ **ĐÃ GỬI EMAIL TEST THÀNH CÔNG!**\n\nVui lòng kiểm tra hộp thư của bạn.")
                    dialog.accept()
                else:
                    error_msg = f"❌ **LỖI GỬI EMAIL TEST**\n\nMã lỗi: {response.status_code}\nChi tiết: {response.text[:200]}"
                    self.add_bot_message(error_msg)
            else:
                # Production mode - gửi từng email
                success_count = 0
                error_count = 0

                for email_item in email_data["emails"]:
                    try:
                        # Tạo payload đơn giản cho từng email
                        payload = {
                            "test_mode": False,
                            "timestamp": datetime.now().isoformat(),
                            "to_email": email_item["to_email"],
                            "subject": email_item["subject"],
                            "body": email_item["body"],
                            "html_body": email_item["html_body"],
                            "cc": email_item.get("cc", ""),
                            "employee_name": email_item["employee_name"],
                            "employee_id": email_item["employee_id"]
                        }

                        response = requests.post(
                            self.n8n_webhook_url,
                            json=payload,
                            headers={'Content-Type': 'application/json'},
                            timeout=30
                        )

                        if response.status_code in [200, 201]:
                            success_count += 1
                        else:
                            error_count += 1
                            print(f"❌ Lỗi gửi email cho {email_item['employee_name']}: {response.status_code}")

                    except Exception as e:
                        error_count += 1
                        print(f"❌ Exception khi gửi email cho {email_item['employee_name']}: {e}")

                # Hiển thị kết quả
                if success_count > 0:
                    message = f"✅ **ĐÃ GỬI {success_count}/{len(email_data['emails'])} EMAIL THÀNH CÔNG!**\n\n"
                    if error_count > 0:
                        message += f"⚠️ Có {error_count} email gửi thất bại.\n"
                    self.add_bot_message(message)

                    QMessageBox.information(self, "Thành công",
                                            f"Đã gửi {success_count} email thành công! {f'Có {error_count} lỗi.' if error_count > 0 else ''}")
                    dialog.accept()
                else:
                    error_msg = "❌ **KHÔNG GỬI ĐƯỢC EMAIL NÀO**\n\nVui lòng kiểm tra kết nối n8n."
                    self.add_bot_message(error_msg)
                    QMessageBox.critical(self, "Lỗi", "Không thể gửi email. Vui lòng kiểm tra kết nối n8n.")

        except requests.exceptions.ConnectionError:
            error_msg = "❌ **KHÔNG THỂ KẾT NỐI ĐẾN n8n**\n\nKiểm tra:\n1. n8n có đang chạy không?\n2. URL webhook có đúng không?\n3. Internet connection"
            self.add_bot_message(error_msg)
            QMessageBox.critical(self, "Lỗi kết nối", "Không thể kết nối đến máy chủ n8n.")

        except Exception as e:
            error_msg = f"❌ **LỖI HỆ THỐNG**\n\n{str(e)}"
            self.add_bot_message(error_msg)
            QMessageBox.critical(self, "Lỗi hệ thống", f"Lỗi: {str(e)}")

        finally:
            self.status_bar.setText("✅ Sẵn sàng")
            self.send_button.setEnabled(True)

    # ========================== CHAT FUNCTIONALITY ==========================

    def initialize_gemini(self):
        """Initialize Gemini Analyzer"""
        if gemini_available:
            try:
                # Load environment variables first (if .env file exists)
                self.load_env()
                # Initialize GeminiAnalyzer without parameters
                gemini = GeminiAnalyzer()
                print("✅ Initialized Gemini Analyzer")
                return gemini
            except Exception as e:
                print(f"⚠️ Error initializing Gemini: {e}")
        print("⚠️ Gemini not available, using simple mode")
        return None

    def initialize_data_processor(self):
        """Initialize Data Processor"""
        if dataprocessor_available:
            try:
                # Initialize DataProcessor without employee_name to manage all
                data_processor = DataProcessor()
                print("✅ Initialized Data Processor for manager")
                return data_processor
            except Exception as e:
                print(f"⚠️ Error initializing Data Processor: {e}")
        return None

    def load_env(self):
        """Load environment variables from .env file"""
        try:
            from dotenv import load_dotenv
            # Determine .env file path
            env_path = Path("C:/Users/legal/PycharmProjects/PythonProject/Chatbot/.env")
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
            else:
                load_dotenv()

            # Check API key
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                print(f"✅ Loaded API key from .env")
            else:
                print("⚠️ GEMINI_API_KEY not found in .env")
            return api_key
        except Exception as e:
            print(f"⚠️ Cannot load .env file: {e}")
            return None

    def init_ui(self, app_name):
        """Initialize interface synchronized with employee_chatbot"""
        self.setWindowTitle(f"💬 {app_name} - Manager Chat")
        self.setGeometry(200, 200, 700, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Status indicator
        self.status_indicator = QLabel("●" if self.gemini else "○")
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                color: {"#10b981" if self.gemini else "#ef4444"};
                font-size: 20px;
                font-weight: bold;
            }}
        """)

        title_label = QLabel(f"💬 MANAGER SUPPORT CHATBOT - {app_name}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1e40af;
            }
        """)

        # Home button
        home_btn = QPushButton("Home")
        home_btn.setFixedSize(100, 35)
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        if self.controller:
            home_btn.clicked.connect(lambda: self.controller.show_home())

        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(home_btn)

        layout.addWidget(header_widget)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet("""
            QTextEdit {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 15px;
                font-size: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        layout.addWidget(self.chat_display, 1)

        # Input area
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter questions about team performance, revenue, analysis...")
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 12px;
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 12px;
            }
            QLineEdit:focus {
                border: 2px solid #3b82f6;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)

        self.send_button = QPushButton("Send")
        self.send_button.setFixedSize(100, 40)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: #cbd5e1;
                color: #64748b;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        self.send_button.setEnabled(False)

        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.send_button)

        layout.addWidget(input_widget)

        # Quick actions - Manager specific
        quick_actions_widget = QWidget()
        quick_layout = QHBoxLayout(quick_actions_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(10)

        quick_buttons = [
            ("📊 Team analysis", "analyze overall team performance"),
            ("💰 Team revenue", "team revenue this month"),
            ("⚠️ Team fraud", "fraud events in team"),
            ("👥 Compare employees", "compare performance between employees"),
            ("🎯 Training recommendations", "training recommendations for team"),
            ("📧 Send emails", lambda: self.handle_quick_action_email()),
            ("🔄 Reload data", self.load_initial_data)
        ]

        for text, command in quick_buttons:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #f1f5f9;
                    color: #475569;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 8px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #e2e8f0;
                }
            """)
            if callable(command):
                btn.clicked.connect(command)
            else:
                btn.clicked.connect(lambda checked, cmd=command: self.quick_command(cmd))
            quick_layout.addWidget(btn)

        layout.addWidget(quick_actions_widget)

        # Status bar
        self.status_bar = QLabel(f"Status: Initializing...")
        self.status_bar.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                padding: 8px;
                background-color: #f8fafc;
                border-radius: 5px;
                border: 1px solid #e2e8f0;
            }
        """)
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_bar)

        # Display welcome message
        self.add_bot_message("Hello Manager! I'm the performance analysis support chatbot.")
        self.add_bot_message("I can help you with:")
        self.add_bot_message("• Overall team performance analysis")
        self.add_bot_message("• Employee comparison")
        self.add_bot_message("• Training and improvement recommendations")
        self.add_bot_message("• Risk management and bottlenecks")
        self.add_bot_message("• Sending emails to employees (use 'send email' or click 📧 button)")

        if not self.gemini:
            self.add_bot_message(
                "⚠️ **Note**: Gemini AI is not available. Using DEMO mode.")

    def handle_quick_action_email(self):
        """Xử lý quick action email button"""
        self.prompt_email_confirmation("gửi email cho nhân viên")

    def add_bot_message(self, message):
        """Add message from bot"""
        timestamp = datetime.now().strftime("%H:%M")
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #f1f5f9; border-radius: 8px;'>"
            f"<b>🤖 Manager AI:</b> {formatted_message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def add_user_message(self, message):
        """Add message from user"""
        timestamp = datetime.now().strftime("%H:%M")
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #dbeafe; border-radius: 8px; text-align: right;'>"
            f"<b>👤 Manager:</b> {formatted_message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Scroll to bottom"""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def quick_command(self, command):
        """Handle quick command"""
        self.input_field.setText(command)
        self.send_message()

    def load_initial_data(self):
        """Load initial data - Multi-employee for manager"""
        self.status_indicator.setText("🔄")
        self.status_bar.setText("📂 Reading aggregate data...")
        self.send_button.setEnabled(False)

        try:
            if not self.data_processor:
                self.status_indicator.setText("○")
                self.status_bar.setText("❌ DataProcessor not available")
                self.send_button.setEnabled(True)
                self.add_bot_message("⚠️ DataProcessor not available. Using demo mode.")
                return

            # Load aggregate data from all employees
            print("📊 Manager: Loading aggregate data...")
            current_year = datetime.now().year
            self.aggregate_data = self.data_processor.load_aggregate_data(current_year)

            if self.aggregate_data:
                self.status_indicator.setText("●")
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        color: #10b981;
                        font-size: 20px;
                        font-weight: bold;
                    }
                """)

                self.send_button.setEnabled(True)

                # Display aggregate report
                self.show_manager_summary()

                # Debug: Show data summary
                self.debug_show_data_summary()
            else:
                self.status_indicator.setText("○")
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        color: #ef4444;
                        font-size: 20px;
                        font-weight: bold;
                    }
                """)
                self.status_bar.setText("❌ Cannot load aggregate data")
                self.send_button.setEnabled(True)
                self.add_bot_message("⚠️ Cannot load aggregate data. Please check data connection.")

        except Exception as e:
            print(f"❌ Error loading manager data: {e}")
            traceback.print_exc()
            self.status_indicator.setText("○")
            self.status_bar.setText(f"Error: {str(e)[:50]}")
            self.send_button.setEnabled(True)
            self.add_bot_message(f"❌ Error loading data: {str(e)}")

    def debug_show_data_summary(self):
        """Debug: Hiển thị tóm tắt dữ liệu"""
        if not self.aggregate_data:
            print("❌ No aggregate data")
            return

        print("\n" + "=" * 70)
        print("📊 AGGREGATE DATA SUMMARY (DEBUG)")
        print("=" * 70)

        print(f"Total Employees: {self.aggregate_data.get('total_employees', 0)}")
        print(f"With Data: {self.aggregate_data.get('employees_with_data', 0)}")
        print(f"Total Revenue (Year): {self.aggregate_data.get('total_revenue', 0):,.0f} VND")
        print(f"Total Profit (Year): {self.aggregate_data.get('total_profit', 0):,.0f} VND")

        monthly_data = self.aggregate_data.get('monthly_data', {})
        revenues = monthly_data.get('revenue', [])
        orders = monthly_data.get('orders', [])

        print("\n📈 MONTHLY BREAKDOWN:")
        for i in range(12):
            if i < len(revenues) and revenues[i] > 0:
                print(f"  Month {i + 1}: {revenues[i]:,.0f} VND | {orders[i] if i < len(orders) else 0} orders")

        print("\n" + "=" * 70)

    def show_manager_summary(self):
        """Display aggregate report for manager"""
        if not self.aggregate_data:
            return

        total_employees = self.aggregate_data.get('total_employees', 0)
        employees_with_data = self.aggregate_data.get('employees_with_data', 0)
        total_revenue = self.aggregate_data.get('total_revenue', 0)
        total_profit = self.aggregate_data.get('total_profit', 0)
        total_fraud = self.aggregate_data.get('total_fraud', 0)
        avg_completion = self.aggregate_data.get('average_completion_rate', 0)
        avg_score = self.aggregate_data.get('average_overall_score', 0)

        # Get current month data
        monthly_data = self.aggregate_data.get('monthly_data', {})
        current_month = datetime.now().month
        revenues = monthly_data.get('revenue', [0] * 12)
        current_month_revenue = revenues[current_month - 1] if current_month <= len(revenues) else 0

        # Update status bar
        self.status_bar.setText(
            f"👥 {total_employees} Emp | "
            f"💰 Year: {total_revenue:,.0f} VND | Month {current_month}: {current_month_revenue:,.0f} VND | "
            f"⚠️ {total_fraud} fraud"
        )

        summary = f"""**📊 TEAM OVERVIEW REPORT**

**📅 Time:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

**📈 AGGREGATE STATISTICS (YEAR {datetime.now().year}):**
- Total employees: {total_employees}
- With data: {employees_with_data} ({employees_with_data / total_employees * 100:.1f}% if have data)
- Total revenue (year): {total_revenue:,.0f} VND
- Total profit (year): {total_profit:,.0f} VND
- Total revenue (month {current_month}): {current_month_revenue:,.0f} VND
- Fraud events: {total_fraud}
- Average completion rate: {avg_completion:.1f}%
- Average overall score: {avg_score:.1f}/100

**🎯 SAMPLE QUESTIONS:**
- "Analyze overall team performance?"
- "Which employees have performance issues?"
- "What are the main workflow bottlenecks?"
- "What training does the team need?"
- "Team revenue this month"
- "Compare performance between employees"
- "Send email to employees" """

        self.add_bot_message(summary)

    def send_message(self):
        """Handle user message"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        # Add user message to chat
        self.add_user_message(user_input)
        self.input_field.clear()

        # Kiểm tra nếu đang chờ confirm
        if self.email_request_state['waiting_confirmation']:
            if self.handle_email_confirmation(user_input):
                return

        # Kiểm tra nếu là lệnh gửi email
        if self.check_email_intent(user_input):
            self.prompt_email_confirmation(user_input)
            return

        # Nếu không phải lệnh email, xử lý bình thường
        self.send_button.setEnabled(False)
        self.status_bar.setText("🤔 AI đang phân tích...")

        # Tạo data context
        context_data = self.get_manager_data_context()

        # Process with thread to not block UI
        self.chat_thread = ManagerChatThread(self.gemini, user_input, context_data)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def on_ai_response(self, response):
        """Receive AI response"""
        self.add_bot_message(response)
        self.send_button.setEnabled(True)
        self.status_bar.setText("✅ Ready")

    def on_ai_error(self, error):
        """Handle AI error"""
        error_msg = f"""**❌ SYSTEM ERROR**

Cannot connect to AI service:

**Details:** {error}

**DEMO mode will be used temporarily.**"""

        self.add_bot_message(error_msg)
        self.send_button.setEnabled(True)
        self.status_bar.setText("⚠️ Error occurred")

    def get_manager_data_context(self):
        """Get special data context for manager as dictionary - FIXED VERSION"""
        if not self.aggregate_data:
            return {
                "status": "no_data",
                "summary": "No aggregate data yet",
                "employee_name": "Manager",
                "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

        # Lấy dữ liệu tháng hiện tại từ monthly_data
        monthly_data = self.aggregate_data.get('monthly_data', {})
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Tính revenue tháng này (index = current_month - 1)
        revenues = monthly_data.get('revenue', [0] * 12)
        current_month_revenue = revenues[current_month - 1] if current_month <= len(revenues) else 0

        # Tính orders tháng này
        orders = monthly_data.get('orders', [0] * 12)
        current_month_orders = orders[current_month - 1] if current_month <= len(orders) else 0

        # Tính fraud tháng này
        frauds = monthly_data.get('fraud', [0] * 12)
        current_month_fraud = frauds[current_month - 1] if current_month <= len(frauds) else 0

        # Tính profit tháng này
        profits = monthly_data.get('profit', [0] * 12)
        current_month_profit = profits[current_month - 1] if current_month <= len(profits) else 0

        # Create comprehensive context similar to employee chatbot
        return {
            "status": "ok",
            "employee_name": "Manager (Team Overview)",
            "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

            # Metrics - Tháng hiện tại
            "metrics": {
                "total_orders": int(current_month_orders),
                "completed_orders": int(current_month_orders * 0.95),  # Giả định 95% completion
                "pending_orders": int(current_month_orders * 0.05),
                "completion_rate": 95.0,
                "total_revenue": float(current_month_revenue),
                "total_profit": float(current_month_profit),
                "fraud_count": int(current_month_fraud),
                "profit_margin": (
                        current_month_profit / current_month_revenue * 100) if current_month_revenue > 0 else 0,
                "on_time_delivery": 95.0
            },

            # Summary - Cả năm
            "summary": {
                "total_employees": self.aggregate_data.get('total_employees', 0),
                "employees_with_data": self.aggregate_data.get('employees_with_data', 0),
                "total_revenue": self.aggregate_data.get('total_revenue', 0),
                "total_profit": self.aggregate_data.get('total_profit', 0),
                "total_fraud": self.aggregate_data.get('total_fraud', 0),
                "average_completion_rate": self.aggregate_data.get('average_completion_rate', 0),
                "average_overall_score": self.aggregate_data.get('average_overall_score', 0)
            },

            # Year data - Dữ liệu cả năm
            "year_data": {
                "summary": {
                    "year": current_year,
                    "months_with_data": 12,
                    "total_orders": sum(orders),
                    "total_revenue": sum(revenues),
                    "total_profit": sum(profits),
                    "total_fraud": sum(frauds),
                    "completion_rate": 95.0,
                    "best_month": revenues.index(max(revenues)) + 1 if revenues and max(revenues) > 0 else 0,
                    "best_month_revenue": max(revenues) if revenues else 0
                }
            },

            # SAP data structure
            "sap_data": {
                "summary": {
                    "total_orders": int(current_month_orders),
                    "completed_orders": int(current_month_orders * 0.95),
                    "pending_orders_count": int(current_month_orders * 0.05),
                    "total_revenue": float(current_month_revenue),
                    "total_profit": float(current_month_profit),
                    "pending_orders": []  # Không cần chi tiết đơn hàng cho manager
                }
            },

            # Work log data
            "work_log": {
                "summary": {
                    "fraud_count": int(current_month_fraud),
                    "total_work_hours": 160 * self.aggregate_data.get('employees_with_data', 0),
                    # Ước tính 160h/người/tháng
                    "critical_count": int(current_month_fraud * 0.3)  # Giả định 30% là critical
                }
            },

            "employees": self.get_employee_list() if self.data_processor else [],
            "is_manager": True  # Flag for Gemini to know this is manager view
        }

    def get_employee_list(self):
        """Get employee list"""
        try:
            if self.data_processor:
                employees = self.data_processor.get_all_employees()
                return employees[:10]  # Limit 10 employees
        except Exception as e:
            print(f"Error getting employee list: {e}")
        return []


class ManagerChatThread(QThread):
    """Thread handling chat for manager"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, gemini, question, context_data):
        super().__init__()
        self.gemini = gemini
        self.question = question
        self.context_data = context_data

    def run(self):
        try:
            if not self.gemini:
                # DEMO mode for manager
                import random
                demo_responses = [
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Hiệu suất team hiện ổn định. Tập trung vào nhân viên có tỷ lệ hoàn thành thấp để cải thiện.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Dữ liệu team cho thấy cần giảm sự kiện gian lận. Cân nhắc đào tạo tuân thủ cho toàn team.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Doanh thu team đang phát triển tốt. Tập trung vào nhân viên hiệu suất cao để nhân rộng thành công.",
                ]
                response = random.choice(demo_responses)
                self.response_ready.emit(response)
                return

            # Use Gemini for analysis - ensure context_data is dictionary
            if isinstance(self.context_data, dict):
                response = self.gemini.analyze_question(self.question, self.context_data)
            else:
                # If not dictionary, create simple dictionary
                response = self.gemini.analyze_question(self.question, {"data": str(self.context_data)})

            self.response_ready.emit(response)
        except Exception as e:
            print(f"Error in ManagerChatThread: {e}")
            traceback.print_exc()
            self.error_occurred.emit(str(e))


def main():
    """Function to run chatbot separately"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    chatbot = ManagerChatbotGUI()
    chatbot.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()