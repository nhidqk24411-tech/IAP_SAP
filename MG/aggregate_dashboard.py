#!/usr/bin/env python3
"""
Aggregate Dashboard - Dashboard tổng hợp cho Manager
Hiển thị tổng doanh thu, lợi nhuận, đơn hàng (không chia theo nhân viên)
"""

import sys
import os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import DataManager
try:
    from data_manager import get_data_manager

    data_manager_available = True
except ImportError as e:
    print(f"⚠️ Không thể import data_manager: {e}")
    data_manager_available = False


class AggregateDashboard(QMainWindow):
    """Dashboard tổng hợp cho Manager - Hiển thị tổng doanh thu, lợi nhuận"""

    def __init__(self, controller=None, parent=None):
        super().__init__(parent)
        self.controller = controller  # Thêm controller

        print("📊 Khởi tạo Aggregate Dashboard...")

        # Khởi tạo DataManager
        self.data_manager = None
        if data_manager_available:
            self.data_manager = get_data_manager()
        else:
            print("⚠️ DataManager không khả dụng")

        # Dữ liệu
        self.aggregate_data = {}
        self.monthly_data = {}  # Dữ liệu theo tháng

        # Khởi tạo UI
        self.init_ui()

        # Tải dữ liệu ban đầu
        QTimer.singleShot(1000, self.load_data)

    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle("Báo Cáo Tổng Hợp - PowerSight")
        self.setGeometry(100, 100, 1400, 900)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header với nút Home
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

        # Nút Home
        home_btn = QPushButton("Về Home")
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

        title = QLabel("BÁO CÁO TỔNG HỢP - POWER SIGHT")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: 600;
            }
        """)

        refresh_btn = QPushButton("Tải Lại")
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

        # Scroll area cho nội dung
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)

        # KPI Cards (hàng đầu tiên) - 6 KPI tổng hợp
        kpi_frame = QFrame()
        kpi_frame.setStyleSheet("""
            QFrame {
                background-color: transparent;
            }
        """)

        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setSpacing(15)

        # Tạo 6 KPI cards
        self.kpi_cards = []
        kpi_configs = [
            ("TỔNG DOANH THU", "0 VND", "#8b5cf6", "Doanh thu cả team"),
            ("TỔNG LỢI NHUẬN", "0 VND", "#10b981", "Lợi nhuận cả team"),
            ("TỔNG ĐƠN HÀNG", "0", "#3b82f6", "Tổng số đơn hàng"),
            ("TỶ LỆ HOÀN THÀNH", "0%", "#06b6d4", "Tỷ lệ hoàn thành TB"),
            ("NHÂN VIÊN", "0", "#f59e0b", "Tổng số nhân viên"),
            ("GIAN LẬN", "0", "#ef4444", "Tổng sự kiện gian lận")
        ]

        for title, value, color, desc in kpi_configs:
            card = self.create_kpi_card(title, value, color, desc)
            self.kpi_cards.append(card)
            kpi_layout.addWidget(card)

        content_layout.addWidget(kpi_frame)

        # Charts section - 2 biểu đồ chính
        charts_container = QWidget()
        charts_layout = QVBoxLayout(charts_container)
        charts_layout.setSpacing(15)

        # Biểu đồ 1: Doanh thu & Lợi nhuận theo tháng
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

        revenue_title = QLabel("DOANH THU & LỢI NHUẬN THEO THÁNG")
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

        # Biểu đồ 2: Số đơn hàng & Gian lận theo tháng
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

        orders_title = QLabel("ĐƠN HÀNG & GIAN LẬN THEO THÁNG")
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

        # Thêm charts vào layout
        charts_layout.addWidget(revenue_chart_frame)
        charts_layout.addWidget(orders_chart_frame)

        content_layout.addWidget(charts_container, 1)

        # Phân tích tổng hợp
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

        analysis_title = QLabel("PHÂN TÍCH TỔNG HỢP")
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
        footer = QLabel(f"Dữ liệu được cập nhật lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
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

        # Đặt content widget vào scroll area
        scroll_area.setWidget(content_widget)

        # Thêm vào main layout
        main_layout.addWidget(header)
        main_layout.addWidget(scroll_area, 1)

    def create_kpi_card(self, title, value, color, description):
        """Tạo KPI card"""
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
        """Tải dữ liệu"""
        if not self.data_manager:
            QMessageBox.warning(self, "Lỗi", "Không thể kết nối đến DataManager")
            return

        try:
            # Lấy dữ liệu tổng hợp
            self.aggregate_data = self.data_manager.get_aggregate_data()

            if not self.aggregate_data:
                QMessageBox.warning(self, "Cảnh báo", "Không có dữ liệu để hiển thị")
                return

            # Tính toán dữ liệu theo tháng
            self.calculate_monthly_data()

            # Cập nhật KPI cards
            self.update_kpi_cards()

            # Cập nhật biểu đồ
            self.update_charts()

            # Cập nhật phân tích
            self.update_analysis()

            print("✅ Đã tải dữ liệu tổng hợp")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể tải dữ liệu:\n{str(e)}")

    def calculate_monthly_data(self):
        """Tính toán dữ liệu theo tháng từ tất cả nhân viên"""
        try:
            # Lấy tất cả nhân viên
            employees = self.data_manager.get_all_employees()

            # Khởi tạo dữ liệu theo tháng
            months = ['T1', 'T2', 'T3', 'T4', 'T5', 'T6',
                      'T7', 'T8', 'T9', 'T10', 'T11', 'T12']

            monthly_revenue = [0] * 12
            monthly_profit = [0] * 12
            monthly_orders = [0] * 12
            monthly_fraud = [0] * 12

            # Tổng hợp dữ liệu từ tất cả nhân viên
            for emp in employees:
                if not emp['has_data']:
                    continue

                # Tải dữ liệu nhân viên
                emp_data = self.data_manager.load_employee_data(emp['name'])

                # Lấy dữ liệu SAP
                sap_data = emp_data.get('sap_data', {})

                for month_key, month_data in sap_data.items():
                    # Tìm tháng từ key (format: YYYY_MM)
                    try:
                        year_str, month_str = month_key.split('_')
                        month_idx = int(month_str) - 1

                        if 0 <= month_idx < 12:
                            # Tính doanh thu và lợi nhuận
                            if 'orders' in month_data and month_data['orders'] is not None:
                                orders_df = month_data['orders']
                                if not orders_df.empty:
                                    # Tổng số đơn hàng
                                    monthly_orders[month_idx] += len(orders_df)

                                    # Tổng doanh thu
                                    if 'revenue' in orders_df.columns:
                                        monthly_revenue[month_idx] += orders_df['revenue'].sum()

                                    # Tổng lợi nhuận
                                    if 'profit' in orders_df.columns:
                                        monthly_profit[month_idx] += orders_df['profit'].sum()
                    except:
                        continue

                # Lấy dữ liệu gian lận
                work_logs = emp_data.get('work_logs', {})
                for month_key, month_data in work_logs.items():
                    try:
                        year_str, month_str = month_key.split('_')
                        month_idx = int(month_str) - 1

                        if 0 <= month_idx < 12:
                            # Tính gian lận
                            if 'fraud_events' in month_data and month_data['fraud_events'] is not None:
                                fraud_df = month_data['fraud_events']
                                if not fraud_df.empty:
                                    monthly_fraud[month_idx] += len(fraud_df)
                    except:
                        continue

            # Lưu dữ liệu theo tháng
            self.monthly_data = {
                'months': months,
                'revenue': monthly_revenue,
                'profit': monthly_profit,
                'orders': monthly_orders,
                'fraud': monthly_fraud
            }

            print(f"📈 Đã tính toán dữ liệu theo tháng")

        except Exception as e:
            print(f"❌ Lỗi tính toán dữ liệu theo tháng: {e}")

    def update_kpi_cards(self):
        """Cập nhật KPI cards"""
        data = self.aggregate_data

        # Format values
        total_revenue = f"{data.get('total_revenue', 0):,.0f} VND"
        total_profit = f"{data.get('total_profit', 0):,.0f} VND"

        # Tính tổng đơn hàng từ dữ liệu theo tháng
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
            # Tìm QLabel con thứ 2 trong layout (value_label)
            layout = card.layout()
            if layout:
                value_label = layout.itemAt(1).widget()  # Lấy widget thứ 2 (index 1)
                if isinstance(value_label, QLabel):
                    value_label.setText(value)

    def update_charts(self):
        """Cập nhật biểu đồ"""
        # Biểu đồ 1: Doanh thu & Lợi nhuận theo tháng
        self.revenue_figure.clear()
        ax1 = self.revenue_figure.add_subplot(111)

        months = self.monthly_data.get('months', [])
        revenue = self.monthly_data.get('revenue', [])
        profit = self.monthly_data.get('profit', [])

        x = np.arange(len(months))
        width = 0.35

        # Chuyển đổi sang triệu VND để dễ đọc
        revenue_mil = [r / 1000000 for r in revenue]
        profit_mil = [p / 1000000 for p in profit]

        bars1 = ax1.bar(x - width / 2, revenue_mil, width, label='Doanh thu (triệu VND)', color='#3b82f6')
        bars2 = ax1.bar(x + width / 2, profit_mil, width, label='Lợi nhuận (triệu VND)', color='#10b981')

        ax1.set_xlabel('Tháng')
        ax1.set_ylabel('Triệu VND')
        ax1.set_title('Doanh thu và Lợi nhuận theo tháng')
        ax1.set_xticks(x)
        ax1.set_xticklabels(months)
        ax1.legend()
        ax1.grid(True, alpha=0.3, linestyle='--')

        # Thêm giá trị trên các bars
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax1.text(bar.get_x() + bar.get_width() / 2., height,
                             f'{height:.1f}', ha='center', va='bottom', fontsize=8)

        self.revenue_figure.tight_layout()
        self.revenue_canvas.draw()

        # Biểu đồ 2: Đơn hàng & Gian lận theo tháng
        self.orders_figure.clear()
        ax2 = self.orders_figure.add_subplot(111)

        orders = self.monthly_data.get('orders', [])
        fraud = self.monthly_data.get('fraud', [])

        # Tạo hai trục y
        ax2_orders = ax2
        ax2_fraud = ax2.twinx()

        # Vẽ đơn hàng
        line_orders = ax2_orders.plot(x, orders, marker='o', linewidth=2,
                                      label='Số đơn hàng', color='#3b82f6')
        ax2_orders.set_xlabel('Tháng')
        ax2_orders.set_ylabel('Số đơn hàng', color='#3b82f6')
        ax2_orders.tick_params(axis='y', labelcolor='#3b82f6')
        ax2_orders.set_xticks(x)
        ax2_orders.set_xticklabels(months)

        # Vẽ gian lận
        line_fraud = ax2_fraud.plot(x, fraud, marker='s', linewidth=2,
                                    label='Sự kiện gian lận', color='#ef4444')
        ax2_fraud.set_ylabel('Sự kiện gian lận', color='#ef4444')
        ax2_fraud.tick_params(axis='y', labelcolor='#ef4444')

        # Kết hợp legend
        lines = line_orders + line_fraud
        labels = [l.get_label() for l in lines]
        ax2_orders.legend(lines, labels, loc='upper left')

        ax2_orders.grid(True, alpha=0.3, linestyle='--')
        ax2_orders.set_title('Số đơn hàng và Sự kiện gian lận theo tháng')

        self.orders_figure.tight_layout()
        self.orders_canvas.draw()

    def update_analysis(self):
        """Cập nhật phân tích tổng hợp"""
        data = self.aggregate_data
        monthly = self.monthly_data

        # Tính toán các chỉ số
        total_revenue = data.get('total_revenue', 0)
        total_profit = data.get('total_profit', 0)
        total_orders = sum(monthly.get('orders', [0] * 12))
        total_fraud = data.get('total_fraud', 0)
        total_employees = data.get('total_employees', 0)
        employees_with_data = data.get('employees_with_data', 0)
        avg_completion = data.get('average_completion_rate', 0)
        avg_score = data.get('average_overall_score', 0)

        # Tính toán các giá trị cần thiết
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

        # Sửa lỗi f-string - tính toán trước
        if employees_with_data > 0:
            orders_per_employee_per_month = total_orders / employees_with_data / 12
        else:
            orders_per_employee_per_month = 0

        if total_orders > 0:
            fraud_rate = total_fraud / total_orders * 100
        else:
            fraud_rate = 0

        # Tìm tháng tốt nhất/xấu nhất
        revenue_by_month = monthly.get('revenue', [0] * 12)
        profit_by_month = monthly.get('profit', [0] * 12)
        orders_by_month = monthly.get('orders', [0] * 12)
        fraud_by_month = monthly.get('fraud', [0] * 12)

        best_revenue_month = revenue_by_month.index(max(revenue_by_month)) if revenue_by_month else -1
        best_profit_month = profit_by_month.index(max(profit_by_month)) if profit_by_month else -1
        worst_fraud_month = fraud_by_month.index(max(fraud_by_month)) if fraud_by_month else -1

        months = ['Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
                  'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12']

        # Tính tỷ lệ nhân viên có dữ liệu
        if total_employees > 0:
            data_percentage = employees_with_data / total_employees * 100
        else:
            data_percentage = 0

        # Phân tích
        analysis_html = f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h3 style="color: #1e40af; margin-bottom: 15px;">PHÂN TÍCH TỔNG HỢP TEAM</h3>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6;">
                    <h4 style="color: #3b82f6; margin-top: 0;">HIỆU QUẢ KINH DOANH</h4>
                    <p><b>Tổng doanh thu:</b> {total_revenue:,.0f} VND</p>
                    <p><b>Tổng lợi nhuận:</b> {total_profit:,.0f} VND</p>
                    <p><b>Tỷ suất lợi nhuận:</b> {profit_margin:.1f}%</p>
                    <p><b>Tháng doanh thu cao nhất:</b> {months[best_revenue_month] if best_revenue_month >= 0 else 'N/A'}</p>
                </div>

                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #10b981;">
                    <h4 style="color: #10b981; margin-top: 0;">ĐỘI NGŨ NHÂN SỰ</h4>
                    <p><b>Tổng số nhân viên:</b> {total_employees}</p>
                    <p><b>Nhân viên có dữ liệu:</b> {employees_with_data} ({data_percentage:.0f}%)</p>
                    <p><b>Điểm TB toàn team:</b> {avg_score:.1f}/100</p>
                    <p><b>Tỷ lệ hoàn thành TB:</b> {avg_completion:.1f}%</p>
                </div>
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 20px;">
                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #8b5cf6;">
                    <h4 style="color: #8b5cf6; margin-top: 0;">HOẠT ĐỘNG ĐƠN HÀNG</h4>
                    <p><b>Tổng số đơn hàng:</b> {total_orders:,}</p>
                    <p><b>Đơn hàng TB/tháng:</b> {total_orders / 12:.0f}</p>
                    <p><b>Tháng nhiều đơn nhất:</b> {months[orders_by_month.index(max(orders_by_month))] if orders_by_month else 'N/A'}</p>
                    <p><b>Đơn hàng/NV/tháng:</b> {orders_per_employee_per_month:.1f}</p>
                </div>

                <div style="background-color: #f8fafc; padding: 15px; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <h4 style="color: #ef4444; margin-top: 0;">QUẢN LÝ RỦI RO</h4>
                    <p><b>Tổng sự kiện gian lận:</b> {total_fraud}</p>
                    <p><b>Gian lận TB/tháng:</b> {total_fraud / 12:.1f}</p>
                    <p><b>Tháng nhiều gian lận nhất:</b> {months[worst_fraud_month] if worst_fraud_month >= 0 else 'N/A'}</p>
                    <p><b>Tỷ lệ gian lận/đơn hàng:</b> {fraud_rate:.2f}%</p>
                </div>
            </div>

            <div style="background-color: #1e293b; color: white; padding: 15px; border-radius: 8px; margin-top: 10px;">
                <h4 style="color: #ffffff; margin-top: 0;">KHUYẾN NGHỊ CHIẾN LƯỢC</h4>
                <ul>
                    <li>Tập trung vào <b>{months[best_profit_month] if best_profit_month >= 0 else 'các tháng có lợi nhuận cao'}</b> để tối ưu hóa chiến lược kinh doanh</li>
                    <li>Cần cải thiện kiểm soát gian lận trong <b>{months[worst_fraud_month] if worst_fraud_month >= 0 else 'các tháng có rủi ro cao'}</b></li>
                    <li>Đề xuất training cho {total_employees - employees_with_data} nhân viên chưa có dữ liệu hiệu suất</li>
                    <li>Mục tiêu: Tăng tỷ lệ hoàn thành từ {avg_completion:.1f}% lên {(avg_completion + 5):.1f}% trong quý tới</li>
                </ul>
            </div>

            <div style="margin-top: 15px; padding: 10px; background-color: #f1f5f9; border-radius: 5px; font-size: 11px; color: #64748b;">
                <p><b>Thời gian phân tích:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><b>Phạm vi dữ liệu:</b> 12 tháng gần nhất</p>
                <p><b>Phương pháp:</b> Tổng hợp từ {employees_with_data} nhân viên có dữ liệu</p>
            </div>
        </div>
        """

        self.analysis_text.setHtml(analysis_html)


def main():
    """Hàm chính"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = AggregateDashboard()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()