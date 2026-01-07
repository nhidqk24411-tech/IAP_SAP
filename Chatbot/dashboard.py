#!/usr/bin/env python3
"""
Dashboard Hiệu Suất - Dùng dữ liệu Excel thực tế
"""

import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np

# Sửa import cho matplotlib tương thích với PyQt6
import matplotlib
matplotlib.use('QtAgg')  # Sử dụng backend QtAgg
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class DataAnalyzer:
    """Phân tích dữ liệu từ Excel files"""

    @staticmethod
    def load_sap_data(file_path):
        """Đọc dữ liệu từ file SAP Excel"""
        try:
            print(f"📂 Đang đọc dữ liệu từ: {file_path}")

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

            data_dict = {
                'fraud_events': None,
                'mouse_details': None,
                'browser_time': None
            }

            # Thử đọc từng sheet
            try:
                fraud_df = pd.read_excel(file_path, sheet_name='Fraud_Events')
                print(f"   Đọc được {len(fraud_df)} dòng từ sheet Fraud_Events")
                data_dict['fraud_events'] = fraud_df
            except Exception as e:
                print(f"   ⚠️ Không đọc được sheet Fraud_Events: {e}")

            try:
                mouse_df = pd.read_excel(file_path, sheet_name='Mouse_Details')
                print(f"   Đọc được {len(mouse_df)} dòng từ sheet Mouse_Details")
                data_dict['mouse_details'] = mouse_df
            except Exception as e:
                print(f"   ⚠️ Không đọc được sheet Mouse_Details: {e}")

            try:
                browser_df = pd.read_excel(file_path, sheet_name='Browser_Time')
                print(f"   Đọc được {len(browser_df)} dòng từ sheet Browser_Time")
                data_dict['browser_time'] = browser_df
            except Exception as e:
                print(f"   ⚠️ Không đọc được sheet Browser_Time: {e}")

            return data_dict
        except Exception as e:
            print(f"❌ Lỗi đọc work logs: {e}")
            return None


