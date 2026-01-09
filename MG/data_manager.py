#!/usr/bin/env python3
"""
data_manager.py - Quản lý và tổng hợp dữ liệu cho Manager
Phiên bản hỗ trợ đa nhân viên, filter theo thời gian, và tích hợp với Gemini
"""

import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')


class DataManager:
    """Quản lý dữ liệu đa nhân viên cho Manager Dashboard"""

    def __init__(self, base_path=None):
        if base_path:
            self.base_path = Path(base_path)
        else:
            # Path mặc định từ config
            self.base_path = Path("C:/Users/legal/PycharmProjects/PythonProject/Saved_file")

        print(f"📁 DataManager khởi tạo với base path: {self.base_path}")

    def get_all_employees(self):
        """Lấy danh sách tất cả nhân viên từ cấu trúc thư mục"""
        employees = []

        try:
            if not self.base_path.exists():
                print(f"❌ Thư mục base không tồn tại: {self.base_path}")
                return []

            # Lấy tất cả thư mục con (mỗi thư mục là một nhân viên)
            for item in self.base_path.iterdir():
                if item.is_dir():
                    # Kiểm tra xem có dữ liệu không
                    employee_name = item.name
                    data_files = self.get_employee_data_files(employee_name)

                    if data_files:
                        employees.append({
                            'name': employee_name,
                            'data_path': str(item),
                            'has_data': True,
                            'data_files': data_files
                        })
                    else:
                        employees.append({
                            'name': employee_name,
                            'data_path': str(item),
                            'has_data': False,
                            'data_files': {}
                        })

            print(f"✅ Tìm thấy {len(employees)} nhân viên")
            return sorted(employees, key=lambda x: x['name'])

        except Exception as e:
            print(f"❌ Lỗi khi lấy danh sách nhân viên: {e}")
            return []

    def get_employee_data_files(self, employee_name):
        """Lấy tất cả file dữ liệu của một nhân viên"""
        employee_path = self.base_path / employee_name
        data_files = {}

        if not employee_path.exists():
            return {}

        try:
            # Tìm tất cả các thư mục năm_tháng
            for year_month_dir in employee_path.iterdir():
                if year_month_dir.is_dir():
                    year_month = year_month_dir.name

                    # Tìm các file Excel
                    excel_files = list(year_month_dir.glob("*.xlsx"))

                    if excel_files:
                        data_files[year_month] = []
                        for excel_file in excel_files:
                            data_files[year_month].append({
                                'name': excel_file.name,
                                'path': str(excel_file),
                                'size': excel_file.stat().st_size,
                                'modified': datetime.fromtimestamp(excel_file.stat().st_mtime)
                            })

            return data_files

        except Exception as e:
            print(f"❌ Lỗi khi lấy file của {employee_name}: {e}")
            return {}

    def load_employee_data(self, employee_name, year_month=None):
        """Tải dữ liệu của một nhân viên cụ thể"""
        try:
            employee_data = {
                'name': employee_name,
                'work_logs': {},
                'sap_data': {},
                'metrics': {},
                'available_months': []
            }

            # Lấy tất cả thư mục năm_tháng
            employee_path = self.base_path / employee_name

            if not employee_path.exists():
                return employee_data

            month_dirs = []
            for item in employee_path.iterdir():
                if item.is_dir() and '_' in item.name:  # Định dạng YYYY_MM
                    month_dirs.append(item)

            # Sắp xếp theo thời gian mới nhất
            month_dirs.sort(reverse=True)
            employee_data['available_months'] = [d.name for d in month_dirs]

            # Nếu chỉ định year_month cụ thể
            if year_month:
                target_dirs = [d for d in month_dirs if d.name == year_month]
            else:
                # Lấy tháng mới nhất
                target_dirs = month_dirs[:1] if month_dirs else []

            for month_dir in target_dirs:
                month_key = month_dir.name

                # Tải work logs
                work_log_path = month_dir / f"work_logs_{employee_name}_{month_key}.xlsx"
                if work_log_path.exists():
                    try:
                        work_logs = self._load_work_logs(str(work_log_path))
                        employee_data['work_logs'][month_key] = work_logs
                    except Exception as e:
                        print(f"⚠️ Không đọc được work log {work_log_path}: {e}")

                # Tải SAP data
                sap_path = month_dir / "sap_data.xlsx"
                if sap_path.exists():
                    try:
                        sap_data = self._load_sap_data(str(sap_path))
                        employee_data['sap_data'][month_key] = sap_data
                    except Exception as e:
                        print(f"⚠️ Không đọc được SAP data {sap_path}: {e}")

                # Tính toán metrics
                if month_key in employee_data['work_logs'] or month_key in employee_data['sap_data']:
                    metrics = self._calculate_employee_metrics(
                        employee_data['work_logs'].get(month_key, {}),
                        employee_data['sap_data'].get(month_key, {})
                    )
                    employee_data['metrics'][month_key] = metrics

            return employee_data

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu {employee_name}: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _load_work_logs(self, file_path):
        """Tải và xử lý work logs"""
        try:
            # Đọc tất cả sheets
            excel_file = pd.ExcelFile(file_path)
            work_logs = {}

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)

                    # Xử lý dữ liệu dựa trên sheet name
                    if 'fraud' in sheet_name.lower():
                        # Xử lý fraud events
                        if not df.empty:
                            # Chuẩn hóa cột
                            df = self._standardize_fraud_data(df)
                        work_logs['fraud_events'] = df

                    elif 'mouse' in sheet_name.lower():
                        # Xử lý mouse data
                        if not df.empty:
                            df = self._standardize_mouse_data(df)
                        work_logs['mouse_data'] = df

                    elif 'browser' in sheet_name.lower() or 'session' in sheet_name.lower():
                        # Xử lý browser/session data
                        if not df.empty:
                            df = self._standardize_browser_data(df)
                        work_logs['browser_sessions'] = df

                    elif 'time' in sheet_name.lower():
                        # Xử lý time tracking
                        if not df.empty:
                            df = self._standardize_time_data(df)
                        work_logs['time_tracking'] = df

                    else:
                        # Sheet khác
                        work_logs[sheet_name.lower().replace(' ', '_')] = df

                except Exception as e:
                    print(f"⚠️ Lỗi đọc sheet {sheet_name}: {e}")

            return work_logs

        except Exception as e:
            print(f"❌ Lỗi đọc work logs {file_path}: {e}")
            return {}

    def _load_sap_data(self, file_path):
        """Tải và xử lý SAP data"""
        try:
            sap_data = {}
            excel_file = pd.ExcelFile(file_path)

            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)

                    if sheet_name.lower() == 'orders':
                        # Xử lý orders data
                        if not df.empty:
                            df = self._standardize_order_data(df)
                        sap_data['orders'] = df

                    elif 'performance' in sheet_name.lower():
                        # Xử lý performance data
                        if not df.empty:
                            df = self._standardize_performance_data(df)
                        sap_data['performance'] = df

                    elif 'customer' in sheet_name.lower():
                        # Customer data
                        sap_data['customers'] = df

                    else:
                        sap_data[sheet_name.lower().replace(' ', '_')] = df

                except Exception as e:
                    print(f"⚠️ Lỗi đọc sheet {sheet_name}: {e}")

            return sap_data

        except Exception as e:
            print(f"❌ Lỗi đọc SAP data {file_path}: {e}")
            return {}

    def _standardize_fraud_data(self, df):
        """Chuẩn hóa fraud data"""
        # Đổi tên cột
        column_mapping = {
            'Timestamp': 'timestamp',
            'Date': 'date',
            'Time': 'time',
            'Event Type': 'event_type',
            'Severity': 'severity',
            'Description': 'description',
            'Action Taken': 'action_taken'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        # Chuyển đổi timestamp nếu có
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        elif 'date' in df.columns and 'time' in df.columns:
            df['timestamp'] = pd.to_datetime(df['date'].astype(str) + ' ' + df['time'].astype(str), errors='coerce')

        return df

    def _standardize_mouse_data(self, df):
        """Chuẩn hóa mouse data"""
        column_mapping = {
            'Timestamp': 'timestamp',
            'Mouse Clicks': 'clicks',
            'Mouse Movements': 'movements',
            'Inactivity Periods': 'inactivity',
            'Active Time': 'active_time',
            'Session ID': 'session_id'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')

        return df

    def _standardize_browser_data(self, df):
        """Chuẩn hóa browser data"""
        column_mapping = {
            'Start Time': 'start_time',
            'End Time': 'end_time',
            'Duration': 'duration',
            'Browser': 'browser',
            'URL': 'url',
            'Tab Count': 'tab_count'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        for col in ['start_time', 'end_time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        return df

    def _standardize_time_data(self, df):
        """Chuẩn hóa time tracking data"""
        column_mapping = {
            'Date': 'date',
            'Start Time': 'start_time',
            'End Time': 'end_time',
            'Total Hours': 'total_hours',
            'Break Time': 'break_time',
            'Productive Time': 'productive_time'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

        return df

    def _standardize_order_data(self, df):
        """Chuẩn hóa order data"""
        column_mapping = {
            'Order ID': 'order_id',
            'Order Date': 'order_date',
            'Customer': 'customer',
            'Product': 'product',
            'Quantity': 'quantity',
            'Revenue': 'revenue',
            'Profit': 'profit',
            'Status': 'status',
            'Employee': 'employee'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        if 'order_date' in df.columns:
            df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')

        return df

    def _standardize_performance_data(self, df):
        """Chuẩn hóa performance data"""
        column_mapping = {
            'Date': 'date',
            'Efficiency': 'efficiency',
            'Accuracy': 'accuracy',
            'Completion Rate': 'completion_rate',
            'Quality Score': 'quality_score'
        }

        df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')

        return df

    def _calculate_employee_metrics(self, work_logs, sap_data):
        """Tính toán metrics cho một nhân viên"""
        metrics = {
            'overall_score': 0,
            'efficiency': 0,
            'productivity': 0,
            'quality': 0,
            'compliance': 0,
            'revenue_generated': 0,
            'fraud_count': 0,
            'working_hours': 0,
            'order_completion_rate': 0
        }

        try:
            # Tính từ work logs
            if work_logs:
                # Đếm fraud events
                if 'fraud_events' in work_logs and not work_logs['fraud_events'].empty:
                    metrics['fraud_count'] = len(work_logs['fraud_events'])

                # Tính working hours từ browser sessions
                if 'browser_sessions' in work_logs and not work_logs['browser_sessions'].empty:
                    df = work_logs['browser_sessions']
                    if 'duration' in df.columns:
                        # Chuyển duration sang giờ
                        def parse_duration(duration):
                            if pd.isna(duration):
                                return 0
                            if isinstance(duration, str):
                                if ':' in duration:
                                    # Format HH:MM:SS
                                    parts = duration.split(':')
                                    if len(parts) == 3:
                                        return int(parts[0]) + int(parts[1]) / 60 + int(parts[2]) / 3600
                                    elif len(parts) == 2:
                                        return int(parts[0]) + int(parts[1]) / 60
                                else:
                                    try:
                                        return float(duration) / 3600  # Giả sử là seconds
                                    except:
                                        return 0
                            return float(duration) / 3600  # Giả sử là seconds

                        df['hours'] = df['duration'].apply(parse_duration)
                        metrics['working_hours'] = df['hours'].sum()

            # Tính từ SAP data
            if sap_data:
                # Tính revenue và profit
                if 'orders' in sap_data and not sap_data['orders'].empty:
                    orders_df = sap_data['orders']

                    if 'revenue' in orders_df.columns:
                        metrics['revenue_generated'] = orders_df['revenue'].sum()

                    if 'profit' in orders_df.columns:
                        metrics['profit_generated'] = orders_df['profit'].sum()

                    # Tính completion rate
                    if 'status' in orders_df.columns:
                        total_orders = len(orders_df)
                        completed_orders = len(
                            orders_df[orders_df['status'].str.lower().str.contains('complete|done|finished', na=False)])
                        metrics['order_completion_rate'] = (
                                    completed_orders / total_orders * 100) if total_orders > 0 else 0

            # Tính overall score (công thức tùy chỉnh)
            # Trọng số: completion_rate 40%, compliance 30%, productivity 30%
            completion_score = min(metrics['order_completion_rate'] / 100, 1) * 100
            compliance_score = max(100 - (metrics['fraud_count'] * 10), 0)  # Mỗi fraud event trừ 10 điểm
            productivity_score = min(metrics['working_hours'] / 40, 1) * 100  # So với 40h/tuần

            metrics['overall_score'] = (
                    completion_score * 0.4 +
                    compliance_score * 0.3 +
                    productivity_score * 0.3
            )

            metrics['efficiency'] = completion_score
            metrics['compliance'] = compliance_score
            metrics['productivity'] = productivity_score

            # Quality score dựa trên completion rate và fraud count
            metrics['quality'] = completion_score * 0.7 + compliance_score * 0.3

        except Exception as e:
            print(f"⚠️ Lỗi tính metrics: {e}")

        return metrics

    def get_aggregate_data(self, year_month=None):
        """Lấy dữ liệu tổng hợp của tất cả nhân viên"""
        try:
            employees = self.get_all_employees()

            if not employees:
                return {}

            aggregate_data = {
                'total_employees': len(employees),
                'employees_with_data': 0,
                'total_revenue': 0,
                'total_profit': 0,
                'total_fraud': 0,
                'total_working_hours': 0,
                'average_completion_rate': 0,
                'average_overall_score': 0,
                'employee_details': [],
                'monthly_trends': {},
                'department_stats': {},
                'top_performers': [],
                'need_improvement': []
            }

            completion_rates = []
            overall_scores = []

            for emp_info in employees:
                if not emp_info['has_data']:
                    continue

                # Tải dữ liệu nhân viên
                emp_data = self.load_employee_data(emp_info['name'], year_month)

                if not emp_data.get('metrics'):
                    continue

                aggregate_data['employees_with_data'] += 1

                # Lấy metrics từ tháng mới nhất
                latest_month = list(emp_data['metrics'].keys())[0] if emp_data['metrics'] else None
                if latest_month:
                    metrics = emp_data['metrics'][latest_month]

                    # Tổng hợp
                    aggregate_data['total_revenue'] += metrics.get('revenue_generated', 0)
                    aggregate_data['total_profit'] += metrics.get('profit_generated', 0)
                    aggregate_data['total_fraud'] += metrics.get('fraud_count', 0)
                    aggregate_data['total_working_hours'] += metrics.get('working_hours', 0)

                    completion_rate = metrics.get('order_completion_rate', 0)
                    completion_rates.append(completion_rate)

                    overall_score = metrics.get('overall_score', 0)
                    overall_scores.append(overall_score)

                    # Thêm chi tiết nhân viên
                    emp_detail = {
                        'name': emp_info['name'],
                        'revenue': metrics.get('revenue_generated', 0),
                        'profit': metrics.get('profit_generated', 0),
                        'fraud_count': metrics.get('fraud_count', 0),
                        'working_hours': metrics.get('working_hours', 0),
                        'completion_rate': completion_rate,
                        'overall_score': overall_score,
                        'efficiency': metrics.get('efficiency', 0),
                        'productivity': metrics.get('productivity', 0),
                        'quality': metrics.get('quality', 0),
                        'compliance': metrics.get('compliance', 0)
                    }

                    aggregate_data['employee_details'].append(emp_detail)

            # Tính trung bình
            if completion_rates:
                aggregate_data['average_completion_rate'] = np.mean(completion_rates)

            if overall_scores:
                aggregate_data['average_overall_score'] = np.mean(overall_scores)

            # Phân loại nhân viên
            if aggregate_data['employee_details']:
                # Sắp xếp theo overall score
                sorted_employees = sorted(aggregate_data['employee_details'],
                                          key=lambda x: x['overall_score'], reverse=True)

                aggregate_data['top_performers'] = sorted_employees[:3]  # Top 3
                aggregate_data['need_improvement'] = sorted_employees[-3:]  # Bottom 3

            return aggregate_data

        except Exception as e:
            print(f"❌ Lỗi lấy dữ liệu tổng hợp: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_filtered_data(self, employee_name=None, year=None, month=None, week=None):
        """Lấy dữ liệu đã filter theo tiêu chí"""
        try:
            result = {}

            if employee_name:
                # Dữ liệu cho một nhân viên cụ thể
                emp_data = self.load_employee_data(employee_name)

                if not emp_data:
                    return {}

                # Filter theo tháng
                if year and month:
                    year_month = f"{year}_{month:02d}"
                    if year_month in emp_data['metrics']:
                        result['employee'] = emp_data
                        result['filtered_month'] = year_month
                else:
                    # Lấy tháng mới nhất
                    latest_month = list(emp_data['metrics'].keys())[0] if emp_data['metrics'] else None
                    result['employee'] = emp_data
                    result['filtered_month'] = latest_month

                # Filter theo tuần (nếu có dữ liệu chi tiết)
                if week and 'work_logs' in emp_data:
                    # Cần xử lý thêm dựa trên timestamp trong work_logs
                    pass

            else:
                # Dữ liệu tổng hợp
                if year and month:
                    year_month = f"{year}_{month:02d}"
                else:
                    year_month = datetime.now().strftime("%Y_%m")

                result = self.get_aggregate_data(year_month)

            return result

        except Exception as e:
            print(f"❌ Lỗi filter data: {e}")
            return {}

    def get_time_periods(self):
        """Lấy tất cả các khoảng thời gian có dữ liệu"""
        periods = {
            'years': set(),
            'months': [],
            'weeks': []
        }

        try:
            employees = self.get_all_employees()

            for emp in employees:
                if emp['data_files']:
                    for month in emp['data_files'].keys():
                        if '_' in month:
                            year, month_num = month.split('_')
                            periods['years'].add(year)
                            periods['months'].append({
                                'year': year,
                                'month': month_num,
                                'display': f"{year}-{month_num}"
                            })

            periods['years'] = sorted(list(periods['years']), reverse=True)
            periods['months'] = sorted(periods['months'],
                                       key=lambda x: (x['year'], x['month']),
                                       reverse=True)

            # Tạo danh sách tuần (giả định)
            current_date = datetime.now()
            for i in range(1, 5):
                week_start = current_date - timedelta(days=current_date.weekday() + (i - 1) * 7)
                week_end = week_start + timedelta(days=6)
                periods['weeks'].append({
                    'week': i,
                    'start': week_start.strftime("%Y-%m-%d"),
                    'end': week_end.strftime("%Y-%m-%d"),
                    'display': f"Tuần {i} ({week_start.strftime('%d/%m')} - {week_end.strftime('%d/%m')})"
                })

            return periods

        except Exception as e:
            print(f"❌ Lỗi lấy periods: {e}")
            return periods

    def export_to_excel(self, data, filepath):
        """Xuất dữ liệu ra Excel"""
        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Xuất employee details
                if 'employee_details' in data:
                    df_details = pd.DataFrame(data['employee_details'])
                    df_details.to_excel(writer, sheet_name='Employee_Details', index=False)

                # Xuất summary
                summary_data = {
                    'Metric': ['Total Employees', 'Employees with Data', 'Total Revenue',
                               'Total Profit', 'Total Fraud Events', 'Average Completion Rate',
                               'Average Overall Score'],
                    'Value': [data.get('total_employees', 0), data.get('employees_with_data', 0),
                              data.get('total_revenue', 0), data.get('total_profit', 0),
                              data.get('total_fraud', 0), data.get('average_completion_rate', 0),
                              data.get('average_overall_score', 0)]
                }
                df_summary = pd.DataFrame(summary_data)
                df_summary.to_excel(writer, sheet_name='Summary', index=False)

            print(f"✅ Đã xuất dữ liệu ra {filepath}")
            return True

        except Exception as e:
            print(f"❌ Lỗi xuất Excel: {e}")
            return False

    # Thêm phương thức này vào class DataManager

    def get_filtered_employees(self, year=None, month=None):
        """Lấy danh sách nhân viên đã lọc theo năm/tháng"""
        try:
            employees = self.get_all_employees()

            if not employees:
                return []

            filtered_employees = []

            for emp in employees:
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
                        data_year, data_month_num = data_month.split('_')

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
                # Nếu không có filter, vẫn hiển thị nhân viên có dữ liệu
                elif year is None and month is None:
                    filtered_employees.append(emp)

            return filtered_employees

        except Exception as e:
            print(f"❌ Lỗi lọc nhân viên: {e}")
            return []


# Singleton instance
_data_manager = None


def get_data_manager():
    """Lấy instance singleton của DataManager"""
    global _data_manager
    if _data_manager is None:
        _data_manager = DataManager()
    return _data_manager