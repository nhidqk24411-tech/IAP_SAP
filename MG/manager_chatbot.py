#!/usr/bin/env python3
"""
Manager Chatbot - Chatbot version for manager
Interface synchronized with employee_chatbot
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import traceback

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

        # Application name
        if config_available and Config:
            app_name = Config.APP_NAME
        else:
            app_name = "PowerSight Manager Assistant"

        self.init_ui(app_name)

        # Load initial data
        QTimer.singleShot(1000, self.load_initial_data)

    def get_manager_data_context(self):
        """Get special data context for manager as dictionary - ENHANCED WITH COMPARISON"""
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

        # **MỚI: Load comparison data cho tất cả nhân viên**
        employee_comparison = []
        top_performers = []
        bottom_performers = []

        try:
            if self.data_processor:
                print("📊 Loading employee comparison data...")
                employee_comparison = self.data_processor.get_employee_comparison_data(current_year, current_month)

                # Lấy top và bottom performers
                if employee_comparison:
                    top_performers = self.data_processor.get_top_performers(current_year, current_month, 3)
                    bottom_performers = self.data_processor.get_bottom_performers(current_year, current_month, 3)

                    print(f"   ✅ Loaded comparison for {len(employee_comparison)} employees")
                    print(f"   🏆 Top 3: {[emp['name'] for emp in top_performers]}")
                    print(f"   ⚠️ Bottom 3: {[emp['name'] for emp in bottom_performers]}")
        except Exception as e:
            print(f"⚠️ Error loading comparison data: {e}")

        # Create comprehensive context similar to employee chatbot
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

            # **MỚI: Employee comparison data**
            "employee_comparison": employee_comparison,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,

            "employees": self.get_employee_list() if self.data_processor else [],
            "is_manager": True
        }

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

        if not self.gemini:
            self.add_bot_message(
                "⚠️ **Note**: Gemini AI is not available. Using DEMO mode.")

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
- "Compare performance between employees" """

        self.add_bot_message(summary)

    def send_message(self):
        """Handle user message"""
        user_input = self.input_field.text().strip()
        if not user_input:
            return

        # Add user message
        self.add_user_message(user_input)
        self.input_field.clear()
        self.send_button.setEnabled(False)
        self.status_bar.setText("🤔 AI analyzing...")

        # Create data context for manager
        context_data = self.get_manager_data_context()

        # DEBUG: In ra context để kiểm tra
        print("\n" + "=" * 70)
        print("🔍 DEBUG: Context sent to Gemini")
        print("=" * 70)
        print(f"Current month revenue: {context_data.get('metrics', {}).get('total_revenue', 0):,.0f}")
        print(f"Current month orders: {context_data.get('metrics', {}).get('total_orders', 0)}")
        print(f"Year total revenue: {context_data.get('summary', {}).get('total_revenue', 0):,.0f}")
        print("=" * 70 + "\n")

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
                    f"**Question:** {self.question}\n\n**Analysis (DEMO):** Team performance is currently stable. Focus on employees with low completion rates to improve.",
                    f"**Question:** {self.question}\n\n**Analysis (DEMO):** Team data shows need to reduce fraud events. Consider compliance training for entire team.",
                    f"**Question:** {self.question}\n\n**Analysis (DEMO):** Team revenue is growing well. Focus on top performer employees to replicate success.",
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