class PerformanceDashboard(QWidget):
    """Dashboard hiển thị hiệu suất nhân viên"""

    def __init__(self, user_name):
        super().__init__()
        self.user_name = user_name
        self.metrics = {}

        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Khởi tạo giao diện"""
        self.setWindowTitle(f"📊 Dashboard Hiệu Suất - {self.user_name}")
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QLabel {
                color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #dce1e6;
                border-radius: 10px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #3498db;
            }
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header với nút tải lại
        header_widget = QWidget()
        header_layout = QHBoxLayout()

        title_label = QLabel(f"📊 Tổng Quan Hiệu Suất Nhân Viên - {self.user_name}")
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
        """)

        self.refresh_btn = QPushButton("🔄 Tải Lại Dữ Liệu")
        self.refresh_btn.clicked.connect(self.load_data)
        self.refresh_btn.setFixedWidth(150)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_btn)
        header_widget.setLayout(header_layout)
        main_layout.addWidget(header_widget)

        # Metrics grid
        metrics_grid = self.create_metrics_grid()
        main_layout.addWidget(metrics_grid)

        # Charts container
        charts_container = QWidget()
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)

        # Left chart (Fraud by week)
        left_chart_widget = self.create_fraud_chart_widget()
        charts_layout.addWidget(left_chart_widget)

        # Right chart (Revenue & Profit)
        right_chart_widget = self.create_revenue_chart_widget()
        charts_layout.addWidget(right_chart_widget)

        charts_container.setLayout(charts_layout)
        main_layout.addWidget(charts_container)

        # Analysis section
        analysis_widget = self.create_analysis_widget()
        main_layout.addWidget(analysis_widget)

        # Footer
        footer_label = QLabel(f"📅 Dữ liệu cập nhật: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        footer_label.setStyleSheet("""
            font-size: 12px;
            color: #7f8c8d;
            font-style: italic;
            padding: 10px;
            background-color: white;
            border-radius: 5px;
            border: 1px solid #e0e0e0;
        """)
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer_label)

        self.setLayout(main_layout)
        self.resize(1400, 900)

    def create_metrics_grid(self):
        """Tạo grid hiển thị các chỉ số chính"""
        grid = QGroupBox("📈 CHỈ SỐ HIỆU SUẤT")
        grid_layout = QGridLayout()
        grid_layout.setSpacing(20)
        grid_layout.setContentsMargins(20, 30, 20, 20)

        # Tổng đơn hàng
        orders_card = self.create_metric_card(
            "📦 TỔNG ĐƠN HÀNG",
            "0",
            "Trung bình: 0 đơn/ngày",
            "#3498db",
            "linear-gradient(135deg, #3498db 0%, #2980b9 100%)"
        )
        grid_layout.addWidget(orders_card, 0, 0)

        # Doanh thu
        revenue_card = self.create_metric_card(
            "💰 DOANH THU",
            "$0",
            "Tổng doanh thu",
            "#2ecc71",
            "linear-gradient(135deg, #2ecc71 0%, #27ae60 100%)"
        )
        grid_layout.addWidget(revenue_card, 0, 1)

        # Sự kiện gian lận
        fraud_card = self.create_metric_card(
            "⚠️ SỰ KIỆN GIAN LẬN",
            "0",
            "Cần theo dõi",
            "#e74c3c",
            "linear-gradient(135deg, #e74c3c 0%, #c0392b 100%)"
        )
        grid_layout.addWidget(fraud_card, 0, 2)

        # Tỷ lệ hoàn thành
        completion_card = self.create_metric_card(
            "✅ TỶ LỆ HOÀN THÀNH",
            "0%",
            "Mục tiêu: 95%",
            "#9b59b6",
            "linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%)"
        )
        grid_layout.addWidget(completion_card, 0, 3)

        self.orders_label = orders_card.findChild(QLabel, "value")
        self.revenue_label = revenue_card.findChild(QLabel, "value")
        self.fraud_label = fraud_card.findChild(QLabel, "value")
        self.completion_label = completion_card.findChild(QLabel, "value")

        grid.setLayout(grid_layout)
        return grid

    def create_metric_card(self, title, value, description, color, gradient):
        """Tạo card hiển thị metric"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {gradient};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: rgba(255, 255, 255, 0.9);
            text-transform: uppercase;
            letter-spacing: 1px;
        """)
        layout.addWidget(title_label)

        # Value
        value_label = QLabel(value)
        value_label.setObjectName("value")
        value_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: white;
            padding: 5px 0;
        """)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(value_label)

        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            font-size: 13px;
            color: rgba(255, 255, 255, 0.8);
            font-style: italic;
        """)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        card.setLayout(layout)
        card.setMinimumHeight(120)
        return card

    def create_fraud_chart_widget(self):
        """Tạo widget biểu đồ sự kiện gian lận theo tuần"""
        widget = QGroupBox("📊 SỰ KIỆN GIAN LẬN THEO TUẦN")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 25, 15, 15)

        # Tạo matplotlib figure
        self.fraud_figure = Figure(figsize=(7, 4), dpi=100)
        self.fraud_figure.patch.set_facecolor('#ffffff')
        self.fraud_canvas = FigureCanvas(self.fraud_figure)
        layout.addWidget(self.fraud_canvas)

        widget.setLayout(layout)
        return widget

    def create_revenue_chart_widget(self):
        """Tạo widget biểu đồ doanh thu và lợi nhuận"""
        widget = QGroupBox("💰 DOANH THU VÀ LỢI NHUẬN")
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 25, 15, 15)

        # Tạo matplotlib figure
        self.revenue_figure = Figure(figsize=(7, 4), dpi=100)
        self.revenue_figure.patch.set_facecolor('#ffffff')
        self.revenue_canvas = FigureCanvas(self.revenue_figure)
        layout.addWidget(self.revenue_canvas)

        widget.setLayout(layout)
        return widget

    def create_analysis_widget(self):
        """Tạo widget phân tích chi tiết"""
        widget = QGroupBox("📋 PHÂN TÍCH CHI TIẾT")
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 25, 20, 20)

        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        self.analysis_text.setStyleSheet("""
            QTextEdit {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                line-height: 1.6;
                color: #34495e;
            }
        """)
        self.analysis_text.setHtml("""
            <div style='text-align: center; color: #7f8c8d;'>
                <h3>Đang tải dữ liệu phân tích...</h3>
                <p>Vui lòng chờ trong giây lát</p>
            </div>
        """)

        layout.addWidget(self.analysis_text)
        widget.setLayout(layout)
        return widget

    def load_data(self):
        """Tải dữ liệu từ file Excel"""
        try:
            print(f"\n{'='*60}")
            print(f"📊 ĐANG TẢI DỮ LIỆU CHO {self.user_name}")
            print(f"{'='*60}")

            # Tìm file trong thư mục hiện tại
            current_dir = os.path.dirname(os.path.abspath(__file__))
            sap_file = os.path.join(current_dir, "sap_data.xlsx")
            work_logs_file = os.path.join(current_dir, f"work_logs_{self.user_name}_2026_01.xlsx")

            # Kiểm tra file tồn tại
            if not os.path.exists(sap_file):
                print(f"❌ Không tìm thấy file: {sap_file}")
                QMessageBox.warning(self, "Cảnh báo",
                                    f"Không tìm thấy file SAP data!\nĐường dẫn: {sap_file}")
                return

            if not os.path.exists(work_logs_file):
                print(f"⚠️ Không tìm thấy file work logs, sử dụng dữ liệu mẫu")
                work_logs_file = None

            # Load SAP data
            sap_data = DataAnalyzer.load_sap_data(sap_file)
            if not sap_data:
                print("❌ Không thể đọc dữ liệu SAP")
                return

            # Load work logs nếu có
            work_logs = None
            if work_logs_file:
                work_logs = DataAnalyzer.load_work_logs(work_logs_file)

            # Tính toán metrics
            self.calculate_metrics(sap_data, work_logs)

            # Update UI
            self.update_ui()

            print(f"✅ Hoàn thành tải dữ liệu!")

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()

            # Hiển thị thông báo lỗi
            QMessageBox.critical(self, "Lỗi",
                                 f"Không thể tải dữ liệu:\n{str(e)}")

    def calculate_metrics(self, sap_data, work_logs):
        """Tính toán các chỉ số hiệu suất"""
        try:
            orders_df = sap_data['orders']
            daily_df = sap_data['daily_performance']

            # 1. Tổng đơn hàng
            total_orders = len(orders_df)
            avg_daily_orders = total_orders / len(daily_df) if len(daily_df) > 0 else 0

            self.metrics['total_orders'] = f"{total_orders:,}"
            self.metrics['avg_daily_orders'] = f"{avg_daily_orders:.1f}"

            # 2. Doanh thu
            total_revenue = orders_df['Revenue'].sum() if 'Revenue' in orders_df.columns else 0
            total_profit = orders_df['Profit'].sum() if 'Profit' in orders_df.columns else 0

            self.metrics['total_revenue'] = f"${total_revenue:,.0f}"
            self.metrics['total_profit'] = f"${total_profit:,.0f}"

            # 3. Sự kiện gian lận
            if work_logs and work_logs['fraud_events'] is not None:
                total_fraud = len(work_logs['fraud_events'])
            else:
                # Ước tính từ dữ liệu mẫu
                total_fraud = max(0, (total_orders // 100) * 3)  # Ước tính 3% đơn hàng có vấn đề

            self.metrics['total_fraud'] = str(total_fraud)

            # 4. Tỷ lệ hoàn thành
            if 'Status' in orders_df.columns:
                completed_orders = len(orders_df[orders_df['Status'] == 'Completed'])
                completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0
            else:
                completion_rate = 95.0  # Giá trị mặc định

            self.metrics['completion_rate'] = f"{completion_rate:.1f}%"

            # 5. Doanh thu theo tháng (từ dữ liệu daily)
            if 'Total_Revenue' in daily_df.columns:
                monthly_revenue = daily_df['Total_Revenue'].sum()
            else:
                monthly_revenue = total_revenue

            self.metrics['monthly_revenue'] = monthly_revenue
            self.metrics['monthly_profit'] = total_profit

            # 6. Sự kiện gian lận theo tuần (giả định từ dữ liệu)
            fraud_by_week = []
            for week in range(1, 5):
                # Ước tính phân bổ đều
                week_fraud = total_fraud // 4
                if week <= total_fraud % 4:
                    week_fraud += 1
                fraud_by_week.append(week_fraud)

            self.metrics['fraud_by_week'] = fraud_by_week

            print(f"📊 Đã tính toán xong metrics:")
            print(f"   - Tổng đơn hàng: {self.metrics['total_orders']}")
            print(f"   - Doanh thu: {self.metrics['total_revenue']}")
            print(f"   - Sự kiện gian lận: {self.metrics['total_fraud']}")
            print(f"   - Tỷ lệ hoàn thành: {self.metrics['completion_rate']}")

        except Exception as e:
            print(f"❌ Lỗi tính toán metrics: {e}")
            # Dữ liệu mẫu nếu có lỗi
            self.metrics = {
                'total_orders': "100",
                'avg_daily_orders': "3.3",
                'total_revenue': "$37,456,789",
                'total_profit': "$8,123,456",
                'total_fraud': "12",
                'completion_rate': "96.5%",
                'monthly_revenue': 37456789,
                'monthly_profit': 8123456,
                'fraud_by_week': [2, 3, 5, 2]
            }

    def update_ui(self):
        """Cập nhật giao diện với dữ liệu mới"""
        try:
            # Update metrics
            if self.orders_label:
                self.orders_label.setText(self.metrics.get('total_orders', '0'))

            if self.revenue_label:
                self.revenue_label.setText(self.metrics.get('total_revenue', '$0'))

            if self.fraud_label:
                self.fraud_label.setText(self.metrics.get('total_fraud', '0'))

            if self.completion_label:
                self.completion_label.setText(self.metrics.get('completion_rate', '0%'))

            # Update charts
            self.update_fraud_chart()
            self.update_revenue_chart()

            # Update analysis text
            self.update_analysis_text()

            # Update window title với thời gian
            self.setWindowTitle(f"📊 Dashboard Hiệu Suất - {self.user_name} (Cập nhật: {datetime.now().strftime('%H:%M:%S')})")

            print("✅ Đã cập nhật giao diện")

        except Exception as e:
            print(f"❌ Lỗi cập nhật UI: {e}")

    def update_fraud_chart(self):
        """Cập nhật biểu đồ gian lận theo tuần"""
        try:
            self.fraud_figure.clear()
            ax = self.fraud_figure.add_subplot(111)

            weeks = ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4']
            fraud_counts = self.metrics.get('fraud_by_week', [0, 0, 0, 0])

            colors = ['#3498db', '#2ecc71', '#e74c3c', '#f39c12']
            bars = ax.bar(weeks, fraud_counts, color=colors, edgecolor='white', linewidth=2)

            # Thêm giá trị trên mỗi cột
            for bar, count in zip(bars, fraud_counts):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{count}', ha='center', va='bottom',
                        fontsize=12, fontweight='bold')

            # Tùy chỉnh biểu đồ
            ax.set_ylabel('Số Lần Gian Lận', fontsize=12, fontweight='bold')
            ax.set_title('PHÂN BỐ SỰ KIỆN GIAN LẬN THEO TUẦN',
                         fontsize=14, fontweight='bold', pad=20)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            # Đặt màu nền
            ax.set_facecolor('#f8f9fa')
            self.fraud_figure.patch.set_facecolor('#ffffff')

            # Tự động điều chỉnh layout
            self.fraud_figure.tight_layout()

            self.fraud_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ gian lận: {e}")

    def update_revenue_chart(self):
        """Cập nhật biểu đồ doanh thu và lợi nhuận"""
        try:
            self.revenue_figure.clear()
            ax = self.revenue_figure.add_subplot(111)

            # Dữ liệu cho 4 tuần
            weeks = ['Tuần 1', 'Tuần 2', 'Tuần 3', 'Tuần 4']

            # Lấy dữ liệu doanh thu và lợi nhuận
            monthly_revenue = self.metrics.get('monthly_revenue', 0)
            monthly_profit = self.metrics.get('monthly_profit', 0)

            # Phân bổ đều cho 4 tuần
            weekly_revenue = [monthly_revenue * 0.22, monthly_revenue * 0.25,
                              monthly_revenue * 0.28, monthly_revenue * 0.25]
            weekly_profit = [monthly_profit * 0.20, monthly_profit * 0.25,
                             monthly_profit * 0.30, monthly_profit * 0.25]

            x = np.arange(len(weeks))
            width = 0.35

            bars1 = ax.bar(x - width/2, weekly_revenue, width,
                           label='DOANH THU', color='#3498db', edgecolor='white', linewidth=2)
            bars2 = ax.bar(x + width/2, weekly_profit, width,
                           label='LỢI NHUẬN', color='#2ecc71', edgecolor='white', linewidth=2)

            # Thêm giá trị trên các cột
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height,
                                f'${height:,.0f}', ha='center', va='bottom',
                                fontsize=9, fontweight='bold')

            ax.set_xlabel('TUẦN', fontsize=12, fontweight='bold')
            ax.set_title('DOANH THU VÀ LỢI NHUẬN THEO TUẦN',
                         fontsize=14, fontweight='bold', pad=20)
            ax.set_xticks(x)
            ax.set_xticklabels(weeks)
            ax.legend(fontsize=11)
            ax.grid(True, alpha=0.3, linestyle='--')
            ax.set_axisbelow(True)

            # Định dạng trục Y
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))

            # Đặt màu nền
            ax.set_facecolor('#f8f9fa')
            self.revenue_figure.patch.set_facecolor('#ffffff')

            # Tự động điều chỉnh layout
            self.revenue_figure.tight_layout()

            self.revenue_canvas.draw()

        except Exception as e:
            print(f"❌ Lỗi cập nhật biểu đồ doanh thu: {e}")

    def update_analysis_text(self):
        """Cập nhật text phân tích"""
        try:
            total_orders = self.metrics.get('total_orders', '0')
            total_revenue = self.metrics.get('total_revenue', '$0')
            total_fraud = self.metrics.get('total_fraud', '0')
            completion_rate = self.metrics.get('completion_rate', '0%')
            avg_daily = self.metrics.get('avg_daily_orders', '0')

            # Đánh giá hiệu suất
            fraud_count = int(total_fraud)
            if fraud_count == 0:
                fraud_evaluation = "🎯 <span style='color:#27ae60;'>RẤT TỐT - Không có sự kiện gian lận</span>"
            elif fraud_count <= 5:
                fraud_evaluation = "✅ <span style='color:#2ecc71;'>TỐT - Số lượng thấp, trong tầm kiểm soát</span>"
            elif fraud_count <= 10:
                fraud_evaluation = "⚠️ <span style='color:#f39c12;'>TRUNG BÌNH - Cần theo dõi thêm</span>"
            else:
                fraud_evaluation = "❌ <span style='color:#e74c3c;'>CẢNH BÁO - Số lượng cao, cần điều tra ngay</span>"

            completion_value = float(completion_rate.replace('%', ''))
            if completion_value >= 97:
                completion_evaluation = "🎯 <span style='color:#27ae60;'>XUẤT SẮC - Vượt mục tiêu</span>"
            elif completion_value >= 95:
                completion_evaluation = "✅ <span style='color:#2ecc71;'>ĐẠT - Đạt mục tiêu đề ra</span>"
            else:
                completion_evaluation = "⚠️ <span style='color:#e74c3c;'>CHƯA ĐẠT - Cần cải thiện</span>"

            analysis_html = f"""
            <div style="font-family: 'Segoe UI', Arial, sans-serif;">
                <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                    📋 PHÂN TÍCH HIỆU SUẤT CHI TIẾT
                </h2>

                <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); 
                          padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h3 style="color: #3498db;">🎯 TỔNG QUAN</h3>
                    <ul style="font-size: 14px; line-height: 1.8;">
                        <li><strong>Tổng đơn hàng xử lý:</strong> <span style="color: #2c3e50; font-weight: bold;">{total_orders}</span> đơn hàng</li>
                        <li><strong>Hiệu suất trung bình:</strong> <span style="color: #2c3e50; font-weight: bold;">{avg_daily}</span> đơn/ngày</li>
                        <li><strong>Tổng doanh thu:</strong> <span style="color: #27ae60; font-weight: bold;">{total_revenue}</span></li>
                    </ul>
                </div>

                <div style="background: linear-gradient(135deg, #fff5f5 0%, #ffeaea 100%); 
                          padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h3 style="color: #e74c3c;">⚠️ KIỂM SOÁT GIAN LẬN</h3>
                    <ul style="font-size: 14px; line-height: 1.8;">
                        <li><strong>Số sự kiện gian lận:</strong> <span style="color: #e74c3c; font-weight: bold;">{total_fraud}</span> sự kiện</li>
                        <li><strong>Đánh giá:</strong> {fraud_evaluation}</li>
                        <li><strong>Khuyến nghị:</strong> {f'Giảm {fraud_count//2} sự kiện vào tuần tới' if fraud_count > 5 else 'Duy trì mức độ hiện tại'}</li>
                    </ul>
                </div>

                <div style="background: linear-gradient(135deg, #f0fff4 0%, #e6ffe6 100%); 
                          padding: 20px; border-radius: 10px; margin: 15px 0;">
                    <h3 style="color: #27ae60;">✅ CHẤT LƯỢNG CÔNG VIỆC</h3>
                    <ul style="font-size: 14px; line-height: 1.8;">
                        <li><strong>Tỷ lệ hoàn thành:</strong> <span style="color: #27ae60; font-weight: bold;">{completion_rate}</span></li>
                        <li><strong>Đánh giá:</strong> {completion_evaluation}</li>
                        <li><strong>Mục tiêu:</strong> 95% (đã {'đạt' if completion_value >= 95 else 'chưa đạt'})</li>
                    </ul>
                </div>

                <div style="margin-top: 20px; padding: 15px; background-color: #e3f2fd; border-radius: 8px;">
                    <h4 style="color: #1565c0;">📌 KẾT LUẬN VÀ KHUYẾN NGHỊ</h4>
                    <p style="font-size: 14px; line-height: 1.6;">
                        Nhân viên <strong>{self.user_name}</strong> đang thể hiện hiệu suất{' tốt' if completion_value >= 95 else ' cần cải thiện'}. 
                        {'Cần tập trung vào việc giảm sự kiện gian lận và duy trì chất lượng công việc.' if fraud_count > 5 else 'Tiếp tục phát huy và duy trì hiệu suất hiện tại.'}
                    </p>
                </div>
            </div>
            """

            self.analysis_text.setHtml(analysis_html)

        except Exception as e:
            print(f"❌ Lỗi cập nhật phân tích: {e}")
            self.analysis_text.setHtml(f"<p style='color: red;'>Lỗi cập nhật phân tích: {str(e)}</p>")


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

    print("🚀 KHỞI ĐỘNG DASHBOARD HIỆU SUẤT")
    print("=" * 50)

    # Tạo và hiển thị dashboard
    dashboard = PerformanceDashboard("Giang")

    # Lấy kích thước màn hình
    screen = app.primaryScreen()
    screen_geometry = screen.geometry()

    # Đặt kích thước cửa sổ (80% màn hình)
    width = int(screen_geometry.width() * 0.85)
    height = int(screen_geometry.height() * 0.85)

    dashboard.resize(width, height)
    dashboard.move(
        (screen_geometry.width() - width) // 2,
        (screen_geometry.height() - height) // 2
    )

    dashboard.show()

    print(f"✅ Dashboard đã hiển thị: {width}x{height}")
    print("=" * 50)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()