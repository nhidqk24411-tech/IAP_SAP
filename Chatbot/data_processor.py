# data_processor.py - Xử lý dữ liệu từ work log và SAP
# CHỈ GIỮ LẠI 8 CHỈ SỐ THEO BỘ TIÊU CHÍ
# ĐÃ BỔ SUNG: chi tiết đơn hàng, gian lận, lợi nhuận cho phân tích cá nhân hóa

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import traceback


class DataProcessor:
    """Xử lý dữ liệu – tính 8 chỉ số và cung cấp chi tiết giao dịch cho AI."""

    def __init__(self, employee_name: str):
        self.employee_name = employee_name
        # Dữ liệu tháng hiện tại (DataFrame)
        self.reality_df: pd.DataFrame = pd.DataFrame()
        self.kpi_df: pd.DataFrame = pd.DataFrame()
        self.browser_df: pd.DataFrame = pd.DataFrame()
        self.fraud_df: pd.DataFrame = pd.DataFrame()
        # Dữ liệu cả năm (DataFrame gộp)
        self.reality_year_df: pd.DataFrame = pd.DataFrame()
        self.kpi_year_df: pd.DataFrame = pd.DataFrame()
        self.browser_year_df: pd.DataFrame = pd.DataFrame()
        self.fraud_year_df: pd.DataFrame = pd.DataFrame()
        # Metrics
        self.metrics = None
        self.monthly_metrics = {}
        self.yearly_metrics = {}
        print(f"🚀 Khởi tạo DataProcessor cho: {employee_name}")

    # ------------------------------------------------------------------
    # 1. TẢI DỮ LIỆU (GIỮ NGUYÊN CẤU TRÚC)
    # ------------------------------------------------------------------
    def load_all_data(self) -> bool:
        """Tải dữ liệu tháng hiện tại và cả năm, thiết lập DataFrames chi tiết."""
        try:
            from config import Config
            self._load_year_data()
            paths = Config.get_employee_data_path(self.employee_name)
            self._load_work_log_current(paths['work_log'])
            self._load_sap_data_current(paths['sap_data'])
            self.calculate_metrics()
            self._calculate_period_metrics()
            return True
        except Exception as e:
            print(f"❌ Lỗi tải dữ liệu: {e}")
            traceback.print_exc()
            return False

    def _load_year_data(self):
        """Gộp tất cả các tháng trong năm, lưu vào DataFrame chung."""
        from config import Config
        year = datetime.now().year
        all_reality = []
        all_kpi = []
        all_browser = []
        all_fraud = []
        print(f"📅 Đang tải dữ liệu cả năm {year}...")
        for month in range(1, 13):
            month_str = f"{year}_{month:02d}"
            base = Path(Config.BASE_DATA_PATH) / self.employee_name / month_str
            if not base.exists():
                continue

            # Work log
            wl_path = base / f"work_logs_{self.employee_name}_{month_str}.xlsx"
            if wl_path.exists():
                try:
                    excel = pd.ExcelFile(wl_path)
                    for sheet in excel.sheet_names:
                        df = pd.read_excel(wl_path, sheet_name=sheet)
                        df['Month'] = month
                        if sheet == 'Browser_Sessions':
                            all_browser.append(df)
                        elif sheet == 'Fraud_Events':
                            all_fraud.append(df)
                except Exception as e:
                    print(f"⚠️ Lỗi work log tháng {month}: {e}")

            # SAP data
            sap_path = base / "sap_data.xlsx"
            if sap_path.exists():
                try:
                    excel = pd.ExcelFile(sap_path)
                    for sheet in excel.sheet_names:
                        df = pd.read_excel(sap_path, sheet_name=sheet)
                        df['Month'] = month
                        if sheet == 'Reality':
                            all_reality.append(df)
                        elif sheet == 'KPI':
                            all_kpi.append(df)
                except Exception as e:
                    print(f"⚠️ Lỗi SAP tháng {month}: {e}")

        # Gộp DataFrame
        self.reality_year_df = pd.concat(all_reality, ignore_index=True) if all_reality else pd.DataFrame()
        self.kpi_year_df = pd.concat(all_kpi, ignore_index=True) if all_kpi else pd.DataFrame()
        self.browser_year_df = pd.concat(all_browser, ignore_index=True) if all_browser else pd.DataFrame()
        self.fraud_year_df = pd.concat(all_fraud, ignore_index=True) if all_fraud else pd.DataFrame()

    def _load_work_log_current(self, path):
        """Chỉ giữ Browser_Sessions và Fraud_Events cho tháng hiện tại."""
        path = Path(path)
        self.browser_df = pd.DataFrame()
        self.fraud_df = pd.DataFrame()
        if not path.exists():
            return
        excel = pd.ExcelFile(path)
        for sheet in excel.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if sheet == 'Browser_Sessions':
                self.browser_df = df
            elif sheet == 'Fraud_Events':
                self.fraud_df = df

    def _load_sap_data_current(self, path):
        """Chỉ giữ Reality và KPI cho tháng hiện tại."""
        path = Path(path)
        self.reality_df = pd.DataFrame()
        self.kpi_df = pd.DataFrame()
        if not path.exists():
            return
        excel = pd.ExcelFile(path)
        for sheet in excel.sheet_names:
            df = pd.read_excel(path, sheet_name=sheet)
            if sheet == 'Reality':
                self.reality_df = df
            elif sheet == 'KPI':
                self.kpi_df = df

    # ------------------------------------------------------------------
    # 2. HÀM TÍNH TOÁN 8 CHỈ SỐ (DÙNG CHUNG CHO MỌI KỲ)
    # ------------------------------------------------------------------
    def _compute_8_metrics(self,
                          reality_df: pd.DataFrame,
                          kpi_df: pd.DataFrame,
                          browser_df: pd.DataFrame,
                          fraud_df: pd.DataFrame) -> Dict[str, float]:
        """
        Đầu vào: DataFrame của các sheet tương ứng.
        Đầu ra: dict chứa 8 chỉ số (đã làm tròn) + thông tin phụ.
        """
        metrics = self._empty_metrics()

        if reality_df.empty:
            return metrics

        # --- Xác định tên cột (xử lý trùng lặp) ---
        cols = reality_df.columns.tolist()
        sales_doc_col = 'Sales Doc.' if 'Sales Doc.' in cols else None
        created_cols = sorted([c for c in cols if c.startswith('Created On')])
        time_cols = sorted([c for c in cols if c.startswith('Time')])
        start_created = created_cols[0] if len(created_cols) > 0 else None
        start_time = time_cols[0] if len(time_cols) > 0 else None
        end_created = created_cols[2] if len(created_cols) > 2 else None
        end_time = time_cols[2] if len(time_cols) > 2 else None
        net_value_col = 'Net Value' if 'Net Value' in cols else None
        custrefdat_col = 'CustRefDat' if 'CustRefDat' in cols else None

        # --------------------------------------------------------------
        # CHỈ SỐ 2 + 6: Tổng số đơn & đơn hoàn thành
        # --------------------------------------------------------------
        if sales_doc_col is not None:
            total_orders = reality_df[sales_doc_col].nunique()
            metrics['total_orders'] = total_orders

            # Đơn hoàn thành: tất cả các dòng của đơn đều KHÔNG có ô trống
            completed_set = set()
            for doc in reality_df[sales_doc_col].unique():
                doc_rows = reality_df[reality_df[sales_doc_col] == doc]
                all_complete = True
                for _, row in doc_rows.iterrows():
                    for col in cols:
                        val = row.get(col)
                        if pd.isna(val) or (isinstance(val, str) and val.strip() == ''):
                            all_complete = False
                            break
                    if not all_complete:
                        break
                if all_complete:
                    completed_set.add(doc)
            completed_orders = len(completed_set)
            metrics['completed_orders'] = completed_orders
            metrics['order_completion_rate'] = round(
                (completed_orders / total_orders * 100) if total_orders > 0 else 0, 2
            )

        # --------------------------------------------------------------
        # CHỈ SỐ 3: Lợi nhuận ròng bình quân / đơn
        # --------------------------------------------------------------
        if sales_doc_col and net_value_col and metrics['completed_orders'] > 0:
            net_per_order = reality_df.groupby(sales_doc_col)[net_value_col].first()
            total_net = net_per_order.sum()
            metrics['avg_net_profit_per_order'] = round(total_net / metrics['completed_orders'], 2)
        else:
            metrics['avg_net_profit_per_order'] = 0

        # --------------------------------------------------------------
        # CHỈ SỐ 4: Tỷ lệ sửa đổi trung bình / đơn
        # --------------------------------------------------------------
        if sales_doc_col and metrics['completed_orders'] > 0:
            mod_counts = reality_df.groupby(sales_doc_col).size()
            total_mods = (mod_counts - 1).sum()
            metrics['avg_modification_rate'] = round(total_mods / metrics['completed_orders'], 2)
        else:
            metrics['avg_modification_rate'] = 0

        # --------------------------------------------------------------
            # CHỈ SỐ 7: Thời gian xử lý đơn hàng (B,C) -> (M,N)
            # --------------------------------------------------------------
            if sales_doc_col and start_created and start_time and end_created and end_time:
                try:
                    # TẠO BẢN SAO ĐỂ TRÁNH SettingWithCopyWarning
                    temp_df = reality_df.copy()

                    # ÉP ĐỊNH DẠNG NGÀY THÁNG ĐỂ TRÁNH UserWarning
                    # Ở đây dùng format='%Y-%m-%d %H:%M:%S' vì dữ liệu generate dùng format này
                    temp_df['_start'] = pd.to_datetime(
                        temp_df[start_created].astype(str) + ' ' + temp_df[start_time].astype(str),
                        format='%Y-%m-%d %H:%M:%S',
                        errors='coerce'
                    )
                    temp_df['_end'] = pd.to_datetime(
                        temp_df[end_created].astype(str) + ' ' + temp_df[end_time].astype(str),
                        format='%Y-%m-%d %H:%M:%S',
                        errors='coerce'
                    )

                    start_min = temp_df.groupby(sales_doc_col)['_start'].min()
                    end_max = temp_df.groupby(sales_doc_col)['_end'].max()

                    diff_hours = (end_max - start_min).dt.total_seconds() / 3600
                    metrics['total_order_processing_hours'] = diff_hours.sum()
                except Exception as e:
                    print(f"⚠️ Lỗi tính thời gian xử lý: {e}")
                    metrics['total_order_processing_hours'] = 0
            else:
                metrics['total_order_processing_hours'] = 0
        # --------------------------------------------------------------
        # CHỈ SỐ 8: Thời gian chu kỳ đơn hàng (CustRefDat - Created On gần nhất)
        # --------------------------------------------------------------
        if sales_doc_col and custrefdat_col and start_created:
            try:
                reality_df_sorted = reality_df.sort_values(by=[start_created, start_time])
                last_rows = reality_df_sorted.groupby(sales_doc_col).last()
                cust_ref = pd.to_datetime(last_rows[custrefdat_col])
                created = pd.to_datetime(last_rows[start_created])
                cycle_hours = (cust_ref - created).dt.total_seconds() / 3600
                metrics['total_cycle_hours'] = cycle_hours.abs().sum()
            except Exception:
                metrics['total_cycle_hours'] = 0
        else:
            metrics['total_cycle_hours'] = 0

        # --------------------------------------------------------------
        # B. TÍNH TỪ WORK LOG
        # --------------------------------------------------------------
        if not browser_df.empty and 'Session_Start' in browser_df.columns and 'Total_Seconds' in browser_df.columns:
            session_starts = pd.to_datetime(browser_df['Session_Start'])
            first_day = session_starts.min()
            last_day = session_starts.max()
            session_days = (last_day - first_day).days + 1
            total_hours = browser_df['Total_Seconds'].sum() / 3600
            metrics['total_session_hours'] = total_hours
            metrics['session_days'] = session_days
        else:
            metrics['total_session_hours'] = 0
            metrics['session_days'] = 1

        if not fraud_df.empty:
            metrics['fraud_events_count'] = len(fraud_df)
        else:
            metrics['fraud_events_count'] = 0

        # --------------------------------------------------------------
        # C. TÍNH 8 CHỈ SỐ HOÀN CHỈNH
        # --------------------------------------------------------------
        # 1. Thời gian làm việc trung bình trên hệ thống
        avg_work_time = metrics['total_session_hours'] / metrics['session_days'] if metrics['session_days'] > 0 else 0
        metrics['avg_working_time_hours'] = round(avg_work_time, 2)

        # 2. Tỷ lệ hoàn thành đơn hàng (đã tính)

        # 3. Lợi nhuận ròng bình quân (đã tính)

        # 4. Tỷ lệ sửa đổi trung bình (đã tính)

        # 5. Tần suất vi phạm trên một đơn vị thời gian
        viol_freq = metrics['fraud_events_count'] / metrics['total_session_hours'] if metrics['total_session_hours'] > 0 else 0
        metrics['violation_frequency_per_hour'] = round(viol_freq, 4)

        # 6. Tỷ lệ hoàn thành KPI (lấy từ sheet KPI, KHÔNG mặc định, đơn vị %)
        kpi_target = self._get_kpi_value(kpi_df)
        if kpi_target is not None and kpi_target > 0:
            metrics['kpi_completion_rate'] = round((metrics['completed_orders'] / kpi_target) * 100, 2)
        else:
            metrics['kpi_completion_rate'] = 0.0

        # 7. Thời gian làm việc hiệu quả trên hệ thống
        eff_ratio = metrics['total_order_processing_hours'] / metrics['total_session_hours'] if metrics['total_session_hours'] > 0 else 0
        metrics['effective_work_time_ratio'] = round(eff_ratio, 4)

        # 8. Thời gian chu kỳ đơn hàng
        cycle_time = metrics['total_cycle_hours'] / metrics['completed_orders'] if metrics['completed_orders'] > 0 else 0
        metrics['order_cycle_time_hours'] = round(cycle_time, 2)

        return metrics

    def _get_kpi_value(self, kpi_df: pd.DataFrame) -> Optional[float]:
        """Đọc giá trị KPI_NUM từ sheet KPI, trả về None nếu không có."""
        if kpi_df.empty:
            return None
        if 'KPI_NUM' not in kpi_df.columns:
            return None
        try:
            val = kpi_df.iloc[0]['KPI_NUM']
            return float(val)
        except:
            return None

    def _empty_metrics(self) -> Dict[str, float]:
        """Trả về dict rỗng cho 8 chỉ số."""
        return {
            'total_orders': 0,
            'completed_orders': 0,
            'order_completion_rate': 0.0,
            'avg_net_profit_per_order': 0.0,
            'avg_modification_rate': 0.0,
            'total_order_processing_hours': 0.0,
            'total_cycle_hours': 0.0,
            'total_session_hours': 0.0,
            'session_days': 1,
            'fraud_events_count': 0,
            'avg_working_time_hours': 0.0,
            'violation_frequency_per_hour': 0.0,
            'kpi_completion_rate': 0.0,
            'effective_work_time_ratio': 0.0,
            'order_cycle_time_hours': 0.0,
        }

    # ------------------------------------------------------------------
    # 3. TÍNH CHO THÁNG HIỆN TẠI, TỪNG THÁNG, CẢ NĂM
    # ------------------------------------------------------------------
    def calculate_metrics(self):
        """Tính metrics cho tháng hiện tại."""
        self.metrics = self._compute_8_metrics(
            self.reality_df,
            self.kpi_df,
            self.browser_df,
            self.fraud_df
        )

    def _calculate_period_metrics(self):
        """Tính metrics cho từng tháng 1-12 và cả năm dùng year DataFrames."""
        if self.reality_year_df.empty:
            return

        # --- Từng tháng ---
        for month in range(1, 13):
            reality_m = self.reality_year_df[self.reality_year_df['Month'] == month] if 'Month' in self.reality_year_df.columns else pd.DataFrame()
            kpi_m = self.kpi_year_df[self.kpi_year_df['Month'] == month] if 'Month' in self.kpi_year_df.columns else pd.DataFrame()
            browser_m = self.browser_year_df[self.browser_year_df['Month'] == month] if 'Month' in self.browser_year_df.columns else pd.DataFrame()
            fraud_m = self.fraud_year_df[self.fraud_year_df['Month'] == month] if 'Month' in self.fraud_year_df.columns else pd.DataFrame()

            if reality_m.empty:
                continue
            self.monthly_metrics[month] = self._compute_8_metrics(reality_m, kpi_m, browser_m, fraud_m)

        # --- Cả năm ---
        if not self.reality_year_df.empty:
            self.yearly_metrics = self._compute_8_metrics(
                self.reality_year_df,
                self.kpi_year_df,
                self.browser_year_df,
                self.fraud_year_df
            )

    # ------------------------------------------------------------------
    # 4. PHƯƠNG THỨC LẤY CHI TIẾT CHO AI
    # ------------------------------------------------------------------
    def get_incomplete_orders(self, month: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Trả về danh sách các đơn hàng chưa hoàn thành (thiếu Delivery hoặc Bill).
        - month = None: lấy tháng hiện tại
        - month = 1..12: lấy tháng cụ thể (dùng year_data)
        """
        if month is None:
            df = self.reality_df.copy()
        else:
            df = self.reality_year_df[self.reality_year_df['Month'] == month].copy()
            if df.empty:
                return []

        if 'Sales Doc.' not in df.columns:
            return []

        incomplete = []
        for doc in df['Sales Doc.'].unique():
            order_rows = df[df['Sales Doc.'] == doc]
            # Kiểm tra Delivery
            missing_delivery = False
            if 'Delivery' in order_rows.columns:
                deliveries = order_rows['Delivery'].dropna()
                missing_delivery = deliveries.empty or deliveries.astype(str).str.strip().eq('').all()
            # Kiểm tra Bill. Doc.
            missing_bill = False
            if 'Bill. Doc.' in order_rows.columns:
                bills = order_rows['Bill. Doc.'].dropna()
                missing_bill = bills.empty or bills.astype(str).str.strip().eq('').all()
            # Nếu thiếu ít nhất một trong hai
            if missing_delivery or missing_bill:
                # Lấy ngày tạo đầu tiên để tham khảo
                created_on = None
                if 'Created On' in order_rows.columns:
                    created_cols = [c for c in order_rows.columns if c.startswith('Created On')]
                    if created_cols:
                        created_on = order_rows[created_cols[0]].iloc[0]
                incomplete.append({
                    'sales_doc': doc,
                    'missing_delivery': missing_delivery,
                    'missing_bill': missing_bill,
                    'created_on': created_on,
                    'month': month or datetime.now().month
                })
        return incomplete

    def get_fraud_events(self, month: Optional[int] = None,
                         severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lấy danh sách sự kiện gian lận.
        - month = None: tháng hiện tại
        - month: tháng cụ thể
        - severity: lọc theo mức độ (WARNING, CRITICAL, ...)
        """
        if month is None:
            df = self.fraud_df.copy()
        else:
            df = self.fraud_year_df[self.fraud_year_df['Month'] == month].copy()

        if df.empty:
            return []

        events = []
        for _, row in df.iterrows():
            event = {
                'timestamp': row.get('Timestamp'),
                'event_type': row.get('Event_Type'),
                'details': row.get('Details'),
                'severity': row.get('Severity'),
                'is_fraud': row.get('IsFraud'),
                'date': row.get('Date'),
                'time': row.get('Time'),
                'module': row.get('Module'),
                'session_id': row.get('Session_ID')
            }
            if severity is None or event['severity'] == severity:
                events.append(event)
        return events

    def get_total_net_profit(self, month: Optional[int] = None) -> float:
        """Tổng lợi nhuận ròng (Net Value) của các đơn hàng trong tháng."""
        if month is None:
            df = self.reality_df
        else:
            df = self.reality_year_df[self.reality_year_df['Month'] == month]

        if df.empty or 'Sales Doc.' not in df.columns or 'Net Value' not in df.columns:
            return 0.0

        # Lấy Net Value đầu tiên (không null) cho mỗi đơn hàng
        net_per_order = df.groupby('Sales Doc.').apply(
            lambda x: x['Net Value'].dropna().iloc[0] if not x['Net Value'].dropna().empty else 0
        )
        return float(net_per_order.sum())

    def get_monthly_net_profit(self) -> Dict[int, float]:
        """Lợi nhuận ròng theo từng tháng (1-12) từ year_data."""
        monthly = {}
        for month in range(1, 13):
            profit = self.get_total_net_profit(month)
            if profit > 0:
                monthly[month] = profit
        return monthly

    # ------------------------------------------------------------------
    # 5. CÁC PHƯƠNG THỨC LẤY DỮ LIỆU (GIỮ NGUYÊN)
    # ------------------------------------------------------------------
    def get_monthly_metrics(self) -> Dict[int, Dict]:
        return self.monthly_metrics

    def get_yearly_metrics(self) -> Dict:
        return self.yearly_metrics

    def get_summary_data(self):
        """Tóm tắt nhanh cho tháng hiện tại để hiển thị lên HOME."""
        m = self.metrics if self.metrics else {}
        return {
            'work_log': {
                'fraud_events_count': m.get('fraud_events_count', 0),
                'total_session_hours': m.get('total_session_hours', 0),
                'session_days': m.get('session_days', 1),
            },
            'sap': {
                'total_orders': m.get('total_orders', 0),
                'completed_orders': m.get('completed_orders', 0),
                'completion_rate': m.get('order_completion_rate', 0),
                'kpi_target': self._get_kpi_value(self.kpi_df) if not self.kpi_df.empty else 0,  # Mục tiêu KPI
                'kpi_percent': m.get('kpi_completion_rate', 0.0),  # % Hoàn thành
            },
            'metrics': m
        }

    def get_context_data(self) -> Dict[str, Any]:
        """Cung cấp toàn bộ dữ liệu cho AI, bao gồm chi tiết giao dịch."""
        return {
            'employee_name': self.employee_name,
            'current_month_metrics': self.metrics,
            'monthly_metrics': self.monthly_metrics,
            'yearly_metrics': self.yearly_metrics,
            'analysis_ready': True,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),

            # --- CHI TIẾT CHO PHÂN TÍCH CÁ NHÂN HÓA ---
            'incomplete_orders_current': self.get_incomplete_orders(),
            'fraud_events_current': self.get_fraud_events(),
            'net_profit_current': self.get_total_net_profit(),
            'net_profit_by_month': self.get_monthly_net_profit(),

            # Giữ lại raw data nếu AI cần truy vấn sâu hơn
            'reality_current': self.reality_df.to_dict(orient='records')[:100],
            'fraud_current': self.fraud_df.to_dict(orient='records')[:50],
            'year_data': {
                'reality': self.reality_year_df.to_dict(orient='records')[:500],
                'fraud': self.fraud_year_df.to_dict(orient='records')[:200]
            }
        }

    def get_all_data(self):
        return {
            'work_log': {
                'Browser_Sessions': self.browser_df,
                'Fraud_Events': self.fraud_df
            },
            'sap_data': {
                'Reality': self.reality_df,
                'KPI': self.kpi_df
            },
            'metrics': self.metrics,
            'year_data': {
                'reality': self.reality_year_df,
                'kpi': self.kpi_year_df,
                'browser': self.browser_year_df,
                'fraud': self.fraud_year_df
            },
            'monthly_metrics': self.monthly_metrics,
            'yearly_metrics': self.yearly_metrics
        }


