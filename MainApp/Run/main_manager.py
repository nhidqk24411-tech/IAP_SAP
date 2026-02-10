
#!/usr/bin/env python3
"""
Main Controller - PowerSight Manager
GIỮ NGUYÊN 100% TÍNH NĂNG CŨ - CHỈ BỔ SUNG TÍNH TOÁN ĐỘNG
"""

import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np

# SỬA: Lấy đường dẫn thư mục gốc đúng cách
current_file = Path(__file__).resolve()
# Đi từ: C:\Users\legal\PycharmProjects\PythonProject\MainApp\MG\main_manager.py
# Đến: C:\Users\legal\PycharmProjects\PythonProject
root_path = current_file.parent.parent.parent

print(f"📁 Root path: {root_path}")

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
        def __init__(self, employee_name=None):
            self.employee_name = employee_name
            self.base_path = Path(root_path) / "Saved_file"

        def get_employees_for_list(self):
            return []

        def load_all_data(self):
            return False

        def get_summary_data(self):
            return {'metrics': {}, 'sap': {}, 'work_log': {}}

        def get_context_data(self):
            return {}

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

        # Cập nhật tên hiển thị
        self.update_display_name()

    def update_display_name(self):
        """Cập nhật tên hiển thị từ ID"""
        try:
            user_id = self.controller.user_id
            display_name = self.controller.get_display_name_from_id(user_id)

            if hasattr(self.ui, 'label_7'):
                self.ui.label_7.setText(f"{display_name}!")
            if hasattr(self.ui, 'label_5'):
                self.ui.label_5.setText(f"Welcome, {display_name}")

            self.setWindowTitle(f"PowerSight Manager - {display_name}")
        except Exception as e:
            print(f"⚠️ Error updating display name: {e}")

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
    def __init__(self, user_id):
        self.user_id = user_id  # Mã quản lý (EM001, MG002, etc.)
        self.display_name = self.get_display_name_from_id(user_id)

        self.windows = {'home': None, 'employee_list': None, 'manager_chatbot': None, 'aggregate_dashboard': None}
        self.active_window = None

        # ĐƯỜNG DẪN ĐÚNG: C:\Users\legal\PycharmProjects\PythonProject\Saved_file
        self.base_data_path = os.path.join(root_path, "Saved_file")

        print(f"🎯 Đường dẫn dữ liệu: {self.base_data_path}")
        print(f"   Tồn tại: {os.path.exists(self.base_data_path)}")

        # Kiểm tra nội dung thư mục
        if os.path.exists(self.base_data_path):
            try:
                items = os.listdir(self.base_data_path)
                print(f"📁 Nội dung Saved_file: {len(items)} items")
                for item in items:
                    item_path = os.path.join(self.base_data_path, item)
                    is_dir = os.path.isdir(item_path)
                    print(f"   - {item} {'(Thư mục)' if is_dir else '(File)'}")
            except Exception as e:
                print(f"⚠️ Không thể đọc thư mục: {e}")
        else:
            print(f"⚠️ Thư mục Saved_file không tồn tại!")
            print(f"   Vui lòng tạo thư mục: {self.base_data_path}")
            print(f"   Và thêm các thư mục nhân viên (EM001, EM002, ...) vào đó")

        self.data_manager = DataProcessor()
        self.show_home()

    def get_display_name_from_id(self, employee_id):
        """Lấy tên hiển thị từ mã nhân viên"""
        try:
            excel_path = os.path.join(root_path, "employee_ids.xlsx")

            if os.path.exists(excel_path):
                df = pd.read_excel(excel_path)

                # Chuẩn hóa tên cột
                df.columns = [str(col).strip().lower() for col in df.columns]

                # Tìm cột ID
                id_column = None
                for col in df.columns:
                    if col == 'id' or 'employee' in col or 'mã' in col:
                        id_column = col
                        break

                if id_column:
                    # Tìm cột tên
                    name_column = None
                    for col in df.columns:
                        if 'full' in col or 'name' in col:
                            name_column = col
                            break

                    if name_column:
                        # Tìm hàng có mã trùng
                        for idx, row in df.iterrows():
                            current_id = str(row[id_column]).strip().upper() if not pd.isna(row[id_column]) else ""
                            if current_id == employee_id.upper():
                                name = str(row[name_column]).strip() if not pd.isna(row[name_column]) else employee_id
                                return name
        except Exception as e:
            print(f"⚠️ Error getting display name: {e}")

        return employee_id  # Trả về mã nếu không tìm thấy tên

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
            self.ui.label_9.hide()

        self.connect_buttons()
        self.initialize_combo_boxes()
        self.update_button_states('employee_list')

        # Cập nhật tiêu đề với tên quản lý
        self.setWindowTitle(f"Employee List - {self.controller.display_name}")

        # Khởi tạo danh sách nhân viên
        self.all_employees = []
        self.current_display_data = []

        self.ui.lineEdit.setFocus()

    def reload_full_list(self):
        """Hiển thị lại danh sách đầy đủ"""
        # Xóa nội dung tìm kiếm
        self.ui.lineEdit.clear()

        # Áp dụng bộ lọc hiện tại để tải lại dữ liệu
        self.apply_filters()

        # Hiển thị thông báo
        QMessageBox.information(self, "Thông báo", "Đã tải lại danh sách nhân viên đầy đủ")

    def connect_buttons(self):
        self.ui.pushButton_17.clicked.connect(lambda: self.controller.show_manager_chatbot())
        self.ui.pushButton_9.clicked.connect(lambda: self.controller.show_aggregate_dashboard())
        self.ui.pushButton_8.setEnabled(False)
        self.ui.pushButton_6.clicked.connect(lambda: self.controller.show_home())

        # Kết nối nút tìm kiếm
        if hasattr(self.ui, 'pushButton_15'):
            self.ui.pushButton_15.clicked.connect(self.search_employee)

        # Kết nối Enter trong lineEdit để tìm kiếm
        if hasattr(self.ui, 'lineEdit'):
            self.ui.lineEdit.returnPressed.connect(self.search_employee)

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
        try:
            y_filter = self.ui.comboBox.currentData()
            m_filter = self.ui.comboBox_2.currentData()

            # Lấy danh sách nhân viên từ thư mục Saved_file
            employees = self.get_employee_list_from_folders()

            if not employees:
                self.show_no_employees_message()
                return

            processed_data = []

            for emp in employees:
                # Gọi hàm tính toán thực tế
                calc = self.recalculate_metrics(emp['id'], y_filter, m_filter)
                if calc:
                    processed_data.append({
                        'id': emp['id'],
                        'name': emp['name'],
                        'path': emp.get('path', ''),
                        'has_data': calc['has_data'],
                        'months_count': calc['months_count'],
                        'score': calc['overall_score'],
                        'all_metrics': calc
                    })

            if not processed_data:
                self.show_no_data_message()
                return

            # Lưu danh sách để tìm kiếm
            self.all_employees = processed_data.copy()
            self.current_display_data = processed_data.copy()

            self.initialize_employee_table(processed_data)

        except Exception as e:
            print(f"❌ Lỗi trong apply_filters: {e}")
            import traceback
            traceback.print_exc()

    def get_employee_list_from_folders(self):
        """Lấy danh sách nhân viên từ thư mục Saved_file - CHỈ LẤY NHÂN VIÊN (EM)"""
        employees = []
        base_path = self.controller.base_data_path

        if not os.path.exists(base_path):
            return employees

        # Lấy tất cả thư mục con trong Saved_file
        try:
            items = os.listdir(base_path)

            for item in items:
                item_path = os.path.join(base_path, item)

                if os.path.isdir(item_path):
                    # CHỈ LẤY NHÂN VIÊN (bắt đầu bằng EM)
                    if item.upper().startswith('EM'):
                        # Lấy tên hiển thị từ ID
                        display_name = self.controller.get_display_name_from_id(item)

                        employees.append({
                            'id': item,
                            'name': display_name,
                            'path': item_path
                        })

        except Exception as e:
            print(f"❌ Lỗi khi đọc thư mục: {e}")

        return employees

    def recalculate_metrics(self, emp_id, year, month):
        """TÍNH TOÁN CHÍNH XÁC: Doanh thu / 12 tháng hoặc theo số tháng tìm thấy"""
        emp_folder = os.path.join(self.controller.base_data_path, emp_id)
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

        try:
            subfolders = os.listdir(emp_folder)

            for folder_name in subfolders:
                if "_" not in folder_name:
                    continue

                try:
                    f_year, f_month = folder_name.split("_")
                except:
                    continue

                # Kiểm tra năm
                if f_year not in years_to_check:
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
                wl_p = os.path.join(path, f"work_logs_{emp_id}_{folder_name}.xlsx")
                if os.path.exists(wl_p):
                    try:
                        df_wl = pd.read_excel(wl_p, sheet_name="Fraud_Events")
                        if not df_wl.empty:
                            if 'IsFraud' in df_wl.columns:
                                total_fraud += len(df_wl[df_wl['IsFraud'] == 1])
                            else:
                                total_fraud += len(df_wl)
                    except Exception as e:
                        print(f"⚠️ Lỗi đọc Work Log {wl_p}: {e}")

                folders_found += 1

        except Exception as e:
            print(f"     ❌ Lỗi khi duyệt thư mục: {e}")

        # LOGIC TÍNH ĐIỂM TB
        if folders_found > 0:
            target_per_month = 10000000  # 10 Triệu
            rev_score = (total_rev / (target_per_month * folders_found)) * 100
            rev_score = min(100, rev_score)

            fraud_penalty = (total_fraud / folders_found) * 20
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
        try:
            self.ui.tableWidget.setRowCount(len(data))
            self.ui.tableWidget.setColumnCount(5)
            headers = ['Tên nhân viên', 'Có dữ liệu', 'Số tháng', 'Điểm TB', 'Hành động']
            self.ui.tableWidget.setHorizontalHeaderLabels(headers)

            for i, emp in enumerate(data):
                # 1. Tên (Flags) - Cột 0
                name_item = QTableWidgetItem(emp['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.ui.tableWidget.setItem(i, 0, name_item)

                # Lưu ID vào item để tìm kiếm
                name_item.setData(Qt.ItemDataRole.UserRole, emp['id'])

                # Thêm tooltip hiển thị mã nhân viên
                name_item.setToolTip(f"Mã nhân viên: {emp['id']}")

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

                # 5. HÀNH ĐỘNG - Cột 4
                y_now = self.ui.comboBox.currentData()
                m_now = self.ui.comboBox_2.currentData()

                action_widget = QWidget()
                layout = QHBoxLayout(action_widget)
                layout.setContentsMargins(5, 2, 5, 2)
                layout.setSpacing(5)

                view_btn = QPushButton("Xem")
                view_btn.setFixedSize(50, 25)
                view_btn.setStyleSheet("background-color: #3b82f6; color: white; border-radius: 3px; font-size: 11px;")
                view_btn.clicked.connect(lambda chk, n=emp['id'], y=y_now, m=m_now:
                                         self.controller.show_performance_dashboard(n, y, m))

                detail_btn = QPushButton("Chi tiết")
                detail_btn.setFixedSize(50, 25)
                detail_btn.setStyleSheet(
                    "background-color: #10b981; color: white; border-radius: 3px; font-size: 11px;")
                detail_btn.clicked.connect(lambda chk, e=emp: self.show_employee_details(e))

                layout.addWidget(view_btn)
                layout.addWidget(detail_btn)
                layout.addStretch()
                self.ui.tableWidget.setCellWidget(i, 4, action_widget)

            self.ui.tableWidget.resizeColumnsToContents()
            self.ui.tableWidget.setColumnWidth(4, 120)

        except Exception as e:
            print(f"❌ Lỗi khởi tạo bảng: {e}")

    def search_employee(self):
        """Tìm kiếm nhân viên theo ID hoặc tên"""
        try:
            search_text = self.ui.lineEdit.text().strip().lower()

            if not search_text:
                # Nếu không có nội dung tìm kiếm, hiển thị tất cả
                self.initialize_employee_table(self.all_employees)
                return

            # Lọc danh sách nhân viên
            filtered_data = []
            for emp in self.all_employees:
                # Tìm trong ID và tên
                if (search_text in emp['id'].lower() or
                        search_text in emp['name'].lower()):
                    filtered_data.append(emp)

            if filtered_data:
                self.initialize_employee_table(filtered_data)
            else:
                # Hiển thị thông báo không tìm thấy
                self.show_no_search_results_message(search_text)

        except Exception as e:
            print(f"❌ Lỗi tìm kiếm: {e}")

    def show_no_search_results_message(self, search_text):
        """Hiển thị thông báo khi không tìm thấy kết quả tìm kiếm"""
        self.ui.tableWidget.setRowCount(1)
        self.ui.tableWidget.setColumnCount(1)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Kết quả tìm kiếm'])

        item = QTableWidgetItem(f"Không tìm thấy nhân viên với từ khóa: '{search_text}'")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor("#ef4444"))
        self.ui.tableWidget.setItem(0, 0, item)
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)

    def show_employee_details(self, emp_info):
        """HIỂN THỊ DIALOG CHI TIẾT"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Chi tiết - {emp_info['name']} ({emp_info['id']})")
            dialog.setMinimumSize(500, 400)
            layout = QVBoxLayout(dialog)
            tab_widget = QTabWidget()

            # Tab 1: Thông tin
            info_tab = QWidget()
            info_layout = QVBoxLayout(info_tab)
            info_text = f"""
            <h3>Thông tin nhân viên</h3>
            <p><b>Tên:</b> {emp_info['name']}</p>
            <p><b>Mã nhân viên:</b> {emp_info['id']}</p>
            <p><b>Loại:</b> {'Nhân viên' if emp_info['id'].upper().startswith('EM') else 'Khác'}</p>
            """
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

    def show_no_employees_message(self):
        """Hiển thị thông báo khi không có nhân viên"""
        self.ui.tableWidget.setRowCount(1)
        self.ui.tableWidget.setColumnCount(1)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Thông báo'])

        item = QTableWidgetItem("Không tìm thấy nhân viên trong hệ thống")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor("#ef4444"))
        self.ui.tableWidget.setItem(0, 0, item)
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)

    def show_no_data_message(self):
        """Hiển thị thông báo khi không có dữ liệu"""
        self.ui.tableWidget.setRowCount(1)
        self.ui.tableWidget.setColumnCount(1)
        self.ui.tableWidget.setHorizontalHeaderLabels(['Thông báo'])

        item = QTableWidgetItem("Không có dữ liệu cho các nhân viên hiện tại")
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item.setForeground(QColor("#f59e0b"))
        self.ui.tableWidget.setItem(0, 0, item)
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)

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

    # ĐỌC THÔNG TIN TỪ THAM SỐ DÒNG LỆNH
    user_id = None
    user_type = None

    if len(sys.argv) >= 3:
        user_id = sys.argv[1]
        user_type = sys.argv[2]

        if user_type != "manager":
            QMessageBox.critical(None, "Lỗi đăng nhập",
                                 f"Bạn không có quyền truy cập vào hệ thống quản lý.\nLoại user: {user_type}")
            sys.exit(1)
    else:
        print("⚠️ Không có tham số dòng lệnh, thử tìm user từ hệ thống...")
        QMessageBox.critical(None, "Lỗi đăng nhập",
                             "Không tìm thấy thông tin đăng nhập hợp lệ.\nVui lòng chạy App.py để đăng nhập.")
        sys.exit(1)

    # Tạo và hiển thị controller với user_id
    try:
        controller = MainController(user_id)
        print(f"🚀 Ứng dụng quản lý đã khởi động cho: {controller.display_name}")

        sys.exit(app.exec())
    except Exception as e:
        print(f"❌ Lỗi khi khởi động ứng dụng quản lý: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.critical(None, "Lỗi hệ thống",
                             f"Không thể khởi động ứng dụng quản lý:\n{str(e)}")


if __name__ == "__main__":
    main()
