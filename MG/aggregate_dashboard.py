#!/usr/bin/env python3
"""
Aggregate Dashboard - Consolidated dashboard for Manager
Displays total revenue, profit, orders (not divided by employee)
"""

import sys
import os
from datetime import datetime, timedelta
import numpy as np

# --- ADD MISSING LIBRARIES TO RUN INTERFACE ---
from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Chart drawing library
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except ImportError:
    print("⚠️ Please install matplotlib: pip install matplotlib")

# ---------------------------------------------------

# Find project root directory path (parent directory of Interface)
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

# Add current directory, parent directory, and Chatbot directory to system
if project_root not in sys.path:
    sys.path.append(project_root)
    sys.path.append(os.path.join(project_root, "MG"))

try:
    # Try to import directly or from Chatbot
    from MG.data_processor import DataProcessor
    data_processor_available = True
    print("✅ Successfully connected to DataProcessor")
except ImportError as e:
    print(f"⚠️ Cannot import data_processor: {e}")
    data_processor_available = False


class AggregateDashboard(QMainWindow):
    """Consolidated dashboard for Manager - Displays total revenue, profit"""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller  # Add controller

        print("📊 Initializing Aggregate Dashboard...")

        # Initialize DataProcessor
        self.data_processor = None
        if data_processor_available:
            try:
                # DataProcessor for aggregate should not have employee_name
                self.data_processor = DataProcessor()  # No employee_name parameter
                print("✅ DataProcessor initialized successfully")
            except Exception as e:
                print(f"❌ Error initializing DataProcessor: {e}")
                self.data_processor = None
        else:
            print("⚠️ DataProcessor not available")

        # Data
        self.aggregate_data = {}
        self.monthly_data = {}  # Monthly data

        # Initialize UI
        self.init_ui()

        # Load initial data
        QTimer.singleShot(1000, self.load_data)

    def init_ui(self):
        """Initialize interface"""
        self.setWindowTitle("Aggregate Report - PowerSight")

        # Set to maximize
        self.setWindowState(Qt.WindowState.WindowMaximized)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with Home button
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border-bottom: 1px solid #334155;
            }
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Home button
        home_btn = QPushButton("Home")
        home_btn.setFixedSize(100, 35)
        home_btn.setStyleSheet("""
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        if self.controller:
            home_btn.clicked.connect(lambda: self.controller.show_home())

        title = QLabel("AGGREGATE REPORT - POWER SIGHT")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
            }
        """)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedSize(100, 35)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #059669;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)

        header_layout.addWidget(home_btn)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(refresh_btn)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # KPI Cards (first row) - 6 aggregate KPIs
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)

        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setSpacing(15)

        # Create 6 KPI cards
        self.kpi_cards = []
        kpi_configs = [
            ("TOTAL REVENUE", "0 VND", "#8b5cf6", "Team total revenue"),
            ("TOTAL PROFIT", "0 VND", "#10b981", "Team total profit"),
            ("TOTAL ORDERS", "0", "#3b82f6", "Total orders"),
            ("COMPLETION RATE", "0%", "#06b6d4", "Average completion rate"),
            ("EMPLOYEES", "0", "#f59e0b", "Total employees"),
            ("FRAUD EVENTS", "0", "#ef4444", "Total fraud events")
        ]

        for title, value, color, desc in kpi_configs:
            card = self.create_kpi_card(title, value, color, desc)
            self.kpi_cards.append(card)
            kpi_layout.addWidget(card)

        content_layout.addWidget(kpi_frame)

        # Charts section - 2 main charts
        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        charts_layout.setSpacing(15)

        # Chart 1: Revenue & Profit by month
        revenue_chart_frame = QFrame()
        revenue_chart_frame.setMinimumHeight(400)
        revenue_chart_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)

        revenue_chart_layout = QVBoxLayout(revenue_chart_frame)
        revenue_chart_layout.setContentsMargins(15, 15, 15, 15)

        revenue_title = QLabel("REVENUE & PROFIT BY MONTH")
        revenue_title.setStyleSheet("""
            QLabel {
                color: #1e293b;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 10px;
            }
        """)

        self.revenue_figure = Figure(figsize=(12, 6), dpi=100, facecolor='white')
        self.revenue_canvas = FigureCanvas(self.revenue_figure)

        revenue_chart_layout.addWidget(revenue_title)
        revenue_chart_layout.addWidget(self.revenue_canvas, 1)

        # Chart 2: Orders & Fraud by month
        orders_chart_frame = QFrame()
        orders_chart_frame.setMinimumHeight(400)
        orders_chart_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)

        orders_chart_layout = QVBoxLayout(orders_chart_frame)
        orders_chart_layout.setContentsMargins(15, 15, 15, 15)

        orders_title = QLabel("ORDERS & FRAUD BY MONTH")
        orders_title.setStyleSheet("""
            QLabel {
                color: #1e293b;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 10px;
            }
        """)

        self.orders_figure = Figure(figsize=(12, 6), dpi=100, facecolor='white')
        self.orders_canvas = FigureCanvas(self.orders_figure)

        orders_chart_layout.addWidget(orders_title)
        orders_chart_layout.addWidget(self.orders_canvas, 1)

        # Add charts to layout
        charts_layout.addWidget(revenue_chart_frame)
        charts_layout.addWidget(orders_chart_frame)

        content_layout.addWidget(charts_container, 1)

        # Aggregate analysis
        analysis_frame = QFrame()
        analysis_frame.setMinimumHeight(200)
        analysis_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
            }
        """)

        analysis_layout = QVBoxLayout(analysis_frame)
        analysis_layout.setContentsMargins(15, 15, 15, 15)

        analysis_title = QLabel("AGGREGATE ANALYSIS")
        analysis_title.setStyleSheet("""
            QLabel {
                color: #1e293b;
                font-size: 14px;
                font-weight: 600;
                margin-bottom: 10px;
            }
        """)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 6px;
                padding: 10px;
                font-size: 12px;
            }
        """)

        analysis_layout.addWidget(analysis_title)
        analysis_layout.addWidget(self.analysis_text, 1)

        content_layout.addWidget(analysis_frame)

        # Footer
        footer = QLabel(f"Data updated at: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        footer.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 11px;
                font-style: italic;
                padding: 10px;
                text-align: center;
            }
        """)
        content_layout.addWidget(footer)

        # Set content widget to scroll area
        scroll_area.setWidget(content_widget)

        # Add to main layout
        main_layout.addWidget(header)
        main_layout.addWidget(scroll_area, 1)

    def create_kpi_card(self, title, value, color, description):
        """Create KPI card"""
        card = QFrame()
        card.setMinimumHeight(100)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                border-left: 4px solid {color};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 12px;
                font-weight: 500;
            }
        """)

        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 20px;
                font-weight: 600;
            }}
        """)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: #94a3b8;
                font-size: 10px;
                font-style: italic;
            }
        """)
        desc_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(desc_label)

        return card

    def load_data(self):
        """Load data from DataProcessor"""
        if not self.data_processor:
            QMessageBox.warning(self, "Error", "Cannot connect to DataProcessor")
            return

        try:
            # Get current year
            current_year = datetime.now().year

            # Get aggregate data from DataProcessor with current year
            self.aggregate_data = self.data_processor.load_aggregate_data(current_year)

            if not self.aggregate_data:
                QMessageBox.warning(self, "Warning", "No data to display")
                return

            # Get monthly data
            self.monthly_data = self.aggregate_data.get('monthly_data', {})

            # Update KPI cards
            self.update_kpi_cards()

            # Update charts
            self.update_charts()

            # Update analysis
            self.update_analysis()

            print(f"✅ Loaded aggregate data for year {current_year}")

        except Exception as e:
            print(f"❌ Error loading data: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Cannot load data:\n{str(e)}")

    def update_kpi_cards(self):
        """Update KPI cards"""
        data = self.aggregate_data

        # Format values
        total_revenue = f"{data.get('total_revenue', 0):,.0f} VND"
        total_profit = f"{data.get('total_profit', 0):,.0f} VND"

        # Calculate total orders from monthly data
        total_orders = sum(self.monthly_data.get('orders', [0] * 12))
        total_orders_str = f"{total_orders:,}"

        avg_completion = f"{data.get('average_completion_rate', 0):.1f}%"
        total_employees = str(data.get('total_employees', 0))
        total_fraud = str(data.get('total_fraud', 0))

        values = [
            total_revenue,
            total_profit,
            total_orders_str,
            avg_completion,
            total_employees,
            total_fraud
        ]

        for i, (card, value) in enumerate(zip(self.kpi_cards, values)):
            # Find second child QLabel in layout (value_label)
            layout = card.layout()
            if layout:
                value_label = layout.itemAt(1).widget()  # Get second widget (index 1)
                if isinstance(value_label, QLabel):
                    value_label.setText(value)

    def update_charts(self):
        """Update charts"""
        # Chart 1: Revenue & Profit by month
        self.revenue_figure.clear()
        ax1 = self.revenue_figure.add_subplot(111)

        months = self.monthly_data.get('months', [])
        revenue = self.monthly_data.get('revenue', [])
        profit = self.monthly_data.get('profit', [])

        x = np.arange(len(months))
        width = 0.35

        # Convert to million VND for easier reading
        revenue_mil = [r / 1000000 for r in revenue]
        profit_mil = [p / 1000000 for p in profit]

        bars1 = ax1.bar(x - width / 2, revenue_mil, width, label='Revenue (million VND)', color='#3b82f6')
        bars2 = ax1.bar(x + width / 2, profit_mil, width, label='Profit (million VND)', color='#10b981')

        ax1.set_xlabel('Month')
        ax1.set_ylabel('Million VND')
        ax1.set_title('Revenue and Profit by Month')
        ax1.set_xticks(x)
        ax1.set_xticklabels(months)
        ax1.legend()
        ax1.grid(True, alpha=0.3, linestyle='--')

        # Add values on bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax1.text(bar.get_x() + bar.get_width() / 2., height,
                             f'{height:.1f}', ha='center', va='bottom', fontsize=8)

        self.revenue_figure.tight_layout()
        self.revenue_canvas.draw()

        # Chart 2: Orders & Fraud by month
        self.orders_figure.clear()
        ax2 = self.orders_figure.add_subplot(111)

        orders = self.monthly_data.get('orders', [])
        fraud = self.monthly_data.get('fraud', [])

        # Create two y axes
        ax2_orders = ax2
        ax2_fraud = ax2.twinx()

        # Plot orders
        line_orders = ax2_orders.plot(x, orders, marker='o', linewidth=2,
                                      label='Number of Orders', color='#3b82f6')
        ax2_orders.set_xlabel('Month')
        ax2_orders.set_ylabel('Number of Orders', color='#3b82f6')
        ax2_orders.tick_params(axis='y', labelcolor='#3b82f6')
        ax2_orders.set_xticks(x)
        ax2_orders.set_xticklabels(months)

        # Plot fraud
        line_fraud = ax2_fraud.plot(x, fraud, marker='s', linewidth=2,
                                    label='Fraud Events', color='#ef4444')
        ax2_fraud.set_ylabel('Fraud Events', color='#ef4444')
        ax2_fraud.tick_params(axis='y', labelcolor='#ef4444')

        # Combine legend
        lines = line_orders + line_fraud
        labels = [l.get_label() for l in lines]
        ax2_orders.legend(lines, labels, loc='upper left')

        ax2_orders.grid(True, alpha=0.3, linestyle='--')
        ax2_orders.set_title('Number of Orders and Fraud Events by Month')

        self.orders_figure.tight_layout()
        self.orders_canvas.draw()

    def update_analysis(self):
        """Update aggregate analysis"""
        data = self.aggregate_data
        monthly = self.monthly_data

        # Calculate indicators
        total_revenue = data.get('total_revenue', 0)
        total_profit = data.get('total_profit', 0)
        total_orders = sum(monthly.get('orders', [0] * 12))
        total_fraud = data.get('total_fraud', 0)
        total_employees = data.get('total_employees', 0)
        employees_with_data = data.get('employees_with_data', 0)
        avg_completion = data.get('average_completion_rate', 0)
        avg_score = data.get('average_overall_score', 0)

        # Calculate required values
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        if employees_with_data > 0:
            orders_per_employee_per_month = total_orders / employees_with_data / 12
        else:
            orders_per_employee_per_month = 0

        if total_orders > 0:
            fraud_rate = total_fraud / total_orders * 100
        else:
            fraud_rate = 0

        # Find best/worst months
        revenue_by_month = monthly.get('revenue', [0] * 12)
        profit_by_month = monthly.get('profit', [0] * 12)
        orders_by_month = monthly.get('orders', [0] * 12)
        fraud_by_month = monthly.get('fraud', [0] * 12)

        best_revenue_month = revenue_by_month.index(max(revenue_by_month)) if revenue_by_month else -1
        best_profit_month = profit_by_month.index(max(profit_by_month)) if profit_by_month else -1
        worst_fraud_month = fraud_by_month.index(max(fraud_by_month)) if fraud_by_month else -1

        months = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December']

        # Calculate percentage of employees with data
        if total_employees > 0:
            data_percentage = employees_with_data / total_employees * 100
        else:
            data_percentage = 0

        # Analysis
        analysis_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h3 style="color: #1e40af; margin-bottom: 15px;">TEAM AGGREGATE ANALYSIS</h3>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <h4 style="color: #3b82f6; margin-top: 0;">BUSINESS PERFORMANCE</h4>
                    <p><b>Total revenue:</b> {total_revenue:,.0f} VND</p>
                    <p><b>Total profit:</b> {total_profit:,.0f} VND</p>
                    <p><b>Profit margin:</b> {profit_margin:.1f}%</p>
                    <p><b>Best revenue month:</b> {months[best_revenue_month] if best_revenue_month >= 0 else 'N/A'}</p>
                </div>

                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <h4 style="color: #10b981; margin-top: 0;">TEAM STAFF</h4>
                    <p><b>Total employees:</b> {total_employees}</p>
                    <p><b>Employees with data:</b> {employees_with_data} ({data_percentage:.0f}%)</p>
                    <p><b>Average team score:</b> {avg_score:.1f}/100</p>
                    <p><b>Average completion rate:</b> {avg_completion:.1f}%</p>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                    <h4 style="color: #8b5cf6; margin-top: 0;">ORDER ACTIVITY</h4>
                    <p><b>Total orders:</b> {total_orders:,}</p>
                    <p><b>Average orders/month:</b> {total_orders / 12:.0f}</p>
                    <p><b>Month with most orders:</b> {months[orders_by_month.index(max(orders_by_month))] if orders_by_month else 'N/A'}</p>
                    <p><b>Orders/employee/month:</b> {orders_per_employee_per_month:.1f}</p>
                </div>

                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <h4 style="color: #ef4444; margin-top: 0;">RISK MANAGEMENT</h4>
                    <p><b>Total fraud events:</b> {total_fraud}</p>
                    <p><b>Average fraud/month:</b> {total_fraud / 12:.1f}</p>
                    <p><b>Month with most fraud:</b> {months[worst_fraud_month] if worst_fraud_month >= 0 else 'N/A'}</p>
                    <p><b>Fraud rate/orders:</b> {fraud_rate:.2f}%</p>
                </div>
            </div>

            <div style="background-color: #1e293b; color: white; padding: 15px; border-radius: 8px; margin-top: 10px;">
                <h4 style="color: #ffffff; margin-top: 0;">STRATEGIC RECOMMENDATIONS</h4>
                <ul>
                    <li>Focus on <b>{months[best_profit_month] if best_profit_month >= 0 else 'months with high profit'}</b> to optimize business strategy</li>
                    <li>Improve fraud control in <b>{months[worst_fraud_month] if worst_fraud_month >= 0 else 'high-risk months'}</b></li>
                    <li>Recommend training for {total_employees - employees_with_data} employees without performance data</li>
                    <li>Target: Increase completion rate from {avg_completion:.1f}% to {(avg_completion + 5):.1f}% next quarter</li>
                </ul>
            </div>

            <div style="margin-top: 15px; padding: 10px; background-color: #f1f5f9; border-radius: 5px; font-size: 11px; color: #64748b;">
                <p><b>Analysis time:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><b>Data scope:</b> Last 12 months</p>
                <p><b>Method:</b> Aggregated from {employees_with_data} employees with data</p>
            </div>
        </div>
        """

        self.analysis_text.setHtml(analysis_html)


def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = AggregateDashboard()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()