#!/usr/bin/env python3
"""
Employee Email Dialog - Dialog for employees to send complaint emails
"""

import sys
import os
from datetime import datetime

import pandas as pd
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import from same directory
try:
    from gemini_analyzer import GeminiAnalyzer

    gemini_available = True
except ImportError:
    gemini_available = False


class EmployeeEmailDialog(QDialog):
    """Dialog for employees to send complaint emails"""

    def __init__(self, parent=None, employee_name="", gemini=None, initial_description="", email_type="complaint"):
        super().__init__(parent)
        self.parent_window = parent
        self.employee_name = employee_name
        self.gemini = gemini
        self.initial_description = initial_description
        self.email_type_from_input = email_type  # Lưu loại email từ input

        self.manager_email = self.load_manager_email()

        self.setWindowTitle("📧 Gửi Khiếu Nại/Đề Xuất")
        self.setMinimumSize(600, 500)

        self.init_ui()
        # Điền sẵn mô tả nếu có
        if self.initial_description and hasattr(self, 'issue_input'):
            self.issue_input.setPlainText(self.initial_description)

            # Tự động tạo email từ mô tả
            QTimer.singleShot(500, self.generate_email_from_description)

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title_label = QLabel("📧 GỬI EMAIL KHIẾU NẠI/ĐỀ XUẤT")
        title_label.setStyleSheet("""
            font-size: 16px;
            font-weight: bold;
            color: #1e40af;
            padding: 15px;
            background-color: #f0f9ff;
            border-radius: 8px;
            text-align: center;
        """)
        layout.addWidget(title_label)

        # Employee info
        info_label = QLabel(f"👤 Người gửi: {self.employee_name}")
        info_label.setStyleSheet("font-size: 14px; font-weight: 500;")
        layout.addWidget(info_label)

        # Issue description
        issue_label = QLabel("📝 Mô tả vấn đề/đề xuất:")
        issue_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(issue_label)

        self.issue_input = QTextEdit()
        self.issue_input.setPlaceholderText(
            "Nhập chi tiết vấn đề bạn gặp phải hoặc đề xuất của bạn...\nVí dụ:\n- Vấn đề về thiết bị làm việc\n- Đề xuất cải tiến quy trình\n- Yêu cầu hỗ trợ kỹ thuật\n- Phản ánh về môi trường làm việc")
        self.issue_input.setMinimumHeight(100)
        self.issue_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 2px solid #3b82f6;
            }
        """)
        layout.addWidget(self.issue_input)

        # Email type selection
        type_label = QLabel("🏷️ Loại email:")
        type_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(type_label)

        type_layout = QHBoxLayout()

        self.type_complaint = QRadioButton("Khiếu nại")
        self.type_suggestion = QRadioButton("Đề xuất")
        self.type_support = QRadioButton("Yêu cầu hỗ trợ")
        self.type_other = QRadioButton("Khác")

        # Set default radio button based on email_type_from_input
        if self.email_type_from_input == "complaint":
            self.type_complaint.setChecked(True)
        elif self.email_type_from_input == "suggestion":
            self.type_suggestion.setChecked(True)
        elif self.email_type_from_input == "request":
            self.type_support.setChecked(True)
        else:
            self.type_other.setChecked(True)

        type_layout.addWidget(self.type_complaint)
        type_layout.addWidget(self.type_suggestion)
        type_layout.addWidget(self.type_support)
        type_layout.addWidget(self.type_other)
        type_layout.addStretch()

        layout.addLayout(type_layout)

        # AI-generated email preview
        preview_label = QLabel("📄 Nội dung email (tự động tạo bởi AI):")
        preview_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-top: 10px;")
        layout.addWidget(preview_label)

        self.email_preview = QTextEdit()
        self.email_preview.setReadOnly(False)  # Cho phép chỉnh sửa
        self.email_preview.setMinimumHeight(150)
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

        self.generate_btn = QPushButton("🤖 AI Soạn email")
        self.generate_btn.clicked.connect(self.generate_email_content)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #7c3aed;
            }
        """)

        self.send_btn = QPushButton("📤 Gửi Email")
        self.send_btn.clicked.connect(self.send_email)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        cancel_btn = QPushButton("Hủy")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)

        button_layout.addWidget(self.generate_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(self.send_btn)

        layout.addLayout(button_layout)

    def load_manager_email(self):
        """Lấy email của quản lý từ file employee_ids.xlsx"""
        try:
            # Đường dẫn file Excel
            excel_path = "C:/Users/legal/PycharmProjects/PythonProject/MG/employee_ids.xlsx"

            # Đọc file Excel
            df = pd.read_excel(excel_path)

            # Tìm quản lý có ID bắt đầu bằng "MG" (Manager)
            manager_row = df[df['ID'].str.upper().str.startswith('MG')]

            if not manager_row.empty:
                # Lấy dòng đầu tiên tìm thấy
                manager = manager_row.iloc[0]
                manager_email = manager['Email']

                if pd.isna(manager_email) or manager_email == '':
                    print(f"⚠️ Quản lý {manager['ID']} không có email trong file")
                    return None  # Fallback
                else:
                    print(f"✅ Tìm thấy email quản lý: {manager_email}")
                    return manager_email
            else:
                print("❌ Không tìm thấy quản lý (MG) trong file")
                return None # Fallback

        except Exception as e:
            print(f"⚠️ Lỗi đọc file Excel: {e}")
            return None  # Fallback

    def generate_email_from_description(self):
        """Tự động tạo email từ mô tả đã được điền sẵn"""
        issue_text = self.issue_input.toPlainText().strip()

        if not issue_text:
            # Nếu không có nội dung, không làm gì
            return

        # Kiểm tra radio button đang được chọn
        if self.type_complaint.isChecked():
            email_type = "khiếu nại"
        elif self.type_suggestion.isChecked():
            email_type = "đề xuất"
        elif self.type_support.isChecked():
            email_type = "yêu cầu hỗ trợ"
        else:
            email_type = "thông tin"

        # Tạo nội dung email
        self.generate_email_content_with_text(issue_text, email_type)

    def generate_email_content_with_text(self, issue_text, email_type):
        """Tạo nội dung email với text và loại email cụ thể"""
        # Generate content using AI
        if self.gemini:
            try:
                email_content = self.gemini.generate_employee_complaint_email(
                    self.employee_name,
                    issue_text,
                    email_type,
                    self.manager_email
                )

                # Parse the content
                subject, body = self.parse_email_content(email_content)
                preview_text = f"TIÊU ĐỀ: {subject}\n\n{body}"
                self.email_preview.setPlainText(preview_text)

            except Exception as e:
                print(f"❌ Lỗi tạo email: {e}")
                # Fallback content
                self.generate_fallback_email(issue_text, email_type)
        else:
            self.generate_fallback_email(issue_text, email_type)

    def generate_email_content(self):
        """Generate email content using AI"""
        issue_text = self.issue_input.toPlainText().strip()

        if not issue_text:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng nhập mô tả vấn đề trước!")
            return

        # Determine email type
        if self.type_complaint.isChecked():
            email_type = "khiếu nại"
        elif self.type_suggestion.isChecked():
            email_type = "đề xuất"
        elif self.type_support.isChecked():
            email_type = "yêu cầu hỗ trợ"
        else:
            email_type = "thông tin"

        # Generate content using AI
        self.generate_email_content_with_text(issue_text, email_type)

    def generate_fallback_email(self, issue_text, email_type):
        """Generate fallback email content"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")

        subject = f"{email_type.upper()} từ nhân viên {self.employee_name}"
        body = f"""Kính gửi Quản lý,

Tôi là {self.employee_name}, xin gửi {email_type} sau:

{issue_text}

Thời gian: {current_time}

Mong nhận được phản hồi từ Quản lý.

Trân trọng,
{self.employee_name}"""

        preview_text = f"TIÊU ĐỀ: {subject}\n\n{body}"
        self.email_preview.setPlainText(preview_text)

    def parse_email_content(self, email_content):
        """Parse email content from AI response"""
        try:
            lines = email_content.strip().split('\n')

            # Find subject line
            subject = "Khiếu nại/Đề xuất từ nhân viên"
            body_start = 0

            for i, line in enumerate(lines):
                line_clean = line.strip()
                if line_clean.startswith('TIÊU ĐỀ:') or line_clean.startswith('Tiêu đề:'):
                    subject_parts = line_clean.split(':', 1)
                    if len(subject_parts) > 1:
                        subject = subject_parts[1].strip()
                    body_start = i + 1
                    break

            # Get body content
            body_lines = []
            if body_start < len(lines):
                if body_start < len(lines) and lines[body_start].strip() == '':
                    body_start += 1

                for i in range(body_start, len(lines)):
                    line = lines[i].strip()
                    if line or (body_lines and body_lines[-1] != ''):
                        body_lines.append(line)

            # Clean up consecutive empty lines
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

            # Remove leading/trailing empty lines
            while cleaned_body_lines and cleaned_body_lines[0] == '':
                cleaned_body_lines.pop(0)
            while cleaned_body_lines and cleaned_body_lines[-1] == '':
                cleaned_body_lines.pop(-1)

            body = '\n'.join(cleaned_body_lines)

            return subject, body

        except Exception as e:
            print(f"❌ Lỗi parse email content: {e}")
            return "Khiếu nại/Đề xuất từ nhân viên", email_content

    def send_email(self):
        """Send the email"""
        email_content = self.email_preview.toPlainText().strip()

        if not email_content:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng tạo nội dung email trước khi gửi!")
            return

        # Parse subject and body
        subject, body = self.parse_email_content(email_content)

        # Confirm sending
        reply = QMessageBox.question(
            self, "Xác nhận gửi email",
            f"Gửi email đến quản lý ({self.manager_email})?\n\nTiêu đề: {subject}\n\nTiếp tục?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.No:
            return

        # Prepare data for n8n
        email_data = {
            "test_mode": False,
            "timestamp": datetime.now().isoformat(),
            "to_email": self.manager_email,
            "subject": subject,
            "body": body,
            "employee_name": self.employee_name,
            "email_type": "employee_complaint",
            "cc": self.employee_name  # CC cho nhân viên
        }

        # Send via n8n (cùng webhook với manager)
        success = self.send_to_n8n(email_data)

        if success:
            QMessageBox.information(self, "Thành công", "✅ Email đã được gửi thành công đến quản lý!")
            self.accept()
        else:
            QMessageBox.critical(self, "Lỗi", "❌ Không thể gửi email. Vui lòng thử lại!")

    def send_to_n8n(self, email_data):
        """Send email via n8n webhook"""
        try:
            import requests
            n8n_webhook_url = "http://localhost:5678/webhook/349efadb-fad2-4589-9827-f99d94e3ac31"

            response = requests.post(
                n8n_webhook_url,
                json=email_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code in [200, 201]:
                print(f"✅ Đã gửi email khiếu nại từ {self.employee_name}")
                return True
            else:
                print(f"❌ Lỗi gửi email: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Exception khi gửi email: {e}")
            return False


if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = EmployeeEmailDialog(employee_name="EM001")
    dialog.show()
    sys.exit(app.exec())