#!/usr/bin/env python3
"""
Performance Dashboard - Enhanced version with diverse charts and hover tooltip
Đã thêm nút Home để quay về HomeWindow
"""

import sys
import os
import traceback

import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import copy

# Fix import for matplotlib compatible with PyQt6
import matplotlib

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class ChartDialog(QDialog):
    """Dialog to display enlarged chart"""

    def __init__(self, figure, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📊 {title}")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMaximizeButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #1e293b;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header with title and close button
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(f"📊 {title}")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: 600;
            color: #ffffff;
            padding: 8px 0;
        """)

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedSize(80, 35)
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        layout.addWidget(header_widget)

        # Canvas for chart
        self.canvas = FigureCanvas(figure)
        self.canvas.setMinimumSize(800, 500)
        layout.addWidget(self.canvas)

        # Footer with control buttons
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        save_btn = QPushButton("💾 Save Image")
        save_btn.setFixedSize(100, 35)
        save_btn.clicked.connect(self.save_image)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedSize(100, 35)
        refresh_btn.clicked.connect(self.refresh_chart)

        footer_layout.addStretch()
        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(refresh_btn)

        layout.addWidget(footer_widget)

        self.setLayout(layout)
        self.resize(900, 600)
        self.original_figure = figure

    def save_image(self):
        """Save chart as image file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Chart",
            f"chart_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )

        if file_path:
            try:
                self.original_figure.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='#1e293b')
                QMessageBox.information(self, "Success", f"Chart saved to:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot save file:\n{str(e)}")

    def refresh_chart(self):
        """Refresh chart"""
        self.canvas.draw()

    def closeEvent(self, event):
        event.accept()


