#!/usr/bin/env python3
"""
Main Controller - PowerSight Manager
GIỮ NGUYÊN 100% TÍNH NĂNG CŨ - CHỈ BỔ SUNG TÍNH TOÁN ĐỘNG
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Lấy đường dẫn thư mục gốc (PythonProject)
root_path = Path(__file__).parent.parent
# Thêm thư mục Chatbot vào hệ thống tìm kiếm của Python
sys.path.append(str(root_path / "MG"))

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import các UI
from MainApp.UI.UI_MG_EMPLIST import Ui_MainWindow as Ui_EmployeeList
from MainApp.UI.UI_MG_HOME import Ui_MainWindow as Ui_Home

try:
    from MG.data_processor import DataProcessor

    data_manager_available = True
except ImportError as e:
    print(f"⚠️ Không thể import data_processor: {e}")
    data_manager_available = False

# Mock class phòng trường hợp không có module
if not data_manager_available:
    class DataProcessor:
        def __init__(self, employee_name=None): self.employee_name = employee_name

        def get_all_employees(self): return []

        def load_all_data(self): return False

        def get_summary_data(self): return {'metrics': {}, 'sap': {}, 'work_log': {}}

        def get_context_data(self): return {}

try:
    from MG.manager_chatbot import ManagerChatbotGUI

    manager_chatbot_available = True
except ImportError:
    manager_chatbot_available = False

try:
    from MG.aggregate_dashboard import AggregateDashboard

    aggregate_dashboard_available = True
except ImportError:
    aggregate_dashboard_available = False

try:
    from MG.dashboard import PerformanceDashboard

    performance_dashboard_available = True
except ImportError:
    performance_dashboard_available = False


class HomeWindow(QMainWindow):
    """Cửa sổ Home - Disable nút phóng to"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ui = Ui_Home()
        self.ui.setupUi(self)
        self.setWindowTitle("Home - PowerSight Manager")

        # Disable nút phóng to
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        self.connect_buttons()
        self.update_button_states('home')

    def connect_buttons(self):
        if hasattr(self.ui, 'pushButton_17'):
            self.ui.pushButton_17.clicked.connect(lambda: self.controller.show_manager_chatbot())
        if hasattr(self.ui, 'pushButton_9'):
            self.ui.pushButton_9.clicked.connect(lambda: self.controller.show_aggregate_dashboard())
        if hasattr(self.ui, 'pushButton_8'):
            self.ui.pushButton_8.clicked.connect(lambda: self.controller.show_employee_list())
        if hasattr(self.ui, 'pushButton_6'):
            self.ui.pushButton_6.clicked.connect(lambda: self.controller.show_home())

    def update_button_states(self, active_button):
        buttons = {
            'home': getattr(self.ui, 'pushButton_6', None),
            'employee_list': getattr(self.ui, 'pushButton_8', None),
            'manager_chatbot': getattr(self.ui, 'pushButton_17', None),
            'aggregate_dashboard': getattr(self.ui, 'pushButton_9', None)
        }
        for btn_name, button in buttons.items():
            if button:
                if btn_name == active_button:
                    button.setEnabled(False)
                    button.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold;")
                else:
                    button.setEnabled(True)
                    button.setStyleSheet("")


