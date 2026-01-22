#!/usr/bin/env python3
"""
Employee Chatbot - PowerSight Employee Assistant
Giao diện giống manager_chatbot nhưng tính năng cho nhân viên
"""

import random
import sys
import os
from pathlib import Path
from datetime import datetime

# Add path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

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


class EmployeeChatbotGUI(QMainWindow):
    """Employee Chatbot với giao diện giống manager_chatbot"""

    def __init__(self, user_name=None, parent=None):
        super().__init__(parent)

        # Initialize with Config
        if config_available and Config:
            if user_name:
                self.employee_name = user_name
            else:
                self.employee_name = Config.DEFAULT_EMPLOYEE_NAME
            app_name = Config.APP_NAME
        else:
            self.employee_name = user_name if user_name else "MG001"
            app_name = "PowerSight Employee Assistant"

        print(f"🤖 Khởi tạo chatbot cho: {self.employee_name}")

        # Store parent window for going back
        self.parent_window = parent

        # Initialize AI
        self.gemini = None
        if gemini_available:
            try:
                self.gemini = GeminiAnalyzer()
            except Exception as e:
                print(f"⚠️ Gemini initialization error: {e}")
        else:
            print("⚠️ Gemini không khả dụng, sử dụng chế độ DEMO")

        # Initialize Data Processor
        self.data_processor = None
        if dataprocessor_available:
            try:
                self.data_processor = DataProcessor(self.employee_name)
            except Exception as e:
                print(f"⚠️ DataProcessor initialization error: {e}")
        else:
            print("⚠️ DataProcessor không khả dụng")

        # Initialize UI với giao diện giống manager_chatbot
        self.init_ui(app_name)

        # Show welcome message
        self.show_welcome_message()

        # Auto load data
        QTimer.singleShot(1000, self.load_initial_data)

    def init_ui(self, app_name):
        """Khởi tạo giao diện giống manager_chatbot"""
        self.setWindowTitle(f"💬 {app_name} - Chat Assistant")
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

        # Home button
        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setFixedSize(80, 35)
        self.home_btn.clicked.connect(self.go_back_to_home)
        self.home_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        # Status indicator
        self.status_indicator = QLabel("●" if self.gemini else "○")
        self.status_indicator.setStyleSheet(f"""
            QLabel {{
                color: {"#10b981" if self.gemini else "#ef4444"};
                font-size: 20px;
                font-weight: bold;
            }}
        """)

        title_label = QLabel(f"💬 CHATBOT HỖ TRỢ NHÂN VIÊN - {app_name}")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #1e40af;
            }
        """)

        header_layout.addWidget(self.home_btn)
        header_layout.addWidget(self.status_indicator)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

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
        self.input_field.setPlaceholderText("Nhập câu hỏi về hiệu suất, phát triển, doanh thu...")
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

        # Quick actions - Employee specific
        quick_actions_widget = QWidget()
        quick_layout = QHBoxLayout(quick_actions_widget)
        quick_layout.setContentsMargins(0, 0, 0, 0)
        quick_layout.setSpacing(10)

        quick_buttons = [
            ("📊 Phân tích hiệu suất", "phân tích hiệu suất làm việc của tôi"),
            ("🎯 Mục tiêu phát triển", "mục tiêu phát triển của tôi là gì"),
            ("📚 Đề xuất đào tạo", "khóa học nào phù hợp với tôi"),
            ("⚠️ Vấn đề cần sửa", "những lỗi nào tôi đang mắc phải"),
            ("💰 Tối ưu doanh thu", "làm thế nào để tăng doanh thu"),
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

        # Status bar
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

        # Show welcome message in UI
        self.show_welcome_ui()

    def show_welcome_ui(self):
        """Hiển thị thông báo chào mừng trong UI"""
        self.add_bot_message(f"Xin chào {self.employee_name}! Tôi là chatbot hỗ trợ nhân viên.")
        self.add_bot_message("Tôi có thể giúp bạn với:")
        self.add_bot_message("• Phân tích hiệu suất làm việc")
        self.add_bot_message("• Mục tiêu phát triển cá nhân")
        self.add_bot_message("• Đề xuất khóa học phù hợp")
        self.add_bot_message("• Tối ưu doanh thu và hiệu suất")

        if not self.gemini:
            self.add_bot_message(
                "⚠️ **Lưu ý**: Gemini AI chưa khả dụng. Đang sử dụng chế độ DEMO.")

    def go_back_to_home(self):
        """Quay về HomeWindow"""
        if self.parent_window:
            try:
                self.parent_window.showNormal()
                self.parent_window.raise_()
                self.parent_window.activateWindow()
                if hasattr(self.parent_window, 'on_chatbot_closed'):
                    self.parent_window.on_chatbot_closed()
            except Exception as e:
                print(f"Lỗi khi khôi phục home window: {e}")
        self.close()

    def show_welcome_message(self):
        """Hiển thị thông báo chào mừng (backend)"""
        ai_status = "✓ Khả dụng" if self.gemini else "✗ CHẾ ĐỘ DEMO"
        data_status = "✓ Khả dụng" if self.data_processor else "✗ Không khả dụng"

        welcome = f"""**CHÀO MỪNG ĐẾN POWER SIGHT AI ASSISTANT**

