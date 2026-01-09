# data_processor.py - Xử lý dữ liệu từ work log và SAP
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import random


class DataProcessor:
    """Xử lý dữ liệu từ nhiều nguồn cho AI phân tích và Dashboard"""

    def __init__(self, employee_name):
        self.employee_name = employee_name
        self.work_log_data = None
        self.sap_data = None
        self.metrics = None
        self.year_data = None  # Dữ liệu cả năm
        print(f"🚀 Khởi tạo DataProcessor cho: {employee_name}")

    def load_all_data(self):
        """Tải tất cả dữ liệu (cả năm)"""
        try:
            print(f"📂 Đang tải dữ liệu cho {self.employee_name}...")

            from config import Config

            # Tải dữ liệu cả năm
            self.year_data = self.load_year_data()

            # Tải dữ liệu tháng hiện tại cho AI
            data_paths = Config.get_employee_data_path(self.employee_name)

            print(f"🔍 Đường dẫn work log: {data_paths['work_log']}")
            print(f"🔍 Đường dẫn SAP: {data_paths['sap_data']}")

            # Tải work log
            print("📊 Đang tải work log...")
            self.work_log_data = self.load_work_log(data_paths['work_log'])
            print(f"✅ Work log loaded")

            # Tải SAP data
            print("📊 Đang tải SAP data...")
            self.sap_data = self.load_sap_data(data_paths['sap_data'])
            print(f"✅ SAP data loaded")

            # Tính metrics
            print("📈 Đang tính metrics...")
            self.calculate_metrics()
            print(f"✅ Metrics calculated")

            return True

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_year_data(self):
        """Tải dữ liệu cả năm từ tất cả các thư mục tháng"""
        try:
            from config import Config
            import pandas as pd
            from pathlib import Path

            current_year = datetime.now().year
            year_data = {
                'work_log': {'sheets': {}},
                'sap_data': {'sheets': {}}
            }

            print(f"📅 Đang tải dữ liệu cả năm {current_year}...")

            # Tải dữ liệu từ tất cả các tháng (1-12)
            for month in range(1, 13):
                month_str = f"{current_year}_{month:02d}"
                base_path = Path(f"{Config.BASE_DATA_PATH}/{self.employee_name}/{month_str}")

                print(f"   📁 Kiểm tra tháng {month}: {base_path}")

                if base_path.exists():
                    # Tải work log của tháng
                    work_log_path = base_path / f"work_logs_{self.employee_name}_{month_str}.xlsx"
                    if work_log_path.exists():
                        try:
                            excel_file = pd.ExcelFile(work_log_path)
                            for sheet_name in excel_file.sheet_names:
                                df = pd.read_excel(work_log_path, sheet_name=sheet_name)
                                df['Month'] = month  # Thêm cột tháng

                                if sheet_name not in year_data['work_log']['sheets']:
                                    year_data['work_log']['sheets'][sheet_name] = []
                                year_data['work_log']['sheets'][sheet_name].append(df)

                            print(f"      ✅ Đã tải work log tháng {month}: {len(df)} dòng")
                        except Exception as e:
                            print(f"      ⚠️ Lỗi đọc work log tháng {month}: {e}")
                    else:
                        print(f"      ⚠️ Không tìm thấy work log tháng {month}")

                    # Tải SAP data của tháng
                    sap_path = base_path / "sap_data.xlsx"
                    if sap_path.exists():
                        try:
                            excel_file = pd.ExcelFile(sap_path)
                            for sheet_name in excel_file.sheet_names:
                                df = pd.read_excel(sap_path, sheet_name=sheet_name)
                                df['Month'] = month  # Thêm cột tháng

                                if sheet_name not in year_data['sap_data']['sheets']:
                                    year_data['sap_data']['sheets'][sheet_name] = []
                                year_data['sap_data']['sheets'][sheet_name].append(df)

                            print(f"      ✅ Đã tải SAP data tháng {month}: {len(df)} dòng")
                        except Exception as e:
                            print(f"      ⚠️ Lỗi đọc SAP data tháng {month}: {e}")
                    else:
                        print(f"      ⚠️ Không tìm thấy SAP data tháng {month}")
                else:
                    print(f"   ⚠️ Thư mục tháng {month} không tồn tại: {base_path}")

            # Gộp dữ liệu từ tất cả các tháng
            print("🔄 Đang gộp dữ liệu từ các tháng...")
            for data_type in ['work_log', 'sap_data']:
                for sheet_name, sheet_list in year_data[data_type]['sheets'].items():
                    if sheet_list:
                        year_data[data_type]['sheets'][sheet_name] = pd.concat(sheet_list, ignore_index=True)
                        print(
                            f"   📊 Gộp {data_type}.{sheet_name}: {len(year_data[data_type]['sheets'][sheet_name])} dòng")
                    else:
                        year_data[data_type]['sheets'][sheet_name] = pd.DataFrame()

            # Tính toán tổng số dữ liệu
            total_orders = len(year_data['sap_data'].get('sheets', {}).get('Orders', pd.DataFrame()))
            total_fraud = len(year_data['work_log'].get('sheets', {}).get('Fraud_Events', pd.DataFrame()))

            print(f"✅ Đã tải dữ liệu cả năm: {total_orders} đơn hàng, {total_fraud} sự kiện gian lận")
            return year_data

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu cả năm: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_dashboard_data(self):
        """Lấy dữ liệu cho dashboard"""
        return self.year_data

    def load_work_log(self, file_path):
        """Tải toàn bộ dữ liệu work log"""
        try:
            file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
            print(f"📁 Work log path: {file_path}")

            if not file_path.exists():
                print(f"⚠️ Work log file không tồn tại: {file_path}")
                return self._get_default_work_log()

            # Đọc tất cả sheet
            excel_file = pd.ExcelFile(file_path)
            print(f"📄 Sheets trong file: {excel_file.sheet_names}")

            data = {
                'file_found': True,
                'sheets': {}
            }

            # Đọc từng sheet
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    data['sheets'][sheet_name] = {
                        'row_count': len(df),
                        'columns': df.columns.tolist(),
                        'data': df.to_dict('records')  # Toàn bộ dữ liệu
                    }
                    print(f"📊 {sheet_name}: {len(df)} rows, {len(df.columns)} columns")

                    # Lấy mẫu dữ liệu
                    if len(df) > 0:
                        print(f"   Sample: {df.iloc[0].to_dict() if len(df) > 0 else 'Empty'}")
                except Exception as e:
                    print(f"⚠️ Lỗi đọc sheet {sheet_name}: {e}")
                    data['sheets'][sheet_name] = {'error': str(e)}

            # Tính toán thống kê từ Fraud_Events
            fraud_events = data['sheets'].get('Fraud_Events', {}).get('data', [])
            fraud_count = 0
            critical_count = 0
            warning_count = 0

            for event in fraud_events:
                if isinstance(event, dict):
                    if event.get('IsFraud') == 1:
                        fraud_count += 1
                    severity = event.get('Severity', '')
                    if severity == 'CRITICAL':
                        critical_count += 1
                    elif severity == 'WARNING':
                        warning_count += 1

            # Tính toán thống kê từ Mouse_Details
            mouse_details = data['sheets'].get('Mouse_Details', {}).get('data', [])
            total_work_seconds = 0
            mouse_anomaly_count = 0

            for mouse in mouse_details:
                if isinstance(mouse, dict):
                    total_work_seconds += mouse.get('DurationSeconds', 0)
                    if mouse.get('AnomalyScore', 0) > 0.5:
                        mouse_anomaly_count += 1

            total_work_hours = round(total_work_seconds / 3600, 1) if total_work_seconds > 0 else 0
            violation_score = (critical_count * 3) + (warning_count * 1)

            data['summary'] = {
                'fraud_count': int(fraud_count),
                'critical_count': int(critical_count),
                'warning_count': int(warning_count),
                'violation_score': int(violation_score),
                'total_work_hours': total_work_hours,
                'total_sessions': len(mouse_details),
                'mouse_anomaly_count': int(mouse_anomaly_count)
            }

            print(f"📋 Work log summary: {data['summary']}")
            return data

        except Exception as e:
            print(f"❌ Lỗi đọc work log: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_work_log()

    def _get_default_work_log(self):
        """Trả về work log mặc định"""
        return {
            'summary': {
                'fraud_count': 0,
                'critical_count': 0,
                'warning_count': 0,
                'violation_score': 0,
                'total_work_hours': 8.0,
                'total_sessions': 10,
                'mouse_anomaly_count': 0
            },
            'sheets': {},
            'file_found': False
        }

    def load_sap_data(self, file_path):
        """Tải toàn bộ dữ liệu SAP"""
        try:
            file_path = Path(file_path) if not isinstance(file_path, Path) else file_path
            print(f"📁 SAP path: {file_path}")

            if not file_path.exists():
                print(f"⚠️ SAP file không tồn tại: {file_path}")
                return self._get_default_sap_data()

            excel_file = pd.ExcelFile(file_path)
            print(f"📄 Sheets trong SAP file: {excel_file.sheet_names}")

            data = {
                'file_found': True,
                'sheets': {}
            }

            # Đọc từng sheet
            for sheet_name in excel_file.sheet_names:
                try:
                    df = pd.read_excel(file_path, sheet_name=sheet_name)
                    data['sheets'][sheet_name] = {
                        'row_count': len(df),
                        'columns': df.columns.tolist(),
                        'data': df.to_dict('records')  # Toàn bộ dữ liệu
                    }
                    print(f"📊 {sheet_name}: {len(df)} rows, {len(df.columns)} columns")

                    # Lấy mẫu dữ liệu
                    if len(df) > 0:
                        print(f"   Sample: {list(df.columns)[:5]}")
                except Exception as e:
                    print(f"⚠️ Lỗi đọc sheet {sheet_name}: {e}")
                    data['sheets'][sheet_name] = {'error': str(e)}

            # Tính toán thống kê từ Orders sheet
            orders_data = data['sheets'].get('Orders', {}).get('data', [])

            total_revenue = 0
            total_profit = 0
            total_orders = len(orders_data)
            completed_orders = 0
            total_edits = 0
            processing_times = []

            # Phân tích theo vùng và loại sản phẩm
            region_stats = {}
            product_stats = {}
            pending_orders = []
            completed_orders_list = []

            for order in orders_data:
                if isinstance(order, dict):
                    # Tính tổng doanh thu và lợi nhuận
                    total_revenue += order.get('Revenue', 0)
                    total_profit += order.get('Profit', 0)

                    # Đếm đơn hoàn thành
                    if order.get('Status') == 'Completed':
                        completed_orders += 1
                        completed_orders_list.append(order)

                    # Lấy đơn chưa xử lý xong
                    if order.get('Status') in ['Pending', 'Processing', 'Review']:
                        pending_orders.append(order)

                    # Số lần chỉnh sửa
                    total_edits += order.get('Edit_Count', 0)

                    # Thời gian xử lý
                    processing_times.append(order.get('Processing_Time', 0))

                    # Thống kê theo vùng
                    region = order.get('Region', 'Unknown')
                    region_stats[region] = region_stats.get(region, 0) + 1

                    # Thống kê theo loại sản phẩm
                    product_type = order.get('Product_Type', 'Unknown')
                    product_stats[product_type] = product_stats.get(product_type, 0) + 1

            completion_rate = round((completed_orders / total_orders) * 100, 1) if total_orders > 0 else 0
            avg_processing_time = round(sum(processing_times) / len(processing_times), 1) if processing_times else 0
            slow_orders = len([t for t in processing_times if t > 120])

            # Lấy dữ liệu từ Daily_Performance sheet
            daily_performance_data = data['sheets'].get('Daily_Performance', {}).get('data', [])
            daily_stats = {}

            for daily in daily_performance_data:
                if isinstance(daily, dict):
                    date = daily.get('Date')
                    if date:
                        daily_stats[date] = {
                            'efficiency_score': daily.get('Efficiency_Score'),
                            'tasks_completed': daily.get('Tasks_Completed'),
                            'total_revenue': daily.get('Total_Revenue'),
                            'total_profit': daily.get('Total_Profit')
                        }

            data['summary'] = {
                'total_revenue': float(total_revenue),
                'total_profit': float(total_profit),
                'total_orders': int(total_orders),
                'completed_orders': int(completed_orders),
                'completion_rate': float(completion_rate),
                'total_edits': int(total_edits),
                'avg_edits_per_order': round(total_edits / total_orders, 1) if total_orders > 0 else 0,
                'avg_processing_time': float(avg_processing_time),
                'slow_orders': int(slow_orders),
                'revenue_per_order': float(total_revenue / total_orders) if total_orders > 0 else 0,
                'profit_margin': float((total_profit / total_revenue * 100) if total_revenue > 0 else 0),

                # Thống kê chi tiết
                'region_stats': region_stats,
                'product_stats': product_stats,
                'pending_orders_count': len(pending_orders),
                'pending_orders': pending_orders[:10],  # Lấy 10 đơn đầu
                'completed_orders_list': completed_orders_list[:10],  # Lấy 10 đơn đầu
                'all_orders': orders_data[:50],  # Lấy 50 đơn đầu để AI phân tích

                # Dữ liệu Daily_Performance
                'daily_performance_stats': daily_stats,
                'total_daily_records': len(daily_performance_data)
            }

            print(f"💰 Total revenue: {total_revenue:,.0f}")
            print(f"💰 Total profit: {total_profit:,.0f}")
            print(f"📦 Total orders: {total_orders}")
            print(f"✅ Completed orders: {completed_orders}")
            print(f"📍 Region stats: {region_stats}")
            print(f"📊 Product stats: {product_stats}")
            print(f"⏳ Pending orders: {len(pending_orders)}")
            print(f"📅 Daily performance records: {len(daily_performance_data)}")

            return data

        except Exception as e:
            print(f"❌ Lỗi đọc SAP data: {e}")
            import traceback
            traceback.print_exc()
            return self._get_default_sap_data()

    def _get_default_sap_data(self):
        """Trả về SAP data mặc định"""
        return {
            'summary': {
                'total_revenue': 0,
                'total_profit': 0,
                'total_orders': 0,
                'completed_orders': 0,
                'completion_rate': 0,
                'total_edits': 0,
                'avg_edits_per_order': 0,
                'avg_processing_time': 0,
                'slow_orders': 0,
                'revenue_per_order': 0,
                'profit_margin': 0,
                'region_stats': {},
                'product_stats': {},
                'pending_orders_count': 0,
                'pending_orders': [],
                'completed_orders_list': [],
                'all_orders': [],
                'daily_performance_stats': {},
                'total_daily_records': 0
            },
            'sheets': {},
            'file_found': False
        }

    def calculate_metrics(self):
        """Tính các chỉ số hiệu suất tổng hợp từ dữ liệu thực tế"""
        try:
            wl = self.work_log_data.get('summary', {}) if self.work_log_data else {}
            sap = self.sap_data.get('summary', {}) if self.sap_data else {}

            print("📈 Đang tính metrics từ dữ liệu thực tế...")

            # Lấy dữ liệu thực tế
            total_orders = sap.get('total_orders', 0)
            completed_orders = sap.get('completed_orders', 0)
            completion_rate = sap.get('completion_rate', 0)
            total_work_hours = wl.get('total_work_hours', 0)
            fraud_count = wl.get('fraud_count', 0)
            critical_count = wl.get('critical_count', 0)
            warning_count = wl.get('warning_count', 0)
            total_revenue = sap.get('total_revenue', 0)
            total_profit = sap.get('total_profit', 0)
            pending_orders = sap.get('pending_orders_count', 0)
            avg_processing_time = sap.get('avg_processing_time', 0)

            # 1. Tính hiệu quả làm việc dựa trên số đơn hàng đã xử lý
            # Giả sử: 20 đơn/ngày = 100 điểm
            efficiency_score = 0
            if total_work_hours > 0:
                orders_per_hour = completed_orders / total_work_hours if total_work_hours > 0 else 0
                # Chuẩn: 2.5 đơn/giờ = 100 điểm (8 giờ làm việc → 20 đơn/ngày)
                efficiency_score = min(100, orders_per_hour * 40)  # 2.5 đơn/giờ = 100 điểm

            # 2. Tính chất lượng dựa trên tỷ lệ hoàn thành và lợi nhuận
            quality_score = 0
            if completion_rate > 0:
                # Tỷ lệ hoàn thành chiếm 70%, lợi nhuận chiếm 30%
                profit_margin = sap.get('profit_margin', 0)
                quality_score = (completion_rate * 0.7) + (min(profit_margin, 30) * 3.33 * 0.3)
                quality_score = min(100, quality_score)

            # 3. Tính tuân thủ dựa trên số sự kiện gian lận và cảnh báo
            compliance_score = 100
            # Trừ điểm cho các vi phạm
            compliance_score -= fraud_count * 5  # Mỗi gian lận trừ 5 điểm
            compliance_score -= critical_count * 3  # Mỗi cảnh báo nghiêm trọng trừ 3 điểm
            compliance_score -= warning_count * 1  # Mỗi cảnh báo nhẹ trừ 1 điểm
            compliance_score = max(0, compliance_score)

            # 4. Tính năng suất dựa trên doanh thu và số đơn hàng
            productivity_score = 0
            if total_orders > 0:
                # Doanh thu/đơn hàng
                revenue_per_order = total_revenue / total_orders if total_orders > 0 else 0
                # Lợi nhuận/đơn hàng
                profit_per_order = total_profit / total_orders if total_orders > 0 else 0

                # Giả sử: Doanh thu 10M/đơn = 100 điểm, Lợi nhuận 2M/đơn = 100 điểm
                revenue_score = min(50, revenue_per_order / 200000)  # 10M = 50 điểm
                profit_score = min(50, profit_per_order / 40000)  # 2M = 50 điểm
                productivity_score = revenue_score + profit_score

            # 5. Điểm tổng thể là trung bình có trọng số
            # Hiệu quả: 25%, Chất lượng: 30%, Tuân thủ: 20%, Năng suất: 25%
            overall_score = (
                    efficiency_score * 0.25 +
                    quality_score * 0.30 +
                    compliance_score * 0.20 +
                    productivity_score * 0.25
            )

            # 6. Tính các chỉ số thực tế khác
            # Tỷ lệ hoàn thành đúng hạn
            on_time_delivery = 0
            if self.sap_data and self.sap_data.get('sheets', {}).get('Orders'):
                orders_df = pd.DataFrame(self.sap_data['sheets']['Orders'].get('data', []))
                if not orders_df.empty and 'Delivery_Status' in orders_df.columns:
                    on_time_count = len(orders_df[orders_df['Delivery_Status'] == 'On Time'])
                    on_time_delivery = (on_time_count / total_orders * 100) if total_orders > 0 else 0

            # Tỷ lệ lỗi
            error_rate = 0
            if total_orders > 0:
                total_errors = fraud_count + critical_count + warning_count
                error_rate = (total_errors / total_orders * 100)

            # Hiệu suất sử dụng thời gian
            time_efficiency = 0
            if total_work_hours > 0 and avg_processing_time > 0:
                # Giả sử: xử lý 1 đơn mất 30 phút là hiệu quả
                ideal_time_per_order = 0.5  # 0.5 giờ = 30 phút
                actual_time_per_order = avg_processing_time / 60 if avg_processing_time > 0 else 0  # phút -> giờ
                if actual_time_per_order > 0:
                    time_efficiency = min(100, (ideal_time_per_order / actual_time_per_order) * 100)

            self.metrics = {
                # Điểm đánh giá
                'efficiency': round(efficiency_score, 1),
                'quality': round(quality_score, 1),
                'compliance': round(compliance_score, 1),
                'productivity': round(productivity_score, 1),
                'overall': round(overall_score, 1),

                # Chỉ số thực tế
                'total_orders': total_orders,
                'completed_orders': completed_orders,
                'completion_rate': round(completion_rate, 1),
                'pending_orders': pending_orders,
                'total_work_hours': round(total_work_hours, 1),
                'fraud_count': fraud_count,
                'critical_count': critical_count,
                'warning_count': warning_count,
                'total_revenue': round(total_revenue, 0),
                'total_profit': round(total_profit, 0),
                'profit_margin': round(sap.get('profit_margin', 0), 1),
                'on_time_delivery': round(on_time_delivery, 1),
                'error_rate': round(error_rate, 1),
                'time_efficiency': round(time_efficiency, 1),
                'avg_processing_time': round(avg_processing_time, 1),
                'orders_per_hour': round(completed_orders / total_work_hours if total_work_hours > 0 else 0, 2),
                'revenue_per_order': round(total_revenue / total_orders if total_orders > 0 else 0, 0),
                'profit_per_order': round(total_profit / total_orders if total_orders > 0 else 0, 0),

                # Work intensity từ work log
                'work_intensity': wl.get('total_work_hours', 0),
                'mouse_anomaly_count': wl.get('mouse_anomaly_count', 0),
                'violation_score': wl.get('violation_score', 0),

                # Điểm từ daily performance
                'avg_daily_efficiency': self._calculate_avg_daily_efficiency()
            }

            print(f"✅ Metrics calculated from real data:")
            print(f"   📊 Orders: {total_orders} (Completed: {completed_orders}, Pending: {pending_orders})")
            print(f"   💰 Revenue: {total_revenue:,.0f}, Profit: {total_profit:,.0f}")
            print(f"   ⚠️ Fraud: {fraud_count}, Critical: {critical_count}, Warning: {warning_count}")
            print(
                f"   🎯 Scores - Eff: {efficiency_score:.1f}, Qual: {quality_score:.1f}, Comp: {compliance_score:.1f}, Prod: {productivity_score:.1f}, Overall: {overall_score:.1f}")

        except Exception as e:
            print(f"❌ Lỗi tính metrics: {e}")
            import traceback
            traceback.print_exc()
            # Sử dụng dữ liệu mặc định thực tế hơn
            self.metrics = {
                'efficiency': 0,
                'quality': 0,
                'compliance': 0,
                'productivity': 0,
                'overall': 0,
                'total_orders': 0,
                'completed_orders': 0,
                'completion_rate': 0,
                'pending_orders': 0,
                'total_work_hours': 0,
                'fraud_count': 0,
                'total_revenue': 0,
                'total_profit': 0,
                'profit_margin': 0,
                'on_time_delivery': 0,
                'error_rate': 0,
                'time_efficiency': 0,
                'avg_daily_efficiency': 0
            }
    def _calculate_avg_daily_efficiency(self):
        """Tính điểm hiệu suất trung bình từ Daily_Performance"""
        try:
            daily_stats = self.sap_data.get('summary', {}).get('daily_performance_stats', {}) if self.sap_data else {}
            if not daily_stats:
                return 0

            efficiency_scores = []
            for date, stats in daily_stats.items():
                efficiency = stats.get('efficiency_score')
                if efficiency and efficiency > 0:
                    efficiency_scores.append(efficiency)

            if efficiency_scores:
                return round(sum(efficiency_scores) / len(efficiency_scores), 1)
            return 0
        except:
            return 0

    def get_context_data(self):
        """Lấy dữ liệu context cho AI với toàn bộ dữ liệu"""
        context = {
            'work_log': {
                'summary': self.work_log_data.get('summary', {}) if self.work_log_data else {},
                'fraud_events': self.work_log_data.get('sheets', {}).get('Fraud_Events', {}).get('data',
                                                                                                 []) if self.work_log_data else [],
                'mouse_details': self.work_log_data.get('sheets', {}).get('Mouse_Details', {}).get('data',
                                                                                                   []) if self.work_log_data else [],
                'browser_sessions': self.work_log_data.get('sheets', {}).get('Browser_Sessions', {}).get('data',
                                                                                                         []) if self.work_log_data else [],
                'all_sheets': self.work_log_data.get('sheets', {}) if self.work_log_data else {},
                'file_found': self.work_log_data.get('file_found', False) if self.work_log_data else False
            },
            'sap_data': {
                'summary': self.sap_data.get('summary', {}) if self.sap_data else {},
                'all_orders': self.sap_data.get('summary', {}).get('all_orders', []) if self.sap_data else [],
                'pending_orders': self.sap_data.get('summary', {}).get('pending_orders', []) if self.sap_data else [],
                'completed_orders': self.sap_data.get('summary', {}).get('completed_orders_list',
                                                                         []) if self.sap_data else [],
                'region_stats': self.sap_data.get('summary', {}).get('region_stats', {}) if self.sap_data else {},
                'product_stats': self.sap_data.get('summary', {}).get('product_stats', {}) if self.sap_data else {},
                'daily_performance': self.sap_data.get('summary', {}).get('daily_performance_stats',
                                                                          {}) if self.sap_data else {},
                'orders_sheet': self.sap_data.get('sheets', {}).get('Orders', {}).get('data',
                                                                                      []) if self.sap_data else [],
                'daily_performance_sheet': self.sap_data.get('sheets', {}).get('Daily_Performance', {}).get('data',
                                                                                                            []) if self.sap_data else [],
                'all_sheets': self.sap_data.get('sheets', {}) if self.sap_data else {},
                'file_found': self.sap_data.get('file_found', False) if self.sap_data else False
            },
            'metrics': self.metrics if self.metrics else {},
            'employee_name': self.employee_name,
            'year_data': self.year_data  # Thêm dữ liệu cả năm
        }

        # Thêm thông tin chi tiết để AI phân tích
        context['analysis_ready'] = True
        context['data_timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return context

    def get_summary_data(self):
        """Lấy dữ liệu tóm tắt cho hiển thị"""
        return {
            'work_log': {
                'fraud_count': self.work_log_data.get('summary', {}).get('fraud_count', 0) if self.work_log_data else 0,
                'critical_count': self.work_log_data.get('summary', {}).get('critical_count',
                                                                            0) if self.work_log_data else 0,
                'warning_count': self.work_log_data.get('summary', {}).get('warning_count',
                                                                           0) if self.work_log_data else 0,
                'total_work_hours': self.work_log_data.get('summary', {}).get('total_work_hours',
                                                                              0) if self.work_log_data else 0,
                'violation_score': self.work_log_data.get('summary', {}).get('violation_score',
                                                                             0) if self.work_log_data else 0,
                'file_found': self.work_log_data.get('file_found', False) if self.work_log_data else False
            },
            'sap': {
                'total_revenue': self.sap_data.get('summary', {}).get('total_revenue', 0) if self.sap_data else 0,
                'total_profit': self.sap_data.get('summary', {}).get('total_profit', 0) if self.sap_data else 0,
                'total_orders': self.sap_data.get('summary', {}).get('total_orders', 0) if self.sap_data else 0,
                'completed_orders': self.sap_data.get('summary', {}).get('completed_orders', 0) if self.sap_data else 0,
                'completion_rate': self.sap_data.get('summary', {}).get('completion_rate', 0) if self.sap_data else 0,
                'avg_edits_per_order': self.sap_data.get('summary', {}).get('avg_edits_per_order',
                                                                            0) if self.sap_data else 0,
                'profit_margin': self.sap_data.get('summary', {}).get('profit_margin', 0) if self.sap_data else 0,
                'pending_orders': self.sap_data.get('summary', {}).get('pending_orders_count',
                                                                       0) if self.sap_data else 0,
                'avg_daily_efficiency': self.metrics.get('avg_daily_efficiency', 0) if self.metrics else 0,
                'file_found': self.sap_data.get('file_found', False) if self.sap_data else False
            },
            'metrics': self.metrics if self.metrics else {}
        }

    def get_all_data(self):
        """Lấy tất cả dữ liệu chi tiết"""
        return {
            'work_log': self.work_log_data,
            'sap_data': self.sap_data,
            'metrics': self.metrics if self.metrics else {},
            'year_data': self.year_data  # Thêm dữ liệu cả năm
        }

    def query_sap_data(self, query_type, filters=None):
        """Truy vấn dữ liệu SAP theo yêu cầu"""
        try:
            if not self.sap_data or 'summary' not in self.sap_data:
                return {"error": "Không có dữ liệu SAP"}

            all_orders = self.sap_data['summary'].get('all_orders', [])
            daily_performance = self.sap_data['summary'].get('daily_performance_stats', {})
            result = {
                'query_type': query_type,
                'total_orders': len(all_orders)
            }

            if query_type == 'pending_orders':
                result['orders'] = [order for order in all_orders
                                    if order.get('Status') in ['Pending', 'Processing', 'Review']]
                result['count'] = len(result['orders'])

            elif query_type == 'completed_orders':
                result['orders'] = [order for order in all_orders
                                    if order.get('Status') == 'Completed']
                result['count'] = len(result['orders'])

            elif query_type == 'region_stats':
                region_stats = {}
                for order in all_orders:
                    region = order.get('Region', 'Unknown')
                    if region not in region_stats:
                        region_stats[region] = {
                            'count': 0,
                            'revenue': 0,
                            'profit': 0,
                            'orders': []
                        }
                    region_stats[region]['count'] += 1
                    region_stats[region]['revenue'] += order.get('Revenue', 0)
                    region_stats[region]['profit'] += order.get('Profit', 0)
                    region_stats[region]['orders'].append({
                        'order_id': order.get('Order_ID'),
                        'revenue': order.get('Revenue', 0),
                        'status': order.get('Status')
                    })
                result['regions'] = region_stats

            elif query_type == 'product_stats':
                product_stats = {}
                for order in all_orders:
                    product = order.get('Product_Type', 'Unknown')
                    if product not in product_stats:
                        product_stats[product] = {
                            'count': 0,
                            'revenue': 0,
                            'profit': 0
                        }
                    product_stats[product]['count'] += 1
                    product_stats[product]['revenue'] += order.get('Revenue', 0)
                    product_stats[product]['profit'] += order.get('Profit', 0)
                result['products'] = product_stats

            elif query_type == 'recent_orders':
                # Sắp xếp theo ngày gần nhất
                sorted_orders = sorted(all_orders,
                                       key=lambda x: x.get('Order_Date', ''),
                                       reverse=True)
                result['orders'] = sorted_orders[:10]  # 10 đơn gần nhất
                result['count'] = len(result['orders'])

            elif query_type == 'top_revenue':
                sorted_orders = sorted(all_orders,
                                       key=lambda x: x.get('Revenue', 0),
                                       reverse=True)
                result['orders'] = sorted_orders[:10]  # 10 đơn doanh thu cao nhất
                result['count'] = len(result['orders'])

            elif query_type == 'low_profit':
                sorted_orders = sorted(all_orders,
                                       key=lambda x: x.get('Profit', 0))
                result['orders'] = sorted_orders[:10]  # 10 đơn lợi nhuận thấp nhất
                result['count'] = len(result['orders'])

            elif query_type == 'daily_performance':
                # Truy vấn dữ liệu hiệu suất hàng ngày
                result['daily_stats'] = daily_performance
                result['total_days'] = len(daily_performance)
                result['avg_efficiency'] = self._calculate_avg_daily_efficiency()

            elif query_type == 'performance_by_date':
                # Hiệu suất theo ngày cụ thể
                if filters and 'date' in filters:
                    date = filters['date']
                    result['date'] = date
                    result['stats'] = daily_performance.get(date, {})
                else:
                    result['all_days'] = list(daily_performance.keys())

            return result

        except Exception as e:
            return {"error": str(e)}

    def get_enhanced_context(self):
        """Lấy dữ liệu context nâng cao cho AI"""
        context = self.get_context_data()

        # Thêm các truy vấn phổ biến
        context['queries'] = {
            'pending_orders': self.query_sap_data('pending_orders'),
            'region_stats': self.query_sap_data('region_stats'),
            'product_stats': self.query_sap_data('product_stats'),
            'recent_orders': self.query_sap_data('recent_orders'),
            'daily_performance': self.query_sap_data('daily_performance')
        }

        return context

    def get_year_summary(self):
        """Lấy tổng quan dữ liệu cả năm - bổ sung mới"""
        try:
            if not self.year_data or 'summary' not in self.year_data:
                return None

            year_summary = self.year_data['summary']

            # Lấy dữ liệu từ các sheet để tính toán chi tiết hơn
            sap_sheets = self.year_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = self.year_data.get('work_log', {}).get('sheets', {})

            # Tính toán thêm các chỉ số chi tiết
            if 'Orders' in sap_sheets and not sap_sheets['Orders'].empty:
                orders_df = sap_sheets['Orders']

                # Đếm đơn hoàn thành
                completed_orders = 0
                if 'Status' in orders_df.columns:
                    completed_orders = len(orders_df[orders_df['Status'] == 'Completed'])

                # Tính doanh thu, lợi nhuận chi tiết hơn
                total_revenue = orders_df['Revenue'].sum() if 'Revenue' in orders_df.columns else year_summary.get(
                    'total_revenue', 0)
                total_profit = orders_df['Profit'].sum() if 'Profit' in orders_df.columns else year_summary.get(
                    'total_profit', 0)

                # Tính tỷ lệ hoàn thành
                completion_rate = (completed_orders / len(orders_df) * 100) if len(orders_df) > 0 else 0

                # Tính lợi nhuận trung bình
                avg_profit = total_profit / len(orders_df) if len(orders_df) > 0 else 0

                # Tìm tháng có doanh thu cao nhất
                if 'Month' in orders_df.columns and 'Revenue' in orders_df.columns:
                    monthly_revenue = orders_df.groupby('Month')['Revenue'].sum()
                    if not monthly_revenue.empty:
                        best_month = monthly_revenue.idxmax()
                        best_month_revenue = monthly_revenue.max()
                    else:
                        best_month = 0
                        best_month_revenue = 0
                else:
                    best_month = 0
                    best_month_revenue = 0

                # Thêm thông tin vào summary
                year_summary.update({
                    'completed_orders': int(completed_orders),
                    'completion_rate': round(completion_rate, 1),
                    'avg_profit_per_order': round(avg_profit, 0),
                    'best_month': int(best_month),
                    'best_month_revenue': float(best_month_revenue),
                    'revenue_calculated': float(total_revenue),
                    'profit_calculated': float(total_profit)
                })

            # Tính toán từ work log
            if 'Fraud_Events' in work_log_sheets and not work_log_sheets['Fraud_Events'].empty:
                fraud_df = work_log_sheets['Fraud_Events']

                # Đếm số tháng có gian lận
                if 'Month' in fraud_df.columns:
                    months_with_fraud = fraud_df['Month'].nunique()
                else:
                    months_with_fraud = 0

                year_summary.update({
                    'months_with_fraud': int(months_with_fraud),
                    'fraud_rate': round(
                        (year_summary.get('total_fraud', 0) / year_summary.get('total_orders', 1) * 100), 1)
                })

            return year_summary

        except Exception as e:
            print(f"❌ Lỗi tính toán year summary: {e}")
            return None


if __name__ == "__main__":
    # Test data processor
    processor = DataProcessor("Giang")
    success = processor.load_all_data()

    if success:
        print("\n" + "=" * 50)
        print("📊 KẾT QUẢ TẢI DỮ LIỆU")
        print("=" * 50)

        summary = processor.get_summary_data()

        print(f"\n📁 WORK LOG:")
        for key, value in summary['work_log'].items():
            if key != 'file_found':
                print(f"  {key}: {value}")

        print(f"\n📈 SAP DATA:")
        for key, value in summary['sap'].items():
            if key not in ['file_found', 'pending_orders']:
                print(f"  {key}: {value}")

        print(f"\n🎯 METRICS:")
        for key, value in summary['metrics'].items():
            print(f"  {key}: {value}")

        # Test year data
        print(f"\n📅 YEAR DATA:")
        if processor.year_data:
            orders_count = len(processor.year_data.get('sap_data', {}).get('sheets', {}).get('Orders', pd.DataFrame()))
            fraud_count = len(
                processor.year_data.get('work_log', {}).get('sheets', {}).get('Fraud_Events', pd.DataFrame()))
            print(f"  Tổng đơn hàng cả năm: {orders_count}")
            print(f"  Tổng sự kiện gian lận cả năm: {fraud_count}")

        # Test queries
        print(f"\n🔍 PENDING ORDERS: {processor.query_sap_data('pending_orders')['count']}")
        print(f"📍 REGION STATS: {processor.query_sap_data('region_stats')['regions'].keys()}")
        print(f"📅 DAILY PERFORMANCE: {processor.query_sap_data('daily_performance')['total_days']} days")
    else:
        print("❌ Không thể tải dữ liệu")