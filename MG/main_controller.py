#!/usr/bin/env python3
"""
Main Controller - Điều khiển chính cho ứng dụng Manager
Kết nối tất cả các module và xử lý chuyển đổi giữa các cửa sổ
"""

import sys
import os
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

# Import các UI
from MainApp.UI.UI_MG_EMPLIST import Ui_MainWindow as Ui_EmployeeList
from MainApp.UI.UI_MG_HOME import Ui_MainWindow as Ui_Home

try:
    from data_manager import get_data_manager

    data_manager_available = True
except ImportError as e:
    print(f"⚠️ Không thể import data_manager: {e}")
    data_manager_available = False

# Tạo mock classes cho các module không có
if not data_manager_available:
    class MockDataManager:
        def get_all_employees(self): return []

        def get_aggregate_data(self): return {}

        def load_employee_data(self, *args): return {}

        def get_time_periods(self): return {'years': [], 'months': [], 'weeks': []}

        def get_filtered_data(self, **kwargs): return {}


    def get_data_manager():
        return MockDataManager()

try:
    from manager_chatbot import ManagerChatbotGUI

    manager_chatbot_available = True
except ImportError as e:
    print(f"⚠️ Không thể import manager_chatbot: {e}")
    manager_chatbot_available = False

try:
    from aggregate_dashboard import AggregateDashboard

    aggregate_dashboard_available = True
except ImportError as e:
    print(f"⚠️ Không thể import aggregate_dashboard: {e}")
    aggregate_dashboard_available = False

try:
    from Chatbot.dashboard import PerformanceDashboard

    performance_dashboard_available = True
except ImportError as e:
    print(f"⚠️ Không thể import dashboard: {e}")
    performance_dashboard_available = False


class HomeWindow(QMainWindow):
    """Cửa sổ Home với các chức năng chính"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ui = Ui_Home()
        self.ui.setupUi(self)

        # Đặt tiêu đề
        self.setWindowTitle("Home - PowerSight Manager")

        # Kết nối các nút
        self.connect_buttons()

        # Cập nhật trạng thái nút
        self.update_button_states('home')

    def connect_buttons(self):
        """Kết nối các nút với controller"""
        # Nút 17: CHATBOT
        if hasattr(self.ui, 'pushButton_17'):
            self.ui.pushButton_17.clicked.connect(
                lambda: self.controller.show_manager_chatbot()
            )

        # Nút 9: REPORTS (Aggregate Dashboard)
        if hasattr(self.ui, 'pushButton_9'):
            self.ui.pushButton_9.clicked.connect(
                lambda: self.controller.show_aggregate_dashboard()
            )

        # Nút 8: DASHBOARD (Employee List)
        if hasattr(self.ui, 'pushButton_8'):
            self.ui.pushButton_8.clicked.connect(
                lambda: self.controller.show_employee_list()
            )

        # Nút 6: HOME - đã ở Home nên disable
        if hasattr(self.ui, 'pushButton_6'):
            self.ui.pushButton_6.clicked.connect(
                lambda: self.controller.show_home()
            )

    def update_button_states(self, active_button):
        """Cập nhật trạng thái các nút"""
        # Danh sách các nút
        buttons = {
            'home': self.ui.pushButton_6 if hasattr(self.ui, 'pushButton_6') else None,
            'employee_list': self.ui.pushButton_8 if hasattr(self.ui, 'pushButton_8') else None,
            'manager_chatbot': self.ui.pushButton_17 if hasattr(self.ui, 'pushButton_17') else None,
            'aggregate_dashboard': self.ui.pushButton_9 if hasattr(self.ui, 'pushButton_9') else None
        }

        for btn_name, button in buttons.items():
            if button:
                if btn_name == active_button:
                    button.setEnabled(False)
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #3b82f6;
                            color: white;
                            font-weight: bold;
                        }
                    """)
                else:
                    button.setEnabled(True)
                    button.setStyleSheet("")  # Reset style

    def reset_button_states(self):
        """Reset trạng thái các nút về mặc định"""
        self.update_button_states('home')


