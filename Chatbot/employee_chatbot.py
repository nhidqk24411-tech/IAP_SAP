#!/usr/bin/env python3
"""
Employee Chatbot - PowerSight Employee Assistant
Phiên bản tối ưu giao diện đơn giản hiện đại
"""
import random
import sys
import os
from pathlib import Path

# Thêm đường dẫn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from datetime import datetime
import pandas as pd

try:
    from config import Config
    from gemini_analyzer import GeminiAnalyzer
    from dashboard import PowerSightDashboard
    from data_processor import DataProcessor
except ImportError as e:
    print(f"⚠️ Import error: {e}")
    Config = None


class EmployeeChatbotGUI(QMainWindow):
    """Giao diện chính - Phiên bản đơn giản hiện đại"""

    def __init__(self, user_name=None, parent=None):
        super().__init__(parent)

        # Khởi tạo với Config
        if Config:
            if user_name:
                self.employee_name = user_name
            else:
                self.employee_name = Config.DEFAULT_EMPLOYEE_NAME
            app_name = Config.APP_NAME
        else:
            self.employee_name = user_name if user_name else "Giang"
            app_name = "PowerSight Employee Assistant"

        print(f"🤖 Initializing chatbot for: {self.employee_name}")

        # Khởi tạo AI
        try:
            self.gemini = GeminiAnalyzer()
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể khởi tạo AI: {e}")
            sys.exit(1)

        # Khởi tạo Data Processor
        self.data_processor = DataProcessor(self.employee_name)

        # Khởi tạo UI
        self.init_ui(app_name)

        # Hiển thị welcome
        self.show_welcome_message()

        # Tự động tải dữ liệu
        QTimer.singleShot(1000, self.load_initial_data)

    def init_ui(self, app_name):
        """Khởi tạo giao diện đơn giản hiện đại"""
        self.setWindowTitle(f"{app_name}")
        self.setGeometry(100, 100, 1100, 750)

        # Màu sắc chủ đạo
        self.primary_color = "#1e40af"  # Xanh dương đậm
        self.secondary_color = "#3b82f6"  # Xanh dương
        self.accent_color = "#10b981"  # Xanh lá
        self.bg_color = "#f8fafc"  # Nền sáng
        self.card_bg = "#ffffff"  # Nền card
        self.text_color = "#1e293b"  # Chữ chính
        self.text_light = "#64748b"  # Chữ phụ

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(f"background-color: {self.bg_color};")

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== HEADER ==========
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.primary_color};
                border: none;
            }}
        """)
        header.setFixedHeight(70)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(25, 0, 25, 0)

        # App title
        title_layout = QVBoxLayout()
        title_label = QLabel(app_name)
        title_label.setStyleSheet(f"""
            color: white;
            font-size: 20px;
            font-weight: bold;
            padding: 0;
        """)

        user_label = QLabel(f"Employee: {self.employee_name}")
        user_label.setStyleSheet(f"""
            color: #dbeafe;
            font-size: 13px;
            padding: 0;
        """)

        title_layout.addWidget(title_label)
        title_layout.addWidget(user_label)

        # Status and buttons
        right_layout = QHBoxLayout()
        right_layout.setSpacing(15)

        self.status_label = QLabel("🟢 Sẵn sàng")
        self.status_label.setStyleSheet(f"""
            color: white;
            font-size: 12px;
            background-color: rgba(255, 255, 255, 0.15);
            padding: 6px 12px;
            border-radius: 4px;
        """)

        dashboard_btn = QPushButton("Dashboard")
        dashboard_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        dashboard_btn.clicked.connect(self.show_dashboard)

        right_layout.addWidget(self.status_label)
        right_layout.addWidget(dashboard_btn)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addLayout(right_layout)

        main_layout.addWidget(header)

        # ========== MAIN CONTENT ==========
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Left panel - Quick actions
        left_panel = QFrame()
        left_panel.setFixedWidth(220)
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-right: 1px solid #e2e8f0;
            }}
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 20, 15, 20)
        left_layout.setSpacing(15)

        # Employee info
        info_card = QFrame()
        info_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.primary_color};
                border-radius: 8px;
                padding: 15px;
            }}
        """)

        info_layout = QVBoxLayout(info_card)
        info_layout.setSpacing(8)

        name_label = QLabel(self.employee_name)
        name_label.setStyleSheet(f"""
            color: white;
            font-size: 16px;
            font-weight: bold;
        """)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        role_label = QLabel("Senior Employee")
        role_label.setStyleSheet(f"""
            color: #dbeafe;
            font-size: 12px;
        """)
        role_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        info_layout.addWidget(name_label)
        info_layout.addWidget(role_label)

        # Quick actions title
        actions_title = QLabel("QUICK ACTIONS")
        actions_title.setStyleSheet(f"""
            color: {self.text_light};
            font-size: 11px;
            font-weight: bold;
            letter-spacing: 1px;
            padding-top: 10px;
        """)

        # Action buttons
        actions = [
            ("📊 Performance Analysis", lambda: self.ask_question("Phân tích hiệu suất làm việc của tôi")),
            ("🎯 Development Goals", lambda: self.ask_question("Mục tiêu phát triển của tôi là gì?")),
            ("📚 Training Recommendations", lambda: self.ask_question("Khóa học nào phù hợp với tôi?")),
            ("⚠️ Issues to Fix", lambda: self.ask_question("Tôi đang mắc những lỗi nào?")),
            ("💰 Revenue Optimization", lambda: self.ask_question("Làm sao tăng doanh thu?")),
            ("🔄 Refresh Data", self.load_initial_data)
        ]

        left_layout.addWidget(info_card)
        left_layout.addWidget(actions_title)

        for text, handler in actions:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.card_bg};
                    color: {self.primary_color};
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    padding: 12px;
                    text-align: left;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background-color: #f1f5f9;
                    border-color: {self.secondary_color};
                }}
            """)
            btn.clicked.connect(handler)
            left_layout.addWidget(btn)

        left_layout.addStretch()

        # Right panel - Chat area
        right_panel = QFrame()
        right_panel.setStyleSheet(f"QFrame {{ background-color: transparent; }}")

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(0)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.card_bg};
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 20px;
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                color: {self.text_color};
                line-height: 1.5;
            }}
        """)
        self.chat_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                margin-top: 15px;
            }}
        """)

        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(10, 10, 10, 10)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập câu hỏi của bạn... (Enter để gửi)")
        self.message_input.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                font-size: 14px;
                padding: 8px;
                background-color: transparent;
                color: {self.text_color};
            }}
            QLineEdit:focus {{
                outline: none;
            }}
        """)
        self.message_input.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("Gửi")
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.accent_color};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 25px;
                font-size: 13px;
                font-weight: 500;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: #0da271;
            }}
            QPushButton:disabled {{
                background-color: #cbd5e1;
            }}
        """)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)

        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(self.chat_display, 1)
        right_layout.addWidget(input_frame)

        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel, 1)

        main_layout.addWidget(content_widget, 1)

        # ========== STATUS BAR ==========
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.data_status = QLabel("⏳ Đang tải dữ liệu...")
        self.data_status.setStyleSheet(f"color: {self.text_light};")
        self.status_bar.addWidget(self.data_status)

        self.ai_status = QLabel("🤖 AI: Khởi động...")
        self.ai_status.setStyleSheet(f"color: {self.text_light};")
        self.status_bar.addPermanentWidget(self.ai_status)

    def show_welcome_message(self):
        """Hiển thị tin nhắn chào mừng"""
        welcome = f"""**CHÀO MỪNG ĐẾN VỚI POWER SIGHT AI ASSISTANT**

