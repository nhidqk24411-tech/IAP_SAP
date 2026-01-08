#!/usr/bin/env python3
"""
Employee Chatbot - PowerSight Employee Assistant
Phiên bản tối ưu giao diện giống dashboard - FIX UI Quick Actions
"""

import random
import sys
import os
from pathlib import Path
from datetime import datetime

# Thêm đường dẫn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import modules với try-except
try:
    from config import Config

    config_available = True
except ImportError:
    print("⚠️ Không thể import config.py")
    config_available = False
    Config = None

try:
    from gemini_analyzer import GeminiAnalyzer

    gemini_available = True
except ImportError as e:
    print(f"⚠️ Không thể import gemini_analyzer: {e}")
    gemini_available = False

try:
    from dashboard import PerformanceDashboard

    dashboard_available = True
except ImportError as e:
    print(f"⚠️ Không thể import dashboard: {e}")
    dashboard_available = False

try:
    from data_processor import DataProcessor

    dataprocessor_available = True
except ImportError as e:
    print(f"⚠️ Không thể import data_processor: {e}")
    dataprocessor_available = False


class EmployeeChatbotGUI(QMainWindow):
    """Giao diện chính - Phiên bản giống Dashboard"""

    def __init__(self, user_name=None, parent=None):
        super().__init__(parent)

        # Khởi tạo với Config
        if config_available and Config:
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
        self.gemini = None
        if gemini_available:
            try:
                self.gemini = GeminiAnalyzer()
            except Exception as e:
                print(f"⚠️ Lỗi khởi tạo Gemini: {e}")
        else:
            print("⚠️ Gemini không khả dụng, sử dụng chế độ DEMO")

        # Khởi tạo Data Processor
        self.data_processor = None
        if dataprocessor_available:
            try:
                self.data_processor = DataProcessor(self.employee_name)
            except Exception as e:
                print(f"⚠️ Lỗi khởi tạo DataProcessor: {e}")
        else:
            print("⚠️ DataProcessor không khả dụng")

        # Khởi tạo Dashboard
        self.dashboard = None
        self.dashboard_available = dashboard_available

        # Khởi tạo UI với theme giống Dashboard
        self.init_ui(app_name)

        # Hiển thị welcome
        self.show_welcome_message()

        # Tự động tải dữ liệu
        QTimer.singleShot(1000, self.load_initial_data)

    def init_ui(self, app_name):
        """Khởi tạo giao diện với theme giống Dashboard - FIXED UI"""
        self.setWindowTitle(f"💬 {app_name} - Chat Assistant")
        self.setGeometry(100, 100, 1200, 800)

        # Màu sắc chủ đạo
        self.primary_color = "#1e40af"  # Xanh dương đậm
        self.secondary_color = "#3b82f6"  # Xanh dương
        self.accent_color = "#10b981"  # Xanh lá
        self.warning_color = "#f59e0b"  # Cam
        self.danger_color = "#ef4444"  # Đỏ

        # Màu nền
        self.bg_color = "#f8fafc"  # Nền sáng xám nhạt
        self.card_bg = "#ffffff"  # Nền card trắng
        self.sidebar_bg = "#1e293b"  # Sidebar tối giống Dashboard
        self.text_color = "#1e293b"  # Chữ chính đen xám
        self.text_light = "#64748b"  # Chữ phụ xám
        self.text_white = "#ffffff"  # Chữ trắng
        self.border_color = "#e2e8f0"  # Viền xám nhạt

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.bg_color};
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            }}
        """)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== SIDEBAR LEFT ==========
        sidebar = QFrame()
        sidebar.setMinimumWidth(260)
        sidebar.setMaximumWidth(320)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.sidebar_bg};
                border-right: 1px solid #334155;
            }}
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # User profile card
        profile_card = QFrame()
        profile_card.setMinimumHeight(130)
        profile_card.setMaximumHeight(150)
        profile_card.setStyleSheet(f"""
            QFrame {{
                background-color: #0f172a;
                border-bottom: 1px solid #334155;
            }}
        """)
        profile_layout = QVBoxLayout(profile_card)
        profile_layout.setContentsMargins(20, 25, 20, 25)
        profile_layout.setSpacing(10)

        # Avatar và tên
        avatar_label = QLabel("👤")
        avatar_label.setStyleSheet(f"""
            font-size: 32px;
            color: {self.secondary_color};
        """)
        avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_label.setFixedHeight(40)

        name_label = QLabel(self.employee_name)
        name_label.setStyleSheet(f"""
            color: {self.text_white};
            font-size: 16px;
            font-weight: 600;
            text-align: center;
        """)
        name_label.setWordWrap(True)

        role_label = QLabel("Senior Employee")
        role_label.setStyleSheet(f"""
            color: #94a3b8;
            font-size: 12px;
            text-align: center;
        """)

        profile_layout.addWidget(avatar_label)
        profile_layout.addWidget(name_label)
        profile_layout.addWidget(role_label)

        # Quick actions section - Sử dụng ScrollArea
        actions_container = QWidget()
        actions_container.setStyleSheet("background-color: transparent;")

        actions_scroll = QScrollArea()
        actions_scroll.setWidgetResizable(True)
        actions_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        actions_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        actions_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #1e293b;
                width: 6px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical {
                background-color: #475569;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #64748b;
            }
        """)

        actions_widget = QWidget()
        actions_layout = QVBoxLayout(actions_widget)
        actions_layout.setContentsMargins(20, 20, 20, 20)
        actions_layout.setSpacing(8)

        actions_title = QLabel("QUICK ACTIONS")
        actions_title.setStyleSheet(f"""
            QLabel {{
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                margin-bottom: 5px;
                padding: 0;
            }}
        """)
        actions_layout.addWidget(actions_title)

        # Action buttons
        actions = [
            ("Mở Dashboard", self.show_dashboard, "#3b82f6"),
            ("Phân tích hiệu suất", lambda: self.ask_question("Phân tích hiệu suất làm việc của tôi"), "#10b981"),
            ("Mục tiêu phát triển", lambda: self.ask_question("Mục tiêu phát triển của tôi là gì?"), "#8b5cf6"),
            ("Đề xuất đào tạo", lambda: self.ask_question("Khóa học nào phù hợp với tôi?"), "#f59e0b"),
            ("Vấn đề cần sửa", lambda: self.ask_question("Tôi đang mắc những lỗi nào?"), "#ef4444"),
            ("Tối ưu doanh thu", lambda: self.ask_question("Làm sao tăng doanh thu?"), "#06b6d4"),
            ("Tải lại dữ liệu", self.load_initial_data, "#64748b"),
        ]

        self.action_buttons = []

        for text, handler, color in actions:
            btn_widget = QWidget()
            btn_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                    border: none;
                }}
            """)

            btn_layout = QHBoxLayout(btn_widget)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn_layout.setSpacing(10)

            # Icon bullet
            icon_label = QLabel("•")
            icon_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 20px;
                    font-weight: bold;
                    min-width: 20px;
                    max-width: 20px;
                }}
            """)
            icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            # Button text
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

            # Disable dashboard button nếu không có dashboard
            if "Dashboard" in text and not self.dashboard_available:
                btn.setEnabled(False)
                btn.setToolTip("Dashboard module không khả dụng")
                color = "#64748b"

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #334155;
                    color: #cbd5e1;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 15px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 500;
                    margin: 0;
                    min-height: 40px;
                }}
                QPushButton:hover {{
                    background-color: #475569;
                    color: white;
                    border-left: 3px solid {color};
                }}
                QPushButton:pressed {{
                    background-color: #1e293b;
                }}
                QPushButton:disabled {{
                    background-color: #1f2937;
                    color: #64748b;
                }}
            """)
            btn.clicked.connect(handler)

            btn_layout.addWidget(icon_label)
            btn_layout.addWidget(btn, 1)

            actions_layout.addWidget(btn_widget)
            self.action_buttons.append(btn)

        actions_layout.addStretch()

        actions_scroll.setWidget(actions_widget)

        # Footer sidebar
        footer_frame = QFrame()
        footer_frame.setMinimumHeight(80)
        footer_frame.setMaximumHeight(100)
        footer_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #0f172a;
                border-top: 1px solid #334155;
            }}
        """)
        footer_layout = QVBoxLayout(footer_frame)
        footer_layout.setContentsMargins(15, 10, 15, 10)
        footer_layout.setSpacing(5)

        self.ai_status_label = QLabel("🤖 AI: Khởi động...")
        self.ai_status_label.setStyleSheet(f"""
            color: #94a3b8;
            font-size: 11px;
            padding: 2px 0;
        """)

        self.data_status_label = QLabel("⏳ Đang tải dữ liệu...")
        self.data_status_label.setStyleSheet(f"""
            color: #94a3b8;
            font-size: 11px;
            padding: 2px 0;
        """)

        footer_layout.addWidget(self.ai_status_label)
        footer_layout.addWidget(self.data_status_label)

        # Thêm các phần vào sidebar
        sidebar_layout.addWidget(profile_card)
        sidebar_layout.addWidget(actions_scroll, 1)
        sidebar_layout.addWidget(footer_frame)

        # ========== MAIN CHAT AREA ==========
        main_area = QFrame()
        main_area.setStyleSheet(f"QFrame {{ background-color: {self.bg_color}; }}")

        main_area_layout = QVBoxLayout(main_area)
        main_area_layout.setContentsMargins(0, 0, 0, 0)
        main_area_layout.setSpacing(0)

        # Header chat area
        chat_header = QFrame()
        chat_header.setMinimumHeight(60)
        chat_header.setMaximumHeight(70)
        chat_header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-bottom: 1px solid {self.border_color};
            }}
        """)

        header_layout = QHBoxLayout(chat_header)
        header_layout.setContentsMargins(25, 0, 25, 0)

        title_label = QLabel("💬 PowerSight AI Chat Assistant")
        title_label.setStyleSheet(f"""
            color: {self.text_color};
            font-size: 16px;
            font-weight: 600;
        """)

        self.status_indicator = QLabel("🟢 Online")
        self.status_indicator.setStyleSheet(f"""
            color: {self.accent_color};
            font-size: 11px;
            background-color: rgba(16, 185, 129, 0.1);
            padding: 4px 10px;
            border-radius: 10px;
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_indicator)

        # Chat display area
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.card_bg};
                border: none;
                font-family: 'Segoe UI', Arial;
                font-size: 13px;
                color: {self.text_color};
                line-height: 1.6;
                padding: 20px;
            }}
            QScrollBar:vertical {{
                background-color: #f1f5f9;
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #cbd5e1;
                border-radius: 4px;
                min-height: 20px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: #94a3b8;
            }}
        """)
        self.chat_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Input area
        input_container = QFrame()
        input_container.setMinimumHeight(80)
        input_container.setMaximumHeight(100)
        input_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-top: 1px solid {self.border_color};
            }}
        """)

        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(20, 15, 20, 15)
        input_layout.setSpacing(12)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập câu hỏi của bạn về hiệu suất, phát triển nghề nghiệp...")
        self.message_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.bg_color};
                border: 1px solid {self.border_color};
                border-radius: 8px;
                padding: 12px 18px;
                font-size: 13px;
                color: {self.text_color};
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.secondary_color};
                outline: none;
            }}
            QLineEdit::placeholder {{
                color: {self.text_light};
                font-size: 13px;
            }}
        """)
        self.message_input.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("Gửi")
        self.send_btn.setMinimumWidth(80)
        self.send_btn.setMaximumWidth(100)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.secondary_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
            QPushButton:disabled {{
                background-color: #cbd5e1;
                color: #64748b;
            }}
        """)
        self.send_btn.clicked.connect(self.send_message)
        self.send_btn.setEnabled(False)

        input_layout.addWidget(self.message_input, 1)
        input_layout.addWidget(self.send_btn)

        # Thêm các phần vào main area
        main_area_layout.addWidget(chat_header)
        main_area_layout.addWidget(self.chat_display, 1)
        main_area_layout.addWidget(input_container)

        # Ghép sidebar và main area
        main_layout.addWidget(sidebar)
        main_layout.addWidget(main_area, 1)

        # Thiết lập size policy
        sidebar.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        main_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def show_welcome_message(self):
        """Hiển thị tin nhắn chào mừng"""
        dashboard_status = "✓ Có sẵn" if self.dashboard_available else "✗ Không khả dụng"
        ai_status = "✓ Có sẵn" if self.gemini else "✗ DEMO MODE"
        data_status = "✓ Có sẵn" if self.data_processor else "✗ Không khả dụng"

        welcome = f"""**CHÀO MỪNG ĐẾN VỚI POWER SIGHT AI ASSISTANT**

**👤 Nhân viên:** {self.employee_name}
**📅 Ngày:** {datetime.now().strftime('%d/%m/%Y')}

**🛠️ TRẠNG THÁI HỆ THỐNG:**
• AI Assistant: {ai_status}
• Dashboard: {dashboard_status}
• Data Processor: {data_status}

**🤖 TÔI CÓ THỂ GIÚP BẠN:**
• Phân tích hiệu suất làm việc
• Đề xuất cải thiện và phát triển
• Cảnh báo vấn đề cần khắc phục
• Tư vấn chiến lược tăng doanh thu
• Đề xuất khóa học phù hợp

**🚀 QUICK ACTIONS:**
- Sử dụng nút bên trái để hỏi nhanh
- **Nhấn "Mở Dashboard"** để xem biểu đồ chi tiết
- Chat tự nhiên bằng tiếng Việt

**⏳ Đang tải dữ liệu từ hệ thống...**"""

        self.append_to_chat("Trợ lý AI", welcome)

    def load_initial_data(self):
        """Tải dữ liệu ban đầu"""
        self.status_indicator.setText("🔄 Đang tải dữ liệu...")
        self.data_status_label.setText("📂 Đang đọc dữ liệu từ hệ thống...")
        self.send_btn.setEnabled(False)

        try:
            # Kiểm tra nếu có DataProcessor
            if not self.data_processor:
                self.status_indicator.setText("⚠️ Không có DataProcessor")
                self.data_status_label.setText("❌ Module DataProcessor không khả dụng")
                self.send_btn.setEnabled(True)

                warning_msg = """**⚠️ CẢNH BÁO: MODULE KHÔNG KHẢ DỤNG**

Không thể tải DataProcessor module. Có thể do:
1. File data_processor.py bị lỗi
2. Thiếu thư viện dependencies
3. Import error

**Hành động:**
• Vẫn có thể chat với AI (DEMO mode)
• Dashboard có thể không hiển thị đầy đủ dữ liệu
• Liên hệ IT support để khắc phục"""

                self.append_to_chat("Hệ thống", warning_msg)
                return

            # Tải dữ liệu qua DataProcessor
            success = self.data_processor.load_all_data()

            if success:
                data = self.data_processor.get_summary_data()
                work_log_data = data.get('work_log', {})
                sap_data = data.get('sap', {})
                metrics = data.get('metrics', {})

                self.status_indicator.setText("🟢 Sẵn sàng")

                # Hiển thị chi tiết work log và SAP
                fraud_count = work_log_data.get('fraud_count', 0)
                warning_count = work_log_data.get('warning_count', 0)
                mouse_sessions = work_log_data.get('total_sessions', 0)
                sap_orders = sap_data.get('total_orders', 0)
                pending_orders = sap_data.get('pending_orders', 0)

                self.data_status_label.setText(
                    f"📊 WL: {fraud_count} gian lận, {warning_count} cảnh báo | "
                    f"🛒 SAP: {sap_orders} đơn ({pending_orders} chờ)"
                )

                if self.gemini and hasattr(self.gemini, 'active_model'):
                    model_name = self.gemini.active_model or 'DEMO'
                    self.ai_status_label.setText(f"🤖 {model_name.split('/')[-1]}")
                else:
                    self.ai_status_label.setText("🤖 DEMO MODE")

                self.send_btn.setEnabled(True)

                # Hiển thị tóm tắt chi tiết
                completion_rate = sap_data.get('completion_rate', 0)
                revenue = sap_data.get('total_revenue', 0)
                profit = sap_data.get('total_profit', 0)

                summary_msg = f"""**✅ ĐÃ TẢI DỮ LIỆU THÀNH CÔNG**

**📅 Thời gian:** {datetime.now().strftime('%d/%m/%Y %H:%M')}

**🔍 WORK LOG PHÂN TÍCH:**
• Sự kiện gian lận: {fraud_count}
• Cảnh báo nghiêm trọng: {work_log_data.get('critical_count', 0)}
• Cảnh báo nhẹ: {warning_count}
• Session chuột: {mouse_sessions}
• Thời gian làm việc: {work_log_data.get('total_work_hours', 0)}h

**📈 SAP DATA TỔNG QUAN:**
• Tổng đơn hàng: {sap_orders:,}
• Đã hoàn thành: {sap_data.get('completed_orders', 0):,}
• Chờ xử lý: {pending_orders:,}
• Tỷ lệ hoàn thành: {completion_rate:.1f}%
• Doanh thu: {revenue:,.0f} VND
• Lợi nhuận: {profit:,.0f} VND

**🎯 ĐIỂM ĐÁNH GIÁ HIỆU SUẤT:**
• **Hiệu quả:** {metrics.get('efficiency', 0):.1f}/100
• **Chất lượng:** {metrics.get('quality', 0):.1f}/100
• **Tuân thủ:** {metrics.get('compliance', 0):.1f}/100
• **Năng suất:** {metrics.get('productivity', 0):.1f}/100
• **🏆 TỔNG THỂ:** {metrics.get('overall', 0):.1f}/100

**💡 GỢI Ý HÀNH ĐỘNG:**
1. **Nhấn "Mở Dashboard"** - Xem biểu đồ chi tiết và xu hướng
2. **Hỏi "Đơn hàng nào chưa xử lý xong?"** - Kiểm tra trạng thái đơn hàng
3. **Hỏi "Làm sao cải thiện hiệu suất?"** - Được tư vấn chiến lược
4. **Hỏi "Doanh thu vùng nào cao nhất?"** - Phân tích dữ liệu kinh doanh"""

                self.append_to_chat("Hệ thống", summary_msg)
            else:
                self.status_indicator.setText("⚠️ Thiếu dữ liệu")
                self.data_status_label.setText("❌ Không thể tải đầy đủ dữ liệu")
                self.append_to_chat("Hệ thống",
                                    "Không thể tải dữ liệu đầy đủ. Vui lòng kiểm tra file dữ liệu!")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            self.status_indicator.setText("❌ Lỗi dữ liệu")
            self.data_status_label.setText(f"Lỗi: {str(e)[:50]}")
            self.send_btn.setEnabled(True)
    def show_dashboard(self):
        """Hiển thị dashboard"""
        try:
            if not self.dashboard_available:
                QMessageBox.warning(self, "Không khả dụng",
                                    "Dashboard module không khả dụng. Không thể mở dashboard.")
                return

            print(f"🚀 Đang mở Dashboard cho {self.employee_name}...")

            # Tạo mới dashboard
            self.dashboard = PerformanceDashboard(self.employee_name)

            # Thiết lập kích thước
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()

            width = int(screen_geometry.width() * 0.85)
            height = int(screen_geometry.height() * 0.85)

            self.dashboard.resize(width, height)
            self.dashboard.move(
                (screen_geometry.width() - width) // 2,
                (screen_geometry.height() - height) // 2
            )

            # Hiển thị dashboard
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()

            print(f"✅ Dashboard đã hiển thị: {width}x{height}")

        except Exception as e:
            print(f"❌ Lỗi khi mở dashboard: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Lỗi",
                                f"Không thể mở dashboard:\n{str(e)}")

    def send_message(self):
        """Gửi tin nhắn"""
        message = self.message_input.text().strip()
        if not message:
            return

        self.append_to_chat("Bạn", message)
        self.message_input.clear()

        # Vô hiệu hóa nút trong khi xử lý
        self.send_btn.setEnabled(False)
        self.status_indicator.setText("🤔 AI đang phân tích...")

        # Lấy dữ liệu context nâng cao
        context_data = {}
        if self.data_processor:
            try:
                context_data = self.data_processor.get_enhanced_context()

                # Log dữ liệu context
                print(f"📋 Context data keys: {list(context_data.keys())}")
                print(f"📊 SAP data: {len(context_data.get('sap_data', {}).get('all_orders', []))} orders")
                print(f"📈 Work log: {len(context_data.get('work_log', {}).get('fraud_events', []))} fraud events")

            except Exception as e:
                print(f"⚠️ Không thể lấy context data: {e}")
                import traceback
                traceback.print_exc()

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
        self.status_indicator.setText("✅ Sẵn sàng")

    def on_ai_error(self, error):
        """Xử lý lỗi AI"""
        error_msg = f"""**❌ LỖI HỆ THỐNG**

Không thể kết nối đến AI service:

**Chi tiết:** {error}

**Khắc phục:**
1. Kiểm tra kết nối Internet
2. Đảm bảo API Key hợp lệ trong file .env
3. Thử lại sau vài phút

**Chế độ DEMO sẽ được sử dụng tạm thời.**"""

        self.append_to_chat("Hệ thống", error_msg)
        self.send_btn.setEnabled(True)
        self.status_indicator.setText("⚠️ Có lỗi xảy ra")

    def append_to_chat(self, sender, message):
        """Thêm tin nhắn vào chat với format đẹp"""
        timestamp = datetime.now().strftime("%H:%M")

        # Xác định màu sắc cho sender
        if sender == "Bạn":
            color = self.secondary_color
            bg_color = "#eff6ff"
            avatar = "👤"
        elif "Lỗi" in sender or "❌" in message or "⚠️" in sender:
            color = self.danger_color
            bg_color = "#fef2f2"
            avatar = "⚠️"
        elif "Hệ thống" in sender:
            color = self.text_light
            bg_color = "#f8fafc"
            avatar = "⚙️"
        else:
            color = self.accent_color
            bg_color = "#f0fdf4"
            avatar = "🤖"

        html = f"""
        <div style="margin: 0 0 15px 0;">
            <div style="display: flex; gap: 10px;">
                <!-- Avatar -->
                <div style="flex-shrink: 0; width: 32px; height: 32px; background-color: {color}; 
                     border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 16px;">
                    {avatar}
                </div>

                <!-- Content -->
                <div style="flex: 1; min-width: 0;">
                    <!-- Header -->
                    <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                        <span style="font-weight: 600; color: {color}; font-size: 13px;">
                            {sender}
                        </span>
                        <span style="color: #94a3b8; font-size: 11px;">
                            {timestamp}
                        </span>
                    </div>

                    <!-- Message -->
                    <div style="background-color: {bg_color}; padding: 12px; border-radius: 8px; 
                         border-left: 3px solid {color}; line-height: 1.5; font-size: 13px; color: {self.text_color};">
                        {message.replace(chr(10), '<br>')}
                    </div>
                </div>
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
            if not self.gemini:
                # Demo response nếu không có Gemini
                import random
                demo_responses = [
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Hiệu suất của bạn hiện ở mức ổn định. Tập trung vào hoàn thành đơn hàng đúng hạn để cải thiện tỷ lệ hoàn thành.",
                    f"**Câu hỏi:** {self.question}\n\n**Phân tích (DEMO):** Dữ liệu cho thấy bạn cần giảm số lượng cảnh báo trong quy trình làm việc. Kiểm tra kỹ các bước trước khi submit.",
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