**👤 Nhân viên:** {self.employee_name}
**📅 Ngày:** {datetime.now().strftime('%d/%m/%Y')}

**🛠️ TRẠNG THÁI HỆ THỐNG:**
• AI Assistant: {ai_status}
• Data Processor: {data_status}

**🤖 TÔI CÓ THỂ GIÚP BẠN:**
• Phân tích hiệu suất làm việc hàng năm
• Đề xuất cải thiện và phát triển hàng tháng
• Cảnh báo vấn đề cần sửa
• Tư vấn chiến lược doanh thu
• Đề xuất khóa học phù hợp

**🚀 HÀNH ĐỘNG NHANH:**
- Sử dụng các nút bên dưới cho câu hỏi nhanh
- Chat tự nhiên bằng tiếng Việt/Anh
- **Nhấn "🏠 Home" để quay về menu chính**

**⏳ Đang tải dữ liệu từ hệ thống...**"""

        self.add_bot_message(welcome)

    def load_initial_data(self):
        """Tải dữ liệu ban đầu"""
        self.status_indicator.setText("🔄")
        self.status_bar.setText("📂 Đang đọc dữ liệu từ hệ thống...")
        self.send_button.setEnabled(False)

        try:
            if not self.data_processor:
                self.status_indicator.setText("○")
                self.status_bar.setText("❌ Module DataProcessor không khả dụng")
                self.send_button.setEnabled(True)
                self.add_bot_message("⚠️ Không thể tải dữ liệu. DataProcessor không khả dụng.")
                return

            success = self.data_processor.load_all_data()

            if success:
                data = self.data_processor.get_summary_data()
                work_log_data = data.get('work_log', {})
                sap_data = data.get('sap', {})
                metrics = data.get('metrics', {})

                self.status_indicator.setText("●")
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        color: #10b981;
                        font-size: 20px;
                        font-weight: bold;
                    }
                """)

                fraud_count = work_log_data.get('fraud_count', 0)
                warning_count = work_log_data.get('warning_count', 0)
                sap_orders = sap_data.get('total_orders', 0)
                pending_orders = sap_data.get('pending_orders', 0)

                year_summary = self.data_processor.get_year_summary()
                if year_summary:
                    total_orders_year = year_summary.get('total_orders', 0)
                    months_with_data = year_summary.get('months_with_data', 0)

                    self.status_bar.setText(
                        f"📅 {year_summary.get('year', datetime.now().year)}: {months_with_data} tháng | "
                        f"📊 WL: {fraud_count} gian lận | "
                        f"🛒 SAP: {sap_orders} đơn ({pending_orders} đang chờ)"
                    )
                else:
                    self.status_bar.setText(
                        f"📊 WL: {fraud_count} gian lận, {warning_count} cảnh báo | "
                        f"🛒 SAP: {sap_orders} đơn ({pending_orders} đang chờ)"
                    )

                self.send_button.setEnabled(True)

                summary_msg = self._create_summary_message(
                    work_log_data, sap_data, metrics, year_summary
                )

                self.add_bot_message(summary_msg)
            else:
                self.status_indicator.setText("○")
                self.status_indicator.setStyleSheet("""
                    QLabel {
                        color: #ef4444;
                        font-size: 20px;
                        font-weight: bold;
                    }
                """)
                self.status_bar.setText("❌ Không thể tải đầy đủ dữ liệu")
                self.add_bot_message("Không thể tải đầy đủ dữ liệu. Vui lòng kiểm tra file dữ liệu!")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            self.status_indicator.setText("○")
            self.status_indicator.setStyleSheet("""
                QLabel {
                    color: #ef4444;
                    font-size: 20px;
                    font-weight: bold;
                }
            """)
            self.status_bar.setText(f"Lỗi: {str(e)[:50]}")
            self.send_button.setEnabled(True)
            self.add_bot_message(f"❌ Lỗi khi tải dữ liệu: {str(e)}")

    def _create_summary_message(self, work_log_data, sap_data, metrics, year_summary):
        """Tạo thông báo tổng hợp với dữ liệu hàng năm"""
        current_year = datetime.now().year

        fraud_count = work_log_data.get('fraud_count', 0)
        warning_count = work_log_data.get('warning_count', 0)
        sap_orders = sap_data.get('total_orders', 0)
        pending_orders = sap_data.get('pending_orders', 0)
        completion_rate = sap_data.get('completion_rate', 0)
        revenue = sap_data.get('total_revenue', 0)
        profit = sap_data.get('total_profit', 0)
        profit_margin = sap_data.get('profit_margin', 0)

        message = f"""**✅ ĐÃ TẢI DỮ LIỆU THÀNH CÔNG**

**📅 Thời gian:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

"""

        if year_summary:
            total_orders_year = year_summary.get('total_orders', 0)
            total_revenue_year = year_summary.get('total_revenue', 0)
            total_profit_year = year_summary.get('total_profit', 0)
            total_fraud_year = year_summary.get('total_fraud', 0)
            months_with_data = year_summary.get('months_with_data', 0)
            year_completion_rate = year_summary.get('completion_rate', 0)
            best_month = year_summary.get('best_month', 0)
            best_month_revenue = year_summary.get('best_month_revenue', 0)

            message += f"""**📊 TỔNG QUAN HÀNG NĂM {current_year}:**
• **Phạm vi dữ liệu:** {months_with_data}/12 tháng
• **Tổng đơn hàng năm:** {total_orders_year:,}
• **Tổng doanh thu năm:** {total_revenue_year:,.0f} VND
• **Tổng lợi nhuận năm:** {total_profit_year:,.0f} VND
• **Tổng gian lận năm:** {total_fraud_year}
• **Tỷ lệ hoàn thành năm:** {year_completion_rate:.1f}%
• **Tháng hiệu quả nhất:** Tháng {best_month} ({best_month_revenue:,.0f} VND)

"""

        message += f"""**🔍 PHÂN TÍCH WORK LOG (THÁNG HIỆN TẠI):**
• Sự kiện gian lận: {fraud_count}
• Cảnh báo nghiêm trọng: {work_log_data.get('critical_count', 0)}
• Cảnh báo nhẹ: {warning_count}
• Thời gian làm việc: {work_log_data.get('total_work_hours', 0)}h

**📈 TỔNG QUAN DỮ LIỆU SAP (THÁNG HIỆN TẠI):**
• Tổng đơn hàng: {sap_orders:,}
• Đã hoàn thành: {sap_data.get('completed_orders', 0):,} ({completion_rate:.1f}%)
• Đang chờ xử lý: {pending_orders:,}
• Doanh thu: {revenue:,.0f} VND
• Lợi nhuận: {profit:,.0f} VND
• Biên lợi nhuận: {profit_margin:.1f}%

**📊 CHỈ SỐ THỰC TẾ:**
• **Hiệu suất làm việc:** {metrics.get('efficiency', 0):.1f}/100 (dựa trên đơn/giờ)
• **Chất lượng công việc:** {metrics.get('quality', 0):.1f}/100 (dựa trên hoàn thành & lợi nhuận)
• **Tuân thủ:** {metrics.get('compliance', 0):.1f}/100 (dựa trên quy định)
• **Năng suất kinh doanh:** {metrics.get('productivity', 0):.1f}/100 (dựa trên doanh thu & lợi nhuận)
• **Tỷ lệ lỗi:** {metrics.get('error_rate', 0):.1f}%
• **Hiệu quả thời gian:** {metrics.get('time_efficiency', 0):.1f}%

"""

        if year_summary:
            message += """**💡 ĐỀ XUẤT HÀNH ĐỘNG (DỰA TRÊN DỮ LIỆU NĂM):**
1. **Hỏi "Phân tích hiệu suất hàng tháng"** - So sánh giữa các tháng
2. **Hỏi "Tháng nào có doanh thu cao nhất?"** - Tìm điểm mạnh theo mùa
3. **Hỏi "Làm thế nào để duy trì hiệu suất cao?"** - Nhận tư vấn chiến lược dài hạn"""
        else:
            message += """**💡 ĐỀ XUẤT HÀNH ĐỘNG:**
1. **Hỏi "Đơn hàng nào chưa xử lý?"** - Kiểm tra trạng thái đơn hàng
2. **Hỏi "Làm thế nào để cải thiện hiệu suất?"** - Nhận tư vấn chiến lược
3. **Hỏi "Phân tích doanh thu theo tháng"** - Phân tích dữ liệu hàng tháng"""

        return message

    def quick_command(self, command):
        """Xử lý lệnh nhanh"""
        self.input_field.setText(command)
        self.send_message()

    def send_message(self):
        """Xử lý tin nhắn người dùng"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        # Thêm tin nhắn người dùng
        self.add_user_message(user_input)
        self.input_field.clear()
        self.send_button.setEnabled(False)
        self.status_bar.setText("🤔 AI đang phân tích...")

        context_data = {}
        if self.data_processor:
            try:
                context_data = self.data_processor.get_enhanced_context()
            except Exception as e:
                print(f"⚠️ Không thể lấy dữ liệu context: {e}")

        self.chat_thread = ChatThread(self.gemini, user_input, context_data)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def on_ai_response(self, response):
        """Nhận phản hồi từ AI"""
        self.add_bot_message(response)
        self.send_button.setEnabled(True)
        self.status_bar.setText("✅ Sẵn sàng")

    def on_ai_error(self, error):
        """Xử lý lỗi AI"""
        error_msg = f"""**❌ LỖI HỆ THỐNG**