Xin chào **{self.employee_name}**! Tôi là trợ lý AI thông minh của bạn.

**TÔI CÓ THỂ GIÚP BẠN:**
• Phân tích hiệu suất làm việc
• Đề xuất cải thiện và phát triển
• Cảnh báo vấn đề cần khắc phục
• Tư vấn chiến lược tăng doanh thu
• Đề xuất khóa học phù hợp

**MẸO SỬ DỤNG:**
- Nhập câu hỏi tự nhiên bằng tiếng Việt
- Sử dụng nút Quick Actions để hỏi nhanh
- Xem Dashboard để biểu đồ chi tiết

**Đang tải dữ liệu từ hệ thống...**"""

        self.append_to_chat("Trợ lý AI", welcome)

    def load_initial_data(self):
        """Tải dữ liệu ban đầu"""
        self.status_label.setText("🔄 Đang tải dữ liệu...")
        self.data_status.setText("📂 Đang đọc dữ liệu từ hệ thống...")
        self.send_btn.setEnabled(False)

        try:
            # Tải dữ liệu qua DataProcessor
            success = self.data_processor.load_all_data()

            if success:
                data = self.data_processor.get_summary_data()
                work_log_data = data.get('work_log', {})
                sap_data = data.get('sap', {})

                self.status_label.setText("✅ Sẵn sàng")
                self.data_status.setText(
                    f"✅ Dữ liệu: Work Log ({work_log_data.get('total_events', 0)}), "
                    f"SAP ({sap_data.get('total_orders', 0)})"
                )

                if hasattr(self, 'gemini') and hasattr(self.gemini, 'active_model'):
                    model_name = self.gemini.active_model or 'DEMO'
                    self.ai_status.setText(f"🤖 AI: {model_name.split('/')[-1]}")

                self.send_btn.setEnabled(True)

                # Hiển thị tóm tắt
                summary_msg = f"""✅ **ĐÃ TẢI DỮ LIỆU THÀNH CÔNG**

📅 **Thời gian:** {datetime.now().strftime('%d/%m/%Y %H:%M')}
👤 **Nhân viên:** {self.employee_name}

📋 **WORK LOG:**
• Sự kiện: {work_log_data.get('total_events', 0):,}
• Cảnh báo: {work_log_data.get('warning_count', 0)}
• Gian lận: {work_log_data.get('fraud_count', 0)}

