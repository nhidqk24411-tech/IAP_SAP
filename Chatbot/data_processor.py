# data_processor.py - Xử lý dữ liệu từ work log và SAP
import os
from pathlib import Path

import pandas as pd
from datetime import datetime
import random


class DataProcessor:
    """Xử lý dữ liệu từ nhiều nguồn"""

    def __init__(self, employee_name):
        self.employee_name = employee_name
        self.work_log_data = None
        self.sap_data = None
        self.metrics = None

    def load_all_data(self):
        """Tải tất cả dữ liệu"""
        try:
            # Lấy đường dẫn từ Config
            from config import Config
            data_paths = Config.get_employee_data_path(self.employee_name)

            # Tải work log
            self.work_log_data = self.load_work_log(data_paths['work_log'])

            # Tải SAP data
            self.sap_data = self.load_sap_data(data_paths['sap_data'])


            # Tính metrics
            self.calculate_metrics()

            return True

        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            return False

    def load_work_log(self, file_path):
        """Tải dữ liệu work log"""
        try:
            # Kiểm tra file tồn tại - FIX: sử dụng Path thay vì os.path
            file_path = Path(file_path) if not isinstance(file_path, Path) else file_path

            if not file_path.exists():
                print(f"⚠️ Work log file not found: {file_path}")
                # Tạo file mẫu nếu không tồn tại
                return {
                    'raw_fraud': [],
                    'raw_mouse': [],
                    'summary': {
                        'total_events': 0,
                        'fraud_count': 0,
                        'warning_count': 0,
                        'error_count': 0,
                        'mouse_events': 0
                    }
                }

            # Đọc Excel
            fraud_df = pd.read_excel(file_path, sheet_name='Fraud_Events')
            mouse_df = pd.read_excel(file_path, sheet_name='Mouse_Details')

            # Xử lý dữ liệu
            fraud_count = len(fraud_df[fraud_df['IsFraud'] == 1]) if 'IsFraud' in fraud_df.columns else 0
            warning_count = len(fraud_df[fraud_df['Severity'] == 'WARNING']) if 'Severity' in fraud_df.columns else 0
            error_count = len(fraud_df[fraud_df['Severity'] == 'ERROR']) if 'Severity' in fraud_df.columns else 0

            mouse_events = mouse_df['TotalMoves'].sum() if 'TotalMoves' in mouse_df.columns else len(mouse_df)

            return {
                'raw_fraud': fraud_df.to_dict('records'),
                'raw_mouse': mouse_df.to_dict('records'),
                'summary': {
                    'total_events': len(fraud_df) + len(mouse_df),
                    'fraud_count': int(fraud_count),
                    'warning_count': int(warning_count),
                    'error_count': int(error_count),
                    'mouse_events': int(mouse_events)
                }
            }

        except Exception as e:
            print(f"❌ Lỗi đọc work log: {e}")
            import traceback
            traceback.print_exc()
            return {
                'raw_fraud': [],
                'raw_mouse': [],
                'summary': {
                    'total_events': 0,
                    'fraud_count': 0,
                    'warning_count': 0,
                    'error_count': 0,
                    'mouse_events': 0
                }
            }

    def load_sap_data(self, file_path):
        """Tải dữ liệu SAP"""
        try:
            df = pd.read_excel(file_path)

            orders = []
            for _, row in df.iterrows():
                orders.append({
                    'order_id': row.get('Order_ID', f'ORD{random.randint(1000, 9999)}'),
                    'date': row.get('Order_Date', datetime.now().strftime('%Y-%m-%d')),
                    'customer': row.get('Customer', 'Unknown'),
                    'revenue': float(row.get('Revenue', random.randint(10000000, 50000000))),
                    'profit': float(row.get('Profit', 0)),
                    'status': row.get('Status', 'Completed')
                })

            total_revenue = sum(o['revenue'] for o in orders)
            total_profit = sum(o['profit'] for o in orders) if any(o['profit'] for o in orders) else total_revenue * 0.2

            return {
                'orders': orders,
                'summary': {
                    'total_orders': len(orders),
                    'total_revenue': total_revenue,
                    'total_profit': total_profit,
                    'completion_rate': len([o for o in orders if o['status'] == 'Completed']) / len(orders) * 100,
                    'avg_revenue': total_revenue / len(orders) if orders else 0
                }
            }

        except Exception as e:
            print(f"❌ Lỗi đọc SAP data: {e}")



    def calculate_metrics(self):
        """Tính các chỉ số hiệu suất"""

        wl = self.work_log_data['summary']
        sap = self.sap_data['summary']

        # Tính điểm hiệu suất
        efficiency = max(0, min(100, 100 - (wl['warning_count'] * 5) - (wl['error_count'] * 10)))
        quality = max(0, min(100, sap['completion_rate'] - (wl['fraud_count'] * 15)))
        profitability = max(0, min(100, (sap['total_profit'] / 10000000) * 10))
        compliance = max(0, min(100, 100 - (wl['fraud_count'] * 20) - (wl['warning_count'] * 5)))

        overall = (efficiency + quality + profitability + compliance) / 4

        self.metrics = {
            'efficiency': round(efficiency, 1),
            'quality': round(quality, 1),
            'profitability': round(profitability, 1),
            'compliance': round(compliance, 1),
            'overall': round(overall, 1)
        }

    def get_context_data(self):
        """Lấy dữ liệu context cho AI"""
        return {
            'work_log': self.work_log_data['summary'] if self.work_log_data else {},
            'sap_data': self.sap_data['summary'] if self.sap_data else {},
            'metrics': self.metrics if self.metrics else {}
        }

    def get_summary_data(self):
        """Lấy dữ liệu tóm tắt - FIX LỖI 'warnings'"""
        work_log_summary = self.work_log_data['summary'] if self.work_log_data else {}
        sap_summary = self.sap_data['summary'] if self.sap_data else {}

        # FIX: Sử dụng đúng key names
        summary = {
            'work_log': {
                'total_events': work_log_summary.get('total_events', 0),
                'fraud_count': work_log_summary.get('fraud_count', 0),
                'warning_count': work_log_summary.get('warning_count', 0),  # Đúng key
                'error_count': work_log_summary.get('error_count', 0),
                'mouse_events': work_log_summary.get('mouse_events', 0)
            },
            'sap': {
                'total_orders': sap_summary.get('total_orders', 0),
                'total_revenue': sap_summary.get('total_revenue', 0),
                'total_profit': sap_summary.get('total_profit', 0),
                'revenue': sap_summary.get('total_revenue', 0),  # Thêm alias
                'profit': sap_summary.get('total_profit', 0),  # Thêm alias
                'completion_rate': sap_summary.get('completion_rate', 0),
                'avg_revenue': sap_summary.get('avg_revenue', 0)
            },
            'metrics': self.metrics if self.metrics else {}
        }
        return summary

    def get_all_data(self):
        """Lấy tất cả dữ liệu"""
        return {
            'work_log': self.work_log_data['summary'] if self.work_log_data else {},
            'sap': self.sap_data['summary'] if self.sap_data else {},
            'full_sap': self.sap_data['orders'] if self.sap_data else [],
            'metrics': self.metrics if self.metrics else {}
        }

    def get_fraud_analysis(self):
        """Phân tích dữ liệu gian lận từ work log"""
        if not self.work_log_data or 'raw_fraud' not in self.work_log_data:
            return {"total_fraud": 0, "by_module": {}}

        try:
            fraud_events = self.work_log_data['raw_fraud']

            # Lọc sự kiện gian lận
            fraud_only = [event for event in fraud_events
                          if event.get('IsFraud') == 1]

            # Phân tích theo module
            fraud_by_module = {}
            for event in fraud_only:
                module = event.get('Module', 'Unknown')
                fraud_by_module[module] = fraud_by_module.get(module, 0) + 1

            # Phân tích theo severity
            fraud_by_severity = {}
            for event in fraud_only:
                severity = event.get('Severity', 'Unknown')
                fraud_by_severity[severity] = fraud_by_severity.get(severity, 0) + 1

            return {
                'total_fraud': len(fraud_only),
                'by_module': fraud_by_module,
                'by_severity': fraud_by_severity,
                'recent_fraud': fraud_only[-5:] if len(fraud_only) > 5 else fraud_only
            }

        except Exception as e:
            print(f"❌ Error analyzing fraud data: {e}")
            return {"total_fraud": 0, "by_module": {}}

    def get_enhanced_context(self):
        """Lấy dữ liệu context nâng cao"""
        context = self.get_context_data()
        context['fraud_analysis'] = self.get_fraud_analysis()
        return context

if __name__ == "__main__":
    # Test data processor
    processor = DataProcessor("Giang")
    processor.load_all_data()

    print("📊 Data Summary:")
    print(processor.get_summary_data())