Không thể kết nối đến dịch vụ AI:

**Chi tiết:** {error}

**Khắc phục sự cố:**
1. Kiểm tra kết nối Internet
2. Đảm bảo API Key hợp lệ trong file .env
3. Thử lại sau vài phút

**Chế độ DEMO sẽ được sử dụng tạm thời.**"""

        self.add_bot_message(error_msg)
        self.send_button.setEnabled(True)
        self.status_bar.setText("⚠️ Đã xảy ra lỗi")

    def add_bot_message(self, message):
        """Thêm tin nhắn từ bot"""
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #f1f5f9; border-radius: 8px;'>"
            f"<b>🤖 PowerSight AI:</b> {message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def add_user_message(self, message):
        """Thêm tin nhắn từ người dùng"""
        timestamp = datetime.now().strftime("%H:%M")
        self.chat_display.append(
            f"<div style='margin: 5px 0; padding: 10px; background-color: #dbeafe; border-radius: 8px; text-align: right;'>"
            f"<b>👤 {self.employee_name}:</b> {message}<br>"
            f"<small style='color: #64748b;'>{timestamp}</small></div>")
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        """Cuộn xuống cuối"""
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def closeEvent(self, event):
        """Xử lý đóng cửa sổ"""
        if self.parent_window and hasattr(self.parent_window, 'on_chatbot_closed'):
            try:
                self.parent_window.on_chatbot_closed()
            except:
                pass
        event.accept()


class ChatThread(QThread):
    """Thread xử lý chat"""
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
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Hiệu suất của bạn hiện đang ổn định. Tập trung hoàn thành đơn hàng đúng hạn để cải thiện tỷ lệ hoàn thành.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Dữ liệu hàng năm cho thấy bạn cần giảm cảnh báo trong quy trình làm việc. Kiểm tra kỹ các bước trước khi gửi.",
                ]
                response = random.choice(demo_responses)
                self.response_ready.emit(response)
                return

            response = self.gemini.analyze_question(self.question, self.context_data)
            self.response_ready.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))


def main():
    """Hàm chính"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("PowerSight Employee Assistant")

    window = EmployeeChatbotGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()