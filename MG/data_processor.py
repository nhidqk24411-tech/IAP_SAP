import os
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import numpy as np
import warnings
import traceback

warnings.filterwarnings('ignore')

try:
    from Chatbot.config import Config

    config_available = True
except ImportError as e:
    print(f"⚠️ Cannot import config: {e}")


    class Config:
        BASE_DATA_PATH = r"C:\Users\legal\PycharmProjects\PythonProject\Saved_file"
        DEFAULT_EMPLOYEE_NAME = "EM001"


    config_available = False


class DataProcessor:
    """Process multi-employee data for AI analysis and Dashboard"""

    def __init__(self, employee_name=None):
        self.employee_name = employee_name
        self.base_path = Path(Config.BASE_DATA_PATH)
        self.work_log_data = None
        self.sap_data = None
        self.metrics = None
        self.year_data = None
        print(f"🚀 Initializing DataProcessor for: {self.employee_name or 'All employees'}")

    def get_employees_for_list(self):
        """Get all employees for list display"""
        try:
            # Get employee contact info (only EM employees)
            employees = self.get_employee_contact_info()

            if not employees:
                print("⚠️ No employees found in contact info")
                return []

            print(f"📋 Found {len(employees)} employees from contact info")

            # For each employee, try to get their data folder
            employees_with_data = []

            for emp in employees:
                emp_id = emp.get('id', '')
                if not emp_id:
                    continue

                # Check if employee has data folder
                emp_path = self.base_path / emp_id
                has_data = False

                if emp_path.exists():
                    # Check if there are month folders (e.g., 2025_01, 2025_02)
                    month_folders = [d for d in emp_path.iterdir() if d.is_dir() and '_' in d.name]
                    has_data = len(month_folders) > 0

                employees_with_data.append({
                    'id': emp_id,
                    'name': emp.get('name', emp_id),
                    'email': emp.get('email', ''),
                    'sap': emp.get('sap', ''),
                    'client': emp.get('client', ''),
                    'has_data': has_data,
                    'path': str(emp_path)
                })

            print(f"✅ Found {len(employees_with_data)} employees with info")
            return employees_with_data

        except Exception as e:
            print(f"❌ Error getting employees for list: {e}")
            import traceback
            traceback.print_exc()
            return []

    # ========== LOAD DATA BY PERIOD ==========
    # Thêm các hàm sau vào class DataProcessor

    def get_employee_detailed_performance(self, employee_id, year=None, month=None):
        """Lấy thông tin chi tiết hiệu suất của nhân viên"""
        try:
            if not employee_id:
                return None

            # Tạo processor cho nhân viên cụ thể
            from MG.data_processor import DataProcessor
            emp_processor = DataProcessor(employee_id)

            # Load dữ liệu theo period
            success = emp_processor.load_period_data(year, month)

            if not success:
                print(f"⚠️ Không thể load dữ liệu cho {employee_id}")
                return None

            # Lấy dữ liệu dashboard
            emp_data = emp_processor.get_dashboard_data()

            if not emp_data:
                return None

            # Lấy các sheet dữ liệu
            sap_sheets = emp_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = emp_data.get('work_log', {}).get('sheets', {})

            # Lấy dữ liệu Orders
            orders_df = sap_sheets.get('Orders', pd.DataFrame())

            # Lấy dữ liệu Fraud Events
            fraud_df = work_log_sheets.get('Fraud_Events', pd.DataFrame())

            # Lấy dữ liệu Daily Performance
            daily_df = sap_sheets.get('Daily_Performance', pd.DataFrame())

            # Lấy dữ liệu Browser Sessions
            browser_df = work_log_sheets.get('Browser_Sessions', pd.DataFrame())
            if browser_df.empty:
                browser_df = work_log_sheets.get('Browser_Time', pd.DataFrame())

            # Tính toán các chỉ số chi tiết
            metrics = self.calculate_single_employee_metrics(emp_data, employee_id, year, month)

            # Phân tích đơn hàng
            orders_analysis = self._analyze_orders(orders_df)

            # Phân tích gian lận
            fraud_analysis = self._analyze_fraud(fraud_df)

            # Phân tích thời gian làm việc
            time_analysis = self._analyze_working_time(browser_df, daily_df)

            return {
                'employee_id': employee_id,
                'year': year,
                'month': month,
                'metrics': metrics,
                'orders_analysis': orders_analysis,
                'fraud_analysis': fraud_analysis,
                'time_analysis': time_analysis,
                'summary': {
                    'total_orders': len(orders_df) if not orders_df.empty else 0,
                    'pending_orders': orders_analysis.get('pending_orders', 0),
                    'critical_fraud': fraud_analysis.get('critical_count', 0),
                    'working_hours': time_analysis.get('total_hours', 0)
                }
            }

        except Exception as e:
            print(f"❌ Lỗi lấy detailed performance cho {employee_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _analyze_orders(self, orders_df):
        """Phân tích chi tiết đơn hàng"""
        try:
            if orders_df.empty:
                return {
                    'total_orders': 0,
                    'completed_orders': 0,
                    'pending_orders': 0,
                    'cancelled_orders': 0,
                    'status_distribution': {},
                    'revenue_by_month': {},
                    'top_products': [],
                    'pending_order_details': []
                }

            # Phân bổ trạng thái
            status_counts = {}
            if 'Status' in orders_df.columns:
                status_counts = orders_df['Status'].value_counts().to_dict()

            # Đếm các loại đơn hàng
            completed_orders = 0
            pending_orders = 0
            cancelled_orders = 0

            for status, count in status_counts.items():
                status_lower = str(status).lower()
                if any(word in status_lower for word in ['completed', 'hoàn thành', 'done', 'finished']):
                    completed_orders += count
                elif any(word in status_lower for word in ['pending', 'đang xử lý', 'chờ', 'waiting']):
                    pending_orders += count
                elif any(word in status_lower for word in ['cancelled', 'hủy', 'cancel']):
                    cancelled_orders += count

            # Doanh thu theo tháng
            revenue_by_month = {}
            if 'Month' in orders_df.columns and 'Revenue' in orders_df.columns:
                monthly_revenue = orders_df.groupby('Month')['Revenue'].sum()
                revenue_by_month = monthly_revenue.to_dict()

            # Top sản phẩm
            top_products = []
            if 'Product' in orders_df.columns:
                product_counts = orders_df['Product'].value_counts().head(5)
                top_products = product_counts.to_dict()

            # Chi tiết đơn hàng chờ xử lý
            pending_order_details = []
            if not orders_df.empty and 'Status' in orders_df.columns:
                pending_df = orders_df[
                    orders_df['Status'].str.contains('pending|đang xử lý|chờ', case=False, na=False)
                ].head(10)

                for _, row in pending_df.iterrows():
                    order_detail = {
                        'order_id': row.get('Order_ID', 'N/A'),
                        'customer': row.get('Customer', 'N/A'),
                        'product': row.get('Product', 'N/A'),
                        'revenue': row.get('Revenue', 0),
                        'date': row.get('Date', 'N/A')
                    }
                    pending_order_details.append(order_detail)

            return {
                'total_orders': len(orders_df),
                'completed_orders': completed_orders,
                'pending_orders': pending_orders,
                'cancelled_orders': cancelled_orders,
                'status_distribution': status_counts,
                'revenue_by_month': revenue_by_month,
                'top_products': top_products,
                'pending_order_details': pending_order_details
            }

        except Exception as e:
            print(f"⚠️ Lỗi phân tích orders: {e}")
            return {}

    def _analyze_fraud(self, fraud_df):
        """Phân tích chi tiết gian lận"""
        try:
            if fraud_df.empty:
                return {
                    'total_fraud': 0,
                    'critical_count': 0,
                    'warning_count': 0,
                    'fraud_by_month': {},
                    'common_types': []
                }

            # Đếm theo severity
            critical_count = 0
            warning_count = 0
            if 'Severity' in fraud_df.columns:
                critical_count = len(fraud_df[
                                         fraud_df['Severity'].str.contains('critical|nghiêm trọng', case=False,
                                                                           na=False)
                                     ])
                warning_count = len(fraud_df[
                                        fraud_df['Severity'].str.contains('warning|cảnh báo', case=False, na=False)
                                    ])

            # Gian lận theo tháng
            fraud_by_month = {}
            if 'Month' in fraud_df.columns:
                monthly_fraud = fraud_df.groupby('Month').size()
                fraud_by_month = monthly_fraud.to_dict()

            # Loại gian lận phổ biến
            common_types = []
            if 'Type' in fraud_df.columns:
                fraud_types = fraud_df['Type'].value_counts().head(5)
                common_types = fraud_types.to_dict()

            return {
                'total_fraud': len(fraud_df),
                'critical_count': critical_count,
                'warning_count': warning_count,
                'fraud_by_month': fraud_by_month,
                'common_types': common_types
            }

        except Exception as e:
            print(f"⚠️ Lỗi phân tích fraud: {e}")
            return {}

    def _analyze_working_time(self, browser_df, daily_df):
        """Phân tích thời gian làm việc"""
        try:
            total_hours = 0

            # Tính từ browser sessions
            if not browser_df.empty:
                if 'Total_Seconds' in browser_df.columns:
                    total_hours = browser_df['Total_Seconds'].sum() / 3600
                elif 'Duration_Seconds' in browser_df.columns:
                    total_hours = browser_df['Duration_Seconds'].sum() / 3600
                elif 'Hours' in browser_df.columns:
                    total_hours = browser_df['Hours'].sum()

            # Tính từ daily performance
            elif not daily_df.empty and 'Working_Hours' in daily_df.columns:
                total_hours = daily_df['Working_Hours'].sum()

            # Phân tích theo tháng
            hours_by_month = {}
            if not browser_df.empty and 'Month' in browser_df.columns:
                if 'Total_Seconds' in browser_df.columns:
                    monthly_hours = browser_df.groupby('Month')['Total_Seconds'].sum() / 3600
                    hours_by_month = monthly_hours.to_dict()
                elif 'Duration_Seconds' in browser_df.columns:
                    monthly_hours = browser_df.groupby('Month')['Duration_Seconds'].sum() / 3600
                    hours_by_month = monthly_hours.to_dict()

            return {
                'total_hours': total_hours,
                'hours_by_month': hours_by_month,
                'avg_daily_hours': total_hours / 30 if total_hours > 0 else 0  # Giả sử 30 ngày
            }

        except Exception as e:
            print(f"⚠️ Lỗi phân tích working time: {e}")
            return {}

    def get_lowest_performing_employees(self, limit=5, year=None, month=None):
        """Lấy danh sách nhân viên hiệu suất thấp nhất"""
        try:
            employees = self.get_employee_contact_info()
            if not employees:
                return []

            employee_performances = []

            for emp in employees:
                emp_id = emp['id']
                # Lấy metrics cho nhân viên
                metrics = self.get_employee_performance_metrics(emp_id, year, month)

                if metrics:
                    employee_performances.append({
                        'id': emp_id,
                        'name': emp.get('name', emp_id),
                        'overall_score': metrics.get('overall_score', 0),
                        'completion_rate': metrics.get('completion_rate', 0),
                        'fraud_rate': metrics.get('fraud_rate', 0),
                        'rank': metrics.get('rank', 'Chưa xếp hạng')
                    })

            # Sắp xếp theo overall_score (tăng dần)
            sorted_performances = sorted(employee_performances, key=lambda x: x['overall_score'])

            return sorted_performances[:limit]

        except Exception as e:
            print(f"❌ Lỗi lấy lowest performing employees: {e}")
            return []

    def get_highest_orders_employees(self, limit=5, year=None, month=None):
        """Lấy danh sách nhân viên có số đơn hàng cao nhất"""
        try:
            employees = self.get_employee_contact_info()
            if not employees:
                return []

            employee_orders = []

            for emp in employees:
                emp_id = emp['id']
                # Lấy detailed performance
                perf_data = self.get_employee_detailed_performance(emp_id, year, month)

                if perf_data and 'summary' in perf_data:
                    total_orders = perf_data['summary'].get('total_orders', 0)
                    if total_orders > 0:
                        employee_orders.append({
                            'id': emp_id,
                            'name': emp.get('name', emp_id),
                            'total_orders': total_orders,
                            'completed_orders': perf_data['orders_analysis'].get('completed_orders', 0),
                            'pending_orders': perf_data['orders_analysis'].get('pending_orders', 0)
                        })

            # Sắp xếp theo total_orders (giảm dần)
            sorted_orders = sorted(employee_orders, key=lambda x: x['total_orders'], reverse=True)

            return sorted_orders[:limit]

        except Exception as e:
            print(f"❌ Lỗi lấy highest orders employees: {e}")
            return []

    def get_employee_comparison(self, employee_ids, year=None, month=None):
        """So sánh nhiều nhân viên cùng lúc"""
        try:
            if not employee_ids:
                return []

            comparison_data = []

            for emp_id in employee_ids:
                # Lấy detailed performance
                perf_data = self.get_employee_detailed_performance(emp_id, year, month)

                if perf_data:
                    # Lấy contact info
                    contact_info = self.get_employee_contact_info([emp_id])
                    emp_name = contact_info[0].get('name', emp_id) if contact_info else emp_id

                    comparison_data.append({
                        'id': emp_id,
                        'name': emp_name,
                        'performance': perf_data
                    })

            return comparison_data

        except Exception as e:
            print(f"❌ Lỗi so sánh nhân viên: {e}")
            return []

    def get_pending_orders_analysis(self, employee_id, year=None, month=None):
        """Phân tích chi tiết đơn hàng chưa xử lý"""
        try:
            perf_data = self.get_employee_detailed_performance(employee_id, year, month)

            if not perf_data:
                return None

            orders_analysis = perf_data.get('orders_analysis', {})

            return {
                'employee_id': employee_id,
                'total_pending': orders_analysis.get('pending_orders', 0),
                'pending_details': orders_analysis.get('pending_order_details', []),
                'pending_by_product': orders_analysis.get('top_products', {}),
                'estimated_revenue': sum(
                    order.get('revenue', 0) for order in orders_analysis.get('pending_order_details', []))
            }

        except Exception as e:
            print(f"❌ Lỗi phân tích pending orders: {e}")
            return None

    def get_employee_contact_info(self, employee_ids=None):
        """Lấy thông tin liên hệ của nhân viên từ file Excel - CHỈ LẤY NHÂN VIÊN (EM)"""
        try:
            # Đường dẫn đến file Excel trong cùng thư mục
            current_dir = Path(__file__).parent
            excel_path = current_dir / 'employee_ids.xlsx'

            if not excel_path.exists():
                print(f"⚠️ File employee info not found: {excel_path}")
                return self.get_sample_employee_data()

            # Đọc file Excel
            df = pd.read_excel(excel_path)
            print(f"✅ Đọc file Excel thành công: {len(df)} dòng, {len(df.columns)} cột")
            print(f"   Các cột: {list(df.columns)}")

            # Chuẩn hóa tên cột (bỏ khoảng trắng, chữ hoa thường)
            df.columns = df.columns.str.strip()

            # Kiểm tra cấu trúc file
            expected_columns = ['ID', 'Full_Name', 'Email', 'SAP', 'Pwd', 'Client']
            available_columns = list(df.columns)

            print(f"   Cột có trong file: {available_columns}")

            # Tìm mapping cho các cột
            column_mapping = {}
            for expected in expected_columns:
                for actual in available_columns:
                    if expected.lower() == actual.lower():
                        column_mapping[actual] = expected
                        break

            print(f"   Mapping cột: {column_mapping}")

            # Đổi tên cột theo mapping
            if column_mapping:
                df = df.rename(columns=column_mapping)

            # Đảm bảo các cột bắt buộc tồn tại
            if 'ID' not in df.columns:
                # Thử tìm cột 'employee_id' hoặc 'Mã NV'
                for col in df.columns:
                    if 'id' in col.lower() or 'mã' in col.lower() or 'code' in col.lower():
                        df = df.rename(columns={col: 'ID'})
                        print(f"   Đổi tên cột '{col}' thành 'ID'")
                        break

            if 'Full_Name' not in df.columns:
                # Thử tìm cột 'Name' hoặc 'Họ tên'
                for col in df.columns:
                    if 'name' in col.lower() or 'họ tên' in col.lower() or 'fullname' in col.lower():
                        df = df.rename(columns={col: 'Full_Name'})
                        print(f"   Đổi tên cột '{col}' thành 'Full_Name'")
                        break

            if 'Email' not in df.columns:
                # Thử tìm cột 'Email' hoặc 'Mail'
                for col in df.columns:
                    if 'email' in col.lower() or 'mail' in col.lower():
                        df = df.rename(columns={col: 'Email'})
                        print(f"   Đổi tên cột '{col}' thành 'Email'")
                        break

            # Lọc chỉ lấy nhân viên (bắt đầu bằng EM), bỏ quản lý (MG)
            if 'ID' in df.columns:
                # Chuyển ID thành string và loại bỏ NaN
                df['ID'] = df['ID'].astype(str).str.strip()
                # Chỉ lấy các dòng có ID bắt đầu bằng EM
                df = df[df['ID'].str.startswith('EM')]
                print(f"   Sau khi lọc EM: {len(df)} nhân viên")
            else:
                print("❌ Không tìm thấy cột ID trong file")
                return self.get_sample_employee_data()

            # Lọc theo ID nếu có
            if employee_ids:
                # Chuẩn hóa employee_ids thành string
                employee_ids = [str(id).strip() for id in employee_ids]
                df = df[df['ID'].isin(employee_ids)]
                print(f"   Sau khi lọc theo ID: {len(df)} nhân viên")

            # Điền giá trị mặc định cho các cột null
            for col in ['Email', 'SAP', 'Pwd', 'Client']:
                if col in df.columns:
                    df[col] = df[col].fillna('')

            # Chuyển thành danh sách dictionary
            employees = []
            for _, row in df.iterrows():
                # Bỏ qua hàng trống
                if pd.isna(row['ID']) or str(row['ID']).strip() == '':
                    continue

                employee_info = {
                    'id': str(row['ID']).strip(),
                    'name': str(row['Full_Name']).strip() if 'Full_Name' in row and not pd.isna(
                        row['Full_Name']) else str(row['ID']).strip(),
                    'email': str(row['Email']).strip() if 'Email' in row and not pd.isna(row['Email']) else '',
                }

                # Thêm thông tin bổ sung nếu có
                if 'SAP' in row and not pd.isna(row['SAP']):
                    employee_info['sap'] = str(row['SAP']).strip()

                if 'Pwd' in row and not pd.isna(row['Pwd']):
                    employee_info['pwd'] = str(row['Pwd']).strip()

                if 'Client' in row and not pd.isna(row['Client']):
                    employee_info['client'] = str(row['Client']).strip()

                employees.append(employee_info)

            print(f"✅ Đã tải {len(employees)} nhân viên từ {excel_path.name}")

            # Debug: In ra thông tin nhân viên
            for emp in employees[:10]:
                print(
                    f"   - {emp['id']}: {emp['name']} | Email: {emp.get('email', 'N/A')} | SAP: {emp.get('sap', 'N/A')}")

            return employees

        except Exception as e:
            print(f"❌ Lỗi đọc thông tin nhân viên: {e}")
            import traceback
            traceback.print_exc()
            return self.get_sample_employee_data()

    def get_sample_employee_data(self):
        """Dữ liệu mẫu khi không có file Excel - CHỈ NHÂN VIÊN"""
        return [
            {
                'id': 'EM001',
                'name': 'Giang',
                'email': 'gameyuno123@gmail.com',
                'sap': 'LEARN-717',
                'pwd': 'Giang1109@',
                'client': '312'
            },
            {
                'id': 'EM002',
                'name': 'Nhi',
                'email': 'konodio3q@gmail.com',
                'sap': '',
                'pwd': '',
                'client': ''
            },
            {
                'id': 'EM003',
                'name': 'Thu',
                'email': '',
                'sap': 'LEARN-757',
                'pwd': '02078126',
                'client': '312'
            },
            {
                'id': 'EM004',
                'name': 'Kha',
                'email': '',
                'sap': '',
                'pwd': '',
                'client': ''
            }
        ]
    # Thêm vào class DataProcessor trong data_processor.py
    def get_employee_performance_metrics(self, employee_id, year=None, month=None):
        """Lấy metrics hiệu suất cụ thể cho một nhân viên"""
        try:
            if not employee_id:
                return None

            # Tạo processor cho nhân viên cụ thể
            from MG.data_processor import DataProcessor
            emp_processor = DataProcessor(employee_id)

            # Load dữ liệu theo period
            success = emp_processor.load_period_data(year, month)

            if not success:
                print(f"⚠️ Không thể load dữ liệu cho {employee_id}")
                return None

            # Lấy dữ liệu dashboard
            emp_data = emp_processor.get_dashboard_data()

            if not emp_data:
                return None

            # Tính toán metrics (sử dụng logic từ _calculate_employee_metrics)
            return self.calculate_single_employee_metrics(emp_data, employee_id, year, month)

        except Exception as e:
            print(f"❌ Lỗi lấy metrics cho {employee_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def calculate_single_employee_metrics(self, emp_data, employee_id, year, month):
        """Tính toán metrics cho một nhân viên - tối ưu hóa từ _calculate_employee_metrics"""
        try:
            sap_sheets = emp_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = emp_data.get('work_log', {}).get('sheets', {})

            # Lấy dữ liệu Orders
            orders_df = sap_sheets.get('Orders', pd.DataFrame())
            fraud_df = work_log_sheets.get('Fraud_Events', pd.DataFrame())
            daily_df = sap_sheets.get('Daily_Performance', pd.DataFrame())

            # Lọc theo month nếu có
            if month and not orders_df.empty and 'Month' in orders_df.columns:
                month_int = int(month)
                orders_df = orders_df[orders_df['Month'] == month_int]
                if not fraud_df.empty and 'Month' in fraud_df.columns:
                    fraud_df = fraud_df[fraud_df['Month'] == month_int]
                if not daily_df.empty and 'Month' in daily_df.columns:
                    daily_df = daily_df[daily_df['Month'] == month_int]

            # Tính toán các chỉ số
            total_orders = len(orders_df) if not orders_df.empty else 0
            total_revenue = orders_df['Revenue'].sum() if not orders_df.empty and 'Revenue' in orders_df.columns else 0
            total_profit = orders_df['Profit'].sum() if not orders_df.empty and 'Profit' in orders_df.columns else 0
            total_fraud = len(fraud_df) if not fraud_df.empty else 0

            # Tính completion rate
            completion_rate = 0
            completed_orders = 0
            if not orders_df.empty and 'Status' in orders_df.columns:
                completed_orders = len(
                    orders_df[orders_df['Status'].str.contains('Completed|Hoàn thành', case=False, na=False)])
                completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

            # Tính profit margin
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

            # Tính revenue per order
            revenue_per_order = total_revenue / total_orders if total_orders > 0 else 0
            profit_per_order = total_profit / total_orders if total_orders > 0 else 0

            # Tính fraud rate
            fraud_rate = (total_fraud / total_orders * 100) if total_orders > 0 else 0

            # Tính working hours
            working_hours = 0
            browser_df = work_log_sheets.get('Browser_Sessions', pd.DataFrame())
            if browser_df.empty:
                browser_df = work_log_sheets.get('Browser_Time', pd.DataFrame())

            if not browser_df.empty:
                if 'Total_Seconds' in browser_df.columns:
                    working_hours = browser_df['Total_Seconds'].sum() / 3600
                elif 'Duration_Seconds' in browser_df.columns:
                    working_hours = browser_df['Duration_Seconds'].sum() / 3600
                elif 'Hours' in browser_df.columns:
                    working_hours = browser_df['Hours'].sum()

            # Tính orders per hour
            orders_per_hour = total_orders / working_hours if working_hours > 0 else 0

            # Phân loại fraud theo severity
            critical_fraud = 0
            warning_fraud = 0
            if not fraud_df.empty and 'Severity' in fraud_df.columns:
                critical_fraud = len(
                    fraud_df[fraud_df['Severity'].str.contains('Critical|Nghiêm trọng', case=False, na=False)])
                warning_fraud = len(
                    fraud_df[fraud_df['Severity'].str.contains('Warning|Cảnh báo', case=False, na=False)])

            # Tính overall score (0-100)
            target_revenue_per_month = 10000000  # 10M VND target
            months_count = 1 if month else 12

            revenue_score = min(100, (total_revenue / (target_revenue_per_month * months_count)) * 100) * 0.3
            completion_score = completion_rate * 0.4
            efficiency_score = min(100, orders_per_hour * 10) * 0.2  # Assume 10 orders/hour is excellent
            compliance_score = max(0, 100 - (fraud_rate * 10)) * 0.1

            overall_score = revenue_score + completion_score + efficiency_score + compliance_score

            # Xác định rank
            if overall_score >= 90:
                rank = "Xuất sắc"
                rank_emoji = "🏆"
            elif overall_score >= 80:
                rank = "Tốt"
                rank_emoji = "⭐"
            elif overall_score >= 70:
                rank = "Khá"
                rank_emoji = "👍"
            elif overall_score >= 60:
                rank = "Trung bình"
                rank_emoji = "📊"
            else:
                rank = "Cần cải thiện"
                rank_emoji = "⚠️"

            # Xác định strengths và weaknesses
            strengths = []
            weaknesses = []

            if completion_rate >= 95:
                strengths.append("Tỷ lệ hoàn thành xuất sắc")
            elif completion_rate < 70:
                weaknesses.append("Tỷ lệ hoàn thành thấp")

            if profit_margin >= 25:
                strengths.append("Lợi nhuận cao")
            elif profit_margin < 15:
                weaknesses.append("Lợi nhuận thấp")

            if fraud_rate <= 5:
                strengths.append("Tuân thủ tốt, ít gian lận")
            elif fraud_rate > 15:
                weaknesses.append("Nhiều sự kiện gian lận")

            if orders_per_hour >= 5:
                strengths.append("Hiệu suất xử lý cao")
            elif orders_per_hour < 2:
                weaknesses.append("Hiệu suất xử lý chậm")

            if revenue_per_order >= 50000000:  # 50M/order
                strengths.append("Giá trị đơn hàng cao")
            elif revenue_per_order < 20000000:  # 20M/order
                weaknesses.append("Giá trị đơn hàng thấp")

            return {
                'employee_id': employee_id,
                'year': year,
                'month': month,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_fraud': total_fraud,
                'critical_fraud': critical_fraud,
                'warning_fraud': warning_fraud,
                'completion_rate': round(completion_rate, 2),
                'profit_margin': round(profit_margin, 2),
                'revenue_per_order': round(revenue_per_order, 2),
                'profit_per_order': round(profit_per_order, 2),
                'fraud_rate': round(fraud_rate, 2),
                'working_hours': round(working_hours, 2),
                'orders_per_hour': round(orders_per_hour, 2),
                'overall_score': round(overall_score, 2),
                'rank': rank,
                'rank_emoji': rank_emoji,
                'strengths': strengths,
                'weaknesses': weaknesses
            }

        except Exception as e:
            print(f"❌ Lỗi tính metrics cho {employee_id}: {e}")
            import traceback
            traceback.print_exc()
            return None

    # ========== LOAD DATA BY PERIOD ==========
    def get_employee_comparison_data(self, year=None, month=None):
        """Load và so sánh dữ liệu của tất cả nhân viên"""
        try:
            if year is None:
                year = datetime.now().year

            employees = self.get_all_employees()
            comparison_data = []

            print(f"\n{'=' * 70}")
            print(f"📊 LOADING COMPARISON DATA FOR ALL EMPLOYEES (Year: {year})")
            print(f"{'=' * 70}")

            for emp in employees:
                if not emp['has_data']:
                    continue

                print(f"\n🔍 Processing: {emp['name']}...")

                # Tạo DataProcessor riêng cho từng nhân viên
                emp_processor = DataProcessor(emp['name'])

                # Load dữ liệu theo year/month
                if month:
                    success = emp_processor.load_year_data(year, month)
                else:
                    success = emp_processor.load_year_data(year)

                if not success:
                    print(f"   ⚠️ Failed to load data for {emp['name']}")
                    continue

                emp_data = emp_processor.get_dashboard_data()

                if not emp_data:
                    print(f"   ⚠️ No dashboard data for {emp['name']}")
                    continue

                # Tính toán metrics cho nhân viên
                metrics = self._calculate_employee_metrics(emp_data, emp['name'], year, month)

                if metrics:
                    comparison_data.append(metrics)
                    print(f"   ✅ Loaded: {metrics['total_orders']} orders, {metrics['total_revenue']:,.0f} VND")

            print(f"\n{'=' * 70}")
            print(f"✅ Loaded comparison data for {len(comparison_data)} employees")
            print(f"{'=' * 70}\n")

            return comparison_data

        except Exception as e:
            print(f"❌ Error loading comparison data: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _calculate_employee_metrics(self, emp_data, emp_name, year, month):
        """Tính toán metrics chi tiết cho 1 nhân viên"""
        try:
            sap_sheets = emp_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = emp_data.get('work_log', {}).get('sheets', {})

            # Lấy dữ liệu Orders
            orders_df = sap_sheets.get('Orders', pd.DataFrame())
            fraud_df = work_log_sheets.get('Fraud_Events', pd.DataFrame())
            daily_df = sap_sheets.get('Daily_Performance', pd.DataFrame())

            # Lọc theo month nếu có
            if month and not orders_df.empty and 'Month' in orders_df.columns:
                orders_df = orders_df[orders_df['Month'] == int(month)]
                if not fraud_df.empty and 'Month' in fraud_df.columns:
                    fraud_df = fraud_df[fraud_df['Month'] == int(month)]
                if not daily_df.empty and 'Month' in daily_df.columns:
                    daily_df = daily_df[daily_df['Month'] == int(month)]

            # Tính toán các chỉ số
            total_orders = len(orders_df) if not orders_df.empty else 0
            total_revenue = orders_df['Revenue'].sum() if not orders_df.empty and 'Revenue' in orders_df.columns else 0
            total_profit = orders_df['Profit'].sum() if not orders_df.empty and 'Profit' in orders_df.columns else 0
            total_fraud = len(fraud_df) if not fraud_df.empty else 0

            # Tính completion rate
            completion_rate = 0
            completed_orders = 0
            if not orders_df.empty and 'Status' in orders_df.columns:
                completed_orders = len(
                    orders_df[orders_df['Status'].str.contains('Completed|Hoàn thành', case=False, na=False)])
                completion_rate = (completed_orders / total_orders * 100) if total_orders > 0 else 0

            # Tính profit margin
            profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0

            # Tính revenue per order
            revenue_per_order = total_revenue / total_orders if total_orders > 0 else 0
            profit_per_order = total_profit / total_orders if total_orders > 0 else 0

            # Tính fraud rate
            fraud_rate = (total_fraud / total_orders * 100) if total_orders > 0 else 0

            # Tính working hours
            working_hours = 0
            browser_df = work_log_sheets.get('Browser_Sessions', pd.DataFrame())
            if browser_df.empty:
                browser_df = work_log_sheets.get('Browser_Time', pd.DataFrame())

            if not browser_df.empty:
                if 'Total_Seconds' in browser_df.columns:
                    working_hours = browser_df['Total_Seconds'].sum() / 3600
                elif 'Duration_Seconds' in browser_df.columns:
                    working_hours = browser_df['Duration_Seconds'].sum() / 3600
                elif 'Hours' in browser_df.columns:
                    working_hours = browser_df['Hours'].sum()

            # Tính orders per hour
            orders_per_hour = total_orders / working_hours if working_hours > 0 else 0

            # Phân loại fraud theo severity
            critical_fraud = 0
            warning_fraud = 0
            if not fraud_df.empty and 'Severity' in fraud_df.columns:
                critical_fraud = len(
                    fraud_df[fraud_df['Severity'].str.contains('Critical|Nghiêm trọng', case=False, na=False)])
                warning_fraud = len(
                    fraud_df[fraud_df['Severity'].str.contains('Warning|Cảnh báo', case=False, na=False)])

            # Tính overall score (0-100)
            # Formula: 40% completion + 30% revenue performance + 20% efficiency + 10% compliance
            target_revenue_per_month = 10000000  # 10M VND target
            months_count = 1 if month else 12

            revenue_score = min(100, (total_revenue / (target_revenue_per_month * months_count)) * 100) * 0.3
            completion_score = completion_rate * 0.4
            efficiency_score = min(100, orders_per_hour * 10) * 0.2  # Assume 10 orders/hour is excellent
            compliance_score = max(0, 100 - (fraud_rate * 10)) * 0.1

            overall_score = revenue_score + completion_score + efficiency_score + compliance_score

            # Xác định rank
            if overall_score >= 90:
                rank = "Xuất sắc"
                rank_emoji = "🏆"
            elif overall_score >= 80:
                rank = "Tốt"
                rank_emoji = "⭐"
            elif overall_score >= 70:
                rank = "Khá"
                rank_emoji = "👍"
            elif overall_score >= 60:
                rank = "Trung bình"
                rank_emoji = "📊"
            else:
                rank = "Cần cải thiện"
                rank_emoji = "⚠️"

            # Xác định strengths và weaknesses
            strengths = []
            weaknesses = []

            if completion_rate >= 95:
                strengths.append("Tỷ lệ hoàn thành xuất sắc")
            elif completion_rate < 70:
                weaknesses.append("Tỷ lệ hoàn thành thấp")

            if profit_margin >= 25:
                strengths.append("Lợi nhuận cao")
            elif profit_margin < 15:
                weaknesses.append("Lợi nhuận thấp")

            if fraud_rate <= 5:
                strengths.append("Tuân thủ tốt, ít gian lận")
            elif fraud_rate > 15:
                weaknesses.append("Nhiều sự kiện gian lận")

            if orders_per_hour >= 5:
                strengths.append("Hiệu suất xử lý cao")
            elif orders_per_hour < 2:
                weaknesses.append("Hiệu suất xử lý chậm")

            if revenue_per_order >= 50000000:  # 50M/order
                strengths.append("Giá trị đơn hàng cao")
            elif revenue_per_order < 20000000:  # 20M/order
                weaknesses.append("Giá trị đơn hàng thấp")

            return {
                'name': emp_name,
                'year': year,
                'month': month,
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_fraud': total_fraud,
                'critical_fraud': critical_fraud,
                'warning_fraud': warning_fraud,
                'completion_rate': round(completion_rate, 2),
                'profit_margin': round(profit_margin, 2),
                'revenue_per_order': round(revenue_per_order, 2),
                'profit_per_order': round(profit_per_order, 2),
                'fraud_rate': round(fraud_rate, 2),
                'working_hours': round(working_hours, 2),
                'orders_per_hour': round(orders_per_hour, 2),
                'overall_score': round(overall_score, 2),
                'rank': rank,
                'rank_emoji': rank_emoji,
                'strengths': strengths,
                'weaknesses': weaknesses
            }

        except Exception as e:
            print(f"❌ Error calculating metrics for {emp_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_top_performers(self, year=None, month=None, top_n=3):
        """Lấy top n nhân viên xuất sắc nhất"""
        comparison_data = self.get_employee_comparison_data(year, month)

        if not comparison_data:
            return []

        # Sắp xếp theo overall_score
        sorted_data = sorted(comparison_data, key=lambda x: x['overall_score'], reverse=True)

        return sorted_data[:top_n]

    def get_bottom_performers(self, year=None, month=None, bottom_n=3):
        """Lấy n nhân viên cần cải thiện nhất"""
        comparison_data = self.get_employee_comparison_data(year, month)

        if not comparison_data:
            return []

        # Sắp xếp theo overall_score
        sorted_data = sorted(comparison_data, key=lambda x: x['overall_score'])

        return sorted_data[:bottom_n]

    def get_employee_rankings(self, year=None, month=None):
        """Lấy bảng xếp hạng đầy đủ của tất cả nhân viên"""
        comparison_data = self.get_employee_comparison_data(year, month)

        if not comparison_data:
            return []

        # Sắp xếp theo overall_score và thêm ranking number
        sorted_data = sorted(comparison_data, key=lambda x: x['overall_score'], reverse=True)

        for i, emp in enumerate(sorted_data):
            emp['ranking'] = i + 1
            if i == 0:
                emp['medal'] = "🥇"
            elif i == 1:
                emp['medal'] = "🥈"
            elif i == 2:
                emp['medal'] = "🥉"
            else:
                emp['medal'] = ""

        return sorted_data

    def load_period_data(self, year=None, month=None):
        """Load data for specific period"""
        try:
            print(f"🎯 Loading data for: year={year}, month={month}")

            # If no year, get last 4 years
            if year is None:
                current_year = datetime.now().year
                years = list(range(current_year - 3, current_year + 1))
                print(f"📅 Getting data for last 4 years: {years}")

                all_data = []
                for y in years:
                    # Call load_year_data with year and month
                    success = self.load_year_data(y, month)
                    if success and self.year_data:
                        all_data.append(self.year_data)

                if all_data:
                    # Merge data from all years
                    self.year_data = self._merge_multiyear_data(all_data)
                    return True
                else:
                    return False
            else:
                # Specific year
                return self.load_year_data(year, month)

        except Exception as e:
            print(f"❌ Error loading period data: {e}")
            traceback.print_exc()
            return False

    def load_year_data(self, year=None, month=None):
        """Load data for specific year and optionally filter by month"""
        try:
            # If no year provided, use current year
            if year is None:
                year = datetime.now().year

            print(f"📅 Loading data for year {year} for {self.employee_name}...")

            year_int = int(year)
            year_data = {
                'work_log': {'sheets': {}},
                'sap_data': {'sheets': {}},
                'summary': {}
            }

            collector = {'work_log': {}, 'sap_data': {}}

            # Load data for all months in year
            for m in range(1, 13):
                # If month filter exists, only get that month
                if month is not None and m != int(month):
                    continue

                month_str = f"{year_int}_{m:02d}"
                month_path = self.base_path / self.employee_name / month_str

                if month_path.exists():
                    # Load work log - Đọc tất cả sheet liên quan
                    work_log_path = month_path / f"work_logs_{self.employee_name}_{month_str}.xlsx"
                    if work_log_path.exists():
                        try:
                            # Đọc Excel file để lấy danh sách sheet
                            excel_file = pd.ExcelFile(work_log_path)
                            sheet_names = excel_file.sheet_names

                            # Đọc từng sheet có tên mong muốn
                            sheets_to_read = ['Fraud_Events', 'Browser_Sessions', 'Browser_Time',
                                              'Browser Session', 'Browser Time', 'Session']

                            for sheet_name in sheet_names:
                                # Tìm sheet phù hợp (không phân biệt hoa thường)
                                normalized_sheet = sheet_name.lower().replace(' ', '_')

                                if any(target_sheet in normalized_sheet for target_sheet in
                                       ['fraud_events', 'browser_sessions', 'browser_time', 'session']):

                                    try:
                                        df = pd.read_excel(work_log_path, sheet_name=sheet_name)
                                        df['Month'] = m
                                        df['Year'] = year_int

                                        # Lưu với tên chuẩn hóa
                                        key_name = 'Fraud_Events' if 'fraud' in normalized_sheet else \
                                            'Browser_Sessions' if 'session' in normalized_sheet else \
                                                'Browser_Time'

                                        if key_name not in collector['work_log']:
                                            collector['work_log'][key_name] = []
                                        collector['work_log'][key_name].append(df)

                                        print(
                                            f"   ✅ Read work log sheet '{sheet_name}' month {m}: {len(df)} rows (saved as {key_name})")

                                    except Exception as e:
                                        print(f"   ⚠️ Error reading sheet {sheet_name} month {m}: {e}")
                        except Exception as e:
                            print(f"⚠️ Error reading work log month {m}: {e}")

                    # Load SAP data (giữ nguyên)
                    sap_path = month_path / "sap_data.xlsx"
                    if sap_path.exists():
                        try:
                            # Read Orders sheet
                            df_orders = pd.read_excel(sap_path, sheet_name='Orders')
                            df_orders['Month'] = m
                            df_orders['Year'] = year_int

                            if 'Orders' not in collector['sap_data']:
                                collector['sap_data']['Orders'] = []
                            collector['sap_data']['Orders'].append(df_orders)

                            # Read Daily_Performance sheet if exists
                            try:
                                df_daily = pd.read_excel(sap_path, sheet_name='Daily_Performance')
                                df_daily['Month'] = m
                                df_daily['Year'] = year_int

                                if 'Daily_Performance' not in collector['sap_data']:
                                    collector['sap_data']['Daily_Performance'] = []
                                collector['sap_data']['Daily_Performance'].append(df_daily)
                            except:
                                pass

                            print(f"   ✅ Read SAP month {m}: {len(df_orders)} orders")
                        except Exception as e:
                            print(f"⚠️ Error reading SAP data month {m}: {e}")
                else:
                    print(f"⚠️ Folder not found: {month_path}")

            # Merge data from all months
            for category in ['work_log', 'sap_data']:
                for sheet_name, df_list in collector[category].items():
                    if df_list:
                        year_data[category]['sheets'][sheet_name] = pd.concat(df_list, ignore_index=True)
                        print(
                            f"   ✅ Merged {category}.{sheet_name}: {len(year_data[category]['sheets'][sheet_name])} rows")
                    else:
                        year_data[category]['sheets'][sheet_name] = pd.DataFrame()

            # Calculate summary
            orders_df = year_data['sap_data']['sheets'].get('Orders', pd.DataFrame())
            fraud_df = year_data['work_log']['sheets'].get('Fraud_Events', pd.DataFrame())

            total_orders = len(orders_df) if not orders_df.empty else 0
            total_revenue = orders_df['Revenue'].sum() if not orders_df.empty and 'Revenue' in orders_df.columns else 0
            total_profit = orders_df['Profit'].sum() if not orders_df.empty and 'Profit' in orders_df.columns else 0
            total_fraud = len(fraud_df) if not fraud_df.empty else 0

            year_data['summary'] = {
                'year': year_int,
                'employee_name': self.employee_name,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_fraud': total_fraud
            }

            self.year_data = year_data
            print(f"✅ Loaded data for year {year_int}: {total_orders} orders, {total_revenue:,.0f} revenue")

            return True

        except Exception as e:
            print(f"❌ Error loading data for year {year}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _merge_multiyear_data(self, data_list):
        """Merge data from multiple years"""
        if not data_list:
            return None

        merged_data = {
            'work_log': {'sheets': {}},
            'sap_data': {'sheets': {}},
            'summary': {}
        }

        # Merge sheets
        for data in data_list:
            for category in ['work_log', 'sap_data']:
                for sheet_name, df in data[category]['sheets'].items():
                    if sheet_name not in merged_data[category]['sheets']:
                        merged_data[category]['sheets'][sheet_name] = df
                    elif not df.empty:
                        merged_data[category]['sheets'][sheet_name] = pd.concat(
                            [merged_data[category]['sheets'][sheet_name], df],
                            ignore_index=True
                        )

        # Calculate aggregated summary
        orders_df = merged_data['sap_data']['sheets'].get('Orders', pd.DataFrame())
        fraud_df = merged_data['work_log']['sheets'].get('Fraud_Events', pd.DataFrame())

        total_orders = len(orders_df) if not orders_df.empty else 0
        total_revenue = orders_df['Revenue'].sum() if not orders_df.empty and 'Revenue' in orders_df.columns else 0
        total_profit = orders_df['Profit'].sum() if not orders_df.empty and 'Profit' in orders_df.columns else 0
        total_fraud = len(fraud_df) if not fraud_df.empty else 0

        merged_data['summary'] = {
            'year': 'Multi-year',
            'employee_name': self.employee_name,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_fraud': total_fraud
        }

        return merged_data

    def load_aggregate_data(self, year=None, month=None):
        """Load and aggregate data from all employees in system"""
        try:
            employees = self.get_all_employees()
            if not employees:
                return {}

            aggregate_data = {
                'total_employees': len(employees),
                'employees_with_data': 0,
                'total_revenue': 0,
                'total_profit': 0,
                'total_orders': 0,
                'total_fraud': 0,
                'average_completion_rate': 0,
                'average_overall_score': 0,
                'monthly_data': self._init_monthly_data()
            }

            for emp in employees:
                if not emp['has_data']:
                    continue

                temp_processor = DataProcessor(emp['name'])
                # Call load_period_data with year and month
                success = temp_processor.load_period_data(year, month)

                if not success:
                    continue

                emp_year_data = temp_processor.get_dashboard_data()

                if not emp_year_data:
                    continue

                aggregate_data['employees_with_data'] += 1
                summary = emp_year_data.get('summary', {})
                aggregate_data['total_revenue'] += summary.get('total_revenue', 0)
                aggregate_data['total_profit'] += summary.get('total_profit', 0)
                aggregate_data['total_orders'] += summary.get('total_orders', 0)
                aggregate_data['total_fraud'] += summary.get('total_fraud', 0)

                self._update_aggregate_monthly_data(aggregate_data['monthly_data'], emp_year_data)

            if aggregate_data['employees_with_data'] > 0:
                aggregate_data['average_completion_rate'] = 95.0
                aggregate_data['average_overall_score'] = 85.0

            return aggregate_data
        except Exception as e:
            print(f"❌ Error aggregating data: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _update_aggregate_monthly_data(self, monthly_data, emp_year_data):
        try:
            sap_sheets = emp_year_data.get('sap_data', {}).get('sheets', {})
            if 'Orders' in sap_sheets:
                df = sap_sheets['Orders']
                if not df.empty and 'Month' in df.columns:
                    for m in range(1, 13):
                        m_df = df[df['Month'] == m]
                        if not m_df.empty:
                            monthly_data['orders'][m - 1] += len(m_df)
                            if 'Revenue' in m_df.columns:
                                monthly_data['revenue'][m - 1] += m_df['Revenue'].sum()
                            if 'Profit' in m_df.columns:
                                monthly_data['profit'][m - 1] += m_df['Profit'].sum()
            wl_sheets = emp_year_data.get('work_log', {}).get('sheets', {})
            if 'Fraud_Events' in wl_sheets:
                df_f = wl_sheets['Fraud_Events']
                if not df_f.empty and 'Month' in df_f.columns:
                    for m in range(1, 13):
                        m_df_f = df_f[(df_f['Month'] == m) & (df_f.get('IsFraud', 0) == 1)]
                        monthly_data['fraud'][m - 1] += len(m_df_f)
        except:
            pass

    def get_dashboard_data(self):
        return self.year_data

    def get_all_data(self):
        return {
            'work_log': self.work_log_data,
            'sap_data': self.sap_data,
            'metrics': self.metrics if self.metrics else {},
            'year_data': self.year_data
        }

    def get_summary_data(self):
        return {
            'work_log': self.work_log_data.get('summary', {}) if self.work_log_data else {},
            'sap': self.sap_data.get('summary', {}) if self.sap_data else {},
            'metrics': self.metrics if self.metrics else {}
        }

    def load_all_data(self):
        try:
            if not self.employee_name:
                return False
            return self.load_period_data(None, None)
        except:
            return False

    def load_work_log(self, file_path):
        if not Path(file_path).exists():
            return self._get_default_work_log()
        try:
            df = pd.read_excel(file_path, sheet_name='Fraud_Events')
            return {'summary': {'fraud_count': len(df[df.get('IsFraud') == 1]), 'total_work_hours': 160},
                    'file_found': True}
        except:
            return self._get_default_work_log()

    def load_sap_data(self, file_path):
        if not Path(file_path).exists():
            return self._get_default_sap_data()
        try:
            df = pd.read_excel(file_path, sheet_name='Orders')
            return {'summary': {'total_revenue': df['Revenue'].sum() if 'Revenue' in df.columns else 0,
                                'total_orders': len(df)}, 'file_found': True}
        except:
            return self._get_default_sap_data()

    def calculate_metrics(self):
        try:
            sap = self.sap_data.get('summary', {})
            wl = self.work_log_data.get('summary', {})
            self.metrics = {
                'overall': 88, 'efficiency': round(sap.get('efficiency_score', 85), 1),
                'quality': 90, 'compliance': max(0, 100 - wl.get('fraud_count', 0) * 10)
            }
        except:
            self.metrics = {}

    def get_all_employees(self):
        try:
            if not self.base_path.exists():
                return []
            return [{'name': d.name, 'has_data': self.check_employee_has_data(d.name), 'path': str(d)} for d in
                    self.base_path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        except:
            return []

    def check_employee_has_data(self, employee_name):
        path = self.base_path / employee_name
        return any(d.is_dir() and '_' in d.name for d in path.iterdir()) if path.exists() else False

    def _init_monthly_data(self):
        return {'months': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
                'revenue': [0.0] * 12, 'profit': [0.0] * 12, 'orders': [0] * 12, 'fraud': [0] * 12}

    def _get_default_work_log(self):
        return {'summary': {'fraud_count': 0, 'total_work_hours': 0}, 'file_found': False}

    def _get_default_sap_data(self):
        return {'summary': {'total_revenue': 0, 'total_orders': 0}, 'file_found': False}