class MainController:
    def __init__(self):
        self.windows = {
            'home': None,
            'employee_list': None,
            'manager_chatbot': None,
            'aggregate_dashboard': None
        }

        self.active_window = None
        self.data_manager = None

        # Khởi tạo DataManager
        if data_manager_available:
            self.data_manager = get_data_manager()
            print("✅ Đã khởi tạo DataManager")

        # Hiển thị cửa sổ đầu tiên
        self.show_home()

    def show_home(self):
        """Hiển thị cửa sổ Home"""
        if self.windows['home'] is None:
            self.windows['home'] = HomeWindow(self)

        self.switch_window('home')

    def show_employee_list(self):
        """Hiển thị cửa sổ Employee List (Dashboard)"""
        if self.windows['employee_list'] is None:
            window = EmployeeListWindow(self)
            self.windows['employee_list'] = window

        self.switch_window('employee_list')

    def show_manager_chatbot(self):
        """Hiển thị Manager Chatbot"""
        if not manager_chatbot_available:
            QMessageBox.warning(None, "Không khả dụng",
                                "Module Manager Chatbot không khả dụng.")
            return

        if self.windows['manager_chatbot'] is None:
            window = ManagerChatbotGUI(self)  # Truyền controller vào
            window.setWindowTitle("Manager Chatbot - PowerSight")
            self.windows['manager_chatbot'] = window

        self.switch_window('manager_chatbot')

    def show_aggregate_dashboard(self):
        """Hiển thị Aggregate Dashboard"""
        if not aggregate_dashboard_available:
            QMessageBox.warning(None, "Không khả dụng",
                                "Module Aggregate Dashboard không khả dụng.")
            return

        if self.windows['aggregate_dashboard'] is None:
            window = AggregateDashboard(self)  # Truyền controller vào
            self.windows['aggregate_dashboard'] = window

        self.switch_window('aggregate_dashboard')

    def show_performance_dashboard(self, employee_name):
        """Hiển thị Performance Dashboard cho một nhân viên cụ thể"""
        if not performance_dashboard_available:
            QMessageBox.warning(None, "Không khả dụng",
                                "Module Performance Dashboard không khả dụng.")
            return

        try:
            # Tạo key unique cho từng nhân viên
            key = f'performance_dashboard_{employee_name}'

            if key not in self.windows or self.windows[key] is None:
                window = PerformanceDashboard(employee_name)
                window.setWindowTitle(f"Performance Dashboard - {employee_name}")
                window.destroyed.connect(lambda: self.on_child_window_closed(key))

                self.windows[key] = window

            # Hiển thị cửa sổ
            self.windows[key].show()
            self.windows[key].raise_()
            self.windows[key].activateWindow()

            # Cập nhật trạng thái nút trong employee list
            if self.active_window == 'employee_list':
                self.windows['employee_list'].update_button_states('employee_list')

        except Exception as e:
            print(f"❌ Lỗi mở Performance Dashboard: {e}")
            QMessageBox.critical(None, "Lỗi",
                                 f"Không thể mở dashboard cho {employee_name}:\n{str(e)}")

    def switch_window(self, window_name):
        """Chuyển đổi giữa các cửa sổ"""
        # Ẩn cửa sổ hiện tại
        if self.active_window and self.windows[self.active_window]:
            self.windows[self.active_window].hide()

        # Hiển thị cửa sổ mới
        if window_name in self.windows and self.windows[window_name]:
            self.windows[window_name].show()
            self.windows[window_name].raise_()
            self.windows[window_name].activateWindow()
            self.active_window = window_name

            # Cập nhật trạng thái nút
            if window_name == 'employee_list':
                self.windows[window_name].update_button_states('employee_list')
            elif window_name == 'home':
                self.windows[window_name].update_button_states('home')

    def on_child_window_closed(self, window_key):
        """Xử lý khi cửa sổ con đóng"""
        if window_key in self.windows:
            self.windows[window_key] = None

        # Reset trạng thái nút trong employee list
        if self.active_window == 'employee_list':
            self.windows['employee_list'].reset_button_states()

    def close_all_windows(self):
        """Đóng tất cả cửa sổ"""
        for window_name, window in self.windows.items():
            if window:
                try:
                    window.close()
                except:
                    pass


