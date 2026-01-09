#!/usr/bin/env python3
"""
Manager Chatbot - Phiên bản chatbot dành cho quản lý
Tích hợp với DataManager để lấy dữ liệu đa nhân viên
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Thêm đường dẫn
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

try:
    from data_manager import get_data_manager

    data_manager_available = True
except ImportError as e:
    print(f"⚠️ Không thể import data_manager: {e}")
    data_manager_available = False

try:
    from gemini_analyzer import GeminiAnalyzer

    gemini_available = True
except ImportError as e:
    print(f"⚠️ Không thể import gemini_analyzer: {e}")
    gemini_available = False


class ManagerChatbotThread(QThread):
    """Thread xử lý chat cho manager"""
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
                # Demo response
                demo_response = self.get_demo_response(self.question, self.context_data)
                self.response_ready.emit(demo_response)
                return

            # Gọi Gemini với context data
            response = self.gemini.analyze_manager_question(self.question, self.context_data)
            self.response_ready.emit(response)

        except Exception as e:
            print(f"❌ Lỗi trong ManagerChatbotThread: {e}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(str(e))

    def get_demo_response(self, question, context):
        """Response demo khi không có Gemini"""
        return f"""**MANAGER CHATBOT - DEMO MODE**

**Câu hỏi:** {question}

**Phân tích (Demo):**
Trong chế độ demo, chatbot có thể phân tích:
1. Hiệu suất tổng thể của team
2. Nhân viên cần cải thiện
3. Đề xuất training
4. Phân bổ resource

**Dữ liệu context:**
- Số nhân viên: {context.get('total_employees', 0)}
- Tổng doanh thu: {context.get('total_revenue', 0):,.0f} VND
- Tỷ lệ hoàn thành TB: {context.get('average_completion_rate', 0):.1f}%