class PerformanceDashboard(QWidget):
    def __init__(self, user_name, parent_window=None):
        super().__init__()
        self.user_name = str(user_name)
        self.parent_window = parent_window
        self.metrics = {}
        self.raw_data_original = {}  # Lưu bản gốc
        self.year_data = None
        self.data_processor = None
        self.metric_labels = []

        # 1. Khởi tạo giao diện trước
        self.init_ui()

        # 2. Tải dữ liệu sau (Để tránh lỗi widgets chưa tồn tại)
        QTimer.singleShot(100, self.load_data)

    def init_ui(self):
        self.setWindowTitle(f"Performance Dashboard - {self.user_name}")
        # Giữ nguyên StyleSheet cũ của bạn
        self.setStyleSheet("""
            QWidget { background-color: #0f172a; font-family: 'Segoe UI'; }
            QLabel { color: #e2e8f0; }
            QGroupBox { font-weight: 600; border: 1px solid #334155; border-radius: 8px; margin-top: 15px; background-color: #1e293b; color: #cbd5e1; }
            QPushButton { background-color: #3b82f6; color: white; border: none; padding: 8px 16px; border-radius: 6px; }
            QComboBox { background-color: #1e293b; color: white; border: 1px solid #334155; padding: 4px; border-radius: 4px; }
        """)

        # Layout chính của cả Widget
        self.main_vbox = QVBoxLayout(self)
        self.main_vbox.setContentsMargins(0, 0, 0, 0)

        # --- THANH HEADER ---
        header_frame = QFrame()
        header_frame.setFixedHeight(60)
        header_frame.setStyleSheet("background-color: #1e293b; border-bottom: 1px solid #334155;")
        header_layout = QHBoxLayout(header_frame)

        self.home_btn = QPushButton("🏠 Home")
        self.home_btn.setFixedSize(90, 35)
        self.home_btn.clicked.connect(self.go_back_to_home)
        header_layout.addWidget(self.home_btn)

        header_layout.addStretch()

        # LOGIC: Chỉ hiện bộ lọc cho nhân viên (không bắt đầu bằng MG)
        if not self.user_name.startswith("MG"):
            header_layout.addWidget(QLabel("Year:"))
            self.year_combo = QComboBox()
            self.year_combo.addItems(["2024", "2025", "2026"])
            self.year_combo.setCurrentText(str(datetime.now().year))
            header_layout.addWidget(self.year_combo)

            header_layout.addWidget(QLabel("Month:"))
            self.month_combo = QComboBox()
            self.month_combo.addItems(["All", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
            header_layout.addWidget(self.month_combo)

            self.filter_btn = QPushButton("🔍 Filter")
            self.filter_btn.setFixedSize(80, 35)
            self.filter_btn.clicked.connect(self.apply_filter)
            header_layout.addWidget(self.filter_btn)

        self.refresh_btn = QPushButton("🔄 Reload")
        self.refresh_btn.setFixedSize(90, 35)
        self.refresh_btn.clicked.connect(self.load_data)
        header_layout.addWidget(self.refresh_btn)

        self.main_vbox.addWidget(header_frame)

        # --- VÙNG NỘI DUNG CUỘN ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: none;")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)

        # Thêm các thành phần biểu đồ (Dùng các hàm tạo widget cũ của bạn)
        self.content_layout.addWidget(self.create_metrics_grid())

        row1 = QHBoxLayout()
        row1.addWidget(self.create_fraud_chart_widget())
        row1.addWidget(self.create_revenue_chart_widget())
        self.content_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self.create_completion_chart_widget())
        row2.addWidget(self.create_working_hours_chart_widget())
        self.content_layout.addLayout(row2)

        self.content_layout.addWidget(self.create_analysis_widget())

        self.scroll_area.setWidget(self.content_widget)
        self.main_vbox.addWidget(self.scroll_area)

    def load_data(self):
        """Tải dữ liệu an toàn"""
        try:
            from data_processor import DataProcessor
            self.data_processor = DataProcessor(self.user_name)
            if not self.data_processor.load_all_data():
                return

            self.year_data = self.data_processor.get_dashboard_data()

            # Trích xuất để lưu bản gốc phục vụ Filter
            sap_sheets = self.year_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = self.year_data.get('work_log', {}).get('sheets', {})

            self.raw_data_original = {
                'orders': sap_sheets.get('Orders', pd.DataFrame()).copy(),
                'fraud': work_log_sheets.get('Fraud_Events', pd.DataFrame()).copy(),
                'browser': work_log_sheets.get('Browser_Sessions', pd.DataFrame()).copy()
            }

            if self.user_name.startswith("MG"):
                self.calculate_dashboard_metrics()
                self.update_ui()
            else:
                self.apply_filter()  # Tự động lọc lần đầu cho nhân viên

        except Exception as e:
            print(f"❌ Load Data Error: {e}")

    def apply_filter(self):
        """Lọc dữ liệu và cập nhật toàn bộ giao diện"""
        if not self.raw_data_original: return

        try:
            year = int(self.year_combo.currentText())
            month_text = self.month_combo.currentText()

            # Lọc bản sao
            df_o = self.raw_data_original['orders'].copy()
            df_f = self.raw_data_original['fraud'].copy()

            if not df_o.empty and 'Year' in df_o.columns:
                df_o = df_o[df_o['Year'] == year]
                if month_text != "All":
                    df_o = df_o[df_o['Month'] == int(month_text)]

            if not df_f.empty:
                df_f['Timestamp'] = pd.to_datetime(df_f['Timestamp'])
                df_f = df_f[df_f['Timestamp'].dt.year == year]
                if month_text != "All":
                    df_f = df_f[df_f['Timestamp'].dt.month == int(month_text)]

            # Ghi đè dữ liệu lọc vào biến mà các hàm cũ của bạn sử dụng
            self.year_data['sap_data']['sheets']['Orders'] = df_o
            self.year_data['work_log']['sheets']['Fraud_Events'] = df_f

            # Chạy lại tính toán và vẽ lại UI
            self.calculate_dashboard_metrics()
            self.update_ui()
            print(f"✅ Dashboard updated for {month_text}/{year}")

        except Exception as e:
            print(f"⚠️ Filter logic error: {e}")

    def keyPressEvent(self, event):
        """LỐI THOÁT KHẨN CẤP: Nhấn ESC để đóng Dashboard nếu bị treo"""
        if event.key() == Qt.Key.Key_Escape:
            self.go_back_to_home()
    def apply_filter(self):
        """Lọc tất cả dữ liệu theo Tháng/Năm và cập nhật toàn bộ Dashboard"""
        if not hasattr(self, 'raw_data_original'): return

        try:
            year = int(self.year_combo.currentText())
            month_text = self.month_combo.currentText()

            # 1. Lọc bảng Orders (Ảnh hưởng đến KPI Orders, Doanh thu, Tỷ lệ hoàn thành)
            df_o = self.raw_data_original['orders'].copy()
            if not df_o.empty and 'Year' in df_o.columns:
                df_o = df_o[df_o['Year'] == year]
                if month_text != "All":
                    df_o = df_o[df_o['Month'] == int(month_text)]

            # 2. Lọc bảng Fraud (Ảnh hưởng đến KPI Cảnh báo và Biểu đồ gian lận)
            df_f = self.raw_data_original['fraud'].copy()
            if not df_f.empty:
                if 'Timestamp' in df_f.columns:
                    df_f['Timestamp'] = pd.to_datetime(df_f['Timestamp'])
                    df_f = df_f[df_f['Timestamp'].dt.year == year]
                    if month_text != "All":
                        df_f = df_f[df_f['Timestamp'].dt.month == int(month_text)]

            # 3. Lọc bảng Browser/Daily (Ảnh hưởng đến KPI Thời gian và Biểu đồ giờ làm)
            df_b = self.raw_data_original['browser'].copy()
            if not df_b.empty and 'Month' in df_b.columns:
                if month_text != "All":
                    df_b = df_b[df_b['Month'] == int(month_text)]

            # 4. GHI ĐÈ DỮ LIỆU ĐÃ LỌC VÀO year_data
            # Đây là bước then chốt để các hàm tính toán cũ hoạt động đúng
            self.year_data['sap_data']['sheets']['Orders'] = df_o
            self.year_data['work_log']['sheets']['Fraud_Events'] = df_f
            self.year_data['work_log']['sheets']['Browser_Sessions'] = df_b

            # 5. CHẠY LẠI TOÀN BỘ LOGIC CẬP NHẬT
            self.calculate_dashboard_metrics()  # Tính toán lại các con số
            self.update_ui()  # Vẽ lại tất cả biểu đồ và chữ phân tích

            print(f"✅ Dashboard updated for: {month_text}/{year}")

        except Exception as e:
            print(f"⚠️ Filter failed: {e}")
            traceback.print_exc()

    def go_back_to_home(self):
        """Go back to HomeWindow"""
        if self.parent_window:
            try:
                self.parent_window.showNormal()
                self.parent_window.raise_()
                self.parent_window.activateWindow()
                # Notify parent that dashboard is closed
                if hasattr(self.parent_window, 'on_dashboard_closed'):
                    self.parent_window.on_dashboard_closed()
            except Exception as e:
                print(f"Error restoring home window: {e}")
        self.close()

    def create_metrics_grid(self):
        """Create grid displaying 4 main indicators"""
        grid = QGroupBox("KEY PERFORMANCE INDICATORS (ANNUAL)")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 25, 15, 15)

        cards = []
        metrics_info = [
            ("📦 TOTAL ORDERS", "0", "Average 0 orders/month", "#3b82f6"),
            ("⏰ TOTAL TIME", "0 hours", "Average 0 hours/month", "#10b981"),
            ("⚠️ FRAUD EVENTS", "0", "Warning level", "#ef4444"),
            ("✅ COMPLETION RATE", "0%", "Target 95%", "#8b5cf6")
        ]

        for i, (title, value, desc, color) in enumerate(metrics_info):
            card = self.create_metric_card(title, value, desc, color)
            cards.append(card)
            grid_layout.addWidget(card, 0, i)

        self.metric_labels = [card.findChild(QLabel, "value") for card in cards]

        for i in range(4):
            grid_layout.setColumnStretch(i, 1)

        grid.setLayout(grid_layout)
        return grid

    def create_metric_card(self, title, value, description, color):
        """Create metric card with better design"""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(140)
        card.setMaximumHeight(160)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(20, 15, 20, 15)

        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel(title.split()[0])
        icon_label.setStyleSheet(f"""
            font-size: 20px;
            color: {color};
        """)
        icon_label.setFixedSize(30, 30)

        title_text = " ".join(title.split()[1:])
        title_label = QLabel(title_text)
        title_label.setStyleSheet(f"""
            font-size: 13px;
            font-weight: 600;
            color: #cbd5e1;
        """)
        title_label.setWordWrap(True)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        card_layout.addWidget(header_widget)

        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 700;
            color: {color};
            margin: 10px 0;
            padding: 5px;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setMinimumHeight(50)
        card_layout.addWidget(value_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #94a3b8;
            font-style: italic;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(desc_label)

        card.setStyleSheet(f"""
            QFrame {{
                background-color: #1e293b;
                border: 2px solid #334155;
                border-radius: 12px;
            }}
            QFrame:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 2px solid {color};
                transform: translateY(-2px);
            }}
        """)

        return card

    def create_fraud_chart_widget(self):
        """Create widget for fraud events bar chart by month"""
        widget = QGroupBox("FRAUD EVENTS BY MONTH")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.fraud_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.fraud_canvas = FigureCanvas(self.fraud_figure)
        self.fraud_canvas.setStyleSheet("background-color: transparent;")
        self.fraud_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fraud_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.fraud_figure,
                                                                                 "Fraud Events By Month")
        layout.addWidget(self.fraud_canvas)

        layout.setStretchFactor(self.fraud_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_revenue_chart_widget(self):
        """Create widget for revenue and profit line chart by month"""
        widget = QGroupBox("REVENUE AND PROFIT BY MONTH")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.revenue_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.revenue_canvas = FigureCanvas(self.revenue_figure)
        self.revenue_canvas.setStyleSheet("background-color: transparent;")
        self.revenue_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.revenue_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.revenue_figure,
                                                                                   "Revenue and Profit By Month")
        layout.addWidget(self.revenue_canvas)

        layout.setStretchFactor(self.revenue_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_completion_chart_widget(self):
        """Create widget for completion rate pie chart"""
        widget = QGroupBox("COMPLETION DISTRIBUTION")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.completion_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.completion_canvas = FigureCanvas(self.completion_figure)
        self.completion_canvas.setStyleSheet("background-color: transparent;")
        self.completion_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.completion_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.completion_figure,
                                                                                      "Completion Distribution")
        layout.addWidget(self.completion_canvas)

        layout.setStretchFactor(self.completion_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_working_hours_chart_widget(self):
        """Create widget for working hours bar chart by month"""
        widget = QGroupBox("WORKING HOURS BY MONTH")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.working_hours_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.working_hours_canvas = FigureCanvas(self.working_hours_figure)
        self.working_hours_canvas.setStyleSheet("background-color: transparent;")
        self.working_hours_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.working_hours_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.working_hours_figure,
                                                                                         "Working Hours By Month")
        layout.addWidget(self.working_hours_canvas)

        layout.setStretchFactor(self.working_hours_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_analysis_widget(self):
        """Create detailed analysis widget"""
        widget = QGroupBox("DETAILED ANALYSIS (ANNUAL)")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(150)
        layout.addWidget(self.analysis_text)

        widget.setLayout(layout)
        return widget

    def open_chart_dialog(self, figure, title):
        """Open enlarged chart dialog"""
        try:
            fig_copy = copy.deepcopy(figure)
            dialog = ChartDialog(fig_copy, title, self)
            dialog.exec()
        except Exception as e:
            print(f"❌ Error opening chart dialog: {e}")



    def calculate_dashboard_metrics(self):
        """Calculate dashboard indicators from annual data"""
        try:
            if not self.year_data:
                print("❌ No annual data to calculate")
                return

            sap_sheets = self.year_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = self.year_data.get('work_log', {}).get('sheets', {})

            orders_df = pd.DataFrame()
            if 'Orders' in sap_sheets and sap_sheets['Orders'] is not None:
                orders_df = sap_sheets['Orders']

            daily_df = pd.DataFrame()
            if 'Daily_Performance' in sap_sheets and sap_sheets['Daily_Performance'] is not None:
                daily_df = sap_sheets['Daily_Performance']

            fraud_df = pd.DataFrame()
            if 'Fraud_Events' in work_log_sheets and work_log_sheets['Fraud_Events'] is not None:
                fraud_df = work_log_sheets['Fraud_Events']

            browser_df = pd.DataFrame()
            if 'Browser_Sessions' in work_log_sheets and work_log_sheets['Browser_Sessions'] is not None:
                browser_df = work_log_sheets['Browser_Sessions']
            elif 'Browser_Time' in work_log_sheets and work_log_sheets['Browser_Time'] is not None:
                browser_df = work_log_sheets['Browser_Time']

            total_orders = len(orders_df) if not orders_df.empty else 0
            avg_monthly_orders = total_orders / 12 if total_orders > 0 else 0

            total_work_hours = 0
            if not browser_df.empty:
                if 'Total_Seconds' in browser_df.columns:
                    total_work_hours = browser_df['Total_Seconds'].sum() / 3600
                elif 'Duration_Seconds' in browser_df.columns:
                    total_work_hours = browser_df['Duration_Seconds'].sum() / 3600
                elif 'Hours' in browser_df.columns:
                    total_work_hours = browser_df['Hours'].sum()

            avg_monthly_hours = total_work_hours / 12 if total_work_hours > 0 else 0

            total_fraud = len(fraud_df) if not fraud_df.empty else 0

            completion_rate = 0
            if not orders_df.empty and 'Status' in orders_df.columns:
                completed_orders = len(orders_df[orders_df['Status'] == 'Completed'])
                completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

            total_revenue = 0
            total_profit = 0
            if not orders_df.empty:
                if 'Revenue' in orders_df.columns:
                    total_revenue = orders_df['Revenue'].sum()
                if 'Profit' in orders_df.columns:
                    total_profit = orders_df['Profit'].sum()

            self.metrics = {
                'total_orders': total_orders,
                'total_orders_str': f"{total_orders:,}",
                'avg_monthly_orders': avg_monthly_orders,
                'avg_monthly_orders_str': f"{avg_monthly_orders:.1f}",
                'total_work_hours': total_work_hours,
                'total_work_hours_str': f"{total_work_hours:.0f}",
                'avg_monthly_hours': avg_monthly_hours,
                'avg_monthly_hours_str': f"{avg_monthly_hours:.1f}",
                'total_fraud': total_fraud,
                'total_fraud_str': str(total_fraud),
                'completion_rate': completion_rate,
                'completion_rate_str': f"{completion_rate:.1f}%",
                'total_revenue': total_revenue,
                'total_revenue_str': f"{total_revenue:,.0f}",
                'total_profit': total_profit,
                'total_profit_str': f"{total_profit:,.0f}",
                'completed_orders': completed_orders if 'completed_orders' in locals() else 0,
                'completed_orders_str': f"{completed_orders:,}" if 'completed_orders' in locals() else "0"
            }

            self.calculate_monthly_chart_data(orders_df, fraud_df, browser_df, daily_df)
            print(f"📊 Metrics calculated from annual data")

        except Exception as e:
            print(f"❌ Error calculating dashboard metrics: {e}")
            import traceback
            traceback.print_exc()

    def calculate_monthly_chart_data(self, orders_df, fraud_df, browser_df, daily_df):
        """Calculate monthly chart data"""
        try:
            fraud_by_month = [0] * 12
            if not fraud_df.empty and 'Month' in fraud_df.columns:
                for month in range(1, 13):
                    month_data = fraud_df[fraud_df['Month'] == month]
                    fraud_by_month[month - 1] = len(month_data)

            self.metrics['fraud_by_month'] = fraud_by_month

            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            revenues = [0] * 12
            profits = [0] * 12

            if not orders_df.empty and 'Month' in orders_df.columns:
                for month in range(1, 13):
                    month_data = orders_df[orders_df['Month'] == month]
                    if not month_data.empty:
                        revenues[month - 1] = month_data['Revenue'].sum() if 'Revenue' in month_data.columns else 0
                        profits[month - 1] = month_data['Profit'].sum() if 'Profit' in month_data.columns else 0

            self.metrics['monthly_data'] = {
                'months': months,
                'revenues': revenues,
                'profits': profits
            }

            completion_distribution = self._calculate_completion_distribution(orders_df)
            self.metrics['completion_distribution'] = completion_distribution

            working_hours_monthly = self._calculate_working_hours_monthly(browser_df, daily_df)
            self.metrics['working_hours_monthly'] = working_hours_monthly

            print(f"📈 Monthly chart data calculated")

        except Exception as e:
            print(f"⚠️ Error calculating chart data: {e}")

    def _calculate_completion_distribution(self, orders_df):
        """Calculate completion distribution from annual data"""
        try:
            if not orders_df.empty and 'Status' in orders_df.columns:
                status_counts = orders_df['Status'].value_counts()

                completed = status_counts.get('Completed', 0) + status_counts.get('Completed', 0)
                processing = status_counts.get('Processing', 0) + status_counts.get('In Progress', 0) + \
                             status_counts.get('Processing', 0)
                pending = status_counts.get('Pending', 0) + status_counts.get('Not Started', 0) + \
                          status_counts.get('Not Started', 0)

                other = len(orders_df) - completed - processing - pending
                if other > 0:
                    pending += other

                sizes = [completed, processing, pending]

                return {
                    'labels': ['Completed', 'In Progress', 'Not Started'],
                    'sizes': sizes,
                    'colors': ['#10b981', '#f59e0b', '#ef4444']
                }
        except Exception as e:
            print(f"⚠️ Error calculating completion distribution: {e}")

        return {
            'labels': ['Completed', 'In Progress', 'Not Started'],
            'sizes': [0, 0, 0],
            'colors': ['#10b981', '#f59e0b', '#ef4444']
        }

    def _calculate_working_hours_monthly(self, browser_df, daily_df):
        """Calculate working hours by month"""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        hours = [0] * 12

        try:
            if not browser_df.empty and 'Month' in browser_df.columns:
                time_col = None
                for col in ['Total_Seconds', 'Duration_Seconds', 'Total_Time', 'Hours']:
                    if col in browser_df.columns:
                        time_col = col
                        break

                if time_col:
                    for month in range(1, 13):
                        month_data = browser_df[browser_df['Month'] == month]
                        if not month_data.empty:
                            if time_col in ['Total_Seconds', 'Duration_Seconds']:
                                hours[month - 1] = month_data[time_col].sum() / 3600
                            elif time_col == 'Total_Time':
                                def time_to_hours(time_str):
                                    try:
                                        if pd.isna(time_str):
                                            return 0
                                        if isinstance(time_str, str):
                                            parts = time_str.split(':')
                                            if len(parts) == 3:
                                                h, m, s = map(int, parts)
                                                return h + m / 60 + s / 3600
                                            elif len(parts) == 2:
                                                h, m = map(int, parts)
                                                return h + m / 60
                                        return float(time_str)
                                    except:
                                        return 0

                                hours[month - 1] = month_data[time_col].apply(time_to_hours).sum()
                            else:
                                hours[month - 1] = month_data[time_col].sum()

            elif not daily_df.empty and 'Month' in daily_df.columns:
                for month in range(1, 13):
                    month_data = daily_df[daily_df['Month'] == month]
                    if not month_data.empty and 'Working_Hours' in month_data.columns:
                        hours[month - 1] = month_data['Working_Hours'].sum()

        except Exception as e:
            print(f"⚠️ Error calculating working hours monthly: {e}")

        return {'months': months, 'hours': hours}

    def update_ui(self):
        """Update UI with new data"""
        try:
            if self.metric_labels:
                metric_values = [
                    self.metrics.get('total_orders_str', '0'),
                    f"{self.metrics.get('total_work_hours_str', '0')} hours",
                    self.metrics.get('total_fraud_str', '0'),
                    self.metrics.get('completion_rate_str', '0%')
                ]

                for label, value in zip(self.metric_labels, metric_values):
                    if label:
                        label.setText(value)

            self.update_fraud_chart()
            self.update_revenue_chart()
            self.update_completion_chart()
            self.update_working_hours_chart()
            self.update_analysis_text()

            current_time = datetime.now().strftime('%H:%M:%S')
            self.setWindowTitle(f"📊 Performance Dashboard - {self.user_name} | {current_time}")

            print("✅ UI updated")

        except Exception as e:
            print(f"❌ Error updating UI: {e}")
            import traceback
            traceback.print_exc()

    def update_fraud_chart(self):
        """Update fraud events bar chart by month"""
        try:
            self.fraud_figure.clear()
            self.fraud_figure.set_figwidth(7)
            self.fraud_figure.set_figheight(5)

            self.fraud_figure.patch.set_facecolor('#1e293b')
            ax = self.fraud_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            fraud_counts = self.metrics.get('fraud_by_month', [0] * 12)

            colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'] * 2
            bars = ax.bar(months, fraud_counts, color=colors, edgecolor='white',
                          linewidth=1, width=0.6, alpha=0.8)

            for bar, count in zip(bars, fraud_counts):
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                            f'{count}', ha='center', va='bottom',
                            fontsize=11, fontweight='bold', color='white')

            ax.set_ylabel('Fraud Events Count', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Fraud Events By Month (Annual)',
                         fontsize=13, fontweight=600, pad=15, color='white')

            ax.tick_params(axis='x', colors='#cbd5e1', labelsize=10, rotation=45)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8', axis='y')
            ax.set_axisbelow(True)

            self.fraud_figure.tight_layout(pad=2.0)

            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            self.fraud_canvas.draw()

        except Exception as e:
            print(f"❌ Error updating fraud chart: {e}")

    def update_revenue_chart(self):
        """Update revenue and profit line chart by month"""
        try:
            self.revenue_figure.clear()
            self.revenue_figure.set_figwidth(7)
            self.revenue_figure.set_figheight(5)

            self.revenue_figure.patch.set_facecolor('#1e293b')
            ax = self.revenue_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            monthly_data = self.metrics.get('monthly_data', {})
            months = monthly_data.get('months',
                                      ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                       'Dec'])
            revenues = monthly_data.get('revenues', [0] * 12)
            profits = monthly_data.get('profits', [0] * 12)

            x = np.arange(len(months))

            line1 = ax.plot(x, revenues, marker='o', linewidth=2, markersize=8,
                            label='Revenue', color='#3b82f6', alpha=0.8)[0]

            line2 = ax.plot(x, profits, marker='s', linewidth=2, markersize=8,
                            label='Profit', color='#10b981', alpha=0.8)[0]

            ax.set_xlabel('Month', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Revenue and Profit by Month (Annual)',
                         fontsize=13, fontweight=600, pad=15, color='white')
            ax.set_xticks(x)
            ax.set_xticklabels(months, fontsize=11, color='#cbd5e1')

            legend = ax.legend(fontsize=11, loc='upper left', facecolor='#1e293b',
                               edgecolor='#334155', framealpha=0.9)
            for text in legend.get_texts():
                text.set_color('#cbd5e1')

            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8')
            ax.set_axisbelow(True)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            def format_money(x, pos):
                if x >= 1e9:
                    return f'${x / 1e9:.1f}B'
                elif x >= 1e6:
                    return f'${x / 1e6:.1f}M'
                elif x >= 1e3:
                    return f'${x / 1e3:.1f}K'
                else:
                    return f'${x:.0f}'

            ax.yaxis.set_major_formatter(plt.FuncFormatter(format_money))

            self.revenue_figure.tight_layout(pad=2.0)

            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            self.revenue_canvas.draw()

        except Exception as e:
            print(f"❌ Error updating revenue chart: {e}")

    def update_completion_chart(self):
        """Update completion distribution pie chart"""
        try:
            self.completion_figure.clear()
            self.completion_figure.set_figwidth(7)
            self.completion_figure.set_figheight(5)

            self.completion_figure.patch.set_facecolor('#1e293b')
            ax = self.completion_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            completion_data = self.metrics.get('completion_distribution', {})
            labels = completion_data.get('labels', ['Completed', 'In Progress', 'Not Started'])
            sizes = completion_data.get('sizes', [0, 0, 0])
            colors = completion_data.get('colors', ['#10b981', '#f59e0b', '#ef4444'])

            if sum(sizes) > 0:
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                                  startangle=90, pctdistance=0.85,
                                                  wedgeprops=dict(width=0.3, edgecolor='w', linewidth=2),
                                                  textprops=dict(color='white', fontsize=11))

                centre_circle = plt.Circle((0, 0), 0.70, fc='#1e293b')
                ax.add_artist(centre_circle)

                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')

                for text in texts:
                    text.set_fontsize(12)
                    text.set_color('#cbd5e1')
            else:
                ax.text(0.5, 0.5, 'No data available', ha='center', va='center',
                        fontsize=14, color='#94a3b8', transform=ax.transAxes)

            ax.set_title('Completion Distribution (Annual)', fontsize=13, fontweight=600, pad=15, color='white')
            ax.axis('equal')

            self.completion_canvas.draw()

        except Exception as e:
            print(f"❌ Error updating pie chart: {e}")

    def update_working_hours_chart(self):
        """Update working hours bar chart by month"""
        try:
            self.working_hours_figure.clear()
            self.working_hours_figure.set_figwidth(7)
            self.working_hours_figure.set_figheight(5)

            self.working_hours_figure.patch.set_facecolor('#1e293b')
            ax = self.working_hours_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            monthly_data = self.metrics.get('working_hours_monthly', {})
            months = monthly_data.get('months',
                                      ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov',
                                       'Dec'])
            hours = monthly_data.get('hours', [0] * 12)

            color_map = ['#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#1c366b'] * 2
            bars = ax.bar(months, hours, color=color_map, edgecolor='white',
                          linewidth=1, alpha=0.9, width=0.6)

            for bar, hour in zip(bars, hours):
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                            f'{hour:.1f}h', ha='center', va='bottom',
                            fontsize=11, fontweight='bold', color='white')

            avg_hours = np.mean(hours) if len(hours) > 0 else 0
            ax.axhline(y=avg_hours, color='#ef4444', linestyle='--', linewidth=1.5, alpha=0.7,
                       label=f'Average: {avg_hours:.1f}h/month')

            ax.set_ylabel('Working hours', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Working hours by month (annual)',
                         fontsize=13, fontweight=600, pad=15, color='white')

            legend = ax.legend(fontsize=11, loc='upper right', facecolor='#1e293b', edgecolor='#334155')
            for text in legend.get_texts():
                text.set_color('#cbd5e1')

            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8', axis='y')
            ax.set_axisbelow(True)
            ax.tick_params(axis='x', colors='#cbd5e1', labelsize=10, rotation=45)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            self.working_hours_figure.tight_layout(pad=2.0)

            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            self.working_hours_canvas.draw()

        except Exception as e:
            print(f"❌ Error updating working hours chart: {e}")

    def update_analysis_text(self):
        """Update analysis text with actual data"""
        try:
            if not self.metrics:
                self.analysis_text.setHtml("""
                    <div style='color: #ef4444; padding: 20px;'>
                        <p>❌ No data available for analysis</p>
                    </div>
                """)
                return

            total_orders = self.metrics.get('total_orders', 0)
            completed_orders = self.metrics.get('completed_orders', 0)
            completion_rate = self.metrics.get('completion_rate', 0)
            total_work_hours = self.metrics.get('total_work_hours', 0)
            total_revenue = self.metrics.get('total_revenue', 0)
            total_profit = self.metrics.get('total_profit', 0)
            total_fraud = self.metrics.get('total_fraud', 0)
            avg_monthly_orders = self.metrics.get('avg_monthly_orders', 0)
            avg_monthly_hours = self.metrics.get('avg_monthly_hours', 0)

            pending_orders = max(0, total_orders - completed_orders)
            avg_monthly_revenue = total_revenue / 12 if total_revenue > 0 else 0
            avg_monthly_profit = total_profit / 12 if total_profit > 0 else 0
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            revenue_per_order = total_revenue / total_orders if total_orders > 0 else 0

            performance_level = ""
            if completion_rate >= 95:
                performance_level = "Excellent"
            elif completion_rate >= 85:
                performance_level = "Good"
            elif completion_rate >= 70:
                performance_level = "Average"
            else:
                performance_level = "Needs Improvement"

            risk_level = ""
            risk_analysis = ""
            if total_fraud > 10:
                risk_level = "High"
                risk_analysis = "Multiple fraud events detected. Immediate review and action required."
            elif total_fraud > 5:
                risk_level = "Medium"
                risk_analysis = "Some fraud events detected. Close monitoring required."
            else:
                risk_level = "Low"
                risk_analysis = "Risk level acceptable."

            time_efficiency = 0
            error_rate = 0
            orders_per_hour = 0

            completion_color = "#10b981" if completion_rate >= 95 else "#f59e0b" if completion_rate >= 85 else "#ef4444"
            completion_note = "(Target achieved)" if completion_rate >= 95 else "(Needs improvement)"

            time_efficiency_color = "#ef4444"
            error_rate_color = "#10b981"

            analysis_html = f"""
            <div style="color: #cbd5e1; font-family: 'Segoe UI', Arial, sans-serif;">
                <h3 style="color: #ffffff; margin-bottom: 15px;">📊 ACTUAL PERFORMANCE ANALYSIS</h3>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <!-- Column 1: Performance -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #3b82f6; margin-top: 0; margin-bottom: 10px;">📈 WORK PERFORMANCE</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Total orders:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_orders:,.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Completed:</span> 
                            <span style="color: #10b981; font-weight: 600;">{completed_orders:,.0f}</span> ({completion_rate:.1f}%)
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Pending:</span> 
                            <span style="color: #f59e0b; font-weight: 600;">{pending_orders:,.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Working time:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_work_hours:,.0f} hours</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Monthly average:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{avg_monthly_orders:.0f} orders | {avg_monthly_hours:.0f} hours</span>
                        </p>
                    </div>

                    <!-- Column 2: Financial -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
                        <h4 style="color: #10b981; margin-top: 0; margin-bottom: 10px;">💰 FINANCIAL RESULTS</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Annual revenue:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_revenue:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Annual profit:</span> 
                            <span style="color: #10b981; font-weight: 600;">{total_profit:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Monthly average:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{avg_monthly_revenue:,.0f} VND | {avg_monthly_profit:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Profit margin:</span> 
                            <span style="color: #10b981; font-weight: 600;">{profit_margin:.1f}%</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Revenue per order:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{revenue_per_order:,.0f} VND</span>
                        </p>
                    </div>
                </div>

                <!-- Risk and evaluation -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <!-- Column 3: Risk -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                        <h4 style="color: #ef4444; margin-top: 0; margin-bottom: 10px;">⚠️ RISK ANALYSIS</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Fraud events:</span> 
                            <span style="color: #ef4444; font-weight: 600;">{total_fraud:.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Risk level:</span> 
                            <span style="color: #ef4444; font-weight: 600;">{risk_level}</span>
                        </p>
                        <p style="color: #f59e0b; font-size: 12px; margin-top: 10px;">
                            {risk_analysis}
                        </p>
                    </div>

                    <!-- Column 4: Evaluation -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                        <h4 style="color: #8b5cf6; margin-top: 0; margin-bottom: 10px;">🎯 OVERALL EVALUATION</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Performance level:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{performance_level}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Completion rate:</span> 
                            <span style="color: {completion_color}; font-weight: 600;">{completion_rate:.1f}%</span>
                            {completion_note}
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Error rate:</span> 
                            <span style="color: {error_rate_color}; font-weight: 600;">{error_rate:.1f}%</span>
                        </p>
                    </div>
                </div>

                <!-- Recommendations -->
                <div style="background-color: #334155; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="color: #ffffff; margin-top: 0; margin-bottom: 10px;">💡 ACTION RECOMMENDATIONS</h4>
                    <ul style="line-height: 1.6; margin-bottom: 10px; padding-left: 20px;">
                        {'<li>Reduce pending orders to improve completion rate</li>' if pending_orders > 10 else ''}
                        {'<li>Enhance quality control to reduce fraud events</li>' if total_fraud > 3 else ''}
                        <li>Maintain and leverage current strengths</li>
                    </ul>

                    <div style="margin-top: 15px; padding: 10px; background-color: #1e293b; border-radius: 5px;">
                        <p style="margin: 0; color: #cbd5e1; font-size: 12px;">
                            <strong>📅 Analysis date:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
                            <strong>📊 Data source:</strong> SAP Orders & Work Logs (annual)<br>
                            <strong>📈 Methodology:</strong> Actual data analysis & KPI indicators
                        </p>
                    </div>
                </div>
            </div>
            """

            self.analysis_text.setHtml(analysis_html)

        except Exception as e:
            print(f"❌ Error updating analysis: {e}")
            import traceback
            traceback.print_exc()
            self.analysis_text.setHtml(f"""
                <div style='color: #ef4444; padding: 20px;'>
                    <p>Error updating analysis: {str(e)}</p>
                </div>
            """)


def main():
    """Main function to run dashboard"""
    app = QApplication(sys.argv)

    try:
        import pandas as pd
        import matplotlib
    except ImportError as e:
        QMessageBox.critical(None, "Library Error",
                             f"Missing required libraries!\n\n"
                             f"Please install:\n"
                             f"pip install pandas matplotlib\n\n"
                             f"Error details: {str(e)}")
        sys.exit(1)

    print("🚀 LAUNCHING PERFORMANCE DASHBOARD - ENHANCED VERSION (ANNUAL DATA)")
    print("=" * 70)

    # Create and display dashboard
    dashboard = PerformanceDashboard("EM001")

    screen = app.primaryScreen()
    screen_geometry = screen.geometry()

    width = min(1400, int(screen_geometry.width() * 0.95))
    height = min(900, int(screen_geometry.height() * 0.95))

    dashboard.resize(width, height)
    dashboard.move(
        (screen_geometry.width() - width) // 2,
        (screen_geometry.height() - height) // 2
    )

    dashboard.show()

    print(f"✅ Dashboard displayed: {width}x{height}")
    print("=" * 70)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()