class EmployeeListWindow(QMainWindow):
    """Cửa sổ Employee List với các chức năng quản lý"""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.ui = Ui_EmployeeList()
        self.ui.setupUi(self)

        # Đặt tiêu đề
        self.setWindowTitle("Employee List - PowerSight Manager")

        # Kết nối các nút
        self.connect_buttons()

        # Khởi tạo bảng nhân viên
        self.initialize_employee_table()

        # Khởi tạo combo boxes
        self.initialize_combo_boxes()

        # Cập nhật trạng thái nút
        self.update_button_states('employee_list')

    def connect_buttons(self):
        """Kết nối các nút với controller"""
        # Nút 17: CHATBOT
        self.ui.pushButton_17.clicked.connect(
            lambda: self.controller.show_manager_chatbot()
        )

        # Nút 9: REPORTS (Aggregate Dashboard)
        self.ui.pushButton_9.clicked.connect(
            lambda: self.controller.show_aggregate_dashboard()
        )

        # Nút 8: DASHBOARD (Employee List) - đang ở đây nên disable
        self.ui.pushButton_8.setEnabled(False)

        # Nút 6: HOME
        self.ui.pushButton_6.clicked.connect(
            lambda: self.controller.show_home()
        )

        # Nút tìm kiếm
        if hasattr(self.ui, 'pushButton_15'):
            self.ui.pushButton_15.clicked.connect(self.search_employee)

    def initialize_employee_table(self):
        """Khởi tạo bảng nhân viên với dữ liệu từ DataManager"""
        try:
            if not self.controller.data_manager:
                QMessageBox.warning(self, "Cảnh báo",
                                    "DataManager không khả dụng. Không thể tải danh sách nhân viên.")
                return

            employees = self.controller.data_manager.get_all_employees()

            if not employees:
                self.ui.tableWidget.setRowCount(0)
                QMessageBox.information(self, "Thông tin",
                                        "Không tìm thấy nhân viên nào.")
                return

            # Đặt số hàng và cột
            self.ui.tableWidget.setRowCount(len(employees))
            self.ui.tableWidget.setColumnCount(6)  # Tăng lên 6 cột

            # Đặt tiêu đề cột
            headers = ['Tên nhân viên', 'Đường dẫn', 'Có dữ liệu', 'Số tháng', 'Điểm TB', 'Hành động']
            self.ui.tableWidget.setHorizontalHeaderLabels(headers)

            # Điền dữliệu
            for i, emp in enumerate(employees):
                # Tên nhân viên
                name_item = QTableWidgetItem(emp['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Đường dẫn (rút gọn)
                path = emp['data_path']
                short_path = path if len(path) <= 40 else "..." + path[-40:]
                path_item = QTableWidgetItem(short_path)
                path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                path_item.setToolTip(path)

                # Có dữ liệu
                if emp['has_data']:
                    data_item = QTableWidgetItem("Có")
                    data_item.setForeground(QColor("#10b981"))
                else:
                    data_item = QTableWidgetItem("Không")
                    data_item.setForeground(QColor("#ef4444"))
                data_item.setFlags(data_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                # Số tháng
                month_count = len(emp['data_files']) if emp['data_files'] else 0
                month_item = QTableWidgetItem(str(month_count))
                month_item.setFlags(month_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                month_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Điểm trung bình (tính từ dữ liệu nếu có)
                avg_score = self.calculate_employee_score(emp)
                score_item = QTableWidgetItem(f"{avg_score:.1f}")
                score_item.setFlags(score_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                # Màu sắc dựa trên điểm
                if avg_score >= 80:
                    score_item.setForeground(QColor("#10b981"))
                elif avg_score >= 60:
                    score_item.setForeground(QColor("#f59e0b"))
                else:
                    score_item.setForeground(QColor("#ef4444"))

                # Nút hành động
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(5, 2, 5, 2)
                action_layout.setSpacing(5)

                # Nút xem dashboard
                view_btn = QPushButton("Xem")
                view_btn.setFixedSize(50, 25)
                view_btn.setToolTip(f"Xem dashboard của {emp['name']}")
                view_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3b82f6;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #2563eb;
                    }
                    QPushButton:disabled {
                        background-color: #cbd5e1;
                        color: #64748b;
                    }
                """)

                # Chỉ enable nếu có dữ liệu
                view_btn.setEnabled(emp['has_data'])
                view_btn.clicked.connect(
                    lambda checked, name=emp['name']: self.controller.show_performance_dashboard(name)
                )

                # Nút xem chi tiết
                detail_btn = QPushButton("Chi tiết")
                detail_btn.setFixedSize(50, 25)
                detail_btn.setToolTip(f"Xem chi tiết {emp['name']}")
                detail_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #10b981;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 11px;
                    }
                    QPushButton:hover {
                        background-color: #059669;
                    }
                """)
                detail_btn.clicked.connect(
                    lambda checked, emp=emp: self.show_employee_details(emp)
                )

                action_layout.addWidget(view_btn)
                action_layout.addWidget(detail_btn)
                action_layout.addStretch()

                # Thêm vào table
                self.ui.tableWidget.setItem(i, 0, name_item)
                self.ui.tableWidget.setItem(i, 1, path_item)
                self.ui.tableWidget.setItem(i, 2, data_item)
                self.ui.tableWidget.setItem(i, 3, month_item)
                self.ui.tableWidget.setItem(i, 4, score_item)
                self.ui.tableWidget.setCellWidget(i, 5, action_widget)

            # Tự động điều chỉnh cột
            self.ui.tableWidget.resizeColumnsToContents()

            # Đặt chiều rộng cột cố định cho cột hành động
            self.ui.tableWidget.setColumnWidth(5, 120)

        except Exception as e:
            print(f"❌ Lỗi khởi tạo bảng nhân viên: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách nhân viên:\n{str(e)}")

    def calculate_employee_score(self, employee_info):
        """Tính điểm trung bình cho nhân viên"""
        if not employee_info['has_data']:
            return 0.0

        try:
            # Tải dữ liệu nhân viên
            emp_data = self.controller.data_manager.load_employee_data(employee_info['name'])

            if not emp_data.get('metrics'):
                return 0.0

            # Lấy điểm từ tháng mới nhất
            latest_month = list(emp_data['metrics'].keys())[0] if emp_data['metrics'] else None
            if latest_month:
                return emp_data['metrics'][latest_month].get('overall_score', 0.0)

            return 0.0

        except Exception:
            return 0.0

    def initialize_combo_boxes(self):
        """Khởi tạo combo boxes với dữ liệu thời gian"""
        try:
            if not self.controller.data_manager:
                return

            periods = self.controller.data_manager.get_time_periods()

            # ComboBox 1: Năm
            self.ui.comboBox.clear()
            self.ui.comboBox.addItem("Tất cả năm", None)
            for year in periods['years']:
                self.ui.comboBox.addItem(year, year)

            # ComboBox 2: Tháng
            self.ui.comboBox_2.clear()
            self.ui.comboBox_2.addItem("Tất cả tháng", None)
            for i in range(1, 13):
                self.ui.comboBox_2.addItem(f"Tháng {i}", i)

            # ComboBox 3: Tuần
            self.ui.comboBox_3.clear()
            self.ui.comboBox_3.addItem("Tất cả tuần", None)
            for week in periods['weeks']:
                self.ui.comboBox_3.addItem(week['display'], week['week'])

            # Kết nối sự kiện
            self.ui.comboBox.currentIndexChanged.connect(self.apply_filters)
            self.ui.comboBox_2.currentIndexChanged.connect(self.apply_filters)
            self.ui.comboBox_3.currentIndexChanged.connect(self.apply_filters)

        except Exception as e:
            print(f"❌ Lỗi khởi tạo combo boxes: {e}")

    def apply_filters(self):
        """Áp dụng bộ lọc cho bảng nhân viên"""
        try:
            if not self.controller.data_manager:
                return

            # Lấy giá trị từ combo boxes
            year = self.ui.comboBox.currentData()
            month = self.ui.comboBox_2.currentData()
            week = self.ui.comboBox_3.currentData()

            # Lấy tất cả nhân viên
            all_employees = self.controller.data_manager.get_all_employees()

            if not all_employees:
                return

            # Lọc nhân viên có dữ liệu trong khoảng thời gian đã chọn
            filtered_employees = []

            for emp in all_employees:
                if not emp['has_data']:
                    # Nếu không có filter, vẫn hiển thị nhân viên không có dữ liệu
                    if year is None and month is None:
                        filtered_employees.append(emp)
                    continue

                # Nếu không chọn filter, hiển thị tất cả
                if year is None and month is None:
                    filtered_employees.append(emp)
                    continue

                # Kiểm tra xem nhân viên có dữ liệu trong tháng/năm đã chọn không
                data_files = emp.get('data_files', {})

                has_matching_data = False

                for data_month in data_files.keys():
                    try:
                        data_year, data_month_num = data_month.split('_') if '_' in data_month else ('', '')

                        # Kiểm tra năm
                        year_match = (year is None) or (data_year == str(year))

                        # Kiểm tra tháng
                        month_match = (month is None) or (data_month_num == str(month).zfill(2))

                        if year_match and month_match:
                            has_matching_data = True
                            break
                    except:
                        continue

                if has_matching_data:
                    filtered_employees.append(emp)

            # Cập nhật bảng với dữ liệu đã lọc
            self.update_table_with_filtered_data(filtered_employees)

            print(
                f"📊 Đã áp dụng filter: Năm={year}, Tháng={month}, Tuần={week}. Tìm thấy {len(filtered_employees)} nhân viên")

        except Exception as e:
            print(f"❌ Lỗi áp dụng filter: {e}")
            import traceback
            traceback.print_exc()

    def update_table_with_filtered_data(self, filtered_employees):
        """Cập nhật bảng với dữ liệu đã lọc"""
        # Đặt số hàng
        self.ui.tableWidget.setRowCount(len(filtered_employees))

        # Điền dữ liệu
        for i, emp in enumerate(filtered_employees):
            # Tên nhân viên
            name_item = QTableWidgetItem(emp['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Đường dẫn (rút gọn)
            path = emp['data_path']
            short_path = path if len(path) <= 40 else "..." + path[-40:]
            path_item = QTableWidgetItem(short_path)
            path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            path_item.setToolTip(path)

            # Có dữ liệu
            if emp['has_data']:
                data_item = QTableWidgetItem("Có")
                data_item.setForeground(QColor("#10b981"))
            else:
                data_item = QTableWidgetItem("Không")
                data_item.setForeground(QColor("#ef4444"))
            data_item.setFlags(data_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            # Số tháng
            month_count = len(emp['data_files']) if emp['data_files'] else 0
            month_item = QTableWidgetItem(str(month_count))
            month_item.setFlags(month_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            month_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Điểm trung bình (tính từ dữ liệu nếu có)
            avg_score = self.calculate_employee_score(emp)
            score_item = QTableWidgetItem(f"{avg_score:.1f}")
            score_item.setFlags(score_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            score_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Màu sắc dựa trên điểm
            if avg_score >= 80:
                score_item.setForeground(QColor("#10b981"))
            elif avg_score >= 60:
                score_item.setForeground(QColor("#f59e0b"))
            else:
                score_item.setForeground(QColor("#ef4444"))

            # Nút hành động
            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(5, 2, 5, 2)
            action_layout.setSpacing(5)

            # Nút xem dashboard
            view_btn = QPushButton("Xem")
            view_btn.setFixedSize(50, 25)
            view_btn.setToolTip(f"Xem dashboard của {emp['name']}")
            view_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
                QPushButton:disabled {
                    background-color: #cbd5e1;
                    color: #64748b;
                }
            """)

            # Chỉ enable nếu có dữ liệu
            view_btn.setEnabled(emp['has_data'])
            view_btn.clicked.connect(
                lambda checked, name=emp['name']: self.controller.show_performance_dashboard(name)
            )

            # Nút xem chi tiết
            detail_btn = QPushButton("Chi tiết")
            detail_btn.setFixedSize(50, 25)
            detail_btn.setToolTip(f"Xem chi tiết {emp['name']}")
            detail_btn.setStyleSheet("""
                QPushButton {
                    background-color: #10b981;
                    color: white;
                    border: none;
                    border-radius: 3px;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #059669;
                }
            """)
            detail_btn.clicked.connect(
                lambda checked, emp=emp: self.show_employee_details(emp)
            )

            action_layout.addWidget(view_btn)
            action_layout.addWidget(detail_btn)
            action_layout.addStretch()

            # Thêm vào table
            self.ui.tableWidget.setItem(i, 0, name_item)
            self.ui.tableWidget.setItem(i, 1, path_item)
            self.ui.tableWidget.setItem(i, 2, data_item)
            self.ui.tableWidget.setItem(i, 3, month_item)
            self.ui.tableWidget.setItem(i, 4, score_item)
            self.ui.tableWidget.setCellWidget(i, 5, action_widget)

    def search_employee(self):
        """Tìm kiếm nhân viên theo ID hoặc tên"""
        search_text = self.ui.lineEdit.text().strip()

        if not search_text:
            # Hiển thị tất cả nếu không có search text
            for row in range(self.ui.tableWidget.rowCount()):
                self.ui.tableWidget.setRowHidden(row, False)
            return

        search_text_lower = search_text.lower()

        for row in range(self.ui.tableWidget.rowCount()):
            # Lấy tên nhân viên từ cột đầu tiên
            name_item = self.ui.tableWidget.item(row, 0)
            if name_item:
                name = name_item.text().lower()
                # Ẩn/hiện hàng dựa trên kết quả tìm kiếm
                self.ui.tableWidget.setRowHidden(row, search_text_lower not in name)

    def show_employee_details(self, employee_info):
        """Hiển thị chi tiết nhân viên"""
        try:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Chi tiết nhân viên - {employee_info['name']}")
            dialog.setMinimumSize(500, 400)

            layout = QVBoxLayout(dialog)

            # Tạo tab widget
            tab_widget = QTabWidget()

            # Tab 1: Thông tin chung
            info_tab = QWidget()
            info_layout = QVBoxLayout(info_tab)

            info_text = f"""
            <h3>Thông tin nhân viên</h3>
            <p><b>Tên:</b> {employee_info['name']}</p>
            <p><b>Đường dẫn dữ liệu:</b> {employee_info['data_path']}</p>
            <p><b>Có dữ liệu:</b> {'Có' if employee_info['has_data'] else 'Không'}</p>
            """

            if employee_info['data_files']:
                info_text += "<h4>File dữ liệu theo tháng:</h4><ul>"
                for month, files in employee_info['data_files'].items():
                    info_text += f"<li><b>{month}:</b> {len(files)} file</li>"
                info_text += "</ul>"

            info_label = QLabel(info_text)
            info_label.setWordWrap(True)
            info_layout.addWidget(info_label)

            # Tab 2: Thống kê hiệu suất
            stats_tab = QWidget()
            stats_layout = QVBoxLayout(stats_tab)

            if employee_info['has_data']:
                # Tải dữ liệu để hiển thị thống kê
                emp_data = self.controller.data_manager.load_employee_data(employee_info['name'])

                if emp_data.get('metrics'):
                    latest_month = list(emp_data['metrics'].keys())[0]
                    metrics = emp_data['metrics'][latest_month]

                    stats_html = f"""
                    <h3>Thống kê hiệu suất (Tháng {latest_month})</h3>
                    <table border="1" cellpadding="5" style="border-collapse: collapse;">
                        <tr>
                            <th>Chỉ số</th>
                            <th>Giá trị</th>
                            <th>Đánh giá</th>
                        </tr>
                        <tr>
                            <td>Điểm tổng thể</td>
                            <td>{metrics.get('overall_score', 0):.1f}</td>
                            <td>{self.get_score_rating(metrics.get('overall_score', 0))}</td>
                        </tr>
                        <tr>
                            <td>Hiệu quả</td>
                            <td>{metrics.get('efficiency', 0):.1f}</td>
                            <td>{self.get_score_rating(metrics.get('efficiency', 0))}</td>
                        </tr>
                        <tr>
                            <td>Năng suất</td>
                            <td>{metrics.get('productivity', 0):.1f}</td>
                            <td>{self.get_score_rating(metrics.get('productivity', 0))}</td>
                        </tr>
                        <tr>
                            <td>Chất lượng</td>
                            <td>{metrics.get('quality', 0):.1f}</td>
                            <td>{self.get_score_rating(metrics.get('quality', 0))}</td>
                        </tr>
                        <tr>
                            <td>Tuân thủ</td>
                            <td>{metrics.get('compliance', 0):.1f}</td>
                            <td>{self.get_score_rating(metrics.get('compliance', 0))}</td>
                        </tr>
                        <tr>
                            <td>Doanh thu</td>
                            <td>{metrics.get('revenue_generated', 0):,.0f} VND</td>
                            <td>-</td>
                        </tr>
                        <tr>
                            <td>Sự kiện gian lận</td>
                            <td>{metrics.get('fraud_count', 0)}</td>
                            <td>{'Tốt' if metrics.get('fraud_count', 0) == 0 else 'Cần xem xét'}</td>
                        </tr>
                    </table>
                    """
                else:
                    stats_html = "<p>Không có dữ liệu thống kê.</p>"
            else:
                stats_html = "<p>Nhân viên chưa có dữ liệu để phân tích.</p>"

            stats_label = QLabel(stats_html)
            stats_label.setWordWrap(True)
            stats_layout.addWidget(stats_label)

            # Thêm các tab
            tab_widget.addTab(info_tab, "Thông tin")
            tab_widget.addTab(stats_tab, "Thống kê")

            layout.addWidget(tab_widget)

            # Nút đóng
            button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            button_box.rejected.connect(dialog.reject)
            layout.addWidget(button_box)

            dialog.exec()

        except Exception as e:
            print(f"❌ Lỗi hiển thị chi tiết: {e}")
            QMessageBox.critical(self, "Lỗi",
                                 f"Không thể hiển thị chi tiết nhân viên:\n{str(e)}")

    def get_score_rating(self, score):
        """Đánh giá dựa trên điểm số"""
        if score >= 90:
            return "Xuất sắc"
        elif score >= 80:
            return "Tốt"
        elif score >= 70:
            return "Khá"
        elif score >= 60:
            return "Trung bình"
        else:
            return "Cần cải thiện"

    def update_button_states(self, active_button):
        """Cập nhật trạng thái các nút"""
        # Danh sách các nút
        buttons = {
            'employee_list': self.ui.pushButton_8,  # Dashboard
            'manager_chatbot': self.ui.pushButton_17,  # Chatbot
            'aggregate_dashboard': self.ui.pushButton_9,  # Reports
            'home': self.ui.pushButton_6  # Home
        }

        for btn_name, button in buttons.items():
            if button:
                if btn_name == active_button:
                    button.setEnabled(False)
                    button.setStyleSheet("""
                        QPushButton {
                            background-color: #3b82f6;
                            color: white;
                            font-weight: bold;
                        }
                    """)
                else:
                    button.setEnabled(True)
                    button.setStyleSheet("")  # Reset style

    def reset_button_states(self):
        """Reset trạng thái các nút về mặc định"""
        self.update_button_states('employee_list')


def main():
    """Hàm chính khởi chạy ứng dụng"""
    app = QApplication(sys.argv)
    app.setApplicationName("PowerSight Manager")
    app.setStyle("Fusion")

    # Áp dụng style tổng thể
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f8fafc;
        }
        QStatusBar {
            background-color: #1e293b;
            color: white;
        }
    """)

    print("🚀 KHỞI ĐỘNG POWER SIGHT MANAGER...")
    print("=" * 50)

    # Kiểm tra các module cần thiết
    if not data_manager_available:
        print("⚠️ CẢNH BÁO: DataManager không khả dụng")
        print("   Ứng dụng có thể không hoạt động đầy đủ chức năng")

    if not manager_chatbot_available:
        print("⚠️ CẢNH BÁO: Manager Chatbot không khả dụng")

    if not aggregate_dashboard_available:
        print("⚠️ CẢNH BÁO: Aggregate Dashboard không khả dụng")

    if not performance_dashboard_available:
        print("⚠️ CẢNH BÁO: Performance Dashboard không khả dụng")

    print("=" * 50)

    try:
        # Khởi tạo controller chính
        controller = MainController()

        # Hiển thị splash screen (tuỳ chọn)
        splash = QSplashScreen()
        splash.setPixmap(QPixmap(300, 200))  # Có thể thêm ảnh splash
        splash.show()
        splash.showMessage("Đang khởi động PowerSight Manager...",
                           Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
                           Qt.GlobalColor.white)
        app.processEvents()

        # Đóng splash sau 2 giây
        QTimer.singleShot(2000, splash.close)

        # Chạy ứng dụng
        exit_code = app.exec()

        # Đóng tất cả cửa sổ trước khi thoát
        controller.close_all_windows()

        print("Đã thoát ứng dụng")
        sys.exit(exit_code)

    except Exception as e:
        print(f"❌ LỖI KHỞI ĐỘNG: {e}")
        import traceback
        traceback.print_exc()

        QMessageBox.critical(None, "Lỗi khởi động",
                             f"Không thể khởi động ứng dụng:\n\n{str(e)}\n\n"
                             f"Vui lòng kiểm tra cài đặt và thử lại.")
        sys.exit(1)


if __name__ == "__main__":
    main()