**Để sử dụng đầy đủ, cần:**
1. Cấu hình Gemini API Key
2. Đảm bảo file dữ liệu nhân viên đúng định dạng
3. Kết nối với hệ thống dữ liệu thực"""


class ManagerChatbotGUI(QMainWindow):
    """Giao diện chatbot dành cho quản lý"""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller  # Thêm controller

        print("🤖 Khởi tạo Manager Chatbot...")

        # Khởi tạo DataManager
        self.data_manager = None
        if data_manager_available:
            self.data_manager = get_data_manager()
        else:
            print("⚠️ DataManager không khả dụng")

        # Khởi tạo Gemini
        self.gemini = None
        if gemini_available:
            try:
                self.gemini = GeminiAnalyzer()
                # Thêm method riêng cho manager
                self._add_manager_methods_to_gemini()
            except Exception as e:
                print(f"⚠️ Lỗi khởi tạo Gemini: {e}")

        # Khởi tạo UI
        self.init_ui()

        # Tải dữ liệu ban đầu
        QTimer.singleShot(1000, self.load_initial_data)

    def _add_manager_methods_to_gemini(self):
        """Thêm method phân tích cho manager vào Gemini"""

        def analyze_manager_question(question, context_data):
            # Prompt riêng cho manager
            manager_prompt = self._create_manager_prompt(question, context_data)

            # Gọi model Gemini
            response = self.gemini.analyze_question(manager_prompt, context_data)
            return response

        # Gán method vào gemini instance
        self.gemini.analyze_manager_question = analyze_manager_question

    def _create_manager_prompt(self, question, context_data):
        """Tạo prompt đặc biệt cho manager"""
        employee_details = context_data.get('employee_details', [])
        top_performers = context_data.get('top_performers', [])
        need_improvement = context_data.get('need_improvement', [])

        prompt = f"""
        Bạn là **PowerSight Manager AI** - Trợ lý thông minh dành cho quản lý và lãnh đạo.

        **VAI TRÒ CỦA BẠN:**
        - Advisor chiến lược: Giúp ra quyết định quản lý dựa trên dữ liệu
        - Performance coach: Phân tích hiệu suất nhân viên và đề xuất cải thiện
        - Risk analyst: Nhận diện rủi ro và điểm nghẽn (bottleneck)
        - Team optimizer: Đề xuất tối ưu hóa đội ngũ và phân bổ resource

        **DỮ LIỆU HIỆN CÓ:**
        - Tổng số nhân viên: {context_data.get('total_employees', 0)}
        - Nhân viên có dữ liệu: {context_data.get('employees_with_data', 0)}
        - Doanh thu tổng: {context_data.get('total_revenue', 0):,.0f} VND
        - Lợi nhuận tổng: {context_data.get('total_profit', 0):,.0f} VND
        - Tỷ lệ hoàn thành TB: {context_data.get('average_completion_rate', 0):.1f}%
        - Điểm tổng thể TB: {context_data.get('average_overall_score', 0):.1f}/100
        - Sự kiện gian lận: {context_data.get('total_fraud', 0)}

        **TOP PERFORMERS (Top {len(top_performers)}):**
        {self._format_employee_list(top_performers)}

        **NEED IMPROVEMENT (Bottom {len(need_improvement)}):**
        {self._format_employee_list(need_improvement)}

        **CÂU HỎI CỦA QUẢN LÝ:**
        "{question}"

        **HƯỚNG DẪN PHÂN TÍCH CHO QUẢN LÝ:**
        1. **Phân tích chiến lược:** Tập trung vào "tại sao" và "như thế nào" hơn là "cái gì"
        2. **Đề xuất hành động:** Cụ thể, khả thi, ưu tiên tác động cao
        3. **Nhận diện rủi ro:** Điểm yếu hệ thống, bottleneck, rủi ro tuân thủ
        4. **Tối ưu resource:** Phân bổ nhân lực, training, công cụ
        5. **KPIs quản lý:** Metrics quan trọng cần theo dõi

        **CẤU TRÚC TRẢ LỜI:**
        📊 **PHÂN TÍCH CHIẾN LƯỢC**
        - Bức tranh tổng thể
        - Điểm mạnh đội ngũ
        - Điểm yếu cần khắc phục

        🎯 **ĐỀ XUẤT HÀNH ĐỘNG ƯU TIÊN**
        1. [Hành động 1 - Ưu tiên cao]
        2. [Hành động 2 - Ưu tiên trung]
        3. [Hành động 3 - Ưu tiên thấp]

        ⚠️ **CẢNH BÁO & RỦI RO**
        - Rủi ro hiện tại
        - Rủi ro tiềm ẩn
        - Biện pháp phòng ngừa

        📈 **KPIs THEO DÕI**
        - Metrics quan trọng tuần này
        - Ngưỡng cảnh báo

        **VĂN PHONG:** Chuyên nghiệp, trực tiếp, tập trung vào kết quả. Như một cố vấn chiến lược.
        """

        return prompt

    def _format_employee_list(self, employees):
        """Định dạng danh sách nhân viên cho prompt"""
        if not employees:
            return "Không có dữ liệu"

        lines = []
        for i, emp in enumerate(employees[:5]):  # Giới hạn 5
            lines.append(f"{i + 1}. {emp.get('name', 'N/A')} - Điểm: {emp.get('overall_score', 0):.1f}, "
                         f"Completion: {emp.get('completion_rate', 0):.1f}%, "
                         f"Doanh thu: {emp.get('revenue', 0):,.0f} VND")

        return "\n".join(lines)

    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("🤖 Manager Chatbot - PowerSight")
        self.setGeometry(100, 100, 1000, 700)

        # Màu sắc theme manager
        self.primary_color = "#1e40af"  # Xanh dương đậm
        self.secondary_color = "#3b82f6"  # Xanh dương
        self.accent_color = "#10b981"  # Xanh lá
        self.warning_color = "#f59e0b"  # Vàng cam
        self.danger_color = "#ef4444"  # Đỏ

        # Màu nền
        self.bg_color = "#f8fafc"
        self.card_bg = "#ffffff"
        self.sidebar_bg = "#1e293b"

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        central_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.bg_color};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
        """)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== SIDEBAR ==========
        sidebar = QFrame()
        sidebar.setFixedWidth(300)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {self.sidebar_bg};
                border-right: 1px solid #334155;
            }}
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Header sidebar
        sidebar_header = QFrame()
        sidebar_header.setFixedHeight(120)
        sidebar_header.setStyleSheet(f"""
            QFrame {{
                background-color: #0f172a;
                border-bottom: 1px solid #334155;
            }}
        """)

        header_layout = QVBoxLayout(sidebar_header)
        header_layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("MANAGER DASHBOARD")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 10px;
            }
        """)

        self.manager_name = QLabel("Quản lý: Sarah")
        self.manager_name.setStyleSheet("""
            QLabel {
                color: #cbd5e1;
                font-size: 14px;
                margin-bottom: 5px;
            }
        """)

        self.team_status = QLabel("👥 Đang tải thông tin team...")
        self.team_status.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 12px;
            }
        """)

        header_layout.addWidget(title)
        header_layout.addWidget(self.manager_name)
        header_layout.addWidget(self.team_status)
        header_layout.addStretch()

        # Quick stats
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                padding: 15px;
            }
        """)

        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.setSpacing(10)

        stats_title = QLabel("📊 THỐNG KÊ NHANH")
        stats_title.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
        """)

        # Stats cards
        self.total_employees_card = self.create_stat_card("👥 Tổng NV", "0", "#3b82f6")
        self.avg_score_card = self.create_stat_card("📈 Điểm TB", "0", "#10b981")
        self.total_revenue_card = self.create_stat_card("💰 Doanh thu", "0", "#8b5cf6")
        self.fraud_count_card = self.create_stat_card("⚠️ Gian lận", "0", "#ef4444")

        stats_layout.addWidget(stats_title)
        stats_layout.addWidget(self.total_employees_card)
        stats_layout.addWidget(self.avg_score_card)
        stats_layout.addWidget(self.total_revenue_card)
        stats_layout.addWidget(self.fraud_count_card)
        stats_layout.addStretch()

        # Quick actions
        actions_frame = QFrame()
        actions_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
                padding: 15px;
            }
        """)

        actions_layout = QVBoxLayout(actions_frame)
        actions_layout.setSpacing(8)

        actions_title = QLabel("⚡ HÀNH ĐỘNG NHANH")
        actions_title.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }
        """)

        # Action buttons
        actions = [
            ("📋 Xem báo cáo tổng hợp", self.show_aggregate_report),
            ("🎯 Phân tích hiệu suất team", lambda: self.ask_question("Phân tích hiệu suất tổng thể của team")),
            ("🔍 Tìm bottleneck", lambda: self.ask_question("Điểm nghẽn chính trong team là gì?")),
            ("📊 So sánh nhân viên", lambda: self.ask_question("So sánh hiệu suất giữa các nhân viên")),
            ("💡 Đề xuất training", lambda: self.ask_question("Nhân viên nào cần training gì?")),
            ("🔄 Tải lại dữ liệu", self.load_initial_data),
        ]

        for text, handler in actions:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #334155;
                    color: #cbd5e1;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 15px;
                    text-align: left;
                    font-size: 12px;
                    font-weight: 500;
                    margin: 2px 0;
                }
                QPushButton:hover {
                    background-color: #475569;
                    color: white;
                }
            """)
            btn.clicked.connect(handler)
            actions_layout.addWidget(btn)

        # Thêm nút Home
        home_btn = QPushButton("Home")
        home_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 15px;
                text-align: left;
                font-size: 12px;
                font-weight: 600;
                margin: 10px 0 2px 0;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        if self.controller:
            home_btn.clicked.connect(lambda: self.controller.show_home())
        actions_layout.addWidget(home_btn)

        actions_layout.addStretch()

        # Thêm các phần vào sidebar
        sidebar_layout.addWidget(sidebar_header)
        sidebar_layout.addWidget(stats_frame)
        sidebar_layout.addWidget(actions_frame, 1)

        # ========== CHAT AREA ==========
        chat_area = QFrame()
        chat_area.setStyleSheet(f"""
            QFrame {{
                background-color: {self.bg_color};
            }}
        """)

        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(0, 0, 0, 0)
        chat_layout.setSpacing(0)

        # Chat header với nút Home
        chat_header = QFrame()
        chat_header.setFixedHeight(80)
        chat_header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-bottom: 1px solid #e2e8f0;
            }}
        """)

        header_chat_layout = QHBoxLayout(chat_header)
        header_chat_layout.setContentsMargins(20, 0, 20, 0)

        # Nút Home trong header
        home_header_btn = QPushButton("Home")
        home_header_btn.setFixedSize(80, 35)
        home_header_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.secondary_color};
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
            }}
        """)
        if self.controller:
            home_header_btn.clicked.connect(lambda: self.controller.show_home())

        chat_title = QLabel("💬 Manager AI Assistant")
        chat_title.setStyleSheet(f"""
            QLabel {{
                color: {self.primary_color};
                font-size: 18px;
                font-weight: 600;
            }}
        """)

        self.ai_status = QLabel("🟢 Đang kết nối...")
        self.ai_status.setStyleSheet("""
            QLabel {
                color: #10b981;
                font-size: 12px;
                background-color: rgba(16, 185, 129, 0.1);
                padding: 4px 12px;
                border-radius: 12px;
            }
        """)

        header_chat_layout.addWidget(home_header_btn)
        header_chat_layout.addWidget(chat_title)
        header_chat_layout.addStretch()
        header_chat_layout.addWidget(self.ai_status)

        # Chat display
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {self.card_bg};
                border: none;
                font-size: 13px;
                line-height: 1.6;
                padding: 20px;
                color: #1e293b;
            }}
            QScrollBar:vertical {{
                width: 8px;
                background-color: #f1f5f9;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background-color: #cbd5e1;
                border-radius: 4px;
                min-height: 20px;
            }}
        """)

        # Input area
        input_frame = QFrame()
        input_frame.setFixedHeight(120)
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.card_bg};
                border-top: 1px solid #e2e8f0;
            }}
        """)

        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(20, 15, 20, 15)

        # Quick questions
        quick_questions_frame = QFrame()
        quick_questions_frame.setStyleSheet("background-color: transparent;")

        quick_layout = QHBoxLayout(quick_questions_frame)
        quick_layout.setSpacing(8)

        quick_questions = [
            "Hiệu suất team?",
            "Bottleneck?",
            "Training cần thiết?",
            "Rủi ro tuân thủ?"
        ]

        for q in quick_questions:
            btn = QPushButton(q)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #e2e8f0;
                    color: #475569;
                    border: none;
                    border-radius: 15px;
                    padding: 6px 12px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #cbd5e1;
                    color: #1e293b;
                }
            """)
            btn.clicked.connect(lambda checked, q=q: self.ask_question(q))
            quick_layout.addWidget(btn)

        quick_layout.addStretch()

        # Input field
        input_field_layout = QHBoxLayout()
        input_field_layout.setSpacing(10)

        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Nhập câu hỏi về quản lý, hiệu suất team, phân tích dữ liệu...")
        self.message_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.secondary_color};
                outline: none;
            }}
        """)
        self.message_input.returnPressed.connect(self.send_message)

        self.send_btn = QPushButton("Gửi")
        self.send_btn.setFixedWidth(80)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.secondary_color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
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

        input_field_layout.addWidget(self.message_input, 1)
        input_field_layout.addWidget(self.send_btn)

        input_layout.addWidget(quick_questions_frame)
        input_layout.addLayout(input_field_layout)

        # Thêm vào chat layout
        chat_layout.addWidget(chat_header)
        chat_layout.addWidget(self.chat_display, 1)
        chat_layout.addWidget(input_frame)

        # Ghép sidebar và chat area
        main_layout.addWidget(sidebar)
        main_layout.addWidget(chat_area, 1)

    def create_stat_card(self, title, value, color):
        """Tạo card thống kê"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 10px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 11px;
            }
        """)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                font-weight: 600;
            }}
        """)

        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return card

    def load_initial_data(self):
        """Tải dữ liệu ban đầu"""
        self.ai_status.setText("🔄 Đang tải dữ liệu...")
        self.send_btn.setEnabled(False)

        if not self.data_manager:
            self.ai_status.setText("⚠️ Không có DataManager")
            self.show_welcome_message()
            return

        try:
            # Lấy dữ liệu tổng hợp
            aggregate_data = self.data_manager.get_aggregate_data()

            # Cập nhật stats
            if aggregate_data:
                # Update cards
                for i in range(self.total_employees_card.layout().count()):
                    widget = self.total_employees_card.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == "0":
                        widget.setText(str(aggregate_data.get('total_employees', 0)))
                        break

                for i in range(self.avg_score_card.layout().count()):
                    widget = self.avg_score_card.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == "0":
                        widget.setText(f"{aggregate_data.get('average_overall_score', 0):.1f}")
                        break

                for i in range(self.total_revenue_card.layout().count()):
                    widget = self.total_revenue_card.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == "0":
                        widget.setText(f"{aggregate_data.get('total_revenue', 0) / 1000000:.1f}M")
                        break

                for i in range(self.fraud_count_card.layout().count()):
                    widget = self.fraud_count_card.layout().itemAt(i).widget()
                    if isinstance(widget, QLabel) and widget.text() == "0":
                        widget.setText(str(aggregate_data.get('total_fraud', 0)))
                        break

                # Update team status
                emp_with_data = aggregate_data.get('employees_with_data', 0)
                total_emp = aggregate_data.get('total_employees', 0)
                self.team_status.setText(
                    f"👥 Team: {emp_with_data}/{total_emp} nhân viên có dữ liệu"
                )

            # Update AI status
            if self.gemini:
                model_info = self.gemini.get_model_info()
                model_name = model_info.get('active_model', 'DEMO').split('/')[-1]
                self.ai_status.setText(f"🤖 {model_name}")
            else:
                self.ai_status.setText("🤖 DEMO MODE")

            self.send_btn.setEnabled(True)
            self.show_welcome_message(aggregate_data)

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            self.ai_status.setText("⚠️ Lỗi dữ liệu")
            self.show_welcome_message()

    def show_welcome_message(self, aggregate_data=None):
        """Hiển thị tin nhắn chào mừng"""
        welcome = """**👋 CHÀO MỪNG ĐẾN VỚI MANAGER AI ASSISTANT**

**Vai trò của tôi:** Trợ lý AI dành riêng cho quản lý và lãnh đạo.

**TÔI CÓ THỂ GIÚP BẠN:**

📊 **PHÂN TÍCH HIỆU SUẤT**
- Đánh giá tổng thể team
- So sánh hiệu suất nhân viên
- Nhận diện top performers và người cần hỗ trợ

🎯 **TỐI ƯU ĐỘI NGŨ**
- Đề xuất phân bổ resource
- Xác định training needs
- Tối ưu workflow

⚠️ **QUẢN LÝ RỦI RO**
- Phát hiện bottleneck
- Cảnh báo rủi ro tuân thủ
- Đề xuất biện pháp phòng ngừa

📈 **CHIẾN LƯỢC PHÁT TRIỂN**
- Kế hoạch phát triển team
- Đề xuất KPI mới
- Phân tích xu hướng

**HƯỚNG DẪN SỬ DỤNG:**
1. Nhập câu hỏi trực tiếp vào ô chat
2. Sử dụng nút "hành động nhanh" bên trái
3. Click vào câu hỏi mẫu phía trên ô chat

**VÍ DỤ CÂU HỎI HIỆU QUẢ:**
- "Phân tích hiệu suất tổng thể của team tháng này?"
- "Nhân viên nào đang gặp vấn đề về hiệu suất?"
- "Điểm nghẽn chính trong workflow là gì?"
- "Nên training gì cho team?"
- "Làm sao tăng tỷ lệ hoàn thành đơn hàng?"
"""

        # Thêm thông tin tổng hợp nếu có
        if aggregate_data:
            welcome += f"""

**📊 THỐNG KÊ NHANH:**
• Tổng nhân viên: {aggregate_data.get('total_employees', 0)}
• Có dữ liệu: {aggregate_data.get('employees_with_data', 0)}
• Doanh thu tổng: {aggregate_data.get('total_revenue', 0):,.0f} VND
• Điểm TB: {aggregate_data.get('average_overall_score', 0):.1f}/100
"""

        self.append_to_chat("Manager AI", welcome)

    def send_message(self):
        """Gửi tin nhắn"""
        question = self.message_input.text().strip()
        if not question:
            return

        self.append_to_chat("Bạn", question)
        self.message_input.clear()

        # Vô hiệu hóa nút trong khi xử lý
        self.send_btn.setEnabled(False)
        self.ai_status.setText("🤔 Đang phân tích...")

        # Lấy dữ liệu context từ DataManager
        context_data = {}
        if self.data_manager:
            try:
                aggregate_data = self.data_manager.get_aggregate_data()
                context_data = {
                    **aggregate_data,
                    'data_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'data_source': 'DataManager'
                }
            except Exception as e:
                print(f"⚠️ Không lấy được context data: {e}")

        # Xử lý trong thread riêng
        self.chat_thread = ManagerChatbotThread(self.gemini, question, context_data)
        self.chat_thread.response_ready.connect(self.on_ai_response)
        self.chat_thread.error_occurred.connect(self.on_ai_error)
        self.chat_thread.start()

    def ask_question(self, question):
        """Hỏi câu hỏi tự động"""
        self.message_input.setText(question)
        self.send_message()

    def on_ai_response(self, response):
        """Nhận phản hồi từ AI"""
        self.append_to_chat("Manager AI", response)
        self.send_btn.setEnabled(True)
        self.ai_status.setText("✅ Sẵn sàng")

    def on_ai_error(self, error):
        """Xử lý lỗi AI"""
        error_msg = f"""**❌ LỖI HỆ THỐNG**

Không thể xử lý yêu cầu:
{str(error)[:200]}...

Vui lòng thử lại sau hoặc liên hệ support."""

        self.append_to_chat("Hệ thống", error_msg)
        self.send_btn.setEnabled(True)
        self.ai_status.setText("⚠️ Có lỗi")

    def show_aggregate_report(self):
        """Hiển thị báo cáo tổng hợp"""
        if self.controller:
            self.controller.show_aggregate_dashboard()
        else:
            print("📊 Mở Aggregate Dashboard")

    def append_to_chat(self, sender, message):
        """Thêm tin nhắn vào chat"""
        timestamp = datetime.now().strftime("%H:%M")

        # Xác định màu sắc
        if sender == "Bạn":
            color = self.secondary_color
            bg_color = "#eff6ff"
            avatar = "👤"
        elif "Lỗi" in sender or "❌" in message:
            color = self.danger_color
            bg_color = "#fef2f2"
            avatar = "⚠️"
        elif "Hệ thống" in sender:
            color = "#64748b"
            bg_color = "#f8fafc"
            avatar = "⚙️"
        else:
            color = self.primary_color
            bg_color = "#eff6ff"
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
                         border-left: 3px solid {color}; line-height: 1.5; font-size: 13px; color: #1e293b;">
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


def main():
    """Hàm chính"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = ManagerChatbotGUI()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()