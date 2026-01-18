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
        DEFAULT_EMPLOYEE_NAME = "Giang_MG"


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
                    # Load work log
                    work_log_path = month_path / f"work_logs_{self.employee_name}_{month_str}.xlsx"
                    if work_log_path.exists():
                        try:
                            df = pd.read_excel(work_log_path, sheet_name='Fraud_Events')
                            df['Month'] = m
                            df['Year'] = year_int

                            if 'Fraud_Events' not in collector['work_log']:
                                collector['work_log']['Fraud_Events'] = []
                            collector['work_log']['Fraud_Events'].append(df)
                            print(f"   ✅ Read work log month {m}: {len(df)} rows")
                        except Exception as e:
                            print(f"⚠️ Error reading work log month {m}: {e}")

                    # Load SAP data
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