# data_processor.py - Xử lý dữ liệu từ work log và SAP
import os
from pathlib import Path
import pandas as pd
from datetime import datetime
import random


class DataProcessor:
    """Xử lý dữ liệu từ nhiều nguồn cho AI phân tích"""

    def __init__(self, employee_name):
        self.employee_name = employee_name
        self.work_log_data = None
        self.sap_data = None
        self.metrics = None
        print(f"🚀 Khởi tạo DataProcessor cho: {employee_name}")

    def load_all_data(self):
        """Tải tất cả dữ liệu"""
        try:
            print(f"📂 Đang tải dữ liệu cho {self.employee_name}...")

            # Lấy đường dẫn từ Config
            from config import Config
            data_paths = Config.get_employee_data_path(self.employee_name)

            print(f"🔍 Đường dẫn work log: {data_paths['work_log']}")
            print(f"🔍 Đường dẫn SAP: {data_paths['sap_data']}")

            # Tải work log
            print("📊 Đang tải work log...")
            self.work_log_data = self.load_work_log(data_paths['work_log'])
            print(f"✅ Work log loaded: có {len(self.work_log_data.get('raw_orders', []))} đơn hàng")

            # Tải SAP data
            print("📊 Đang tải SAP data...")
            self.sap_data = self.load_sap_data(data_paths['sap_data'])
            print(f"✅ SAP data loaded: có {len(self.sap_data.get('orders', []))} đơn hàng")

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
        """Tính các chỉ số hiệu suất tổng hợp"""
        try:
            wl = self.work_log_data.get('summary', {}) if self.work_log_data else {}
            sap = self.sap_data.get('summary', {}) if self.sap_data else {}

            print("📈 Đang tính metrics...")

            # Tính điểm hiệu suất (0-100)
            efficiency_score = max(0, min(100, 100 - (wl.get('violation_score', 0) * 5) - (
                        wl.get('mouse_anomaly_count', 0) * 3)))

            quality_score = max(0, min(100, sap.get('completion_rate', 0) - (wl.get('fraud_count', 0) * 10)))

            productivity_score = max(0, min(100,
                                            (sap.get('completed_orders', 0) / max(sap.get('total_orders', 1), 1) * 30) +
                                            (100 - sap.get('avg_edits_per_order', 0) * 2) +  # Ít chỉnh sửa = tốt
                                            (100 - sap.get('slow_orders', 0) * 5)  # Ít đơn chậm = tốt
                                            ))

            compliance_score = max(0, min(100,
                                          100 - (wl.get('critical_count', 0) * 15) - (wl.get('warning_count', 0) * 5)))

            # Điểm tổng thể
            overall_score = round((efficiency_score + quality_score + productivity_score + compliance_score) / 4, 1)

            self.metrics = {
                'efficiency': round(efficiency_score, 1),
                'quality': round(quality_score, 1),
                'productivity': round(productivity_score, 1),
                'compliance': round(compliance_score, 1),
                'overall': overall_score,

                # Các chỉ số phụ
                'work_intensity': round(wl.get('total_work_hours', 0) / 8 * 100, 1) if wl.get('total_work_hours',
                                                                                              0) > 0 else 0,
                'error_rate': round(
                    (wl.get('fraud_count', 0) + wl.get('mouse_anomaly_count', 0)) / max(sap.get('total_orders', 1),
                                                                                        1) * 100, 1),
                'completion_speed': round(100 - (sap.get('slow_orders', 0) / max(sap.get('total_orders', 1), 1) * 100),
                                          1),

                # Thêm metrics từ daily performance
                'avg_daily_efficiency': self._calculate_avg_daily_efficiency()
            }

            print(f"✅ Metrics calculated: {self.metrics}")

        except Exception as e:
            print(f"❌ Lỗi tính metrics: {e}")
            self.metrics = {
                'efficiency': 0,
                'quality': 0,
                'productivity': 0,
                'compliance': 0,
                'overall': 0,
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
            'employee_name': self.employee_name
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
            'metrics': self.metrics if self.metrics else {}
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

        # Test queries
        print(f"\n🔍 PENDING ORDERS: {processor.query_sap_data('pending_orders')['count']}")
        print(f"📍 REGION STATS: {processor.query_sap_data('region_stats')['regions'].keys()}")
        print(f"📅 DAILY PERFORMANCE: {processor.query_sap_data('daily_performance')['total_days']} days")
    else:
        print("❌ Không thể tải dữ liệu")