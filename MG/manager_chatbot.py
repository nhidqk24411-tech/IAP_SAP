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
import re
from datetime import datetime, timedelta
import traceback
import pandas as pd

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
        self.n8n_webhook_url = "http://localhost:5678/webhook/349efadb-fad2-4589-9827-f99d94e3ac31"
        self.n8n_summary_webhook_url = "http://localhost:5678/webhook/smr119966"

        # Initialize variables
        self.summary_thread = None
        self.custom_email_templates = []
        self.selected_employee_ids = []
        self.current_email_type = "improvement"
        self.custom_email_description = ""
        self.current_email_description = ""
        self.manager_info = {}

        # Load manager info
        self.load_manager_info()

        print("🤖 Initializing Manager Chatbot...")

        # Set to maximize
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Initialize Gemini Analyzer
        self.gemini = self.initialize_gemini()

        # Initialize Data Processor
        self.data_processor = self.initialize_data_processor()

        # Store aggregate data
        self.aggregate_data = None
        self.all_employees_data = []

        # Email request state
        self.email_request_state = {
            'waiting_confirmation': False,
            'original_command': '',
            'email_type': None
        }

        # Application name
        if config_available and Config:
            app_name = Config.APP_NAME
        else:
            app_name = "PowerSight Manager Assistant"

        self.init_ui(app_name)

        # Load initial data
        QTimer.singleShot(1000, self.load_initial_data)

    def load_manager_info(self):
        """Tải thông tin quản lý từ file employee_ids.xlsx"""
        try:
            root_path = Path(__file__).resolve().parent.parent
            excel_path = root_path / "employee_ids.xlsx"

            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)

                # Chuẩn hóa tên cột
                df.columns = [str(col).strip().lower() for col in df.columns]

                # Tìm cột ID
                id_column = None
                for col in df.columns:
                    if col == 'id' or 'employee' in col or 'mã' in col:
                        id_column = col
                        break

                if id_column:
                    # Tìm hàng có mã trùng với manager_id
                    manager_id = self.controller.user_id if self.controller else "MG001"

                    for idx, row in df.iterrows():
                        current_id = str(row[id_column]).strip().upper() if not pd.isna(row[id_column]) else ""
                        if current_id == manager_id.upper():
                            # Lấy thông tin quản lý
                            self.manager_info = {
                                'id': manager_id,
                                'name': str(row.get('full_name',
                                                    manager_id)).strip() if 'full_name' in df.columns and not pd.isna(
                                    row.get('full_name')) else manager_id,
                                'email': str(row.get('email', '')).strip() if 'email' in df.columns and not pd.isna(
                                    row.get('email')) else '',
                                'sap': str(row.get('sap', '')).strip() if 'sap' in df.columns and not pd.isna(
                                    row.get('sap')) else '',
                                'client': str(row.get('client', '')).strip() if 'client' in df.columns and not pd.isna(
                                    row.get('client')) else ''
                            }
                            print(f"✅ Loaded manager info: {self.manager_info}")
                            return

                # Nếu không tìm thấy, tạo thông tin mặc định
                self.manager_info = {
                    'id': manager_id,
                    'name': 'Quản lý',
                    'email': 'legalgiang@gmail.com',
                    'sap': '',
                    'client': ''
                }

        except Exception as e:
            print(f"⚠️ Error loading manager info: {e}")
            self.manager_info = {
                'id': self.controller.user_id if self.controller else 'MG001',
                'name': 'Quản lý',
                'email': 'legalgiang@gmail.com',
                'sap': '',
                'client': ''
            }

    def check_summary_email_intent(self, user_input):
        """Phát hiện ý định tổng hợp email từ nhân viên"""
        user_input_lower = user_input.lower()

        summary_keywords = [
            'tổng hợp mail', 'tổng hợp email', 'mail nhân viên gửi',
            'email nhân viên gửi', 'gửi mail tổng hợp', 'gửi email tổng hợp',
            'thống kê mail', 'thống kê email', 'mail đã nhận', 'email đã nhận',
            'nhân viên gửi mail', 'nhân viên gửi email', 'tập hợp mail',
            'tập hợp email', 'báo cáo mail', 'báo cáo email'
        ]

        for keyword in summary_keywords:
            if keyword in user_input_lower:
                return True

        summary_patterns = [
            'tôi muốn tổng hợp',
            'mình muốn tổng hợp',
            'cần tổng hợp',
            'hãy tổng hợp',
            'tổng hợp cho tôi',
            'gửi tôi tổng hợp',
            'tổng kết mail',
            'tổng kết email'
        ]

        for pattern in summary_patterns:
            if pattern in user_input_lower and any(word in user_input_lower for word in ['mail', 'email']):
                return True

        return False

    def handle_summary_email_request(self, user_input):
        """Xử lý yêu cầu tổng hợp email từ nhân viên"""
        try:
            print(f"🚀 Kích hoạt workflow n8n: {user_input}")
            self.add_bot_message("📊 **ĐANG KÍCH HOẠT WORKFLOW TỔNG HỢP EMAIL**\n\nWorkflow n8n đang được kích hoạt...")

            # Tạo payload với thông tin quản lý
            payload = {
                "action": "summarize_emails",
                "timestamp": datetime.now().isoformat(),
                "request": user_input,
                "manager_request": True,
                "manager_id": self.manager_info.get('id', 'MG001'),
                "manager_name": self.manager_info.get('name', 'Quản lý'),
                "manager_email": self.manager_info.get('email', 'legalgiang@gmail.com'),
                "test_mode": False,
                "summary_type": "employee_feedback"
            }

            self.status_bar.setText("⚡ Đang kích hoạt workflow...")

            # Tạo và lưu thread
            self.summary_thread = SummaryEmailThread(self.n8n_summary_webhook_url, payload)
            self.summary_thread.response_received.connect(self.on_summary_response_simple)
            self.summary_thread.error_occurred.connect(self.on_summary_error_simple)
            self.summary_thread.start()

        except Exception as e:
            print(f"⚠️ Lỗi kích hoạt workflow: {e}")
            self.status_bar.setText("✅ Đã kích hoạt workflow (async)")

    def on_summary_response_simple(self, response_data):
        """Xử lý phản hồi đơn giản"""
        try:
            print(f"✅ Workflow response: {response_data}")

            if isinstance(response_data, dict):
                status = response_data.get('status', 'unknown')
                message = response_data.get('message', '')

                if status == 'success':
                    summary = response_data.get('summary', 'Không có tóm tắt')
                    email_count = response_data.get('email_count', 0)

                    self.add_bot_message(f"✅ **ĐÃ TỔNG HỢP EMAIL THÀNH CÔNG**\n\n"
                                         f"• Số email đã xử lý: {email_count}\n"
                                         f"• Đã gửi kết quả đến: {self.manager_info.get('email', 'legalgiang@gmail.com')}\n"
                                         f"• Trạng thái: {message}")
                    self.status_bar.setText(f"✅ Đã tổng hợp {email_count} email")
                else:
                    self.add_bot_message(f"⚠️ **HỆ THỐNG TỔNG HỢP EMAIL**\n\n"
                                         f"Trạng thái: {status}\n"
                                         f"Thông báo: {message}")
                    self.status_bar.setText("⚠️ Hệ thống tổng hợp email trả về lỗi")
            else:
                self.add_bot_message(
                    f"📊 **KẾT QUẢ TỔNG HỢP EMAIL**\n\nĐã gửi kết quả đến email quản lý: {self.manager_info.get('email', 'legalgiang@gmail.com')}")
                self.status_bar.setText("✅ Đã nhận kết quả tổng hợp")

        except Exception as e:
            print(f"❌ Lỗi xử lý phản hồi tổng hợp: {e}")
            self.add_bot_message("✅ **ĐÃ KÍCH HOẠT WORKFLOW**\n\nHệ thống đang tổng hợp email từ nhân viên.")
            self.status_bar.setText("✅ Đã kích hoạt workflow")

    def on_summary_error_simple(self, error_message):
        """Xử lý lỗi đơn giản"""
        print(f"⚠️ Lỗi kích hoạt workflow: {error_message}")
        self.add_bot_message("⚠️ **CÓ THỂ CÓ LỖI KẾT NỐI**\n\nNhưng workflow đã được kích hoạt.")
        self.status_bar.setText("⚠️ Workflow đã kích hoạt")

    def check_email_intent(self, user_input):
        """Phát hiện ý định gửi email từ câu nói"""
        user_input_lower = user_input.lower()

        email_keywords = [
            'gửi mail', 'gửi email', 'send email', 'email',
            'thông báo', 'notify', 'thông báo cho', 'inform',
            'email cho', 'gửi thư', 'mail cho', 'thông báo tới',
            'nhắn cho', 'liên hệ với', 'contact', 'send mail',
            'phàn nàn', 'khiếu nại', 'đề xuất', 'kiến nghị',
            'nhắc nhở', 'cảnh báo', 'khen ngợi', 'cải thiện',
            'báo cáo', 'report', 'feedback', 'đánh giá'
        ]

        for keyword in email_keywords:
            if keyword in user_input_lower:
                return True

        email_patterns = [
            'tôi muốn gửi',
            'mình muốn gửi',
            'cần gửi',
            'hãy gửi',
            'gửi cho',
            'thông báo đến',
            'thông báo tới',
            'mail tới',
            'email tới',
            'soạn mail',
            'soạn email',
            'tạo mail',
            'tạo email'
        ]

        for pattern in email_patterns:
            if pattern in user_input_lower:
                return True

        employee_ids = self.extract_employee_ids_from_message(user_input)
        if employee_ids:
            communication_keywords = ['cho', 'với', 'về', 'đến', 'tới']
            if any(keyword in user_input_lower for keyword in communication_keywords):
                return True

        return False

    def detect_email_type_and_description(self, user_input):
        """Phát hiện loại email và trích xuất mô tả từ câu nói"""
        user_input_lower = user_input.lower()

        email_type_patterns = [
            ('complaint', ['phàn nàn về', 'khiếu nại về', 'than phiền về', 'tố cáo về']),
            ('suggestion', ['đề xuất về', 'kiến nghị về', 'ý kiến về', 'góp ý về']),
            ('reminder', ['nhắc nhở về', 'nhắc việc về', 'nhắc deadline', 'hạn chót']),
            ('warning', ['cảnh báo về', 'cảnh cáo về', 'đe dọa về', 'cảnh tỉnh về']),
            ('praise', ['khen ngợi về', 'khen thưởng về', 'biểu dương về', 'tuyên dương về']),
            ('improvement', ['cải thiện về', 'hiệu suất về', 'đánh giá về', 'performance về']),
            ('complaint', ['phàn nàn', 'khiếu nại', 'than phiền', 'tố cáo']),
            ('suggestion', ['đề xuất', 'kiến nghị', 'ý kiến', 'góp ý']),
            ('reminder', ['nhắc nhở', 'reminder']),
            ('warning', ['cảnh báo', 'cảnh cáo', 'warning']),
            ('praise', ['khen ngợi', 'khen thưởng', 'biểu dương']),
            ('improvement', ['cải thiện', 'hiệu suất', 'đánh giá'])
        ]

        detected_type = 'general'
        description = user_input

        for email_type, patterns in email_type_patterns:
            for pattern in patterns:
                if pattern in user_input_lower:
                    detected_type = email_type
                    pattern_index = user_input_lower.find(pattern)
                    if pattern_index != -1:
                        after_keyword = user_input[pattern_index + len(pattern):].strip()
                        if after_keyword and len(after_keyword) > 3:
                            description = after_keyword
                    break
            if detected_type != 'general':
                break

        if 'gửi' in user_input_lower and detected_type == 'general':
            detected_type = 'reminder'

        return detected_type, description

    def extract_email_recipients(self, user_input):
        """Trích xuất thông tin người nhận từ câu nói (nếu có)"""
        user_input_lower = user_input.lower()

        all_keywords = ['tất cả', 'mọi người', 'toàn bộ', 'cả team', 'cả phòng', 'all', 'everyone']
        for keyword in all_keywords:
            if keyword in user_input_lower:
                return 'all'

        return 'specific'

    def handle_email_confirmation(self, user_input):
        """Xử lý phản hồi confirm của người dùng"""
        if not self.email_request_state['waiting_confirmation']:
            return False

        user_input_lower = user_input.lower()
        confirm_keywords = ['có', 'yes', 'y', 'ok', 'oke', 'okay', 'đồng ý', 'chắc chắn', 'được']
        deny_keywords = ['không', 'no', 'n', 'cancel', 'hủy', 'thôi', 'đừng']

        if any(keyword in user_input_lower for keyword in confirm_keywords):
            self.add_bot_message("✅ Đã xác nhận. Đang mở cửa sổ chọn nhân viên...")
            self.email_request_state['waiting_confirmation'] = False
            QTimer.singleShot(500, lambda: self.open_employee_selection_dialog())
            return True
        elif any(keyword in user_input_lower for keyword in deny_keywords):
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

        self.email_request_state['waiting_confirmation'] = True
        self.email_request_state['original_command'] = user_input
        self.email_request_state['email_type'] = email_type

    def handle_email_request(self, user_input):
        """Xử lý yêu cầu gửi email - Mở dialog chọn nhân viên ngay"""
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

        self.open_employee_selection_dialog()

        self.add_bot_message("✅ **ĐÃ MỞ CỬA SỔ CHỌN NHÂN VIÊN**\n\nVui lòng chọn nhân viên và tạo nội dung email.")

    def open_employee_selection_dialog(self, auto_select_ids=None, email_type="improvement", custom_description=""):
        """Mở dialog chọn nhân viên để gửi email"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"📧 Gửi Email - {email_type.upper()}")
            dialog.setMinimumSize(900, 750)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)

            # Title
            title_label = QLabel(f"CHỌN NHÂN VIÊN ĐỂ GỬI EMAIL ({email_type.upper()})")
            title_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #1e40af;
                padding: 15px;
                background-color: #f0f9ff;
                border-radius: 8px;
                text-align: center;
            """)
            layout.addWidget(title_label)

            # Filter section
            filter_widget = QWidget()
            filter_layout = QHBoxLayout(filter_widget)
            filter_layout.setContentsMargins(0, 0, 0, 0)

            year_label = QLabel("Năm:")
            year_combo = QComboBox()
            current_year = datetime.now().year
            for year in range(current_year - 2, current_year + 1):
                year_combo.addItem(str(year))
            year_combo.setCurrentText(str(current_year))

            month_label = QLabel("Tháng:")
            month_combo = QComboBox()
            month_combo.addItem("Tất cả")
            for month in range(1, 13):
                month_combo.addItem(f"Tháng {month}")

            filter_layout.addWidget(year_label)
            filter_layout.addWidget(year_combo)
            filter_layout.addSpacing(20)
            filter_layout.addWidget(month_label)
            filter_layout.addWidget(month_combo)
            filter_layout.addStretch()

            layout.addWidget(filter_widget)

            # Employee table
            employee_table_label = QLabel("📋 Danh sách nhân viên (EM):")
            employee_table_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            layout.addWidget(employee_table_label)

            employee_table = QTableWidget()
            employee_table.setColumnCount(7)
            employee_table.setHorizontalHeaderLabels(["Chọn", "Mã NV", "Họ Tên", "Email", "SAP", "Client", "Điểm"])

            employee_table.setColumnWidth(0, 50)
            employee_table.setColumnWidth(1, 80)
            employee_table.setColumnWidth(2, 150)
            employee_table.setColumnWidth(3, 200)
            employee_table.setColumnWidth(4, 100)
            employee_table.setColumnWidth(5, 80)
            employee_table.setColumnWidth(6, 80)

            employee_table.horizontalHeader().setStretchLastSection(True)
            employee_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            employee_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

            employee_table.setStyleSheet("""
                QTableWidget {
                    border: 2px solid #e2e8f0;
                    border-radius: 8px;
                    font-size: 13px;
                }
                QTableWidget::item {
                    padding: 8px;
                }
                QTableWidget::item:selected {
                    background-color: #dbeafe;
                }
                QHeaderView::section {
                    background-color: #f1f5f9;
                    padding: 8px;
                    border: 1px solid #e2e8f0;
                    font-weight: bold;
                }
            """)

            layout.addWidget(employee_table)

            # Description section
            description_label = QLabel("📝 Mô tả vấn đề/yêu cầu (nhập hoặc để AI tự tạo):")
            description_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
            layout.addWidget(description_label)

            description_edit = QTextEdit()
            description_edit.setMaximumHeight(100)
            description_edit.setPlaceholderText(
                f"Ví dụ: Phàn nàn về việc đi trễ, đề xuất đào tạo, nhắc nhở deadline... (Loại: {email_type})")
            description_edit.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 12px;
                    background-color: white;
                }
            """)

            if custom_description and custom_description.strip():
                description_edit.setPlainText(custom_description)

            layout.addWidget(description_edit)

            # Email content section
            email_label = QLabel("📧 Nội dung email (AI tự động tạo dựa trên mô tả và dữ liệu hiệu suất):")
            email_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
            layout.addWidget(email_label)

            email_content_edit = QTextEdit()
            email_content_edit.setMinimumHeight(200)
            email_content_edit.setReadOnly(True)
            email_content_edit.setStyleSheet("""
                QTextEdit {
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 10px;
                    font-size: 12px;
                    background-color: #f8fafc;
                    color: #334155;
                }
            """)
            layout.addWidget(email_content_edit)

            # Buttons
            description_buttons = QHBoxLayout()

            load_from_desc_btn = QPushButton("📥 Tạo email từ mô tả")
            load_from_desc_btn.setStyleSheet("""
                QPushButton {
                    background-color: #06b6d4;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #0891b2;
                }
            """)

            generate_btn = QPushButton("🤖 AI Tạo từ hiệu suất")
            generate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 15px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)

            description_buttons.addWidget(load_from_desc_btn)
            description_buttons.addWidget(generate_btn)
            description_buttons.addStretch()
            layout.addLayout(description_buttons)

            # Action buttons
            button_layout = QHBoxLayout()

            select_all_btn = QPushButton("✅ Chọn tất cả")
            select_all_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)

            clear_btn = QPushButton("🗑️ Bỏ chọn")
            clear_btn.setStyleSheet("""
                QPushButton {
                    background-color: #f59e0b;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #d97706;
                }
            """)

            send_btn = QPushButton("📤 Gửi Email")
            send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 30px;
                    font-weight: bold;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)

            cancel_btn = QPushButton("Hủy")
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ef4444;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 30px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #dc2626;
                }
            """)

            button_layout.addWidget(select_all_btn)
            button_layout.addWidget(clear_btn)
            button_layout.addStretch()
            button_layout.addWidget(cancel_btn)
            button_layout.addWidget(send_btn)

            layout.addLayout(button_layout)

            # Load employees
            self.load_employees_to_table_local(
                employee_table, year_combo, month_combo
            )

            # Connect buttons
            select_all_btn.clicked.connect(lambda: self.select_all_employees_local(employee_table))
            clear_btn.clicked.connect(lambda: self.clear_all_selection_local(employee_table))

            load_from_desc_btn.clicked.connect(lambda: self.generate_email_from_description_local(
                employee_table, description_edit, email_content_edit, year_combo, month_combo, email_type
            ))

            generate_btn.clicked.connect(lambda: self.generate_email_content_local(
                employee_table, email_content_edit, year_combo, month_combo
            ))

            send_btn.clicked.connect(lambda: self.send_ai_generated_emails_local(
                dialog, employee_table, email_content_edit, year_combo, month_combo
            ))
            cancel_btn.clicked.connect(dialog.reject)

            # Connect filter
            year_combo.currentTextChanged.connect(
                lambda: self.load_employees_to_table_local(employee_table, year_combo, month_combo)
            )
            month_combo.currentTextChanged.connect(
                lambda: self.load_employees_to_table_local(employee_table, year_combo, month_combo)
            )

            # Auto select employees
            if auto_select_ids:
                QTimer.singleShot(100, lambda: self.auto_select_employees_in_dialog_local(
                    employee_table, auto_select_ids
                ))

            dialog.show()

            if custom_description and custom_description.strip():
                print(f"🔄 Có mô tả, đang tự động bấm nút 'Tạo email từ mô tả'...")
                QTimer.singleShot(1000, lambda: self.auto_click_generate_button(
                    load_from_desc_btn, employee_table, description_edit,
                    email_content_edit, year_combo, month_combo, email_type
                ))

            dialog.exec()

        except Exception as e:
            print(f"❌ Lỗi mở dialog: {e}")
            import traceback
            traceback.print_exc()

    def auto_click_generate_button(self, button, table, desc_edit, content_edit,
                                   year_combo, month_combo, email_type):
        """Tự động bấm nút tạo email từ mô tả"""
        try:
            print(f"✅ Tự động bấm nút 'Tạo email từ mô tả'")

            selected_employees = self.get_selected_employees_local(table)
            if not selected_employees:
                print("⚠️ Chưa có nhân viên nào được chọn, đang chọn tất cả...")
                self.select_all_employees_local(table)
                selected_employees = self.get_selected_employees_local(table)

            print(f"📋 Số nhân viên được chọn: {len(selected_employees)}")

            button.click()

            QTimer.singleShot(500, lambda: content_edit.setFocus())

        except Exception as e:
            print(f"❌ Lỗi tự động bấm nút: {e}")
            import traceback
            traceback.print_exc()

    def generate_email_from_description_local(self, table, desc_edit, content_edit, year_combo, month_combo,
                                              email_type):
        """Tạo email từ mô tả vấn đề của người dùng"""
        selected_employees = self.get_selected_employees_local(table)

        if not selected_employees:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một nhân viên!")
            return

        description = desc_edit.toPlainText().strip()
        if not description:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập mô tả vấn đề!")
            return

        year = int(year_combo.currentText()) if year_combo.currentText() else datetime.now().year
        month = None
        if month_combo.currentText() != "Tất cả":
            month = int(month_combo.currentText().split(" ")[1])

        content_edit.setPlainText("🔄 Đang tạo email từ mô tả...")

        QTimer.singleShot(100, lambda: self._generate_email_from_description_async(
            selected_employees, description, content_edit, year, month, email_type
        ))

    def _generate_email_from_description_async(self, selected_employees, description, content_edit, year, month,
                                               email_type):
        """Tạo email bất đồng bộ từ mô tả"""
        try:
            if not self.gemini:
                try:
                    content_edit.setPlainText("⚠️ AI chưa khả dụng. Vui lòng kiểm tra cấu hình Gemini.")
                except RuntimeError:
                    pass
                return

            employees_data = []
            for emp in selected_employees:
                metrics = self.data_processor.get_employee_performance_metrics(
                    emp['id'],
                    year=year,
                    month=month
                )

                employee_info = {
                    'id': emp['id'],
                    'name': emp.get('name', emp['id']),
                    'email': emp.get('email', ''),
                    'metrics': metrics if metrics else {},
                    'year': year,
                    'month': month
                }
                employees_data.append(employee_info)

            email_content = self.gemini.generate_custom_email_content(
                employees_data=employees_data,
                custom_request=description,
                email_type=email_type,
                year=year,
                month=month
            )

            subject, body = self.parse_email_content(email_content)
            preview_text = f"TIÊU ĐỀ: {subject}\n\n{body}"

            try:
                content_edit.setPlainText(preview_text)
            except RuntimeError:
                pass

        except Exception as e:
            print(f"❌ Lỗi tạo email từ mô tả: {e}")
            import traceback
            traceback.print_exc()
            try:
                content_edit.setPlainText(f"⚠️ Lỗi tạo email:\n{str(e)[:200]}")
            except RuntimeError:
                pass

    def load_employees_to_table_local(self, table, year_combo, month_combo):
        """Load danh sách nhân viên vào table widget local"""
        try:
            table.setRowCount(0)

            employees = self.data_processor.get_employee_contact_info()

            if not employees:
                table.setRowCount(1)
                item = QTableWidgetItem("⚠️ Không có dữ liệu nhân viên. Vui lòng kiểm tra file employee_ids.xlsx")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(0, 0, item)
                table.setSpan(0, 0, 1, 7)
                return

            year = int(year_combo.currentText()) if year_combo.currentText() else datetime.now().year
            month = None
            if month_combo.currentText() != "Tất cả":
                month = int(month_combo.currentText().split(" ")[1])

            table.setRowCount(len(employees))

            for row, emp in enumerate(employees):
                # Checkbox
                checkbox = QCheckBox()
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                table.setCellWidget(row, 0, checkbox_widget)

                # ID
                id_item = QTableWidgetItem(emp['id'])
                id_item.setData(Qt.ItemDataRole.UserRole, emp)
                table.setItem(row, 1, id_item)

                # Name
                table.setItem(row, 2, QTableWidgetItem(emp.get('name', '')))

                # Email
                email = emp.get('email', '')
                email_item = QTableWidgetItem(email if email else "Không có")
                if not email:
                    email_item.setForeground(QColor("#ef4444"))
                table.setItem(row, 3, email_item)

                # SAP
                sap = emp.get('sap', '')
                table.setItem(row, 4, QTableWidgetItem(sap if sap else "N/A"))

                # Client
                client = emp.get('client', '')
                table.setItem(row, 5, QTableWidgetItem(client if client else "N/A"))

                # Score
                metrics = self.data_processor.get_employee_performance_metrics(
                    emp['id'],
                    year=year,
                    month=month
                )

                score = metrics.get('overall_score', 0) if metrics else 0
                score_item = QTableWidgetItem(f"{score}/100")

                if score >= 80:
                    score_item.setBackground(QColor("#10b981"))
                    score_item.setForeground(QColor("#ffffff"))
                elif score >= 60:
                    score_item.setBackground(QColor("#f59e0b"))
                    score_item.setForeground(QColor("#000000"))
                else:
                    score_item.setBackground(QColor("#ef4444"))
                    score_item.setForeground(QColor("#ffffff"))

                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, 6, score_item)

        except Exception as e:
            print(f"❌ Lỗi load employees to table: {e}")
            import traceback
            traceback.print_exc()

    def select_all_employees_local(self, table):
        """Chọn tất cả nhân viên trong table local"""
        for row in range(table.rowCount()):
            widget = table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def clear_all_selection_local(self, table):
        """Bỏ chọn tất cả nhân viên trong table local"""
        for row in range(table.rowCount()):
            widget = table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

    def get_selected_employees_local(self, table):
        """Lấy danh sách nhân viên được chọn từ table local"""
        selected_employees = []

        for row in range(table.rowCount()):
            widget = table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    item = table.item(row, 1)
                    if item:
                        emp_data = item.data(Qt.ItemDataRole.UserRole)
                        if emp_data and isinstance(emp_data, dict):
                            selected_employees.append(emp_data)

        return selected_employees

    def auto_select_employees_in_dialog_local(self, table, employee_ids):
        """Tự động tick chọn nhân viên trong dialog local"""
        for row in range(table.rowCount()):
            item = table.item(row, 1)
            if item and item.text() in employee_ids:
                widget = table.cellWidget(row, 0)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)

    def generate_email_content_local(self, table, content_edit, year_combo, month_combo):
        """Tạo nội dung email bằng Gemini và hiển thị trong khung chỉnh sửa"""
        selected_employees = self.get_selected_employees_local(table)

        if not selected_employees:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một nhân viên!")
            return

        content_edit.setPlainText("🔄 Đang tạo nội dung email bằng AI...")

        year = int(year_combo.currentText()) if year_combo.currentText() else datetime.now().year
        month = None
        if month_combo.currentText() != "Tất cả":
            month = int(month_combo.currentText().split(" ")[1])

        QTimer.singleShot(100, lambda: self._generate_email_content_async(
            selected_employees, content_edit, year, month
        ))

    def _generate_email_content_async(self, selected_employees, content_edit, year, month):
        """Tạo nội dung email bất đồng bộ"""
        try:
            if not self.gemini:
                content_edit.setPlainText("⚠️ AI chưa khả dụng. Vui lòng kiểm tra cấu hình Gemini.")
                return

            employees_data = []
            for emp in selected_employees:
                metrics = self.data_processor.get_employee_performance_metrics(
                    emp['id'],
                    year=year,
                    month=month
                )

                employee_info = {
                    'id': emp['id'],
                    'name': emp.get('name', emp['id']),
                    'email': emp.get('email', ''),
                    'metrics': metrics if metrics else {}
                }

                for field in ['sap', 'pwd', 'client']:
                    if field in emp:
                        employee_info[field] = emp[field]

                employees_data.append(employee_info)

            content_edit.setPlainText("🔄 Đang tạo nội dung email bằng AI...\nVui lòng chờ trong giây lát.")

            email_content = self.gemini.generate_email_content(employees_data)

            subject, body = self.parse_email_content(email_content)

            preview_text = f"TIÊU ĐỀ: {subject}\n\n{body}"
            content_edit.setPlainText(preview_text)

        except Exception as e:
            print(f"❌ Lỗi tạo email content: {e}")
            import traceback
            traceback.print_exc()
            content_edit.setPlainText(f"⚠️ Lỗi tạo nội dung email:\n{str(e)[:200]}")

    def parse_email_content(self, email_content):
        """Phân tích và chuẩn hóa nội dung email từ Gemini"""
        try:
            if not email_content:
                return "Đánh giá hiệu suất công việc", "Kính gửi,\n\nĐây là email đánh giá hiệu suất.\n\nTrân trọng,\nQuản lý"

            lines = email_content.strip().split('\n')

            subject = "Đánh giá hiệu suất công việc"
            body_start = 0

            for i, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean.startswith('TIÊU ĐỀ:') or line_clean.startswith('Tiêu đề:'):
                    subject_parts = line_clean.split(':', 1)
                    if len(subject_parts) > 1:
                        subject = subject_parts[1].strip()
                    body_start = i + 1
                    break

            body_lines = []
            if body_start < len(lines):
                if body_start < len(lines) and lines[body_start].strip() == '':
                    body_start += 1

                for i in range(body_start, len(lines)):
                    line = lines[i].strip()
                    if line or (body_lines and body_lines[-1] != ''):
                        body_lines.append(line)

            cleaned_body_lines = []
            prev_was_blank = False
            for line in body_lines:
                if line == '':
                    if not prev_was_blank:
                        cleaned_body_lines.append(line)
                        prev_was_blank = True
                else:
                    cleaned_body_lines.append(line)
                    prev_was_blank = False

            while cleaned_body_lines and cleaned_body_lines[0] == '':
                cleaned_body_lines.pop(0)
            while cleaned_body_lines and cleaned_body_lines[-1] == '':
                cleaned_body_lines.pop(-1)

            if not cleaned_body_lines:
                cleaned_body_lines = [
                    "Kính gửi,",
                    "",
                    "Đây là email đánh giá hiệu suất công việc.",
                    "",
                    "Trân trọng,",
                    "Quản lý"
                ]

            body = '\n'.join(cleaned_body_lines)

            if len(subject) > 100:
                subject = subject[:97] + "..."

            return subject, body

        except Exception as e:
            print(f"❌ Lỗi parse email content: {e}")
            return "Đánh giá hiệu suất công việc", "Kính gửi,\n\nĐây là email đánh giá hiệu suất.\n\nTrân trọng,\nQuản lý"

    def send_ai_generated_emails_local(self, dialog, table, content_edit, year_combo, month_combo):
        """Gửi email với nội dung được tạo bởi AI - local version"""
        try:
            selected_employees = self.get_selected_employees_local(table)

            if not selected_employees:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một nhân viên!")
                return

            year = int(year_combo.currentText()) if year_combo.currentText() else datetime.now().year
            month = None
            if month_combo.currentText() != "Tất cả":
                month = int(month_combo.currentText().split(" ")[1])

            employees_without_email = [emp for emp in selected_employees if not emp.get('email')]
            if employees_without_email:
                names = ", ".join([emp.get('name', emp['id']) for emp in employees_without_email])
                reply = QMessageBox.question(
                    self, "Cảnh báo",
                    f"{len(employees_without_email)} nhân viên không có email:\n{names}\n\nTiếp tục gửi cho những người có email?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return

            email_content = content_edit.toPlainText()

            if not email_content or "⚠️" in email_content or "🔄" in email_content:
                QMessageBox.warning(self, "Cảnh báo", "Vui lòng tạo nội dung email trước khi gửi!")
                return

            subject, body = self.parse_email_content(email_content)

            if not body or len(body.strip()) < 20:
                QMessageBox.warning(self, "Cảnh báo", "Nội dung email quá ngắn. Vui lòng tạo lại nội dung!")
                return

            if len(selected_employees) == 1:
                emp = selected_employees[0]
                confirm_msg = f"Gửi email cho {emp.get('name', emp['id'])}?"
                email_info = f"Email: {emp.get('email', 'Không có email')}"
            else:
                confirm_msg = f"Gửi email cho {len(selected_employees)} nhân viên đã chọn?"
                email_info = f"Số người có email: {len([e for e in selected_employees if e.get('email')])}/{len(selected_employees)}"

            reply = QMessageBox.question(
                self, "Xác nhận gửi email",
                f"{confirm_msg}\n\n{email_info}\n\nTiêu đề: {subject}\n\nNội dung: {body[:200]}...\n\nTiếp tục?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.No:
                return

            self.status_bar.setText("📤 Đang gửi email...")

            email_data = {
                "test_mode": False,
                "timestamp": datetime.now().isoformat(),
                "emails": []
            }

            success_count = 0
            for emp in selected_employees:
                if not emp.get('email'):
                    continue

                try:
                    metrics = self.data_processor.get_employee_performance_metrics(
                        emp['id'],
                        year=year,
                        month=month
                    )

                    personalized_body = self._personalize_email_body(body, emp, metrics)

                    html_body = EmailTemplates.get_improvement_email_template(
                        employee_name=emp.get('name', emp['id']),
                        manager_name="Quản lý",
                        recommendations=personalized_body,
                        employee_id=emp['id']
                    )

                    email_data["emails"].append({
                        "to_email": emp['email'],
                        "subject": subject,
                        "body": personalized_body,
                        "html_body": html_body,
                        "cc": "gameyuno123@gmail.com",
                        "employee_name": emp.get('name', emp['id']),
                        "employee_id": emp['id'],
                        "metrics": metrics
                    })

                    success_count += 1

                except Exception as e:
                    print(f"❌ Lỗi chuẩn bị email cho {emp.get('id')}: {e}")

            if not email_data["emails"]:
                QMessageBox.warning(self, "Cảnh báo", "Không có email nào để gửi!")
                self.status_bar.setText("❌ Không có email để gửi")
                return

            success = self.send_emails_to_n8n(email_data)

            if success:
                QMessageBox.information(self, "Thành công",
                                        f"✅ Đã gửi {success_count}/{len(selected_employees)} email thành công!")
                if dialog and dialog.isVisible():
                    dialog.accept()
                self.status_bar.setText(f"✅ Đã gửi {success_count} email")
            else:
                QMessageBox.critical(self, "Lỗi", "❌ Không thể gửi email. Vui lòng thử lại!")
                self.status_bar.setText("❌ Lỗi gửi email")

        except Exception as e:
            print(f"❌ Lỗi không mong muốn trong send_ai_generated_emails_local: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi hệ thống", f"Lỗi: {str(e)}")
            self.status_bar.setText("❌ Lỗi hệ thống")

    def _personalize_email_body(self, base_body, employee, metrics):
        """Cá nhân hóa nội dung email cho từng nhân viên"""
        try:
            emp_name = employee.get('name', employee['id'])

            personalized_body = f"Kính gửi Anh/Chị {emp_name},\n\n"

            if metrics:
                rank = metrics.get('rank', '')
                score = metrics.get('overall_score', 0)

                if rank and score > 0:
                    personalized_body += f"Dựa trên đánh giá hiệu suất, bạn được xếp hạng: {rank} với {score}/100 điểm.\n\n"

            personalized_body += base_body

            lines = personalized_body.split('\n')
            cleaned_lines = []
            prev_was_blank = False

            for line in lines:
                line = line.strip()
                if line:
                    cleaned_lines.append(line)
                    prev_was_blank = False
                elif not prev_was_blank and cleaned_lines:
                    cleaned_lines.append('')
                    prev_was_blank = True

            while cleaned_lines and cleaned_lines[-1] == '':
                cleaned_lines.pop()

            return '\n'.join(cleaned_lines)

        except Exception as e:
            print(f"❌ Lỗi personalize email: {e}")
            return base_body

    def send_emails_to_n8n(self, email_data):
        """Gửi email đến n8n - tối ưu hóa"""
        try:
            success_count = 0

            for email_item in email_data["emails"]:
                try:
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
                        print(f"✅ Đã gửi email cho {email_item['employee_name']}")
                    else:
                        print(f"❌ Lỗi gửi email cho {email_item['employee_name']}: {response.status_code}")

                except Exception as e:
                    print(f"❌ Exception khi gửi email: {e}")

            self.status_bar.setText(f"✅ Đã gửi {success_count}/{len(email_data['emails'])} email")
            return success_count > 0

        except Exception as e:
            print(f"❌ Lỗi hệ thống gửi email: {e}")
            self.status_bar.setText("❌ Lỗi gửi email")
            return False
    def initialize_gemini(self):
        """Initialize Gemini Analyzer"""
        if gemini_available:
            try:
                self.load_env()
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
            env_path = Path("C:/Users/legal/PycharmProjects/PythonProject/Chatbot/.env")
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
            else:
                load_dotenv()

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

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

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

        # Quick actions
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
            ("📨 Tổng hợp mail", lambda: self.quick_summary_email()),
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
        manager_email = self.manager_info.get('email', 'legalgiang@gmail.com')
        manager_name = self.manager_info.get('name', 'Quản lý')
        self.status_bar = QLabel(f"👤 {manager_name} | 📧 {manager_email} | Status: Initializing...")
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

        # Welcome message
        self.add_bot_message(f"Xin chào Quản lý {manager_name}! Tôi là chatbot hỗ trợ phân tích hiệu suất.")
        self.add_bot_message("Tôi có thể giúp bạn với:")
        self.add_bot_message("• Phân tích hiệu suất tổng thể của team")
        self.add_bot_message("• So sánh nhân viên")
        self.add_bot_message("• Đề xuất đào tạo và cải thiện")
        self.add_bot_message("• Quản lý rủi ro và điểm nghẽn")
        self.add_bot_message("• Gửi email cho nhân viên (dùng 'send email' hoặc nhấn 📧)")
        self.add_bot_message("• Tổng hợp email từ nhân viên (dùng 'aggregate mails' hoặc nhấn 📨)")

        if not self.gemini:
            self.add_bot_message("⚠️ **Note**: Gemini AI is not available. Using DEMO mode.")

    def quick_summary_email(self):
        """Xử lý nút tổng hợp mail trong quick actions"""
        self.input_field.setText("I want to aggregate my employees' feedback and receive summary")
        self.send_message()

    def handle_quick_action_email(self):
        """Xử lý quick action email button"""
        try:
            if not self.data_processor:
                self.add_bot_message("❌ **KHÔNG CÓ DATA PROCESSOR**\n\nKhông thể truy cập dữ liệu nhân viên.")
                return

            employees = self.data_processor.get_employee_contact_info()
            if not employees:
                self.add_bot_message("❌ **KHÔNG CÓ DỮ LIỆU NHÂN VIÊN**\n\nKhông thể tìm thấy thông tin nhân viên.")
                return

            self.add_bot_message("📧 **MỞ CỬA SỔ SOẠN EMAIL**\n\nVui lòng chọn nhân viên và nhập mô tả...")
            QTimer.singleShot(1000, lambda: self.open_employee_selection_dialog(
                email_type="general",
                custom_description=""
            ))

        except Exception as e:
            print(f"❌ Lỗi mở dialog email: {e}")
            self.add_bot_message(f"❌ **LỖI MỞ DIALOG**: {str(e)[:100]}")

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
        self.status_bar.setText(
            f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | 📂 Reading aggregate data...")
        self.send_button.setEnabled(False)

        try:
            if not self.data_processor:
                self.status_indicator.setText("○")
                self.status_bar.setText(
                    f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | ❌ DataProcessor not available")
                self.send_button.setEnabled(True)
                self.add_bot_message("⚠️ DataProcessor not available. Using demo mode.")
                return

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

                self.show_manager_summary()

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
                self.status_bar.setText(
                    f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | ❌ Cannot load aggregate data")
                self.send_button.setEnabled(True)
                self.add_bot_message("⚠️ Cannot load aggregate data. Please check data connection.")

        except Exception as e:
            print(f"❌ Error loading manager data: {e}")
            traceback.print_exc()
            self.status_indicator.setText("○")
            self.status_bar.setText(
                f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | Error: {str(e)[:50]}")
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

        monthly_data = self.aggregate_data.get('monthly_data', {})
        current_month = datetime.now().month
        revenues = monthly_data.get('revenue', [0] * 12)
        current_month_revenue = revenues[current_month - 1] if current_month <= len(revenues) else 0

        manager_email = self.manager_info.get('email', 'legalgiang@gmail.com')
        manager_name = self.manager_info.get('name', 'Quản lý')
        self.status_bar.setText(
            f"👤 {manager_name} | 📧 {manager_email} | 👥 {total_employees} Emp | "
            f"💰 Year: {total_revenue:,.0f} VND | Month {current_month}: {current_month_revenue:,.0f} VND | "
            f"⚠️ {total_fraud} fraud"
        )

        summary = f"""**📊 TEAM OVERVIEW REPORT**

**📅 Time:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
**👤 Manager:** {manager_name}
**📧 Email:** {manager_email}

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
- "Send email to employees"
- "Aggregate email from employees" """

        self.add_bot_message(summary)

    def send_message(self):
        """Handle user message"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.add_user_message(user_input)
        self.input_field.clear()

        if self.email_request_state['waiting_confirmation']:
            if self.handle_email_confirmation(user_input):
                return

        if self.check_summary_email_intent(user_input):
            print(f"✅ Đã phát hiện yêu cầu tổng hợp email: {user_input}")
            QTimer.singleShot(100, lambda: self.handle_summary_email_request(user_input))
            return

        if self.check_email_intent(user_input):
            employee_ids = self.extract_employee_ids_from_message(user_input)
            email_type, description = self.detect_email_type_and_description(user_input)

            print(f"🚀 EMAIL INTENT DETECTED: Type={email_type}, Desc={description}, Employees={employee_ids}")

            self.email_request_state['email_type'] = email_type
            self.current_email_description = description

            self.add_bot_message(
                f"📧 **ĐANG MỞ CỬA SỔ SOẠN EMAIL**\n\n• Loại: {email_type}\n• Mô tả: {description[:100]}...")

            QTimer.singleShot(800, lambda: self.open_employee_selection_dialog(
                auto_select_ids=employee_ids,
                email_type=email_type,
                custom_description=description
            ))
            return

        self.send_button.setEnabled(False)
        self.status_bar.setText(
            f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | 🤔 AI đang phân tích...")

        context_data = self.get_manager_data_context()

        self.chat_thread = ManagerChatThread(self.gemini, user_input, context_data)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def on_ai_response(self, response):
        """Receive AI response"""
        self.add_bot_message(response)
        self.send_button.setEnabled(True)
        self.status_bar.setText(
            f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | ✅ Ready")

    def on_ai_error(self, error):
        """Handle AI error"""
        error_msg = f"""**❌ SYSTEM ERROR**

Cannot connect to AI service:

**Details:** {error}

**DEMO mode will be used temporarily.**"""

        self.add_bot_message(error_msg)
        self.send_button.setEnabled(True)
        self.status_bar.setText(
            f"👤 {self.manager_info.get('name', 'Quản lý')} | 📧 {self.manager_info.get('email', 'legalgiang@gmail.com')} | ⚠️ Error occurred")

    def get_manager_data_context(self):
        """Get comprehensive data context for manager - ENHANCED VERSION"""
        if not self.aggregate_data:
            return {
                "status": "no_data",
                "summary": "No aggregate data yet",
                "employee_name": "Manager",
                "manager_info": self.manager_info,
                "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "employees_detail": []
            }

        monthly_data = self.aggregate_data.get('monthly_data', {})
        current_month = datetime.now().month
        current_year = datetime.now().year

        revenues = monthly_data.get('revenue', [0] * 12)
        current_month_revenue = revenues[current_month - 1] if current_month <= len(revenues) else 0

        orders = monthly_data.get('orders', [0] * 12)
        current_month_orders = orders[current_month - 1] if current_month <= len(orders) else 0

        frauds = monthly_data.get('fraud', [0] * 12)
        current_month_fraud = frauds[current_month - 1] if current_month <= len(frauds) else 0

        profits = monthly_data.get('profit', [0] * 12)
        current_month_profit = profits[current_month - 1] if current_month <= len(profits) else 0

        employees_detail = self._get_detailed_employees_data(current_year, current_month)

        lowest_performers = self.data_processor.get_lowest_performing_employees(5, current_year,
                                                                                current_month) if self.data_processor else []
        highest_orders = self.data_processor.get_highest_orders_employees(5, current_year,
                                                                          current_month) if self.data_processor else []

        return {
            "status": "ok",
            "employee_name": "Manager (Team Overview)",
            "manager_info": self.manager_info,
            "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

            "metrics": {
                "total_orders": int(current_month_orders),
                "completed_orders": int(current_month_orders * 0.95),
                "pending_orders": int(current_month_orders * 0.05),
                "completion_rate": 95.0,
                "total_revenue": float(current_month_revenue),
                "total_profit": float(current_month_profit),
                "fraud_count": int(current_month_fraud),
                "profit_margin": (
                            current_month_profit / current_month_revenue * 100) if current_month_revenue > 0 else 0,
                "on_time_delivery": 95.0
            },

            "summary": {
                "total_employees": self.aggregate_data.get('total_employees', 0),
                "employees_with_data": self.aggregate_data.get('employees_with_data', 0),
                "total_revenue": self.aggregate_data.get('total_revenue', 0),
                "total_profit": self.aggregate_data.get('total_profit', 0),
                "total_fraud": self.aggregate_data.get('total_fraud', 0),
                "average_completion_rate": self.aggregate_data.get('average_completion_rate', 0),
                "average_overall_score": self.aggregate_data.get('average_overall_score', 0)
            },

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

            "employees_detail": employees_detail,

            "rankings": {
                "lowest_performers": lowest_performers,
                "highest_orders": highest_orders,
                "total_employees_count": len(employees_detail)
            },

            "sap_data": {
                "summary": {
                    "total_orders": int(current_month_orders),
                    "completed_orders": int(current_month_orders * 0.95),
                    "pending_orders_count": int(current_month_orders * 0.05),
                    "total_revenue": float(current_month_revenue),
                    "total_profit": float(current_month_profit),
                    "pending_orders": []
                }
            },

            "work_log": {
                "summary": {
                    "fraud_count": int(current_month_fraud),
                    "total_work_hours": 160 * self.aggregate_data.get('employees_with_data', 0),
                    "critical_count": int(current_month_fraud * 0.3)
                }
            },

            "employees": self.get_employee_list() if self.data_processor else [],
            "is_manager": True,

            "capabilities": {
                "employee_specific_queries": True,
                "comparison_queries": True,
                "ranking_queries": True,
                "performance_analysis": True,
                "order_analysis": True,
                "fraud_analysis": True,
                "time_analysis": True,
                "recommendation_generation": True
            }
        }

    def _get_detailed_employees_data(self, year, month):
        """Lấy dữ liệu chi tiết của tất cả nhân viên"""
        try:
            employees = self.data_processor.get_employee_contact_info() if self.data_processor else []
            if not employees:
                return []

            detailed_data = []

            for emp in employees[:20]:
                emp_id = emp['id']

                metrics = self.data_processor.get_employee_performance_metrics(emp_id, year,
                                                                               month) if self.data_processor else {}
                detailed_perf = self.data_processor.get_employee_detailed_performance(emp_id, year,
                                                                                      month) if self.data_processor else {}
                pending_analysis = self.data_processor.get_pending_orders_analysis(emp_id, year,
                                                                                   month) if self.data_processor else {}

                employee_detail = {
                    'id': emp_id,
                    'name': emp.get('name', emp_id),
                    'email': emp.get('email', ''),
                    'sap': emp.get('sap', ''),
                    'client': emp.get('client', ''),
                    'metrics': metrics if metrics else {},
                    'detailed_performance': detailed_perf if detailed_perf else {},
                    'pending_orders': pending_analysis if pending_analysis else {}
                }

                detailed_data.append(employee_detail)

            return detailed_data

        except Exception as e:
            print(f"❌ Lỗi lấy detailed employees data: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_employee_list(self):
        """Get employee list"""
        try:
            if self.data_processor:
                employees = self.data_processor.get_all_employees()
                return employees[:10]
        except Exception as e:
            print(f"Error getting employee list: {e}")
        return []

    def extract_employee_ids_from_message(self, message):
        """Trích xuất mã nhân viên từ tin nhắn"""
        pattern = r'EM\d{3}'
        employee_ids = re.findall(pattern, message.upper())
        return employee_ids

    def handle_custom_email_request(self, user_input, employee_ids):
        """Xử lý yêu cầu tạo email tùy chỉnh"""
        email_type, description = self.detect_email_type_and_description(user_input)

        self.email_request_state['email_type'] = email_type
        self.custom_email_description = description

        if employee_ids:
            emp_list = ', '.join(employee_ids)
            message = f"📧 **MỞ CỬA SỔ SOẠN EMAIL**\n\n• Loại: {email_type}\n• Cho: {emp_list}\n• Mô tả: {description[:80]}..."
        else:
            message = f"📧 **MỞ CỬA SỔ SOẠN EMAIL**\n\n• Loại: {email_type}\n• Mô tả: {description[:80]}..."

        self.add_bot_message(message)

        QTimer.singleShot(1500, lambda: self.open_employee_selection_dialog(
            auto_select_ids=employee_ids,
            email_type=email_type,
            custom_description=description
        ))

    def closeEvent(self, event):
        """Xử lý khi đóng ứng dụng"""
        if self.summary_thread and self.summary_thread.isRunning():
            print("🛑 Đang dừng summary thread...")
            self.summary_thread.quit()
            self.summary_thread.wait(1000)
        super().closeEvent(event)


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
                import random
                demo_responses = [
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Hiệu suất team hiện ổn định. Tập trung vào nhân viên có tỷ lệ hoàn thành thấp để cải thiện.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Dữ liệu team cho thấy cần giảm sự kiện gian lận. Cân nhắc đào tạo tuân thủ cho toàn team.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Doanh thu team đang phát triển tốt. Tập trung vào nhân viên hiệu suất cao để nhân rộng thành công.",
                ]
                response = random.choice(demo_responses)
                self.response_ready.emit(response)
                return

            if isinstance(self.context_data, dict):
                response = self.gemini.analyze_question(self.question, self.context_data)
            else:
                response = self.gemini.analyze_question(self.question, {"data": str(self.context_data)})

            self.response_ready.emit(response)
        except Exception as e:
            print(f"Error in ManagerChatThread: {e}")
            traceback.print_exc()
            self.error_occurred.emit(str(e))


class SummaryEmailThread(QThread):
    """Thread để kích hoạt workflow n8n"""
    response_received = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(self, webhook_url, payload):
        super().__init__()
        self.webhook_url = webhook_url
        self.payload = payload

    def run(self):
        try:
            print(f"🌐 Kích hoạt workflow tổng hợp email: {self.webhook_url}")
            print(f"📧 Manager email: {self.payload.get('manager_email', 'legalgiang@gmail.com')}")

            response = requests.post(
                self.webhook_url,
                json=self.payload,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code in [200, 201, 202]:
                try:
                    response_data = response.json()
                    print(f"✅ Workflow response: {response_data}")
                    self.response_received.emit(response_data)
                except:
                    self.response_received.emit({
                        "status": "success",
                        "message": f"Workflow triggered (status: {response.status_code})",
                        "manager_email": self.payload.get('manager_email', 'legalgiang@gmail.com')
                    })
            else:
                self.response_received.emit({
                    "status": "error",
                    "message": f"HTTP {response.status_code}: {response.text[:100]}",
                    "manager_email": self.payload.get('manager_email', 'legalgiang@gmail.com')
                })

        except requests.exceptions.Timeout:
            print("⚡ Request timeout (nhưng workflow có thể đã được kích hoạt)")
            self.response_received.emit({
                "status": "timeout",
                "message": "Workflow timeout but may have been triggered",
                "manager_email": self.payload.get('manager_email', 'legalgiang@gmail.com')
            })
        except Exception as e:
            print(f"⚠️ Lỗi khi gửi request: {e}")
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