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
        self.n8n_webhook_url = "https://gain1109.app.n8n.cloud/webhook/349efadb-fad2-4589-9827-f99d94e3ac31"

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

    def open_dashboard(self):
        """Open employee list dashboard"""
        try:
            # Kiểm tra và tạo DataProcessor nếu chưa có
            if not self.data_processor:
                self.data_processor = DataProcessor()

            # Lấy danh sách nhân viên
            employees = self.data_processor.get_employees_for_list()

            if not employees:
                self.add_bot_message("❌ Không tìm thấy dữ liệu nhân viên nào")
                return

            print(f"📊 Opening dashboard with {len(employees)} employees")

            # Tạo dialog hiển thị danh sách nhân viên
            dialog = QDialog(self)
            dialog.setWindowTitle("📊 Employee Dashboard")
            dialog.setMinimumSize(900, 600)

            layout = QVBoxLayout(dialog)
            layout.setSpacing(15)

            # Header
            header_label = QLabel("📋 DANH SÁCH NHÂN VIÊN")
            header_label.setStyleSheet("""
                font-size: 18px;
                font-weight: bold;
                color: #1e40af;
                padding: 15px;
                background-color: #f0f9ff;
                border-radius: 8px;
                text-align: center;
            """)
            layout.addWidget(header_label)

            # Search and filter section
            filter_widget = QWidget()
            filter_layout = QHBoxLayout(filter_widget)
            filter_layout.setContentsMargins(0, 0, 0, 0)

            # Year filter
            year_label = QLabel("Năm:")
            year_combo = QComboBox()
            current_year = datetime.now().year
            for year in range(current_year - 2, current_year + 1):
                year_combo.addItem(str(year))
            year_combo.setCurrentText(str(current_year))

            # Month filter
            month_label = QLabel("Tháng:")
            month_combo = QComboBox()
            month_combo.addItem("Tất cả")
            for month in range(1, 13):
                month_combo.addItem(f"Tháng {month}")

            # Search input
            search_label = QLabel("Tìm kiếm:")
            search_input = QLineEdit()
            search_input.setPlaceholderText("Nhập mã nhân viên...")

            search_button = QPushButton("🔍 Tìm")
            search_button.clicked.connect(lambda: self.search_employee_in_table(table_widget, search_input.text()))

            filter_layout.addWidget(year_label)
            filter_layout.addWidget(year_combo)
            filter_layout.addSpacing(10)
            filter_layout.addWidget(month_label)
            filter_layout.addWidget(month_combo)
            filter_layout.addStretch()
            filter_layout.addWidget(search_label)
            filter_layout.addWidget(search_input)
            filter_layout.addWidget(search_button)

            layout.addWidget(filter_widget)

            # Create table
            table_widget = QTableWidget()
            table_widget.setColumnCount(7)
            table_widget.setHorizontalHeaderLabels(
                ["Mã NV", "Họ Tên", "Email", "SAP", "Client", "Có dữ liệu", "Hành động"])

            # Set column widths
            table_widget.setColumnWidth(0, 80)  # Mã NV
            table_widget.setColumnWidth(1, 150)  # Họ Tên
            table_widget.setColumnWidth(2, 200)  # Email
            table_widget.setColumnWidth(3, 100)  # SAP
            table_widget.setColumnWidth(4, 80)  # Client
            table_widget.setColumnWidth(5, 100)  # Có dữ liệu
            table_widget.setColumnWidth(6, 120)  # Hành động

            # Set table properties
            table_widget.setAlternatingRowColors(True)
            table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            table_widget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table_widget.horizontalHeader().setStretchLastSection(True)

            # Fill table with employee data
            for emp in employees:
                self.add_employee_to_table(table_widget, emp, year_combo, month_combo)

            layout.addWidget(table_widget)

            # Button row
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)

            view_all_btn = QPushButton("👁️ Xem tất cả")
            view_all_btn.clicked.connect(lambda: self.view_all_employees(table_widget, employees))

            export_btn = QPushButton("📥 Xuất Excel")
            export_btn.clicked.connect(lambda: self.export_employees_to_excel(employees))

            refresh_btn = QPushButton("🔄 Làm mới")
            refresh_btn.clicked.connect(lambda: self.refresh_employee_table(table_widget, year_combo, month_combo))

            close_btn = QPushButton("Đóng")
            close_btn.clicked.connect(dialog.reject)

            button_layout.addWidget(view_all_btn)
            button_layout.addWidget(export_btn)
            button_layout.addStretch()
            button_layout.addWidget(refresh_btn)
            button_layout.addWidget(close_btn)

            layout.addWidget(button_widget)

            # Kết nối filter changes
            year_combo.currentTextChanged.connect(
                lambda: self.filter_employee_table(table_widget, employees, year_combo.currentText(),
                                                   month_combo.currentText())
            )
            month_combo.currentTextChanged.connect(
                lambda: self.filter_employee_table(table_widget, employees, year_combo.currentText(),
                                                   month_combo.currentText())
            )

            dialog.exec()

        except Exception as e:
            print(f"❌ Error opening dashboard: {e}")
            import traceback
            traceback.print_exc()
            self.add_bot_message(f"❌ Lỗi mở dashboard: {str(e)}")

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
        """Xử lý yêu cầu gửi email - Mở dialog chọn nhân viên ngay"""
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

        # Mở dialog chọn nhân viên ngay
        self.open_employee_selection_dialog()

        # Thông báo cho user
        self.add_bot_message("✅ **ĐÃ MỞ CỬA SỔ CHỌN NHÂN VIÊN**\n\nVui lòng chọn nhân viên và tạo nội dung email.")
    # Thay thế hàm open_employee_selection_dialog trong manager_chatbot.py

    def open_employee_selection_dialog(self):
        """Mở dialog chọn nhân viên để gửi email - SỬ DỤNG TABLE"""
        dialog = QDialog(self)
        dialog.setWindowTitle("📧 Gửi Email Nhắc Nhở Công Việc")
        dialog.setMinimumSize(900, 700)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("CHỌN NHÂN VIÊN ĐỂ GỬI EMAIL (CHỈ NHÂN VIÊN EM)")
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
        self.year_combo = QComboBox()
        current_year = datetime.now().year
        for year in range(current_year - 2, current_year + 1):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(current_year))

        month_label = QLabel("Tháng:")
        self.month_combo = QComboBox()
        self.month_combo.addItem("Tất cả")
        for month in range(1, 13):
            self.month_combo.addItem(f"Tháng {month}")

        filter_layout.addWidget(year_label)
        filter_layout.addWidget(self.year_combo)
        filter_layout.addSpacing(20)
        filter_layout.addWidget(month_label)
        filter_layout.addWidget(self.month_combo)
        filter_layout.addStretch()

        layout.addWidget(filter_widget)

        # Employee table - SỬ DỤNG TABLE WIDGET
        employee_table_label = QLabel("📋 Danh sách nhân viên (EM):")
        employee_table_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(employee_table_label)

        # Tạo table widget
        self.employee_table = QTableWidget()
        self.employee_table.setColumnCount(7)  # Tăng thêm 1 cột cho checkbox
        self.employee_table.setHorizontalHeaderLabels(["Chọn", "Mã NV", "Họ Tên", "Email", "SAP", "Client", "Điểm"])

        # Đặt chiều rộng cột
        self.employee_table.setColumnWidth(0, 50)  # Chọn
        self.employee_table.setColumnWidth(1, 80)  # Mã NV
        self.employee_table.setColumnWidth(2, 150)  # Họ Tên
        self.employee_table.setColumnWidth(3, 200)  # Email
        self.employee_table.setColumnWidth(4, 100)  # SAP
        self.employee_table.setColumnWidth(5, 80)  # Client
        self.employee_table.setColumnWidth(6, 80)  # Điểm

        self.employee_table.horizontalHeader().setStretchLastSection(True)
        self.employee_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.employee_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.employee_table.setStyleSheet("""
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

        # Load employees vào table
        self.load_employees_to_table()

        # Kết nối filter
        self.year_combo.currentTextChanged.connect(self.load_employees_to_table)
        self.month_combo.currentTextChanged.connect(self.load_employees_to_table)

        layout.addWidget(self.employee_table)

        # Email preview section
        preview_label = QLabel("📝 Xem trước nội dung email (tự động tạo bởi AI):")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(preview_label)

        self.email_preview = QTextEdit()
        self.email_preview.setReadOnly(True)
        self.email_preview.setMaximumHeight(150)
        self.email_preview.setStyleSheet("""
            QTextEdit {
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
                background-color: #f8fafc;
            }
        """)
        layout.addWidget(self.email_preview)

        # Buttons
        button_layout = QHBoxLayout()

        select_all_btn = QPushButton("✅ Chọn tất cả")
        select_all_btn.clicked.connect(self.select_all_employees)
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
        clear_btn.clicked.connect(self.clear_all_selection)
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

        preview_btn = QPushButton("👁️ Xem trước email")
        preview_btn.clicked.connect(self.preview_email_content)
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)

        send_btn = QPushButton("📤 Gửi Email")
        send_btn.clicked.connect(lambda: self.send_ai_generated_emails(dialog))
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
        cancel_btn.clicked.connect(dialog.reject)
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
        # Trong phần buttons của open_employee_selection_dialog, thêm nút này:
        refresh_btn = QPushButton("🔄 Làm mới nội dung")
        refresh_btn.clicked.connect(self.preview_email_content)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #06b6d4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #0891b2;
            }
        """)

        # Thêm vào button_layout trước preview_btn
        button_layout.addWidget(refresh_btn)

        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        button_layout.addWidget(preview_btn)
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(send_btn)

        layout.addLayout(button_layout)

        dialog.exec()

    def load_employees_to_table(self):
        """Load danh sách nhân viên vào table widget"""
        try:
            # Clear table trước
            self.employee_table.setRowCount(0)

            # Lấy danh sách nhân viên từ DataProcessor
            employees = self.data_processor.get_employee_contact_info()

            if not employees:
                self.employee_table.setRowCount(1)
                item = QTableWidgetItem("⚠️ Không có dữ liệu nhân viên. Vui lòng kiểm tra file employee_ids.xlsx")
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.employee_table.setItem(0, 0, item)
                self.employee_table.setSpan(0, 0, 1, 7)  # Merge cells
                return

            print(f"📊 Đang load {len(employees)} nhân viên vào table...")

            # Lấy năm và tháng filter
            year = int(self.year_combo.currentText()) if self.year_combo.currentText() else datetime.now().year
            month = None
            if self.month_combo.currentText() != "Tất cả":
                month = int(self.month_combo.currentText().split(" ")[1])

            self.employee_table.setRowCount(len(employees))

            for row, emp in enumerate(employees):
                # Cột 0: Checkbox để chọn
                checkbox = QCheckBox()
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.employee_table.setCellWidget(row, 0, checkbox_widget)

                # Cột 1: Mã NV
                id_item = QTableWidgetItem(emp['id'])
                id_item.setData(Qt.ItemDataRole.UserRole, emp)  # Lưu toàn bộ thông tin
                self.employee_table.setItem(row, 1, id_item)

                # Cột 2: Họ tên
                self.employee_table.setItem(row, 2, QTableWidgetItem(emp.get('name', '')))

                # Cột 3: Email
                email = emp.get('email', '')
                email_item = QTableWidgetItem(email if email else "Không có")
                if not email:
                    email_item.setForeground(QColor("#ef4444"))  # Màu đỏ nếu không có email
                self.employee_table.setItem(row, 3, email_item)

                # Cột 4: SAP
                sap = emp.get('sap', '')
                self.employee_table.setItem(row, 4, QTableWidgetItem(sap if sap else "N/A"))

                # Cột 5: Client
                client = emp.get('client', '')
                self.employee_table.setItem(row, 5, QTableWidgetItem(client if client else "N/A"))

                # Cột 6: Điểm (lấy từ metrics nếu có)
                metrics = self.data_processor.get_employee_performance_metrics(
                    emp['id'],
                    year=year,
                    month=month
                )

                score = metrics.get('overall_score', 0) if metrics else 0
                score_item = QTableWidgetItem(f"{score}/100")

                # Đặt màu nền dựa trên điểm
                if score >= 80:
                    score_item.setBackground(QColor("#10b981"))  # Xanh
                    score_item.setForeground(QColor("#ffffff"))
                elif score >= 60:
                    score_item.setBackground(QColor("#f59e0b"))  # Vàng
                    score_item.setForeground(QColor("#000000"))
                else:
                    score_item.setBackground(QColor("#ef4444"))  # Đỏ
                    score_item.setForeground(QColor("#ffffff"))

                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.employee_table.setItem(row, 6, score_item)

            print(f"✅ Đã load {len(employees)} nhân viên vào table thành công")

        except Exception as e:
            print(f"❌ Lỗi load employees to table: {e}")
            import traceback
            traceback.print_exc()

    def select_all_employees(self):
        """Chọn tất cả nhân viên trong table"""
        for row in range(self.employee_table.rowCount()):
            widget = self.employee_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

    def clear_all_selection(self):
        """Bỏ chọn tất cả nhân viên trong table"""
        for row in range(self.employee_table.rowCount()):
            widget = self.employee_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

    def get_selected_employees(self):
        """Lấy danh sách nhân viên được chọn từ table"""
        selected_employees = []

        for row in range(self.employee_table.rowCount()):
            widget = self.employee_table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox and checkbox.isChecked():
                    # Lấy thông tin từ cột Mã NV (cột 1)
                    item = self.employee_table.item(row, 1)
                    if item:
                        emp_data = item.data(Qt.ItemDataRole.UserRole)
                        if emp_data and isinstance(emp_data, dict):
                            selected_employees.append(emp_data)

        return selected_employees

    def preview_email_content(self):
        """Xem trước nội dung email sẽ gửi"""
        selected_employees = self.get_selected_employees()

        if not selected_employees:
            self.email_preview.setPlainText("⚠️ Vui lòng chọn ít nhất một nhân viên để xem trước email.")
            return

        # Hiển thị thông báo đang tạo
        self.email_preview.setPlainText("🔄 Đang tạo nội dung email bằng AI...")

        # Lấy năm và tháng filter
        year = int(self.year_combo.currentText()) if self.year_combo.currentText() else datetime.now().year
        month = None
        if self.month_combo.currentText() != "Tất cả":
            month = int(self.month_combo.currentText().split(" ")[1])

        # Tạo nội dung email bằng Gemini
        QTimer.singleShot(100, lambda: self.generate_email_preview(selected_employees, year, month))

    def parse_email_content(self, email_content):
        """Phân tích và chuẩn hóa nội dung email từ Gemini"""
        try:
            if not email_content:
                return "Đánh giá hiệu suất công việc", "Kính gửi,\n\nĐây là email đánh giá hiệu suất.\n\nTrân trọng,\nQuản lý"

            lines = email_content.strip().split('\n')

            # Tìm dòng tiêu đề
            subject = "Đánh giá hiệu suất công việc"
            body_start = 0

            for i, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean.startswith('TIÊU ĐỀ:') or line_clean.startswith('Tiêu đề:'):
                    # Lấy phần sau dấu ":"
                    subject_parts = line_clean.split(':', 1)
                    if len(subject_parts) > 1:
                        subject = subject_parts[1].strip()
                    body_start = i + 1
                    break

            # Lấy phần nội dung
            body_lines = []
            if body_start < len(lines):
                # Bỏ qua dòng trống sau tiêu đề nếu có
                if body_start < len(lines) and lines[body_start].strip() == '':
                    body_start += 1

                for i in range(body_start, len(lines)):
                    line = lines[i].strip()
                    if line or (body_lines and body_lines[-1] != ''):  # Giữ 1 dòng trống giữa các đoạn
                        body_lines.append(line)

            # Đảm bảo không có 2 dòng trống liên tiếp
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

            # Xóa dòng trống ở đầu và cuối
            while cleaned_body_lines and cleaned_body_lines[0] == '':
                cleaned_body_lines.pop(0)
            while cleaned_body_lines and cleaned_body_lines[-1] == '':
                cleaned_body_lines.pop(-1)

            # Nếu không có nội dung, tạo nội dung mặc định
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

            # Giới hạn độ dài tiêu đề
            if len(subject) > 100:
                subject = subject[:97] + "..."

            return subject, body

        except Exception as e:
            print(f"❌ Lỗi parse email content: {e}")
            return "Đánh giá hiệu suất công việc", "Kính gửi,\n\nĐây là email đánh giá hiệu suất.\n\nTrân trọng,\nQuản lý"

    def generate_email_preview(self, selected_employees, year, month):
        """Tạo nội dung email preview bằng Gemini - ĐÃ SỬA"""
        try:
            if not self.gemini:
                self.email_preview.setPlainText("⚠️ AI chưa khả dụng. Vui lòng kiểm tra cấu hình Gemini.")
                return

            # Chuẩn bị dữ liệu nhân viên với metrics
            employees_data = []
            for emp in selected_employees:
                # Lấy metrics cho nhân viên
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

                # Thêm thông tin bổ sung
                for field in ['sap', 'pwd', 'client']:
                    if field in emp:
                        employee_info[field] = emp[field]

                employees_data.append(employee_info)

            # Hiển thị thông báo đang tạo
            self.email_preview.setPlainText("🔄 Đang tạo nội dung email bằng AI...\nVui lòng chờ trong giây lát.")

            # Gọi Gemini tạo nội dung email - SỬ DỤNG HÀM MỚI
            email_content = self.gemini.generate_email_content(employees_data)

            # Parse và hiển thị nội dung đã được định dạng
            subject, body = self.parse_email_content(email_content)

            # Hiển thị cả tiêu đề và nội dung
            preview_text = f"TIÊU ĐỀ: {subject}\n\n{body}"
            self.email_preview.setPlainText(preview_text)

            print(f"✅ Đã tạo email preview: {len(subject)} ký tự tiêu đề, {len(body)} ký tự nội dung")

        except Exception as e:
            print(f"❌ Lỗi tạo email preview: {e}")
            import traceback
            traceback.print_exc()
            self.email_preview.setPlainText(f"⚠️ Lỗi tạo nội dung email:\n{str(e)[:200]}")

    def send_ai_generated_emails(self, dialog):
        """Gửi email với nội dung được tạo bởi AI - ĐÃ SỬA"""
        # Lấy danh sách nhân viên được chọn
        selected_employees = self.get_selected_employees()

        if not selected_employees:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một nhân viên!")
            return

        # Lấy năm và tháng filter
        year = int(self.year_combo.currentText()) if self.year_combo.currentText() else datetime.now().year
        month = None
        if self.month_combo.currentText() != "Tất cả":
            month = int(self.month_combo.currentText().split(" ")[1])

        # Kiểm tra email
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

        # Lấy nội dung email từ preview
        email_content = self.email_preview.toPlainText()

        # Kiểm tra nội dung
        if not email_content or "⚠️" in email_content or "🔄" in email_content:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng tạo nội dung email trước khi gửi!")
            return

        # Parse nội dung email
        subject, body = self.parse_email_content(email_content)

        if not body or len(body.strip()) < 20:
            QMessageBox.warning(self, "Cảnh báo", "Nội dung email quá ngắn. Vui lòng tạo lại nội dung!")
            return

        # Xác nhận gửi
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

        # Gửi email
        self.status_bar.setText("📤 Đang gửi email...")

        # Chuẩn bị dữ liệu cho n8n
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
                # Lấy metrics cho personalization
                metrics = self.data_processor.get_employee_performance_metrics(
                    emp['id'],
                    year=year,
                    month=month
                )

                # Tạo nội dung email cá nhân hóa
                personalized_body = self._personalize_email_body(body, emp, metrics)

                # Tạo HTML content từ template
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
                    "cc": "legalgiang@gmail.com",
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

        # Gửi đến n8n
        success = self.send_emails_to_n8n(email_data)

        if success:
            QMessageBox.information(self, "Thành công",
                                    f"✅ Đã gửi {success_count}/{len(selected_employees)} email thành công!")
            dialog.accept()
            self.status_bar.setText(f"✅ Đã gửi {success_count} email")
        else:
            QMessageBox.critical(self, "Lỗi", "❌ Không thể gửi email. Vui lòng thử lại!")
            self.status_bar.setText("❌ Lỗi gửi email")

    def _personalize_email_body(self, base_body, employee, metrics):
        """Cá nhân hóa nội dung email cho từng nhân viên"""
        try:
            emp_name = employee.get('name', employee['id'])

            # Thêm thông tin cá nhân vào đầu email
            personalized_body = f"Kính gửi Anh/Chị {emp_name},\n\n"

            # Thêm thông tin hiệu suất nếu có
            if metrics:
                rank = metrics.get('rank', '')
                score = metrics.get('overall_score', 0)

                if rank and score > 0:
                    personalized_body += f"Dựa trên đánh giá hiệu suất, bạn được xếp hạng: {rank} với {score}/100 điểm.\n\n"

            # Thêm nội dung chính
            personalized_body += base_body

            # Đảm bảo định dạng đúng
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

            # Xóa dòng trống ở cuối
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
        """Xử lý quick action email button - Mở dialog ngay"""
        self.open_employee_selection_dialog()
        self.add_bot_message("📧 **ĐÃ MỞ CỬA SỔ GỬI EMAIL**\n\nVui lòng chọn nhân viên trong cửa sổ vừa mở.")
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
        """Get comprehensive data context for manager - ENHANCED VERSION"""
        if not self.aggregate_data:
            return {
                "status": "no_data",
                "summary": "No aggregate data yet",
                "employee_name": "Manager",
                "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "employees_detail": []
            }

        # Lấy dữ liệu tháng hiện tại từ monthly_data
        monthly_data = self.aggregate_data.get('monthly_data', {})
        current_month = datetime.now().month
        current_year = datetime.now().year

        # Tính các chỉ số tháng này
        revenues = monthly_data.get('revenue', [0] * 12)
        current_month_revenue = revenues[current_month - 1] if current_month <= len(revenues) else 0

        orders = monthly_data.get('orders', [0] * 12)
        current_month_orders = orders[current_month - 1] if current_month <= len(orders) else 0

        frauds = monthly_data.get('fraud', [0] * 12)
        current_month_fraud = frauds[current_month - 1] if current_month <= len(frauds) else 0

        profits = monthly_data.get('profit', [0] * 12)
        current_month_profit = profits[current_month - 1] if current_month <= len(profits) else 0

        # Lấy danh sách nhân viên chi tiết
        employees_detail = self._get_detailed_employees_data(current_year, current_month)

        # Lấy các thông tin xếp hạng
        lowest_performers = self.data_processor.get_lowest_performing_employees(5, current_year, current_month)
        highest_orders = self.data_processor.get_highest_orders_employees(5, current_year, current_month)

        return {
            "status": "ok",
            "employee_name": "Manager (Team Overview)",
            "data_timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

            # Metrics - Tháng hiện tại
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

            # Chi tiết nhân viên
            "employees_detail": employees_detail,

            # Xếp hạng
            "rankings": {
                "lowest_performers": lowest_performers,
                "highest_orders": highest_orders,
                "total_employees_count": len(employees_detail)
            },

            # SAP data structure
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

            # Work log data
            "work_log": {
                "summary": {
                    "fraud_count": int(current_month_fraud),
                    "total_work_hours": 160 * self.aggregate_data.get('employees_with_data', 0),
                    "critical_count": int(current_month_fraud * 0.3)
                }
            },

            "employees": self.get_employee_list() if self.data_processor else [],
            "is_manager": True,

            # Thêm metadata cho chatbot biết các loại câu hỏi có thể trả lời
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
            employees = self.data_processor.get_employee_contact_info()
            if not employees:
                return []

            detailed_data = []

            for emp in employees[:20]:  # Giới hạn 20 nhân viên để tránh quá tải
                emp_id = emp['id']

                # Lấy performance metrics
                metrics = self.data_processor.get_employee_performance_metrics(emp_id, year, month)

                # Lấy detailed performance
                detailed_perf = self.data_processor.get_employee_detailed_performance(emp_id, year, month)

                # Lấy pending orders analysis
                pending_analysis = self.data_processor.get_pending_orders_analysis(emp_id, year, month)

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