if __name__ == "__main__":
    # Test nhanh
    dp = DataProcessor("EM002")
    if dp.load_all_data():
        print("\n" + "=" * 50)
        print("📊 8 CHỈ SỐ - THÁNG HIỆN TẠI")
        print("=" * 50)
        m = dp.metrics
        if m:
            print(f"1. Thời gian làm việc TB         : {m['avg_working_time_hours']:>8.2f} giờ/ngày")
            print(f"2. Tỷ lệ hoàn thành đơn         : {m['order_completion_rate']:>8.2f} %")
            print(f"3. LN ròng TB/đơn               : {m['avg_net_profit_per_order']:>8.2f} VND")
            print(f"4. Tỷ lệ sửa đổi TB             : {m['avg_modification_rate']:>8.2f} lần/đơn")
            print(f"5. Tần suất vi phạm             : {m['violation_frequency_per_hour']:>8.4f} lần/giờ")
            print(f"6. Tỷ lệ hoàn thành KPI         : {m['kpi_completion_rate']:>8.2f} %")
            print(f"7. Thời gian LV hiệu quả        : {m['effective_work_time_ratio']:>8.4f}")
            print(f"8. Chu kỳ đơn hàng              : {m['order_cycle_time_hours']:>8.2f} giờ")
        print("\n📅 Số tháng có dữ liệu:", len(dp.get_monthly_metrics()))
        y = dp.get_yearly_metrics()
        if y:
            print("📆 Metrics cả năm:", y.get('order_completion_rate', 'N/A'), '%')