class MainController:
    def __init__(self):
        self.windows = {'home': None, 'employee_list': None, 'manager_chatbot': None, 'aggregate_dashboard': None}
        self.active_window = None
        # Đường dẫn gốc quan trọng
        self.base_data_path = r"C:\Users\legal\PycharmProjects\PythonProject\Saved_file"
        self.data_manager = DataProcessor()
        self.show_home()

    def show_home(self):
        if self.windows['home'] is None:
            self.windows['home'] = HomeWindow(self)
        self.switch_window('home')

    def show_employee_list(self):
        if self.windows['employee_list'] is None:
            self.windows['employee_list'] = EmployeeListWindow(self)
        self.switch_window('employee_list')
        self.windows['employee_list'].refresh_all_data()

    def show_manager_chatbot(self):
        if not manager_chatbot_available:
            QMessageBox.warning(None, "Cảnh báo", "Manager Chatbot không khả dụng!")
            return
        if self.windows['manager_chatbot'] is None:
            self.windows['manager_chatbot'] = ManagerChatbotGUI(self)
        self.switch_window('manager_chatbot')

    def show_aggregate_dashboard(self):
        if not aggregate_dashboard_available:
            QMessageBox.warning(None, "Cảnh báo", "Aggregate Dashboard không khả dụng!")
            return
        if self.windows['aggregate_dashboard'] is None:
            self.windows['aggregate_dashboard'] = AggregateDashboard(self)
        self.switch_window('aggregate_dashboard')

    def show_performance_dashboard(self, employee_name, year=None, month=None):
        if not performance_dashboard_available:
            QMessageBox.warning(None, "Cảnh báo", "Performance Dashboard không khả dụng!")
            return

        try:
            # Tạo key duy nhất cho cửa sổ dashboard
            key = f'perf_{employee_name}_{year}_{month}'

            # Nếu cửa sổ chưa tồn tại hoặc đã đóng
            if key not in self.windows or self.windows[key] is None:
                # Chuyển đổi month từ "Tháng 03" thành "03" hoặc từ "3" thành "03"
                month_code = None
                if month:
                    if isinstance(month, str) and "Tháng" in month:
                        month_code = month.replace("Tháng", "").strip().zfill(2)
                    else:
                        month_code = str(month).zfill(2)

                # Tạo dashboard với bộ lọc
                dashboard = PerformanceDashboard(employee_name, year, month_code)

                # Thiết lập chế độ phóng to toàn màn hình
                dashboard.setWindowState(Qt.WindowState.WindowMaximized)

                # Kết nối sự kiện đóng cửa sổ
                def on_closed():
                    self.windows[key] = None

                dashboard.destroyed.connect(on_closed)

                self.windows[key] = dashboard
                print(f"✅ Đã tạo dashboard cho {employee_name} với bộ lọc: Năm={year}, Tháng={month_code}")

            # Hiển thị cửa sổ
            self.windows[key].show()
            self.windows[key].raise_()
            self.windows[key].activateWindow()

        except Exception as e:
            print(f"❌ Lỗi hiển thị Dashboard: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(None, "Lỗi", f"Không thể mở Dashboard:\n{str(e)}")

    def switch_window(self, window_name):
        # Ẩn cửa sổ hiện tại nếu có
        if self.active_window and self.windows[self.active_window]:
            self.windows[self.active_window].hide()

        # Hiển thị cửa sổ mới
        if window_name in self.windows and self.windows[window_name]:
            # Nếu là chatbot hoặc dashboard, phóng to toàn màn hình
            if window_name in ['manager_chatbot', 'aggregate_dashboard']:
                self.windows[window_name].setWindowState(Qt.WindowState.WindowMaximized)
            else:
                # Các cửa sổ khác giữ nguyên kích thước
                self.windows[window_name].setWindowState(Qt.WindowState.WindowNoState)

            self.windows[window_name].show()
            self.active_window = window_name

            # Cập nhật trạng thái nút
            if hasattr(self.windows[window_name], 'update_button_states'):
                self.windows[window_name].update_button_states(window_name)

    def on_child_window_closed(self, key):
        self.windows[key] = None

    def close_all_windows(self):
        for window in self.windows.values():
            if window:
                window.close()


class EmployeeListWindow(QMainWindow):
    """Employee List Window - Bỏ cột đường dẫn"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ui = Ui_EmployeeList()
        self.ui.setupUi(self)
        self.setWindowTitle("Employee List - PowerSight Manager")

        # Disable nút phóng to
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowMaximizeButtonHint)

        # Bỏ bộ lọc tuần theo yêu cầu
        if hasattr(self.ui, 'comboBox_3'):
            self.ui.comboBox_3.hide()
        if hasattr(self.ui, 'label_9'):
            self.ui.label_9.hide()  # Giả định label Tuần

        self.connect_buttons()
        self.initialize_combo_boxes()
        self.update_button_states('employee_list')

    def connect_buttons(self):
        self.ui.pushButton_17.clicked.connect(lambda: self.controller.show_manager_chatbot())
        self.ui.pushButton_9.clicked.connect(lambda: self.controller.show_aggregate_dashboard())
        self.ui.pushButton_8.setEnabled(False)
        self.ui.pushButton_6.clicked.connect(lambda: self.controller.show_home())
        if hasattr(self.ui, 'pushButton_15'):
            self.ui.pushButton_15.clicked.connect(self.search_employee)

    def initialize_combo_boxes(self):
        """Khởi tạo ComboBox Năm và Tháng với 4 năm gần nhất"""
        self.ui.comboBox.clear()
        self.ui.comboBox.addItem("Tất cả năm", None)

        # Thêm 4 năm gần nhất
        current_year = datetime.now().year
        for year in range(current_year, current_year - 4, -1):
            self.ui.comboBox.addItem(str(year), str(year))

        self.ui.comboBox_2.clear()
        self.ui.comboBox_2.addItem("Tất cả tháng", None)
        for i in range(1, 13):
            self.ui.comboBox_2.addItem(f"Tháng {i:02d}", f"{i:02d}")

        self.ui.comboBox.currentIndexChanged.connect(self.apply_filters)
        self.ui.comboBox_2.currentIndexChanged.connect(self.apply_filters)

    def refresh_all_data(self):
        self.apply_filters()

    def apply_filters(self):
        """Hàm nòng cốt: Tính toán lại dựa trên Năm/Tháng được chọn"""
        y_filter = self.ui.comboBox.currentData()
        m_filter = self.ui.comboBox_2.currentData()

        raw_employees = self.controller.data_manager.get_all_employees()
        processed_data = []

        for emp in raw_employees:
            # Gọi hàm tính toán thực tế
            calc = self.recalculate_metrics(emp['name'], y_filter, m_filter)
            if calc:
                processed_data.append({
                    'name': emp['name'],
                    'path': emp['path'],
                    'has_data': calc['has_data'],
                    'months_count': calc['months_count'],
                    'score': calc['overall_score'],
                    'all_metrics': calc  # Lưu lại để dùng cho Dialog Chi tiết
                })

        self.initialize_employee_table(processed_data)

    def recalculate_metrics(self, emp_name, year, month):
        """TÍNH TOÁN CHÍNH XÁC: Doanh thu / 12 tháng hoặc theo số tháng tìm thấy"""
        emp_folder = os.path.join(self.controller.base_data_path, emp_name)
        total_rev, total_orders, total_fraud, folders_found = 0, 0, 0, 0

        if not os.path.exists(emp_folder):
            return None

        # Xác định năm cần lấy
        years_to_check = []
        if year is None:
            # Lấy 4 năm gần nhất
            current_year = datetime.now().year
            years_to_check = [str(y) for y in range(current_year - 3, current_year + 1)]
        else:
            years_to_check = [str(year)]

        for year_str in years_to_check:
            for folder_name in os.listdir(emp_folder):
                if "_" not in folder_name:
                    continue

                f_year, f_month = folder_name.split("_")

                # Kiểm tra năm
                if f_year != year_str:
                    continue

                # Kiểm tra tháng
                if month is not None and f_month != str(month).zfill(2):
                    continue

                path = os.path.join(emp_folder, folder_name)

                # Tính SAP - Orders
                sap_p = os.path.join(path, "sap_data.xlsx")
                if os.path.exists(sap_p):
                    try:
                        df = pd.read_excel(sap_p, sheet_name="Orders")
                        if not df.empty:
                            total_orders += len(df)
                            if 'Revenue' in df.columns:
                                total_rev += df['Revenue'].sum()
                    except Exception as e:
                        print(f"⚠️ Lỗi đọc SAP {sap_p}: {e}")

                # Tính Gian lận
                wl_p = os.path.join(path, f"work_logs_{emp_name}_{folder_name}.xlsx")
                if os.path.exists(wl_p):
                    try:
                        df_wl = pd.read_excel(wl_p, sheet_name="Fraud_Events")
                        if not df_wl.empty:
                            if 'IsFraud' in df_wl.columns:
                                total_fraud += len(df_wl[df_wl['IsFraud'] == 1])
                            else:
                                # Nếu không có cột IsFraud, đếm tất cả
                                total_fraud += len(df_wl)
                    except Exception as e:
                        print(f"⚠️ Lỗi đọc Work Log {wl_p}: {e}")

                folders_found += 1

        # LOGIC TÍNH ĐIỂM TB (Công thức mẫu để bạn điều chỉnh)
        # Giả sử 1 tháng mục tiêu doanh thu là 10M
        if folders_found > 0:
            target_per_month = 10000000  # 10 Triệu
            rev_score = (total_rev / (target_per_month * folders_found)) * 100
            rev_score = min(100, rev_score)

            fraud_penalty = (total_fraud / folders_found) * 20  # Mỗi lỗi/tháng trừ 20đ
            overall = max(0, rev_score - fraud_penalty)
        else:
            overall = 0

        return {
            'has_data': folders_found > 0,
            'overall_score': overall,
            'total_revenue': total_rev,
            'total_orders': total_orders,
            'fraud_count': total_fraud,
            'months_count': folders_found
        }

    def initialize_employee_table(self, data):
        """VẼ BẢNG: BỎ CỘT ĐƯỜNG DẪN, CHỈ CÒN 5 CỘT"""
        self.ui.tableWidget.setRowCount(len(data))
        self.ui.tableWidget.setColumnCount(5)  # Bỏ cột đường dẫn
        headers = ['Tên nhân viên', 'Có dữ liệu', 'Số tháng', 'Điểm TB', 'Hành động']
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)

        for i, emp in enumerate(data):
            # 1. Tên (Flags) - Cột 0
            name_item = QTableWidgetItem(emp['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.ui.tableWidget.setItem(i, 0, name_item)

            # 2. Dữ liệu (Màu xanh/đỏ) - Cột 1
            has_d = "Có" if emp['has_data'] else "Không"
            data_item = QTableWidgetItem(has_d)
            data_item.setForeground(QColor("#10b981" if emp['has_data'] else "#ef4444"))
            data_item.setFlags(name_item.flags())
            self.ui.tableWidget.setItem(i, 1, data_item)

            # 3. Số tháng (Căn lề giữa) - Cột 2
            m_item = QTableWidgetItem(str(emp['months_count']))
            m_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tableWidget.setItem(i, 2, m_item)

            # 4. Điểm TB (Màu sắc theo dải điểm) - Cột 3
            score = emp['score']
            score_item = QTableWidgetItem(f"{score:.1f}")
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if score >= 80:
                score_item.setForeground(QColor("#10b981"))
            elif score >= 60:
                score_item.setForeground(QColor("#f59e0b"))
            else:
                score_item.setForeground(QColor("#ef4444"))
            self.ui.tableWidget.setItem(i, 3, score_item)

            # 5. HÀNH ĐỘNG (GIỮ NGUYÊN NÚT XEM VÀ CHI TIẾT) - Cột 4
            y_now = self.ui.comboBox.currentData()
            m_now = self.ui.comboBox_2.currentData()

            action_widget = QWidget()
            layout = QHBoxLayout(action_widget)
            layout.setContentsMargins(5, 2, 5, 2)
            layout.setSpacing(5)

            view_btn = QPushButton("Xem")
            view_btn.setFixedSize(50, 25)
            view_btn.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 3px; font-size: 11px;")
            # KHI NHẤN XEM: Truyền filter hiện tại vào
            view_btn.clicked.connect(lambda chk, n=emp['name'], y=y_now, m=m_now:
                                     self.controller.show_performance_dashboard(n, y, m))

            detail_btn = QPushButton("Chi tiết")
            detail_btn.setFixedSize(50, 25)
            detail_btn.setStyleSheet("background-color: #10b981; color: white; border-radius: 3px; font-size: 11px;")
            detail_btn.clicked.connect(lambda chk, e=emp: self.show_employee_details(e))

            layout.addWidget(view_btn)
            layout.addWidget(detail_btn)
            layout.addStretch()
            self.ui.tableWidget.setCellWidget(i, 4, action_widget)

        self.ui.tableWidget.resizeColumnsToContents()
        self.ui.tableWidget.setColumnWidth(4, 120)

    def search_employee(self):
        """Giữ nguyên tính năng tìm kiếm"""
        text = self.ui.lineEdit.text().lower()
        for i in range(self.ui.tableWidget.rowCount()):
            name = self.ui.tableWidget.item(i, 0).text().lower()
            self.ui.tableWidget.setRowHidden(i, text not in name)

    def show_employee_details(self, emp_info):
        """HIỂN THỊ DIALOG CHI TIẾT - BỎ ĐƯỜNG DẪN"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Chi tiết - {emp_info['name']}")
            dialog.setMinimumSize(500, 400)
            layout = QVBoxLayout(dialog)
            tab_widget = QTabWidget()

            # Tab 1: Thông tin
            info_tab = QWidget()
            info_layout = QVBoxLayout(info_tab)
            info_text = f"<h3>Thông tin nhân viên</h3><p><b>Tên:</b> {emp_info['name']}</p>"
            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            info_layout.addWidget(info_label)
            info_layout.addStretch()

            # Tab 2: Thống kê
            stats_tab = QWidget()
            stats_layout = QVBoxLayout(stats_tab)
            m = emp_info['all_metrics']
            stats_html = f"""
            <h3 style="color: #1e40af;">Thống kê kỳ được chọn</h3>
            <table border="1" cellpadding="5" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f1f5f9;"><th>Chỉ số</th><th>Giá trị</th><th>Xếp hạng</th></tr>
                <tr><td>Điểm trung bình</td><td>{m['overall_score']:.1f}</td><td>{self.get_rating_text(m['overall_score'])}</td></tr>
                <tr><td>Doanh thu tổng</td><td>{m['total_revenue']:,.0f} VND</td><td>-</td></tr>
                <tr><td>Tổng đơn hàng</td><td>{m['total_orders']}</td><td>-</td></tr>
                <tr><td>Số lỗi gian lận</td><td>{m['fraud_count']}</td><td>{'Tốt' if m['fraud_count'] == 0 else 'Cần xem xét'}</td></tr>
                <tr><td>Số tháng có dữ liệu</td><td>{m['months_count']}</td><td>-</td></tr>
            </table>
            """
            label = QLabel(stats_html)
            label.setWordWrap(True)
            stats_layout.addWidget(label)
            stats_layout.addStretch()

            tab_widget.addTab(info_tab, "Thông tin")
            tab_widget.addTab(stats_tab, "Thống kê")
            layout.addWidget(tab_widget)

            btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            btns.rejected.connect(dialog.reject)
            layout.addWidget(btns)
            dialog.exec()
        except Exception as e:
            print(f"Lỗi Details: {e}")

    def get_rating_text(self, s):
        """Giữ nguyên các mốc xếp hạng cũ"""
        if s >= 90:
            return "Xuất sắc"
        elif s >= 80:
            return "Tốt"
        elif s >= 70:
            return "Khá"
        else:
            return "Trung bình"

    def update_button_states(self, active_button):
        buttons = {
            'employee_list': self.ui.pushButton_8,
            'manager_chatbot': self.ui.pushButton_17,
            'aggregate_dashboard': self.ui.pushButton_9,
            'home': self.ui.pushButton_6
        }
        for k, btn in buttons.items():
            if btn:
                if k == active_button:
                    btn.setEnabled(False)
                    btn.setStyleSheet("background-color: #3b82f6; color: white; font-weight: bold;")
                else:
                    btn.setEnabled(True)
                    btn.setStyleSheet("")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # Đọc thông tin đăng nhập từ file tạm
    login_file = os.path.join(root_path, "temp_login.txt")
    user_name = None
    user_type = None

    if os.path.exists(login_file):
        try:
            with open(login_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                print(f"📄 Nội dung file login: {content}")
                parts = content.split(":")
                if len(parts) == 2:
                    user_type = parts[0]
                    user_name = parts[1]

                    if user_type == "manager":
                        print(f"✅ Đã đăng nhập với tư cách QUẢN LÝ: {user_name}")
                        # Xóa file tạm
                        os.remove(login_file)
                    else:
                        print(f"❌ Người dùng không phải quản lý: {user_type}")
                        QMessageBox.critical(None, "Lỗi đăng nhập",
                                             "Bạn không có quyền truy cập vào hệ thống quản lý.\nVui lòng đăng nhập với tài khoản quản lý.")
                        sys.exit(1)
                else:
                    print("❌ Thông tin đăng nhập không hợp lệ")
        except Exception as e:
            print(f"❌ Lỗi đọc file đăng nhập: {e}")

    c = MainController()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()