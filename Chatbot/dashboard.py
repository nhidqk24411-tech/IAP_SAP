#!/usr/bin/env python3
"""
Dashboard Hiệu Suất - Phiên bản cải tiến với đa dạng biểu đồ và tooltip hover
Lấy dữ liệu từ DataProcessor và hiển thị theo tháng
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
from pathlib import Path
import copy
from matplotlib.patches import Wedge

# Sửa import cho matplotlib tương thích với PyQt6
import matplotlib

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.patches import Patch

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class ChartDialog(QDialog):
    """Dialog để hiển thị biểu đồ phóng to"""

    def __init__(self, figure, title, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"📊 {title}")
        self.setWindowFlags(
            Qt.WindowType.Window | Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMaximizeButtonHint)

        # Style cho dialog
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

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        # Header với tiêu đề và nút đóng
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

        close_btn = QPushButton("✕ Đóng")
        close_btn.setFixedSize(80, 35)
        close_btn.clicked.connect(self.close)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)

        layout.addWidget(header_widget)

        # Canvas cho biểu đồ
        self.canvas = FigureCanvas(figure)
        self.canvas.setMinimumSize(800, 500)
        layout.addWidget(self.canvas)

        # Footer với các nút điều khiển
        footer_widget = QWidget()
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)

        save_btn = QPushButton("💾 Lưu Ảnh")
        save_btn.setFixedSize(100, 35)
        save_btn.clicked.connect(self.save_image)

        refresh_btn = QPushButton("🔄 Làm Mới")
        refresh_btn.setFixedSize(100, 35)
        refresh_btn.clicked.connect(self.refresh_chart)

        footer_layout.addStretch()
        footer_layout.addWidget(save_btn)
        footer_layout.addWidget(refresh_btn)

        layout.addWidget(footer_widget)

        self.setLayout(layout)
        self.resize(900, 600)

        # Lưu figure gốc để làm mới
        self.original_figure = figure

    def save_image(self):
        """Lưu biểu đồ thành file ảnh"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Lưu Biểu Đồ",
            f"biểu_đồ_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
        )

        if file_path:
            try:
                self.original_figure.savefig(file_path, dpi=300, bbox_inches='tight', facecolor='#1e293b')
                QMessageBox.information(self, "Thành công", f"Đã lưu biểu đồ vào:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Lỗi", f"Không thể lưu file:\n{str(e)}")

    def refresh_chart(self):
        """Làm mới biểu đồ"""
        self.canvas.draw()

    def closeEvent(self, event):
        """Xử lý khi đóng dialog"""
        event.accept()


class DataAnalyzer:
    """Phân tích dữ liệu từ Excel files"""

    @staticmethod
    def load_sap_data(file_path):
        """Đọc dữ liệu từ file SAP Excel"""
        try:
            print(f"📂 Đang đọc dữ liệu từ: {file_path}")

            if not os.path.exists(file_path):
                print(f"❌ File không tồn tại: {file_path}")
                return None

            # Đọc sheet Orders
            orders_df = pd.read_excel(file_path, sheet_name='Orders')
            print(f"   Đọc được {len(orders_df)} dòng từ sheet Orders")

            # Đọc sheet Daily_Performance
            daily_df = pd.read_excel(file_path, sheet_name='Daily_Performance')
            print(f"   Đọc được {len(daily_df)} dòng từ sheet Daily_Performance")

            return {
                'orders': orders_df,
                'daily_performance': daily_df
            }
        except Exception as e:
            print(f"❌ Lỗi đọc dữ liệu SAP: {e}")
            return None

    @staticmethod
    def load_work_logs(file_path):
        """Đọc dữ liệu từ file work logs"""
        try:
            print(f"📂 Đang đọc dữ liệu từ: {file_path}")

            if not os.path.exists(file_path):
                print(f"❌ File không tồn tại: {file_path}")
                return None

            data_dict = {
                'fraud_events': None,
                'mouse_details': None,
                'browser_time': None,
                'browser_session': None
            }

            # Thử đọc từng sheet
            excel_file = pd.ExcelFile(file_path)
            sheet_names = excel_file.sheet_names

            for sheet in sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    key = sheet.lower().replace(' ', '_')
                    data_dict[key] = df
                    print(f"   Đọc được {len(df)} dòng từ sheet {sheet}")
                except Exception as e:
                    print(f"   ⚠️ Không đọc được sheet {sheet}: {e}")

            return data_dict
        except Exception as e:
            print(f"❌ Lỗi đọc work logs: {e}")
            return None


class HoverTooltip:
    """Class để xử lý tooltip khi hover trên biểu đồ"""

    @staticmethod
    def add_bar_tooltip(ax, bars, values, formatter=None):
        """Thêm tooltip cho biểu đồ cột"""

        def format_value(val):
            if formatter:
                return formatter(val)
            return str(val)

        def hover(event):
            if event.inaxes == ax:
                for bar, val in zip(bars, values):
                    if bar.contains(event)[0]:
                        # Xóa tooltip cũ
                        for txt in ax.texts:
                            if txt.get_text().startswith('Tooltip:'):
                                txt.remove()

                        # Thêm tooltip mới
                        x = bar.get_x() + bar.get_width() / 2
                        y = bar.get_height()
                        ax.text(x, y + 0.5, f'Tooltip: {format_value(val)}',
                                ha='center', va='bottom', fontsize=10,
                                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))
                        ax.figure.canvas.draw_idle()
                        return

        return hover

    @staticmethod
    def add_line_tooltip(ax, lines, x_data, y_data, formatter=None):
        """Thêm tooltip cho biểu đồ đường"""

        def format_value(val):
            if formatter:
                return formatter(val)
            return str(val)

        def hover(event):
            if event.inaxes == ax:
                for line, x_vals, y_vals in zip(lines, x_data, y_data):
                    cont, ind = line.contains(event)
                    if cont:
                        # Xóa tooltip cũ
                        for txt in ax.texts:
                            if txt.get_text().startswith('Tooltip:'):
                                txt.remove()

                        # Thêm tooltip mới
                        idx = ind['ind'][0]
                        x = x_vals[idx]
                        y = y_vals[idx]
                        ax.text(x, y, f'Tooltip: {format_value(y)}',
                                ha='center', va='bottom', fontsize=10,
                                bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.8))
                        ax.figure.canvas.draw_idle()
                        return

        return hover