📊 **HIỆU SUẤT SAP:**
• Đơn hàng: {sap_data.get('total_orders', 0):,}
• Doanh thu: {sap_data.get('total_revenue', sap_data.get('revenue', 0)):,.0f} VND
• Lợi nhuận: {sap_data.get('total_profit', sap_data.get('profit', 0)):,.0f} VND

🎯 **SẴN SÀNG TRÒ CHUYỆN!**"""

                self.append_to_chat("Hệ thống", summary_msg)
            else:
                self.status_label.setText("⚠️ Thiếu dữ liệu")
                self.data_status.setText("❌ Không thể tải đầy đủ dữ liệu")
                self.append_to_chat("Hệ thống",
                                    "Không thể tải dữ liệu đầy đủ. Vui lòng kiểm tra file dữ liệu!")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText("❌ Lỗi dữ liệu")
            self.data_status.setText(f"Lỗi: {str(e)[:50]}")

    def show_dashboard(self):
        """Hiển thị dashboard - ĐÃ SỬA LỖI"""
        try:
            # Tải dữ liệu mới nhất
            self.data_processor.load_all_data()
            data = self.data_processor.get_all_data()

            # Kiểm tra dữ liệu có hợp lệ không
            work_log = data.get('work_log', {})
            sap_data = data.get('sap', {})

            if not work_log and not sap_data:
                QMessageBox.information(self, "Thông tin",
                                        "Chưa có đủ dữ liệu để hiển thị dashboard.\n"
                                        "Vui lòng làm việc thêm để có dữ liệu phân tích.")
                return

            print(f"📊 Mở dashboard với dữ liệu: work_log={bool(work_log)}, sap={bool(sap_data)}")

            # Tạo dashboard
            self.dashboard = PowerSightDashboard(
                employee_name=self.employee_name,
                work_log_data=work_log,
                sap_data=sap_data
            )

            # Thiết lập kích thước
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()

            # 80% màn hình
            width = int(screen_geometry.width() * 0.8)
            height = int(screen_geometry.height() * 0.8)

            self.dashboard.resize(width, height)
            self.dashboard.move(
                (screen_geometry.width() - width) // 2,
                (screen_geometry.height() - height) // 2
            )

            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()

            # Minimize chatbot window
            self.showMinimized()

        except Exception as e:
            print(f"❌ Lỗi khi mở dashboard: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Lỗi",
                                f"Không thể mở dashboard: {str(e)[:100]}")

    def send_message(self):
        """Gửi tin nhắn"""
        message = self.message_input.text().strip()
        if not message:
            return

        self.append_to_chat("Bạn", message)
        self.message_input.clear()

        # Vô hiệu hóa nút trong khi xử lý
        self.send_btn.setEnabled(False)
        self.status_label.setText("🤔 AI đang phân tích...")

        # Lấy dữ liệu context
        context_data = self.data_processor.get_context_data()

        # Xử lý trong thread riêng
        self.chat_thread = ChatThread(self.gemini, message, context_data)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def ask_question(self, question):
        """Hỏi câu hỏi tự động"""
        self.message_input.setText(question)
        self.send_message()

    def on_ai_response(self, response):
        """Nhận phản hồi từ AI"""
        self.append_to_chat("Trợ lý AI", response)
        self.send_btn.setEnabled(True)
        self.status_label.setText("✅ Sẵn sàng")

    def on_ai_error(self, error):
        """Xử lý lỗi AI"""
        self.append_to_chat("Lỗi hệ thống",
                            f"Đã xảy ra lỗi khi xử lý: {error}\n\nVui lòng thử lại hoặc liên hệ IT support.")
        self.send_btn.setEnabled(True)
        self.status_label.setText("⚠️ Có lỗi xảy ra")

    def append_to_chat(self, sender, message):
        """Thêm tin nhắn vào chat"""
        timestamp = datetime.now().strftime("%H:%M")

        # Xác định màu sắc cho sender
        if sender == "Bạn":
            color = self.primary_color
            bg_color = "#eff6ff"
        elif "Lỗi" in sender:
            color = "#dc2626"
            bg_color = "#fef2f2"
        elif "Hệ thống" in sender:
            color = self.text_light
            bg_color = "#f8fafc"
        else:
            color = self.accent_color
            bg_color = "#f0fdf4"

        html = f"""
        <div style="margin-bottom: 16px; padding: 16px; background: {bg_color}; border-radius: 8px; border-left: 3px solid {color};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <span style="font-weight: 600; color: {color}; font-size: 13px;">
                    {sender}
                </span>
                <span style="color: #94a3b8; font-size: 11px;">
                    {timestamp}
                </span>
            </div>
            <div style="color: {self.text_color}; line-height: 1.6; font-size: 13.5px;">
                {message.replace(chr(10), '<br>')}
            </div>
        </div>
        """

        current_html = self.chat_display.toHtml()
        self.chat_display.setHtml(current_html + html)

        # Cuộn xuống cuối
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.chat_display.setTextCursor(cursor)


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