#!/usr/bin/env python3
"""
Employee Chatbot - PowerSight Employee Assistant
Giao diện đồng bộ hóa hoàn toàn với manager_chatbot
"""

import sys
import os
import re  # Thêm import re để trích xuất thông tin
from pathlib import Path
from datetime import datetime
import traceback

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from PyQt6.QtCore import QTimer, pyqtSignal, Qt

# Import modules with try-except
try:
    from config import Config

    config_available = True
except ImportError:
    print("⚠️ Cannot import config.py")
    config_available = False
    Config = None

try:
    from gemini_analyzer import GeminiAnalyzer

    gemini_available = True
except ImportError as e:
    print(f"⚠️ Cannot import gemini_analyzer: {e}")
    gemini_available = False

try:
    from data_processor import DataProcessor

    dataprocessor_available = True
except ImportError as e:
    print(f"⚠️ Cannot import data_processor: {e}")
    dataprocessor_available = False

try:
    from employee_email_dialog import EmployeeEmailDialog
    email_dialog_available = True
except ImportError as e:
    print(f"⚠️ Cannot import employee_email_dialog: {e}")
    email_dialog_available = False


class EmployeeChatbotGUI(QMainWindow):
    """Employee Chatbot với giao diện đồng bộ hóa với Manager version"""

    def __init__(self, user_name=None, parent=None):
        super().__init__(parent)
        self.parent_window = parent

        # Set to maximize
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Initialize with Config
        if config_available and Config:
            self.employee_name = user_name if user_name else Config.DEFAULT_EMPLOYEE_NAME
            app_name = Config.APP_NAME
        else:
            self.employee_name = user_name if user_name else "EM001"
            app_name = "PowerSight Assistant"

        print(f"🤖 Khởi tạo chatbot cho: {self.employee_name}")

        # Initialize AI
        self.gemini = self.initialize_gemini()

        # Initialize Data Processor
        self.data_processor = self.initialize_data_processor()

        # Biến cho email system
        self.email_request_state = {
            'waiting_confirmation': False,
            'original_command': '',
            'email_type': 'complaint'
        }
        self.current_email_description = ""

        # Initialize UI
        self.init_ui(app_name)

        # Show welcome messages
        self.show_welcome_sequence()

        # Load initial data
        QTimer.singleShot(1000, self.load_initial_data)

    def initialize_gemini(self):
        """Khởi tạo Gemini Analyzer"""
        if gemini_available:
            try:
                return GeminiAnalyzer()
            except Exception as e:
                print(f"⚠️ Error initializing Gemini: {e}")
        return None

    def initialize_data_processor(self):
        """Khởi tạo Data Processor cho nhân viên cụ thể"""
        if dataprocessor_available:
            try:
                return DataProcessor(self.employee_name)
            except Exception as e:
                print(f"⚠️ Error initializing Data Processor: {e}")
        return None

    def init_ui(self, app_name):
        """Khởi tạo giao diện đồng bộ hoàn toàn với manager_chatbot"""
        self.setWindowTitle(f"💬 {app_name} - Employee Chat")
        self.setGeometry(200, 200, 700, 600)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # --- HEADER ---
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

        title_label = QLabel(f"💬 EMPLOYEE SUPPORT CHATBOT - {app_name}")
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
        home_btn.clicked.connect(self.go_back_to_home)

        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(home_btn)

        layout.addWidget(header_widget)

        # --- CHAT DISPLAY ---
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

        # --- INPUT AREA ---
        input_widget = QWidget()
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Nhập câu hỏi về hiệu suất cá nhân, doanh thu, mục tiêu phát triển...")
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

        self.send_button = QPushButton("Gửi")
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

        # --- QUICK ACTIONS ---
        quick_actions_widget = QWidget()
        quick_layout = QHBoxLayout(quick_actions_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(10)

        quick_buttons = [
            ("📊 Hiệu suất của tôi", "phân tích hiệu suất làm việc của tôi"),
            ("🎯 Mục tiêu tháng", "mục tiêu phát triển của tôi trong tháng này là gì"),
            ("📚 Khóa học đề xuất", "những khóa học nào phù hợp để tôi cải thiện kỹ năng"),
            ("💰 Doanh thu cá nhân", "tổng hợp doanh thu của tôi tháng này"),
            ("📧 Gửi khiếu nại", self.open_complaint_email),
            ("⚠️ Cảnh báo lỗi", "tôi có những lỗi Work Log hay vấn đề gì cần sửa không"),
            ("🔄 Tải lại dữ liệu", self.load_initial_data)
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

        # --- STATUS BAR ---
        self.status_bar = QLabel(f"Trạng thái: Đang khởi tạo...")
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

    def show_welcome_sequence(self):
        """Hiển thị chuỗi tin nhắn chào mừng đẹp mắt"""
        self.add_bot_message(f"Xin chào **{self.employee_name}**! Tôi là AI Assistant hỗ trợ riêng cho bạn.")
        self.add_bot_message("Tôi có thể giúp bạn các vấn đề sau:")
        self.add_bot_message("• Phân tích hiệu suất làm việc và doanh thu\n"
                             "• Theo dõi trạng thái đơn hàng SAP\n"
                             "• Cảnh báo các lỗi tuân thủ Work Log\n"
                             "• Đề xuất lộ trình phát triển và đào tạo")
        self.add_bot_message("• Gửi khiếu nại/đề xuất đến quản lý (gõ 'gửi email' hoặc nhấn nút 📧)")

        if not self.gemini:
            self.add_bot_message("⚠️ **Lưu ý**: Hệ thống đang chạy ở chế độ **DEMO** (AI chưa kết nối).")

    def go_back_to_home(self):
        """Quay lại màn hình Home"""
        if self.parent_window:
            self.parent_window.show()
        self.close()

    def add_bot_message(self, message):
        """Thêm tin nhắn từ bot (Style đồng bộ Manager)"""
        timestamp = datetime.now().strftime("%H:%M")
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #f1f5f9; border-radius: 8px;'>"
            f"<b>🤖 PowerSight AI:</b> {formatted_message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def add_user_message(self, message):
        """Thêm tin nhắn từ người dùng (Style đồng bộ Manager)"""
        timestamp = datetime.now().strftime("%H:%M")
        formatted_message = message.replace('\n', '<br>')
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #dbeafe; border-radius: 8px; text-align: right;'>"
            f"<b>👤 {self.employee_name}:</b> {formatted_message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Cuộn xuống cuối chat"""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def quick_command(self, command):
        """Xử lý các câu lệnh nhanh"""
        self.input_field.setText(command)
        self.send_message()

    def load_initial_data(self):
        """Tải dữ liệu ban đầu từ DataProcessor"""
        self.status_indicator.setText("🔄")
        self.status_bar.setText("📂 Đang tải dữ liệu cá nhân...")
        self.send_button.setEnabled(False)

        try:
            if not self.data_processor:
                self.status_bar.setText("❌ Không có bộ xử lý dữ liệu")
                self.send_button.setEnabled(True)
                return

            success = self.data_processor.load_all_data()
            if success:
                self.status_indicator.setText("●")
                self.status_indicator.setStyleSheet("QLabel { color: #10b981; font-size: 20px; font-weight: bold; }")
                self.send_button.setEnabled(True)

                # Lấy tóm tắt nhanh để hiển thị status bar
                data = self.data_processor.get_summary_data()
                sap = data.get('sap', {})
                wl = data.get('work_log', {})

                self.status_bar.setText(
                    f"📊 WL: {wl.get('fraud_count', 0)} lỗi | "
                    f"💰 Doanh thu: {sap.get('total_revenue', 0):,.0f} VND | "
                    f"🛒 Đơn hàng: {sap.get('total_orders', 0)}"
                )

                # Gửi báo cáo tóm tắt tự động
                self.show_performance_summary(data)
            else:
                self.status_bar.setText("⚠️ Dữ liệu trống hoặc lỗi file")
                self.send_button.setEnabled(True)

        except Exception as e:
            print(f"❌ Error loading data: {e}")
            self.status_bar.setText(f"❌ Lỗi: {str(e)[:40]}")
            self.send_button.setEnabled(True)

    def show_performance_summary(self, data):
        """Hiển thị báo cáo tóm tắt ban đầu"""
        sap = data.get('sap', {})
        wl = data.get('work_log', {})
        metrics = data.get('metrics', {})

        summary = f"""**📊 TÓM TẮT HIỆU SUẤT CỦA BẠN**

**📈 DỮ LIỆU SAP:**
- Tổng đơn hàng: {sap.get('total_orders', 0)}
- Tỷ lệ hoàn thành: {sap.get('completion_rate', 0):.1f}%
- Doanh thu: {sap.get('total_revenue', 0):,.0f} VND

**⚠️ WORK LOG & TUÂN THỦ:**
- Sự kiện nghi vấn: {wl.get('fraud_count', 0)}
- Cảnh báo nghiêm trọng: {wl.get('critical_count', 0)}
- Tổng giờ làm: {wl.get('total_work_hours', 0)}h

**🎯 ĐIỂM ĐÁNH GIÁ:**
- Chỉ số chất lượng: {metrics.get('quality', 0):.1f}/100
- Chỉ số tuân thủ: {metrics.get('compliance', 0):.1f}/100

*Hãy hỏi tôi nếu bạn cần phân tích chi tiết hơn!*"""
        self.add_bot_message(summary)

    # ========================== EMAIL FUNCTIONALITY ==========================

    def check_email_intent(self, user_input):
        """Phát hiện ý định gửi email từ câu nói - CẢI THIỆN"""
        user_input_lower = user_input.lower()

        # Các từ khóa phát hiện ý định gửi email
        email_keywords = [
            'gửi mail', 'gửi email', 'send email', 'email',
            'khiếu nại', 'phàn nàn', 'complaint', 'than phiền',
            'đề xuất', 'suggestion', 'kiến nghị', 'ý kiến',
            'yêu cầu', 'request', 'thắc mắc', 'vấn đề',
            'liên hệ quản lý', 'gặp quản lý', 'báo cáo',
            'mail cho manager', 'gửi cho sếp', 'thông báo'
        ]

        # Kiểm tra từ khóa cơ bản
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
            'email tới',
            'soạn mail',
            'soạn email',
            'tạo mail',
            'tạo email'
        ]

        for pattern in email_patterns:
            if pattern in user_input_lower:
                return True

        return False

    def detect_email_type_and_description(self, user_input):
        """Phát hiện loại email và trích xuất mô tả từ câu nói"""
        user_input_lower = user_input.lower()

        # Phát hiện loại email
        email_type_patterns = [
            ('complaint', ['phàn nàn về', 'khiếu nại về', 'than phiền về']),
            ('suggestion', ['đề xuất về', 'kiến nghị về', 'ý kiến về']),
            ('request', ['yêu cầu về', 'xin về', 'đề nghị về']),
            ('report', ['báo cáo về', 'thông báo về']),
            ('complaint', ['phàn nàn', 'khiếu nại', 'than phiền']),
            ('suggestion', ['đề xuất', 'kiến nghị', 'ý kiến']),
            ('request', ['yêu cầu', 'xin', 'đề nghị']),
            ('report', ['báo cáo', 'thông báo'])
        ]

        detected_type = 'complaint'  # Mặc định là khiếu nại
        description = user_input

        # Tìm loại email
        for email_type, patterns in email_type_patterns:
            for pattern in patterns:
                if pattern in user_input_lower:
                    detected_type = email_type
                    # Trích xuất mô tả sau từ khóa
                    pattern_index = user_input_lower.find(pattern)
                    if pattern_index != -1:
                        after_keyword = user_input[pattern_index + len(pattern):].strip()
                        if after_keyword and len(after_keyword) > 3:
                            description = after_keyword
                    break
            if detected_type != 'complaint':
                break

        return detected_type, description

    def handle_email_confirmation(self, user_input):
        """Xử lý phản hồi confirm của người dùng"""
        if not self.email_request_state['waiting_confirmation']:
            return False

        user_input_lower = user_input.lower()
        confirm_keywords = ['có', 'yes', 'y', 'ok', 'oke', 'okay', 'đồng ý', 'chắc chắn', 'được']
        deny_keywords = ['không', 'no', 'n', 'cancel', 'hủy', 'thôi', 'đừng']

        if any(keyword in user_input_lower for keyword in confirm_keywords):
            # Người dùng đồng ý
            self.add_bot_message("✅ Đã xác nhận. Đang mở cửa sổ soạn email...")
            self.email_request_state['waiting_confirmation'] = False
            QTimer.singleShot(500, self.open_complaint_email_with_description)
            return True
        elif any(keyword in user_input_lower for keyword in deny_keywords):
            # Người dùng từ chối
            self.add_bot_message("❌ Đã hủy yêu cầu gửi email.")
            self.email_request_state['waiting_confirmation'] = False
            self.send_button.setEnabled(True)
            return True

        return False

    def prompt_email_confirmation(self, user_input, description):
        """Hiển thị prompt xác nhận gửi email"""
        confirmation_msg = f"""⚠️ **XÁC NHẬN GỬI EMAIL**

Bạn muốn gửi email với nội dung:
"{description[:100]}..."

Gửi email khiếu nại/đề xuất này đến quản lý?

Trả lời: 'Có' hoặc 'Không'"""

        self.add_bot_message(confirmation_msg)

        # Lưu trạng thái
        self.email_request_state['waiting_confirmation'] = True
        self.email_request_state['original_command'] = user_input
        self.current_email_description = description

    def open_complaint_email_with_description(self):
        """Mở dialog với mô tả đã trích xuất"""
        try:
            if not email_dialog_available:
                self.add_bot_message("❌ Chức năng gửi email chưa khả dụng")
                return

            # Lấy email type từ trạng thái
            email_type = self.email_request_state.get('email_type', 'complaint')
            description = self.current_email_description

            dialog = EmployeeEmailDialog(
                self,
                self.employee_name,
                self.gemini,
                initial_description=description,
                email_type=email_type
            )

            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                self.add_bot_message("✅ Đã gửi email khiếu nại đến quản lý thành công!")

            # Reset state
            self.email_request_state['waiting_confirmation'] = False
            self.email_request_state['original_command'] = ''
            self.current_email_description = ""

        except Exception as e:
            print(f"❌ Lỗi khi mở dialog email: {e}")
            import traceback
            traceback.print_exc()
            self.add_bot_message(f"❌ Lỗi khi mở cửa sổ email: {str(e)}")

    def send_message(self):
        """Xử lý gửi tin nhắn"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        self.add_user_message(user_input)
        self.input_field.clear()

        # Kiểm tra nếu đang chờ confirm
        if self.email_request_state['waiting_confirmation']:
            if self.handle_email_confirmation(user_input):
                return

        # Kiểm tra nếu là lệnh gửi email
        if self.check_email_intent(user_input):
            # Trích xuất thông tin chi tiết
            email_type, description = self.detect_email_type_and_description(user_input)

            print(f"DEBUG: Phát hiện email - Loại: {email_type}, Mô tả: {description}")

            # Lưu thông tin
            self.email_request_state['email_type'] = email_type
            self.current_email_description = description

            # Hiển thị prompt xác nhận
            self.prompt_email_confirmation(user_input, description)
            return

        # Nếu không phải lệnh email, xử lý bình thường
        self.send_button.setEnabled(False)
        self.status_bar.setText("🤔 AI đang suy nghĩ...")

        # Lấy context dữ liệu để gửi cho AI
        context_data = {}
        if self.data_processor:
            context_data = self.data_processor.get_enhanced_context()

        # Khởi chạy thread xử lý AI
        self.chat_thread = EmployeeChatThread(self.gemini, user_input, context_data, self.employee_name)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def on_ai_response(self, response):
        """Kết quả trả về từ AI"""
        self.add_bot_message(response)
        self.send_button.setEnabled(True)
        self.status_bar.setText("✅ Sẵn sàng")

    def on_ai_error(self, error):
        """Xử lý khi lỗi AI"""
        self.add_bot_message(f"❌ **Lỗi kết nối AI**: {error}\n\nĐang sử dụng phản hồi mẫu.")
        self.send_button.setEnabled(True)
        self.status_bar.setText("⚠️ Có lỗi xảy ra")

    def open_complaint_email(self):
        """Mở dialog gửi khiếu nại - từ nút Quick Action"""
        try:
            if not email_dialog_available:
                self.add_bot_message("❌ Chức năng gửi email chưa khả dụng")
                return

            dialog = EmployeeEmailDialog(
                self,
                self.employee_name,
                self.gemini,
                initial_description="",
                email_type="complaint"
            )

            result = dialog.exec()

            if result == QDialog.DialogCode.Accepted:
                self.add_bot_message("✅ Đã gửi email khiếu nại đến quản lý thành công!")

        except Exception as e:
            print(f"❌ Lỗi khi mở dialog email: {e}")
            import traceback
            traceback.print_exc()
            self.add_bot_message(f"❌ Lỗi khi mở cửa sổ email: {str(e)}")


class EmployeeChatThread(QThread):
    """Thread xử lý AI tách biệt với UI để tránh treo app"""
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, gemini, question, context_data, employee_name):
        super().__init__()
        self.gemini = gemini
        self.question = question
        self.context_data = context_data
        self.employee_name = employee_name

    def run(self):
        try:
            if not self.gemini:
                # Phản hồi giả lập nếu không có Gemini
                import time
                time.sleep(1)
                self.response_ready.emit(
                    f"Dữ liệu của bạn ({self.employee_name}) cho thấy hiệu suất đang ở mức tốt. Tuy nhiên cần chú ý giảm các lỗi Work Log.")
                return

            response = self.gemini.analyze_question(self.question, self.context_data)
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = EmployeeChatbotGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()