class PerformanceDashboard(QWidget):
    """Dashboard hiển thị hiệu suất nhân viên - Phiên bản cải tiến với dữ liệu theo tháng"""

    def __init__(self, user_name):
        super().__init__()
        self.user_name = user_name
        self.metrics = {}
        self.tooltip_annotations = []
        self.data_processor = None
        self.year_data = None

        try:
            from config import Config
            self.config = Config
            print(f"✅ Đã tải config cho {user_name}")
        except ImportError as e:
            print(f"❌ Không thể import config: {e}")
            QMessageBox.critical(None, "Lỗi", "Không thể tải cấu hình từ config.py")
            self.config = None

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Khởi tạo giao diện với thanh cuộn"""
        self.setWindowTitle(f"📊 DASHBOARD HIỆU SUẤT - {self.user_name}")

        # Áp dụng style sheet
        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
            }
            QLabel {
                color: #e2e8f0;
            }
            QGroupBox {
                font-weight: 600;
                font-size: 14px;
                border: 1px solid #334155;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: #1e293b;
                color: #cbd5e1;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #60a5fa;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
            QTextEdit {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 15px;
                font-size: 13px;
                line-height: 1.5;
                color: #cbd5e1;
            }
            QFrame {
                background-color: #1e293b;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Main scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Header
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(f"Tổng Quan Hiệu Suất Nhân Viên - {self.user_name} (Dữ liệu cả năm)")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
            padding: 10px 0;
        """)

        self.refresh_btn = QPushButton("🔄 Tải Lại")
        self.refresh_btn.clicked.connect(self.load_data)
        self.refresh_btn.setFixedSize(100, 35)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)

        content_layout.addWidget(header_widget)

        # Metrics grid - 4 metric cards hàng trên
        metrics_grid = self.create_metrics_grid()
        content_layout.addWidget(metrics_grid)

        # Charts section - 2 biểu đồ trên cùng
        charts_container = QWidget()
        charts_layout = QHBoxLayout(charts_container)
        charts_layout.setSpacing(20)
        charts_layout.setContentsMargins(0, 0, 0, 0)

        # Biểu đồ 1: Fraud by month (cột)
        fraud_chart = self.create_fraud_chart_widget()
        charts_layout.addWidget(fraud_chart)

        # Biểu đồ 2: Revenue & Profit (đường)
        revenue_chart = self.create_revenue_chart_widget()
        charts_layout.addWidget(revenue_chart)

        content_layout.addWidget(charts_container)

        # Two more charts section - 2 biểu đồ dưới
        charts_container2 = QWidget()
        charts_layout2 = QHBoxLayout(charts_container2)
        charts_layout2.setSpacing(20)
        charts_layout2.setContentsMargins(0, 0, 0, 0)

        # Biểu đồ 3: Completion Rate (tròn)
        completion_chart = self.create_completion_chart_widget()
        charts_layout2.addWidget(completion_chart)

        # Biểu đồ 4: Working Hours (cột) - Đổi tên thành theo tháng
        working_hours_chart = self.create_working_hours_chart_widget()
        charts_layout2.addWidget(working_hours_chart)

        content_layout.addWidget(charts_container2)

        # Analysis section
        analysis_widget = self.create_analysis_widget()
        content_layout.addWidget(analysis_widget)

        # Footer
        footer_label = QLabel(
            f"Dữ liệu từ hệ thống SAP và nhật ký công việc. Ngày cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        footer_label.setStyleSheet("""
            font-size: 11px;
            color: #94a3b8;
            font-style: italic;
            padding: 8px;
            background-color: #1e293b;
            border-radius: 5px;
            border: 1px solid #334155;
        """)
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(footer_label)

        # Thêm stretch để đẩy footer xuống dưới
        content_layout.addStretch(1)

        # Đặt content widget vào scroll area
        scroll_area.setWidget(content_widget)

        # Main layout cho widget chính
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll_area)

        self.setMinimumSize(1200, 700)

    def create_metrics_grid(self):
        """Tạo grid hiển thị 4 chỉ số chính"""
        grid = QGroupBox("CHỈ SỐ HIỆU SUẤT (CẢ NĂM)")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)
        grid_layout.setContentsMargins(15, 25, 15, 15)

        # Tạo 4 metric cards
        cards = []
        metrics_info = [
            ("📦 TỔNG ĐƠN HÀNG", "0", "Trung bình 0 đơn/tháng", "#3b82f6"),
            ("⏰ TỔNG THỜI GIAN", "0 giờ", "Trung bình 0 giờ/tháng", "#10b981"),
            ("⚠️ SỰ KIỆN GIAN LẬN", "0", "Mức cảnh báo", "#ef4444"),
            ("✅ TỶ LỆ HOÀN THÀNH", "0%", "Mục tiêu 95%", "#8b5cf6")
        ]

        for i, (title, value, desc, color) in enumerate(metrics_info):
            card = self.create_metric_card(title, value, desc, color)
            cards.append(card)
            grid_layout.addWidget(card, 0, i)

        # Lưu reference đến các label
        self.metric_labels = [card.findChild(QLabel, "value") for card in cards]

        # Thiết lập tỷ lệ co giãn cho các cột
        for i in range(4):
            grid_layout.setColumnStretch(i, 1)

        grid.setLayout(grid_layout)
        return grid

    def create_metric_card(self, title, value, description, color):
        """Tạo card hiển thị metric với thiết kế đẹp hơn"""
        card = QFrame()
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        card.setMinimumHeight(140)
        card.setMaximumHeight(160)

        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(8)
        card_layout.setContentsMargins(20, 15, 20, 15)

        # Icon và Title
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        # Icon (sử dụng emoji trong QLabel)
        icon_label = QLabel(title.split()[0])  # Lấy emoji từ title
        icon_label.setStyleSheet(f"""
            font-size: 20px;
            color: {color};
        """)
        icon_label.setFixedSize(30, 30)

        title_text = " ".join(title.split()[1:])  # Bỏ emoji
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

        # Value
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

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 12px;
            color: #94a3b8;
            font-style: italic;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(desc_label)

        # Thiết lập style cho card
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
        """Tạo widget biểu đồ cột sự kiện gian lận theo tháng"""
        widget = QGroupBox("SỰ KIỆN GIAN LẬN THEO THÁNG")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.fraud_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.fraud_canvas = FigureCanvas(self.fraud_figure)
        self.fraud_canvas.setStyleSheet("background-color: transparent;")
        self.fraud_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.fraud_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.fraud_figure,
                                                                                 "Sự Kiện Gian Lận Theo Tháng")
        layout.addWidget(self.fraud_canvas)

        layout.setStretchFactor(self.fraud_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_revenue_chart_widget(self):
        """Tạo widget biểu đồ đường doanh thu và lợi nhuận theo tháng"""
        widget = QGroupBox("DOANH THU VÀ LỢI NHUẬN THEO THÁNG")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.revenue_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.revenue_canvas = FigureCanvas(self.revenue_figure)
        self.revenue_canvas.setStyleSheet("background-color: transparent;")
        self.revenue_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.revenue_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.revenue_figure,
                                                                                   "Doanh Thu và Lợi Nhuận Theo Tháng")
        layout.addWidget(self.revenue_canvas)

        layout.setStretchFactor(self.revenue_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_completion_chart_widget(self):
        """Tạo widget biểu đồ tròn tỷ lệ hoàn thành"""
        widget = QGroupBox("PHÂN BỔ MỨC ĐỘ HOÀN THÀNH")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.completion_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.completion_canvas = FigureCanvas(self.completion_figure)
        self.completion_canvas.setStyleSheet("background-color: transparent;")
        self.completion_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.completion_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.completion_figure,
                                                                                      "Phân Bổ Mức Độ Hoàn Thành")
        layout.addWidget(self.completion_canvas)

        layout.setStretchFactor(self.completion_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_working_hours_chart_widget(self):
        """Tạo widget biểu đồ cột thời gian làm việc theo tháng"""
        widget = QGroupBox("THỜI GIAN LÀM VIỆC THEO THÁNG")
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 10)

        self.working_hours_figure = Figure(figsize=(7, 5), dpi=100, facecolor='#1e293b')
        self.working_hours_canvas = FigureCanvas(self.working_hours_figure)
        self.working_hours_canvas.setStyleSheet("background-color: transparent;")
        self.working_hours_canvas.setCursor(Qt.CursorShape.PointingHandCursor)
        self.working_hours_canvas.mousePressEvent = lambda event: self.open_chart_dialog(self.working_hours_figure,
                                                                                         "Thời Gian Làm Việc Theo Tháng")
        layout.addWidget(self.working_hours_canvas)

        layout.setStretchFactor(self.working_hours_canvas, 1)
        widget.setLayout(layout)
        widget.setMinimumHeight(350)
        return widget

    def create_analysis_widget(self):
        """Tạo widget phân tích chi tiết"""
        widget = QGroupBox("PHÂN TÍCH CHI TIẾT (CẢ NĂM)")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 20, 15, 15)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setMinimumHeight(150)
        layout.addWidget(self.analysis_text)

        widget.setLayout(layout)
        return widget

    def open_chart_dialog(self, figure, title):
        """Mở dialog phóng to biểu đồ"""
        try:
            # Tạo bản sao của figure để tránh thay đổi figure gốc
            fig_copy = copy.deepcopy(figure)
            dialog = ChartDialog(fig_copy, title, self)
            dialog.exec()
        except Exception as e:
            print(f"❌ Lỗi mở dialog biểu đồ: {e}")

    def load_data(self):
        """Tải dữ liệu từ DataProcessor cả năm"""
        try:
            print(f"\n{'=' * 70}")
            print(f"📊 ĐANG TẢI DỮ LIỆU CHO {self.user_name} (CẢ NĂM)")
            print(f"{'=' * 70}")

            if not self.config:
                print("❌ Không có config để tải dữ liệu")
                QMessageBox.warning(self, "Lỗi", "Không thể tải cấu hình hệ thống")
                return

            # Tạo DataProcessor
            from data_processor import DataProcessor
            self.data_processor = DataProcessor(self.user_name)

            # Tải dữ liệu cả năm
            success = self.data_processor.load_all_data()

            if not success:
                print("❌ Không thể tải dữ liệu từ DataProcessor")
                QMessageBox.warning(self, "Lỗi", "Không thể tải dữ liệu từ hệ thống")
                return

            # Lấy dữ liệu từ DataProcessor
            all_data = self.data_processor.get_all_data()
            self.year_data = self.data_processor.get_dashboard_data()

            if not all_data or not self.year_data:
                print("❌ Không có dữ liệu từ DataProcessor")
                QMessageBox.warning(self, "Lỗi", "Không có dữ liệu để hiển thị")
                return

            # Lấy summary data từ DataProcessor
            summary_data = self.data_processor.get_summary_data()

            # Tính toán metrics cho dashboard
            self.calculate_dashboard_metrics()

            # Update UI
            self.update_ui()

            print(f"✅ Hoàn thành tải dữ liệu cả năm!")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể tải dữ liệu:\n{str(e)}")

    def calculate_dashboard_metrics(self):
        """Tính toán các chỉ số cho dashboard từ dữ liệu cả năm"""
        try:
            if not self.year_data:
                print("❌ Không có dữ liệu năm để tính toán")
                return

            # Lấy dữ liệu từ year_data
            sap_sheets = self.year_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = self.year_data.get('work_log', {}).get('sheets', {})

            # 1. Tổng hợp dữ liệu orders
            orders_df = pd.DataFrame()
            if 'Orders' in sap_sheets and sap_sheets['Orders'] is not None:
                orders_df = sap_sheets['Orders']

            # 2. Tổng hợp dữ liệu daily performance
            daily_df = pd.DataFrame()
            if 'Daily_Performance' in sap_sheets and sap_sheets['Daily_Performance'] is not None:
                daily_df = sap_sheets['Daily_Performance']

            # 3. Tổng hợp dữ liệu fraud events
            fraud_df = pd.DataFrame()
            if 'Fraud_Events' in work_log_sheets and work_log_sheets['Fraud_Events'] is not None:
                fraud_df = work_log_sheets['Fraud_Events']

            # 4. Tổng hợp dữ liệu browser sessions
            browser_df = pd.DataFrame()
            if 'Browser_Sessions' in work_log_sheets and work_log_sheets['Browser_Sessions'] is not None:
                browser_df = work_log_sheets['Browser_Sessions']
            elif 'Browser_Time' in work_log_sheets and work_log_sheets['Browser_Time'] is not None:
                browser_df = work_log_sheets['Browser_Time']

            # 5. Tính toán các chỉ số
            # Tổng đơn hàng cả năm
            total_orders = len(orders_df) if not orders_df.empty else 0
            avg_monthly_orders = total_orders / 12 if total_orders > 0 else 0

            # Tổng thời gian làm việc cả năm
            total_work_hours = 0
            if not browser_df.empty:
                if 'Total_Seconds' in browser_df.columns:
                    total_work_hours = browser_df['Total_Seconds'].sum() / 3600
                elif 'Duration_Seconds' in browser_df.columns:
                    total_work_hours = browser_df['Duration_Seconds'].sum() / 3600
                elif 'Hours' in browser_df.columns:
                    total_work_hours = browser_df['Hours'].sum()

            avg_monthly_hours = total_work_hours / 12 if total_work_hours > 0 else 0

            # Tổng sự kiện gian lận
            total_fraud = len(fraud_df) if not fraud_df.empty else 0

            # Tỷ lệ hoàn thành
            completion_rate = 0
            if not orders_df.empty and 'Status' in orders_df.columns:
                completed_orders = len(orders_df[orders_df['Status'] == 'Completed'])
                completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

            # Tổng doanh thu và lợi nhuận
            total_revenue = 0
            total_profit = 0
            if not orders_df.empty:
                if 'Revenue' in orders_df.columns:
                    total_revenue = orders_df['Revenue'].sum()
                if 'Profit' in orders_df.columns:
                    total_profit = orders_df['Profit'].sum()

            # Lưu metrics
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

            # 6. Tính toán dữ liệu cho biểu đồ theo tháng
            self.calculate_monthly_chart_data(orders_df, fraud_df, browser_df, daily_df)

            print(f"📊 Đã tính toán metrics từ dữ liệu cả năm")

        except Exception as e:
            print(f"❌ Lỗi tính toán metrics dashboard: {e}")
            import traceback
            traceback.print_exc()

    def calculate_monthly_chart_data(self, orders_df, fraud_df, browser_df, daily_df):
        """Tính toán dữ liệu biểu đồ theo tháng"""
        try:
            # 1. Sự kiện gian lận theo tháng
            fraud_by_month = [0] * 12
            if not fraud_df.empty and 'Month' in fraud_df.columns:
                for month in range(1, 13):
                    month_data = fraud_df[fraud_df['Month'] == month]
                    fraud_by_month[month - 1] = len(month_data)

            self.metrics['fraud_by_month'] = fraud_by_month

            # 2. Doanh thu và lợi nhuận theo tháng
            months = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
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

            # 3. Phân bổ mức độ hoàn thành
            completion_distribution = self._calculate_completion_distribution(orders_df)
            self.metrics['completion_distribution'] = completion_distribution

            # 4. Thời gian làm việc theo tháng
            working_hours_monthly = self._calculate_working_hours_monthly(browser_df, daily_df)
            self.metrics['working_hours_monthly'] = working_hours_monthly

            print(f"📈 Đã tính toán dữ liệu biểu đồ theo tháng")

        except Exception as e:
            print(f"⚠️ Lỗi tính toán dữ liệu biểu đồ: {e}")

    def _calculate_completion_distribution(self, orders_df):
        """Tính toán phân bổ mức độ hoàn thành từ dữ liệu cả năm"""
        try:
            if not orders_df.empty and 'Status' in orders_df.columns:
                status_counts = orders_df['Status'].value_counts()

                # Phân loại trạng thái
                completed = status_counts.get('Completed', 0) + status_counts.get('Hoàn thành', 0)
                processing = status_counts.get('Processing', 0) + status_counts.get('Đang xử lý', 0) + \
                             status_counts.get('In Progress', 0)
                pending = status_counts.get('Pending', 0) + status_counts.get('Chưa bắt đầu', 0) + \
                          status_counts.get('Not Started', 0)

                # Tính các trạng thái khác
                other = len(orders_df) - completed - processing - pending
                if other > 0:
                    pending += other  # Thêm vào pending

                sizes = [completed, processing, pending]

                return {
                    'labels': ['Hoàn thành', 'Đang xử lý', 'Chưa bắt đầu'],
                    'sizes': sizes,
                    'colors': ['#10b981', '#f59e0b', '#ef4444']
                }
        except Exception as e:
            print(f"⚠️ Lỗi tính completion distribution: {e}")

        # Nếu không có dữ liệu, trả về giá trị 0
        return {
            'labels': ['Hoàn thành', 'Đang xử lý', 'Chưa bắt đầu'],
            'sizes': [0, 0, 0],
            'colors': ['#10b981', '#f59e0b', '#ef4444']
        }

    def _calculate_working_hours_monthly(self, browser_df, daily_df):
        """Tính toán thời gian làm việc theo tháng"""
        months = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
        hours = [0] * 12

        try:
            # Ưu tiên dữ liệu từ browser session
            if not browser_df.empty and 'Month' in browser_df.columns:
                # Tìm cột thời gian
                time_col = None
                for col in ['Total_Seconds', 'Duration_Seconds', 'Total_Time', 'Hours']:
                    if col in browser_df.columns:
                        time_col = col
                        break

                if time_col:
                    # Tính toán cho từng tháng
                    for month in range(1, 13):
                        month_data = browser_df[browser_df['Month'] == month]
                        if not month_data.empty:
                            if time_col in ['Total_Seconds', 'Duration_Seconds']:
                                hours[month - 1] = month_data[time_col].sum() / 3600
                            elif time_col == 'Total_Time':
                                # Xử lý định dạng HH:MM:SS
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

            # Nếu không có browser data, thử từ daily_df
            elif not daily_df.empty and 'Month' in daily_df.columns:
                for month in range(1, 13):
                    month_data = daily_df[daily_df['Month'] == month]
                    if not month_data.empty and 'Working_Hours' in month_data.columns:
                        hours[month - 1] = month_data['Working_Hours'].sum()

        except Exception as e:
            print(f"⚠️ Lỗi tính working hours monthly: {e}")

        return {'months': months, 'hours': hours}

    def update_ui(self):
        """Cập nhật giao diện với dữ liệu mới"""
        try:
            # Update metrics cards
            if self.metric_labels:
                metric_values = [
                    self.metrics.get('total_orders_str', '0'),
                    f"{self.metrics.get('total_work_hours_str', '0')} giờ",
                    self.metrics.get('total_fraud_str', '0'),
                    self.metrics.get('completion_rate_str', '0%')
                ]

                for label, value in zip(self.metric_labels, metric_values):
                    if label:
                        label.setText(value)

            # Update charts
            self.update_fraud_chart()
            self.update_revenue_chart()
            self.update_completion_chart()
            self.update_working_hours_chart()

            # Update analysis text
            self.update_analysis_text()

            # Update window title
            current_time = datetime.now().strftime('%H:%M:%S')
            self.setWindowTitle(f"📊 Dashboard Hiệu Suất - {self.user_name} | {current_time}")

            print("✅ Đã cập nhật giao diện")

        except Exception as e:
            print(f"❌ Lỗi cập nhật UI: {e}")
            import traceback
            traceback.print_exc()

    def update_fraud_chart(self):
        """Cập nhật biểu đồ cột gian lận theo tháng"""
        try:
            self.fraud_figure.clear()

            # Tăng kích thước figure
            self.fraud_figure.set_figwidth(7)
            self.fraud_figure.set_figheight(5)

            # Đặt màu nền cho figure và axes
            self.fraud_figure.patch.set_facecolor('#1e293b')
            ax = self.fraud_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            months = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12']
            fraud_counts = self.metrics.get('fraud_by_month', [0] * 12)

            # Tạo biểu đồ cột
            colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4'] * 2
            bars = ax.bar(months, fraud_counts, color=colors, edgecolor='white',
                          linewidth=1, width=0.6, alpha=0.8)

            # Thêm giá trị trên mỗi cột
            for bar, count in zip(bars, fraud_counts):
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                            f'{count}', ha='center', va='bottom',
                            fontsize=11, fontweight='bold', color='white')

            # Tùy chỉnh biểu đồ
            ax.set_ylabel('Số Lần Gian Lận', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Sự Kiện Gian Lận Theo Tháng (Cả Năm)',
                         fontsize=13, fontweight=600, pad=15, color='white')

            # Đặt màu cho các trục và nhãn
            ax.tick_params(axis='x', colors='#cbd5e1', labelsize=10, rotation=45)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            # Grid nhạt
            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8', axis='y')
            ax.set_axisbelow(True)

            # Tự động điều chỉnh layout
            self.fraud_figure.tight_layout(pad=2.0)

            # Ẩn các đường viền
            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            # Thêm tooltip hover
            def hover(event):
                if event.inaxes == ax:
                    for bar, count in zip(bars, fraud_counts):
                        if bar.contains(event)[0]:
                            # Hiển thị tooltip
                            x = bar.get_x() + bar.get_width() / 2
                            y = bar.get_height()

                            # Xóa annotation cũ (an toàn)
                            if hasattr(self, 'fraud_annotation') and self.fraud_annotation:
                                try:
                                    self.fraud_annotation.remove()
                                except:
                                    pass
                                self.fraud_annotation = None

                            # Tạo annotation mới
                            self.fraud_annotation = ax.annotate(f'{count} sự kiện',
                                                                xy=(x, y),
                                                                xytext=(0, 10),
                                                                textcoords='offset points',
                                                                ha='center',
                                                                fontsize=10,
                                                                bbox=dict(boxstyle='round,pad=0.5',
                                                                          facecolor='yellow',
                                                                          alpha=0.8))
                            self.fraud_canvas.draw_idle()
                            return

                    # Xóa annotation nếu không hover vào bar nào
                    if hasattr(self, 'fraud_annotation') and self.fraud_annotation:
                        try:
                            self.fraud_annotation.remove()
                        except:
                            pass
                        self.fraud_annotation = None
                        self.fraud_canvas.draw_idle()

            # Kết nối sự kiện hover
            self.fraud_canvas.mpl_connect('motion_notify_event', hover)

            self.fraud_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ gian lận: {e}")

    def update_revenue_chart(self):
        """Cập nhật biểu đồ đường doanh thu và lợi nhuận theo tháng"""
        try:
            self.revenue_figure.clear()

            # Tăng kích thước figure
            self.revenue_figure.set_figwidth(7)
            self.revenue_figure.set_figheight(5)

            self.revenue_figure.patch.set_facecolor('#1e293b')
            ax = self.revenue_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            # Lấy dữ liệu theo tháng
            monthly_data = self.metrics.get('monthly_data', {})
            months = monthly_data.get('months',
                                      ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'])
            revenues = monthly_data.get('revenues', [0] * 12)
            profits = monthly_data.get('profits', [0] * 12)

            # Tạo biểu đồ đường
            x = np.arange(len(months))

            # Vẽ đường doanh thu
            line1 = ax.plot(x, revenues, marker='o', linewidth=2, markersize=8,
                            label='Doanh thu', color='#3b82f6', alpha=0.8)[0]

            # Vẽ đường lợi nhuận
            line2 = ax.plot(x, profits, marker='s', linewidth=2, markersize=8,
                            label='Lợi nhuận', color='#10b981', alpha=0.8)[0]

            ax.set_xlabel('Tháng', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Doanh thu và Lợi nhuận theo Tháng (Cả Năm)',
                         fontsize=13, fontweight=600, pad=15, color='white')
            ax.set_xticks(x)
            ax.set_xticklabels(months, fontsize=11, color='#cbd5e1')

            # Legend với màu sắc tối
            legend = ax.legend(fontsize=11, loc='upper left', facecolor='#1e293b',
                               edgecolor='#334155', framealpha=0.9)
            for text in legend.get_texts():
                text.set_color('#cbd5e1')

            # Grid và trục
            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8')
            ax.set_axisbelow(True)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            # Định dạng trục Y
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

            # Tự động điều chỉnh layout
            self.revenue_figure.tight_layout(pad=2.0)

            # Ẩn các đường viền
            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            # Thêm tooltip hover
            def hover(event):
                if event.inaxes == ax:
                    # Kiểm tra xem có hover vào line nào không
                    for line, values, label, color in zip([line1, line2], [revenues, profits],
                                                          ['Doanh thu', 'Lợi nhuận'], ['#3b82f6', '#10b981']):
                        cont, ind = line.contains(event)
                        if cont:
                            idx = ind['ind'][0]
                            x_val = x[idx]
                            y_val = values[idx]

                            # Xóa annotation cũ (an toàn)
                            if hasattr(self, 'revenue_annotation') and self.revenue_annotation:
                                try:
                                    self.revenue_annotation.remove()
                                except:
                                    pass
                                self.revenue_annotation = None

                            # Tạo annotation mới
                            self.revenue_annotation = ax.annotate(f'{label}: ${y_val:,.0f}',
                                                                  xy=(x_val, y_val),
                                                                  xytext=(10, 10),
                                                                  textcoords='offset points',
                                                                  ha='left',
                                                                  fontsize=10,
                                                                  bbox=dict(boxstyle='round,pad=0.5',
                                                                            facecolor=color,
                                                                            alpha=0.8),
                                                                  arrowprops=dict(arrowstyle='->',
                                                                                  connectionstyle='arc3',
                                                                                  color='white'))
                            self.revenue_canvas.draw_idle()
                            return

                    # Xóa annotation nếu không hover vào line nào
                    if hasattr(self, 'revenue_annotation') and self.revenue_annotation:
                        try:
                            self.revenue_annotation.remove()
                        except:
                            pass
                        self.revenue_annotation = None
                        self.revenue_canvas.draw_idle()

            # Kết nối sự kiện hover
            self.revenue_canvas.mpl_connect('motion_notify_event', hover)

            self.revenue_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ doanh thu: {e}")

    def update_completion_chart(self):
        """Cập nhật biểu đồ tròn phân bổ mức độ hoàn thành"""
        try:
            self.completion_figure.clear()

            # Tăng kích thước figure
            self.completion_figure.set_figwidth(7)
            self.completion_figure.set_figheight(5)

            self.completion_figure.patch.set_facecolor('#1e293b')
            ax = self.completion_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            # Lấy dữ liệu
            completion_data = self.metrics.get('completion_distribution', {})
            labels = completion_data.get('labels', ['Hoàn thành', 'Đang xử lý', 'Chưa bắt đầu'])
            sizes = completion_data.get('sizes', [0, 0, 0])
            colors = completion_data.get('colors', ['#10b981', '#f59e0b', '#ef4444'])

            # Chỉ vẽ biểu đồ nếu có dữ liệu
            if sum(sizes) > 0:
                # Tạo biểu đồ tròn với khoảng cách giữa các phần
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                                                  startangle=90, pctdistance=0.85,
                                                  wedgeprops=dict(width=0.3, edgecolor='w', linewidth=2),
                                                  textprops=dict(color='white', fontsize=11))

                # Tạo hiệu ứng donut chart
                centre_circle = plt.Circle((0, 0), 0.70, fc='#1e293b')
                ax.add_artist(centre_circle)

                # Cải thiện hiển thị phần trăm
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontweight('bold')

                # Cải thiện nhãn
                for text in texts:
                    text.set_fontsize(12)
                    text.set_color('#cbd5e1')
            else:
                # Hiển thị thông báo không có dữ liệu
                ax.text(0.5, 0.5, 'Không có dữ liệu', ha='center', va='center',
                        fontsize=14, color='#94a3b8', transform=ax.transAxes)

            ax.set_title('Phân Bổ Mức Độ Hoàn Thành (Cả Năm)', fontsize=13, fontweight=600, pad=15, color='white')
            ax.axis('equal')  # Đảm bảo biểu đồ tròn

            # Thêm tooltip hover
            def hover(event):
                if event.inaxes == ax and sum(sizes) > 0:
                    for i, wedge in enumerate(wedges):
                        if wedge.contains_point((event.x, event.y)):
                            # Xóa annotation cũ
                            if hasattr(self, 'completion_annotation') and self.completion_annotation:
                                try:
                                    self.completion_annotation.remove()
                                except:
                                    pass
                                self.completion_annotation = None

                            # Tính phần trăm
                            total = sum(sizes)
                            percentage = (sizes[i] / total * 100) if total > 0 else 0

                            # Tạo annotation mới
                            self.completion_annotation = ax.annotate(f'{labels[i]}\n{sizes[i]} đơn ({percentage:.1f}%)',
                                                                     xy=(0, 0),
                                                                     xytext=(20, 20),
                                                                     textcoords='offset points',
                                                                     ha='left',
                                                                     fontsize=10,
                                                                     bbox=dict(boxstyle='round,pad=0.5',
                                                                               facecolor=colors[i],
                                                                               alpha=0.8))
                            self.completion_canvas.draw_idle()
                            return

                    # Xóa annotation nếu không hover vào wedge nào
                    if hasattr(self, 'completion_annotation') and self.completion_annotation:
                        try:
                            self.completion_annotation.remove()
                        except:
                            pass
                        self.completion_annotation = None
                        self.completion_canvas.draw_idle()

            # Kết nối sự kiện hover
            self.completion_canvas.mpl_connect('motion_notify_event', hover)

            self.completion_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ tròn: {e}")

    def update_working_hours_chart(self):
        """Cập nhật biểu đồ cột thời gian làm việc theo tháng"""
        try:
            self.working_hours_figure.clear()

            # Tăng kích thước figure
            self.working_hours_figure.set_figwidth(7)
            self.working_hours_figure.set_figheight(5)

            self.working_hours_figure.patch.set_facecolor('#1e293b')
            ax = self.working_hours_figure.add_subplot(111)
            ax.set_facecolor('#1e293b')

            # Lấy dữ liệu theo tháng
            monthly_data = self.metrics.get('working_hours_monthly', {})
            months = monthly_data.get('months',
                                      ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'])
            hours = monthly_data.get('hours', [0] * 12)

            # Tạo biểu đồ cột gradient
            color_map = ['#3b82f6', '#2563eb', '#1d4ed8', '#1e40af', '#1e3a8a', '#1c366b'] * 2
            bars = ax.bar(months, hours, color=color_map, edgecolor='white',
                          linewidth=1, alpha=0.9, width=0.6)

            # Thêm giá trị trên mỗi cột
            for bar, hour in zip(bars, hours):
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                            f'{hour:.1f}h', ha='center', va='bottom',
                            fontsize=11, fontweight='bold', color='white')

            # Đường trung bình
            avg_hours = np.mean(hours) if len(hours) > 0 else 0
            ax.axhline(y=avg_hours, color='#ef4444', linestyle='--', linewidth=1.5, alpha=0.7,
                       label=f'Trung bình: {avg_hours:.1f}h/tháng')

            ax.set_ylabel('Giờ làm việc', fontsize=12, fontweight=600, color='#cbd5e1')
            ax.set_title('Thời gian làm việc theo tháng (cả năm)',
                         fontsize=13, fontweight=600, pad=15, color='white')

            # Legend
            legend = ax.legend(fontsize=11, loc='upper right', facecolor='#1e293b', edgecolor='#334155')
            for text in legend.get_texts():
                text.set_color('#cbd5e1')

            # Grid và trục
            ax.grid(True, alpha=0.1, linestyle='--', color='#94a3b8', axis='y')
            ax.set_axisbelow(True)
            ax.tick_params(axis='x', colors='#cbd5e1', labelsize=10, rotation=45)
            ax.tick_params(axis='y', colors='#cbd5e1', labelsize=11)

            # Tự động điều chỉnh layout
            self.working_hours_figure.tight_layout(pad=2.0)

            # Ẩn các đường viền
            for spine in ax.spines.values():
                spine.set_edgecolor('#334155')

            # Thêm tooltip hover
            def hover(event):
                if event.inaxes == ax:
                    for bar, hour, month in zip(bars, hours, months):
                        if bar.contains(event)[0]:
                            # Hiển thị tooltip
                            x = bar.get_x() + bar.get_width() / 2
                            y = bar.get_height()

                            # Xóa annotation cũ (an toàn)
                            if hasattr(self, 'hours_annotation') and self.hours_annotation:
                                try:
                                    self.hours_annotation.remove()
                                except:
                                    pass
                                self.hours_annotation = None

                            # Tạo annotation mới
                            self.hours_annotation = ax.annotate(f'{month}: {hour:.1f} giờ',
                                                                xy=(x, y),
                                                                xytext=(0, 10),
                                                                textcoords='offset points',
                                                                ha='center',
                                                                fontsize=10,
                                                                bbox=dict(boxstyle='round,pad=0.5',
                                                                          facecolor='yellow',
                                                                          alpha=0.8))
                            self.working_hours_canvas.draw_idle()
                            return

                    # Xóa annotation nếu không hover vào bar nào
                    if hasattr(self, 'hours_annotation') and self.hours_annotation:
                        try:
                            self.hours_annotation.remove()
                        except:
                            pass
                        self.hours_annotation = None
                        self.working_hours_canvas.draw_idle()

            # Kết nối sự kiện hover
            self.working_hours_canvas.mpl_connect('motion_notify_event', hover)

            self.working_hours_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ thời gian làm việc: {e}")

    def update_analysis_text(self):
        """Cập nhật text phân tích với dữ liệu thực tế"""
        try:
            # Hàm helper để parse metric
            def parse_metric(value):
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    # Loại bỏ dấu phẩy và ký tự không phải số
                    cleaned = value.replace(',', '').replace(' ', '').replace('%', '').replace('giờ', '')
                    try:
                        return float(cleaned)
                    except:
                        return 0.0
                return 0.0

            # Parse các giá trị từ metrics
            total_orders = parse_metric(self.metrics.get('total_orders', 0))
            completed_orders = parse_metric(self.metrics.get('completed_orders', 0))
            completion_rate = parse_metric(self.metrics.get('completion_rate', 0))
            total_work_hours = parse_metric(self.metrics.get('total_work_hours', 0))
            total_revenue = parse_metric(self.metrics.get('total_revenue', 0))
            total_profit = parse_metric(self.metrics.get('total_profit', 0))
            fraud_count = parse_metric(self.metrics.get('fraud_count', 0))
            critical_count = parse_metric(self.metrics.get('critical_count', 0))
            warning_count = parse_metric(self.metrics.get('warning_count', 0))

            # Tính pending orders
            pending_orders = max(0, total_orders - completed_orders)

            # Tính trung bình/tháng
            avg_monthly_orders = total_orders / 12 if total_orders > 0 else 0
            avg_monthly_hours = total_work_hours / 12 if total_work_hours > 0 else 0
            avg_monthly_revenue = total_revenue / 12 if total_revenue > 0 else 0
            avg_monthly_profit = total_profit / 12 if total_profit > 0 else 0

            # Đánh giá hiệu suất
            performance_level = ""
            if completion_rate >= 95:
                performance_level = "Xuất sắc"
            elif completion_rate >= 85:
                performance_level = "Tốt"
            elif completion_rate >= 70:
                performance_level = "Trung bình"
            else:
                performance_level = "Cần cải thiện"

            # Phân tích rủi ro
            risk_level = ""
            risk_analysis = ""
            if fraud_count > 10 or critical_count > 5:
                risk_level = "Cao"
                risk_analysis = "Có nhiều sự kiện gian lận và cảnh báo nghiêm trọng. Cần xem xét và xử lý ngay."
            elif fraud_count > 5 or critical_count > 3:
                risk_level = "Trung bình"
                risk_analysis = "Có một số sự kiện gian lận và cảnh báo. Cần giám sát chặt chẽ."
            else:
                risk_level = "Thấp"
                risk_analysis = "Rủi ro ở mức chấp nhận được."

            # Lấy các metrics khác
            profit_margin = parse_metric(self.metrics.get('profit_margin', 0))
            time_efficiency = parse_metric(self.metrics.get('time_efficiency', 0))
            error_rate = parse_metric(self.metrics.get('error_rate', 0))
            orders_per_hour = parse_metric(self.metrics.get('orders_per_hour', 0))

            # Tính toán các giá trị bổ sung
            revenue_per_order = total_revenue / total_orders if total_orders > 0 else 0
            profit_per_order = total_profit / total_orders if total_orders > 0 else 0

            analysis_html = f"""
            <div style="color: #cbd5e1; font-family: 'Segoe UI', Arial, sans-serif;">
                <h3 style="color: #ffffff; margin-bottom: 15px;">📊 PHÂN TÍCH HIỆU SUẤT THỰC TẾ</h3>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <!-- Cột 1: Hiệu suất -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                        <h4 style="color: #3b82f6; margin-top: 0; margin-bottom: 10px;">📈 HIỆU SUẤT LÀM VIỆC</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Tổng đơn hàng:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_orders:,.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Đã hoàn thành:</span> 
                            <span style="color: #10b981; font-weight: 600;">{completed_orders:,.0f}</span> ({completion_rate:.1f}%)
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Chờ xử lý:</span> 
                            <span style="color: #f59e0b; font-weight: 600;">{pending_orders:,.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Thời gian làm việc:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_work_hours:,.0f} giờ</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Trung bình/tháng:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{avg_monthly_orders:.0f} đơn | {avg_monthly_hours:.0f} giờ</span>
                        </p>
                    </div>

                    <!-- Cột 2: Tài chính -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
                        <h4 style="color: #10b981; margin-top: 0; margin-bottom: 10px;">💰 KẾT QUẢ TÀI CHÍNH</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Doanh thu cả năm:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{total_revenue:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Lợi nhuận cả năm:</span> 
                            <span style="color: #10b981; font-weight: 600;">{total_profit:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Trung bình/tháng:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{avg_monthly_revenue:,.0f} VND | {avg_monthly_profit:,.0f} VND</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Tỷ suất lợi nhuận:</span> 
                            <span style="color: #10b981; font-weight: 600;">{profit_margin:.1f}%</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Doanh thu/đơn hàng:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{revenue_per_order:,.0f} VND</span>
                        </p>
                    </div>
                </div>

                <!-- Rủi ro và đánh giá -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
                    <!-- Cột 3: Rủi ro -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                        <h4 style="color: #ef4444; margin-top: 0; margin-bottom: 10px;">⚠️ PHÂN TÍCH RỦI RO</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Sự kiện gian lận:</span> 
                            <span style="color: #ef4444; font-weight: 600;">{fraud_count:.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Cảnh báo nghiêm trọng:</span> 
                            <span style="color: #f59e0b; font-weight: 600;">{critical_count:.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Cảnh báo nhẹ:</span> 
                            <span style="color: #f59e0b; font-weight: 600;">{warning_count:.0f}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Mức độ rủi ro:</span> 
                            <span style="color: #ef4444; font-weight: 600;">{risk_level}</span>
                        </p>
                        <p style="color: #f59e0b; font-size: 12px; margin-top: 10px;">
                            {risk_analysis}
                        </p>
                    </div>

                    <!-- Cột 4: Đánh giá -->
                    <div style="background-color: #1e293b; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                        <h4 style="color: #8b5cf6; margin-top: 0; margin-bottom: 10px;">🎯 ĐÁNH GIÁ TỔNG QUAN</h4>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Mức độ hiệu suất:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{performance_level}</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Tỷ lệ hoàn thành:</span> 
                            <span style="color: #{'10b981' if completion_rate >= 95 else 'f59e0b' if completion_rate >= 85 else 'ef4444'}; font-weight: 600;">{completion_rate:.1f}%</span>
                            {'(Đạt mục tiêu)' if completion_rate >= 95 else '(Cần cải thiện)'}
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Hiệu suất thời gian:</span> 
                            <span style="color: #{'10b981' if time_efficiency >= 80 else 'f59e0b' if time_efficiency >= 60 else 'ef4444'}; font-weight: 600;">{time_efficiency:.1f}%</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Tỷ lệ lỗi:</span> 
                            <span style="color: #{'ef4444' if error_rate > 10 else 'f59e0b' if error_rate > 5 else '10b981'}; font-weight: 600;">{error_rate:.1f}%</span>
                        </p>
                        <p style="margin: 5px 0;">
                            <span style="color: #94a3b8;">Đơn hàng/giờ:</span> 
                            <span style="color: #ffffff; font-weight: 600;">{orders_per_hour:.2f}</span>
                        </p>
                    </div>
                </div>

                <!-- Khuyến nghị -->
                <div style="background-color: #334155; padding: 15px; border-radius: 8px; margin-top: 15px;">
                    <h4 style="color: #ffffff; margin-top: 0; margin-bottom: 10px;">💡 KHUYẾN NGHỊ HÀNH ĐỘNG</h4>
                    <ul style="line-height: 1.6; margin-bottom: 10px; padding-left: 20px;">
                        {'<li>Giảm số lượng đơn hàng chờ xử lý để cải thiện tỷ lệ hoàn thành</li>' if pending_orders > 10 else ''}
                        {'<li>Tăng cường kiểm soát chất lượng để giảm sự kiện gian lận</li>' if fraud_count > 3 else ''}
                        {'<li>Tối ưu hóa quy trình làm việc để tăng hiệu suất thời gian</li>' if time_efficiency < 70 else ''}
                        {'<li>Tập trung vào các đơn hàng có giá trị cao để tăng lợi nhuận</li>' if profit_margin < 15 else ''}
                        <li>Duy trì và phát huy các điểm mạnh hiện có</li>
                    </ul>

                    <div style="margin-top: 15px; padding: 10px; background-color: #1e293b; border-radius: 5px;">
                        <p style="margin: 0; color: #cbd5e1; font-size: 12px;">
                            <strong>📅 Ngày phân tích:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}<br>
                            <strong>📊 Dữ liệu:</strong> SAP Orders & Work Logs (cả năm)<br>
                            <strong>📈 Phương pháp:</strong> Phân tích dữ liệu thực tế & chỉ số KPI
                        </p>
                    </div>
                </div>
            </div>
            """

            self.analysis_text.setHtml(analysis_html)

        except Exception as e:
            print(f"❌ Lỗi cập nhật phân tích: {e}")
            import traceback
            traceback.print_exc()
            self.analysis_text.setHtml(f"""
                <div style='color: #ef4444; padding: 20px;'>
                    <p>Lỗi khi cập nhật phân tích: {str(e)}</p>
                </div>
            """)


def main():
    """Hàm chính để chạy dashboard"""
    app = QApplication(sys.argv)

    # Kiểm tra thư viện cần thiết
    try:
        import pandas as pd
        import matplotlib
    except ImportError as e:
        QMessageBox.critical(None, "Lỗi Thư Viện",
                             f"Thiếu thư viện cần thiết!\n\n"
                             f"Vui lòng cài đặt:\n"
                             f"pip install pandas matplotlib\n\n"
                             f"Chi tiết lỗi: {str(e)}")
        sys.exit(1)

    print("🚀 KHỞI ĐỘNG DASHBOARD HIỆU SUẤT - PHIÊN BẢN CẢI TIẾN (DỮ LIỆU CẢ NĂM)")
    print("=" * 70)

    # Tạo và hiển thị dashboard
    dashboard = PerformanceDashboard("Giang")

    # Lấy kích thước màn hình
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()

    # Đặt kích thước cửa sổ
    width = min(1400, int(screen_geometry.width() * 0.95))
    height = min(900, int(screen_geometry.height() * 0.95))

    dashboard.resize(width, height)
    dashboard.move(
        (screen_geometry.width() - width) // 2,
        (screen_geometry.height() - height) // 2
    )

    dashboard.show()

    print(f"✅ Dashboard đã hiển thị: {width}x{height}")
    print("=" * 70)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()