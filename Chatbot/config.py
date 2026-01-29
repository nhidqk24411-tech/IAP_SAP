# config.py - Cấu hình tối ưu
import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Tải .env
BASE_DIR = Path(__file__).parent
ENV_PATH = BASE_DIR / '.env'

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"✅ Đã tải cấu hình từ: {ENV_PATH}")
else:
    print(f"⚠️ Không tìm thấy .env tại: {ENV_PATH}")


class Config:
    """Cấu hình ứng dụng - Phiên bản tối ưu"""

    # ========== APP CONFIG ==========
    APP_NAME = os.getenv("APP_NAME", "PowerSight Employee Assistant")
    VERSION = os.getenv("APP_VERSION", "3.0.0")

    # ========== GEMINI AI ==========
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyCN3QaoAjO1qFoiJDvdVjYsr6ku-VB_15k")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))

    # ========== EMPLOYEE ==========
    DEFAULT_EMPLOYEE_NAME = os.getenv("DEFAULT_EMPLOYEE_NAME", "EM001")

    # ========== DEBUG ==========
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

    # ========== FIXED DATA PATHS ==========
    BASE_DATA_PATH = "C:/Users/legal/PycharmProjects/PythonProject/Saved_file"

    @classmethod
    def get_all_gemini_models(cls):
        """Danh sách tất cả model Gemini từ mới nhất đến cũ nhất"""
        return [
            # Gemini 3.0 Series (khi có)
            "gemini-3.0-ultra", "gemini-3.0-pro", "gemini-3.0-flash",

            # Gemini 2.5 Series
            "gemini-2.5-pro-exp", "gemini-2.5-pro",
            "gemini-2.5-flash-exp", "gemini-2.5-flash",

            # Gemini 2.0 Series
            "gemini-2.0-flash-exp", "gemini-2.0-flash", "gemini-2.0-flash-lite",
            "gemini-2.0-pro-exp", "gemini-2.0-pro",

            # Gemini 1.5 Series
            "gemini-1.5-pro", "gemini-1.5-flash", "gemini-1.5-flash-8b",

            # Fallback models
            "gemini-pro", "gemini-pro-vision"
        ]

    @classmethod
    def get_employee_data_path(cls, employee_name=None):
        """Lấy đường dẫn dữ liệu cho nhân viên"""
        from datetime import datetime

        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        year_month = datetime.now().strftime("%Y_%m")
        base_path = f"{cls.BASE_DATA_PATH}/{employee_name}/{year_month}"

        return {
            'base_dir': Path(base_path),
            'work_log': Path(f"{base_path}/work_logs_{employee_name}_{year_month}.xlsx"),
            'sap_data': Path(f"{base_path}/sap_data.xlsx")
        }

    @classmethod
    def validate_config(cls):
        """Kiểm tra cấu hình"""
        print(f"\n{'=' * 50}")
        print(f"🔧 KIỂM TRA CẤU HÌNH")
        print(f"{'=' * 50}")

        if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY == "YOUR_API_KEY_HERE":
            print("⚠️ LỖI: GEMINI_API_KEY không hợp lệ hoặc chưa được cấu hình")
            print("⚠️ Sử dụng chế độ DEMO")
            return False

        print(f"📱 App: {cls.APP_NAME}")
        print(f"📦 Version: {cls.VERSION}")
        print(f"🤖 Model mặc định: {cls.GEMINI_MODEL}")
        print(f"👤 Employee: {cls.DEFAULT_EMPLOYEE_NAME}")
        print(f"🔑 API Key: Đã cấu hình")
        print(f"🌡️ Temperature: {cls.TEMPERATURE}")
        print(f"🧠 Max Tokens: {cls.MAX_TOKENS}")
        print(f"🐛 Debug Mode: {cls.DEBUG_MODE}")

        return True

    @classmethod
    def get_work_log_path(cls, employee_name=None):
        """Lấy đường dẫn work log cho nhân viên"""
        from datetime import datetime

        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        year_month = datetime.now().strftime("%Y_%m")
        base_path = f"{cls.BASE_DATA_PATH}/{employee_name}/{year_month}"

        return Path(f"{base_path}/work_logs_{employee_name}_{year_month}.xlsx")

    @classmethod
    def get_sap_data_path(cls, employee_name=None):
        """Lấy đường dẫn SAP data"""
        from datetime import datetime

        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        year_month = datetime.now().strftime("%Y_%m")
        base_path = f"{cls.BASE_DATA_PATH}/{employee_name}/{year_month}"

        # Tạo thư mục nếu chưa tồn tại
        sap_path = Path(f"{base_path}/sap_data.xlsx")
        sap_path.parent.mkdir(parents=True, exist_ok=True)

        return sap_path

    @classmethod
    def validate_gemini_config(cls):
        """Kiểm tra cấu hình Gemini mới"""
        try:
            # Kiểm tra API key
            if not cls.GEMINI_API_KEY or cls.GEMINI_API_KEY == "" or cls.GEMINI_API_KEY == "YOUR_API_KEY_HERE":
                print("⚠️ Không có API Key hợp lệ, sử dụng chế độ DEMO")
                return False

            print(f"🔑 API Key đã cấu hình: {cls.GEMINI_API_KEY[:10]}...{cls.GEMINI_API_KEY[-10:]}")

            # Thử import API mới
            try:
                import google.genai as genai
                print("✅ Sử dụng google.genai (API mới)")

                # Tạo client
                client = genai.Client(api_key=cls.GEMINI_API_KEY)

                # Test model availability
                try:
                    models = client.models.list()
                    available_models = [model.name for model in models]

                    print(f"✅ Google GenAI cấu hình thành công")
                    print(f"📋 Có {len(available_models)} model khả dụng")
                    print(f"🎯 Model mặc định: {cls.GEMINI_MODEL}")

                    if cls.GEMINI_MODEL not in available_models:
                        print(f"⚠️ Model mặc định không khả dụng, sẽ dùng model khác")
                    else:
                        print(f"✅ Model mặc định khả dụng")

                    return True

                except Exception as e:
                    print(f"❌ Lỗi khi test model: {e}")
                    return False

            except ImportError:
                # Fallback to old API
                print("⚠️ Sử dụng google.generativeai (API cũ)")
                import google.generativeai as genai

                genai.configure(api_key=cls.GEMINI_API_KEY)
                models = list(genai.list_models())
                available_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]

                print(f"✅ Google GenAI cấu hình thành công")
                print(f"📋 Có {len(available_models)} model khả dụng")
                print(f"🎯 Model mặc định: {cls.GEMINI_MODEL}")

                return True

        except Exception as e:
            print(f"❌ Lỗi cấu hình Google GenAI: {e}")
            return False

    @classmethod
    def get_all_data_files(cls, employee_name=None):
        """Lấy tất cả các file dữ liệu cho nhân viên"""
        from datetime import datetime

        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        year_month = datetime.now().strftime("%Y_%m")
        base_path = Path(f"{cls.BASE_DATA_PATH}/{employee_name}/{year_month}")

        # Tạo thư mục nếu chưa tồn tại
        base_path.mkdir(parents=True, exist_ok=True)

        return {
            'base_dir': base_path,
            'work_log': base_path / f"work_logs_{employee_name}_{year_month}.xlsx",
            'sap_data': base_path / "sap_data.xlsx",
            'face_captures': base_path / "face_captures"
        }

    @classmethod
    def create_sample_sap_data(cls, employee_name=None):
        """Tạo dữ liệu SAP mẫu nếu không có"""
        try:
            if employee_name is None:
                employee_name = cls.DEFAULT_EMPLOYEE_NAME

            sap_path = cls.get_sap_data_path(employee_name)

            if not sap_path.exists():
                import pandas as pd
                from datetime import datetime, timedelta

                # Tạo dữ liệu mẫu
                data = []
                start_date = datetime.now() - timedelta(days=30)

                for i in range(30):
                    order_date = start_date + timedelta(days=i)
                    revenue = 10000000 + (i * 500000)  # Tăng dần
                    profit = revenue * 0.2  # 20% lợi nhuận

                    data.append({
                        'Order_ID': f'ORD{1000 + i}',
                        'Order_Date': order_date.strftime('%Y-%m-%d'),
                        'Customer': f'Customer_{i + 1}',
                        'Product': f'Product_{((i % 5) + 1)}',
                        'Quantity': (i % 10) + 1,
                        'Revenue': revenue,
                        'Profit': profit,
                        'Status': 'Completed' if i % 10 != 0 else 'Pending',
                        'Employee': employee_name
                    })

                df = pd.DataFrame(data)
                df.to_excel(sap_path, index=False)
                print(f"✅ Đã tạo dữ liệu SAP mẫu tại: {sap_path}")

                return True
            else:
                print(f"✅ File SAP đã tồn tại: {sap_path}")
                return True

        except Exception as e:
            print(f"❌ Lỗi tạo dữ liệu SAP mẫu: {e}")
            return False

    @classmethod
    def check_data_availability(cls, employee_name=None):
        """Kiểm tra xem dữ liệu có sẵn không"""
        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        work_log_path = cls.get_work_log_path(employee_name)
        sap_path = cls.get_sap_data_path(employee_name)

        work_log_exists = work_log_path.exists()
        sap_exists = sap_path.exists()

        return {
            'work_log': work_log_exists,
            'sap_data': sap_exists,
            'work_log_path': str(work_log_path),
            'sap_path': str(sap_path)
        }

    @classmethod
    def get_all_months_data(cls, employee_name=None):
        """Lấy đường dẫn dữ liệu cho tất cả các tháng trong năm hiện tại"""
        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        current_year = datetime.now().year
        month_paths = []

        for month in range(1, 13):
            month_str = f"{current_year}_{month:02d}"
            base_path = f"{cls.BASE_DATA_PATH}/{employee_name}/{month_str}"

            month_paths.append({
                'month': month,
                'month_str': month_str,
                'base_path': Path(base_path),
                'work_log': Path(f"{base_path}/work_logs_{employee_name}_{month_str}.xlsx"),
                'sap_data': Path(f"{base_path}/sap_data.xlsx")
            })

        return month_paths

    @classmethod
    def get_config_summary(cls):
        """Lấy tổng quan cấu hình"""
        return {
            'app_name': cls.APP_NAME,
            'version': cls.VERSION,
            'employee_name': cls.DEFAULT_EMPLOYEE_NAME,
            'gemini_model': cls.GEMINI_MODEL,
            'has_api_key': bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY != "YOUR_API_KEY_HERE"),
            'debug_mode': cls.DEBUG_MODE,
            'base_data_path': cls.BASE_DATA_PATH,
            'max_tokens': cls.MAX_TOKENS,
            'temperature': cls.TEMPERATURE
        }

    @classmethod
    def get_current_year_data_path(cls, employee_name=None):
        """Lấy đường dẫn dữ liệu cho toàn bộ năm hiện tại"""
        from datetime import datetime

        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        current_year = datetime.now().year
        base_path = Path(f"{cls.BASE_DATA_PATH}/{employee_name}")

        # Tạo dictionary chứa đường dẫn tất cả các tháng trong năm
        year_data = {
            'base_dir': base_path,
            'year': current_year,
            'months': {}
        }

        for month in range(1, 13):
            month_str = f"{current_year}_{month:02d}"
            month_path = base_path / month_str

            year_data['months'][month] = {
                'month': month,
                'month_str': month_str,
                'base_path': month_path,
                'work_log': month_path / f"work_logs_{employee_name}_{month_str}.xlsx",
                'sap_data': month_path / "sap_data.xlsx"
            }

        return year_data

    @classmethod
    def get_current_year_work_logs(cls, employee_name=None):
        """Lấy danh sách tất cả work logs của năm hiện tại"""
        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        from datetime import datetime
        import pandas as pd
        from pathlib import Path

        current_year = datetime.now().year
        all_work_logs = []

        for month in range(1, 13):
            month_str = f"{current_year}_{month:02d}"
            work_log_path = Path(
                f"{cls.BASE_DATA_PATH}/{employee_name}/{month_str}/work_logs_{employee_name}_{month_str}.xlsx")

            if work_log_path.exists():
                try:
                    # Đọc tất cả sheets từ file work log
                    excel_file = pd.ExcelFile(work_log_path)
                    sheets_data = {}

                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(work_log_path, sheet_name=sheet_name)
                        df['Month'] = month  # Thêm cột tháng
                        df['Year'] = current_year  # Thêm cột năm
                        sheets_data[sheet_name] = df

                    all_work_logs.append({
                        'month': month,
                        'month_str': month_str,
                        'path': work_log_path,
                        'sheets': sheets_data,
                        'exists': True
                    })
                except Exception as e:
                    print(f"⚠️ Lỗi đọc work log tháng {month}: {e}")
                    all_work_logs.append({
                        'month': month,
                        'month_str': month_str,
                        'path': work_log_path,
                        'exists': False,
                        'error': str(e)
                    })
            else:
                all_work_logs.append({
                    'month': month,
                    'month_str': month_str,
                    'path': work_log_path,
                    'exists': False
                })

        return all_work_logs

    @classmethod
    def get_current_year_sap_data(cls, employee_name=None):
        """Lấy danh sách tất cả SAP data của năm hiện tại"""
        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        from datetime import datetime
        import pandas as pd
        from pathlib import Path

        current_year = datetime.now().year
        all_sap_data = []

        for month in range(1, 13):
            month_str = f"{current_year}_{month:02d}"
            sap_path = Path(f"{cls.BASE_DATA_PATH}/{employee_name}/{month_str}/sap_data.xlsx")

            if sap_path.exists():
                try:
                    # Đọc tất cả sheets từ file SAP
                    excel_file = pd.ExcelFile(sap_path)
                    sheets_data = {}

                    for sheet_name in excel_file.sheet_names:
                        df = pd.read_excel(sap_path, sheet_name=sheet_name)
                        df['Month'] = month  # Thêm cột tháng
                        df['Year'] = current_year  # Thêm cột năm
                        sheets_data[sheet_name] = df

                    all_sap_data.append({
                        'month': month,
                        'month_str': month_str,
                        'path': sap_path,
                        'sheets': sheets_data,
                        'exists': True
                    })
                except Exception as e:
                    print(f"⚠️ Lỗi đọc SAP data tháng {month}: {e}")
                    all_sap_data.append({
                        'month': month,
                        'month_str': month_str,
                        'path': sap_path,
                        'exists': False,
                        'error': str(e)
                    })
            else:
                all_sap_data.append({
                    'month': month,
                    'month_str': month_str,
                    'path': sap_path,
                    'exists': False
                })

        return all_sap_data

    @classmethod
    def merge_year_data(cls, employee_name=None):
        """Gộp dữ liệu từ tất cả các tháng trong năm hiện tại thành một DataFrame"""
        if employee_name is None:
            employee_name = cls.DEFAULT_EMPLOYEE_NAME

        from datetime import datetime
        import pandas as pd

        current_year = datetime.now().year
        merged_data = {
            'work_log': {},
            'sap_data': {}
        }

        print(f"📅 Đang gộp dữ liệu năm {current_year} cho {employee_name}...")

        # Gộp work logs
        work_logs = cls.get_current_year_work_logs(employee_name)
        for month_data in work_logs:
            if month_data['exists'] and 'sheets' in month_data:
                for sheet_name, df in month_data['sheets'].items():
                    if sheet_name not in merged_data['work_log']:
                        merged_data['work_log'][sheet_name] = []
                    merged_data['work_log'][sheet_name].append(df)

        # Gộp SAP data
        sap_data_list = cls.get_current_year_sap_data(employee_name)
        for month_data in sap_data_list:
            if month_data['exists'] and 'sheets' in month_data:
                for sheet_name, df in month_data['sheets'].items():
                    if sheet_name not in merged_data['sap_data']:
                        merged_data['sap_data'][sheet_name] = []
                    merged_data['sap_data'][sheet_name].append(df)

        # Gộp các DataFrame theo sheet
        for data_type in ['work_log', 'sap_data']:
            for sheet_name, df_list in merged_data[data_type].items():
                if df_list:
                    merged_data[data_type][sheet_name] = pd.concat(df_list, ignore_index=True)
                    print(f"   ✅ {data_type}.{sheet_name}: {len(merged_data[data_type][sheet_name])} dòng")
                else:
                    merged_data[data_type][sheet_name] = pd.DataFrame()

        # Tính toán tổng quan
        total_orders = 0
        total_revenue = 0
        total_profit = 0
        total_fraud = 0

        if 'Orders' in merged_data['sap_data']:
            orders_df = merged_data['sap_data']['Orders']
            if not orders_df.empty:
                total_orders = len(orders_df)
                if 'Revenue' in orders_df.columns:
                    total_revenue = orders_df['Revenue'].sum()
                if 'Profit' in orders_df.columns:
                    total_profit = orders_df['Profit'].sum()

        if 'Fraud_Events' in merged_data['work_log']:
            fraud_df = merged_data['work_log']['Fraud_Events']
            if not fraud_df.empty:
                total_fraud = len(fraud_df)

        merged_data['summary'] = {
            'year': current_year,
            'employee_name': employee_name,
            'total_orders': total_orders,
            'total_revenue': total_revenue,
            'total_profit': total_profit,
            'total_fraud': total_fraud,
            'months_with_data': len([m for m in work_logs if m['exists']])
        }

        print(
            f"✅ Đã gộp dữ liệu năm {current_year}: {total_orders} đơn hàng, {total_revenue:,.0f} doanh thu, {total_fraud} sự kiện gian lận")

        return merged_data

    @classmethod
    def get_year_data_summary(cls, employee_name=None):
        """Lấy tổng quan dữ liệu cả năm - bổ sung mới"""
        try:
            from datetime import datetime
            import pandas as pd

            if employee_name is None:
                employee_name = cls.DEFAULT_EMPLOYEE_NAME

            current_year = datetime.now().year
            print(f"📊 Đang tổng hợp dữ liệu năm {current_year} cho {employee_name}...")

            # Lấy tất cả dữ liệu tháng
            all_months = cls.get_all_months_data(employee_name)

            total_orders = 0
            total_revenue = 0
            total_profit = 0
            total_fraud = 0
            months_with_data = 0

            # Danh sách tháng có dữ liệu
            months_with_data_list = []

            for month_data in all_months:
                month_has_data = False

                # Kiểm tra file SAP
                if month_data['sap_data'].exists():
                    try:
                        df = pd.read_excel(month_data['sap_data'])
                        if not df.empty:
                            total_orders += len(df)
                            if 'Revenue' in df.columns:
                                total_revenue += df['Revenue'].sum()
                            if 'Profit' in df.columns:
                                total_profit += df['Profit'].sum()
                            month_has_data = True
                    except Exception as e:
                        print(f"⚠️ Lỗi đọc SAP data tháng {month_data['month']}: {e}")

                # Kiểm tra file work log
                if month_data['work_log'].exists():
                    try:
                        df = pd.read_excel(month_data['work_log'])
                        if not df.empty:
                            # Kiểm tra cột IsFraud
                            if 'IsFraud' in df.columns:
                                total_fraud += df['IsFraud'].sum()
                            month_has_data = True
                    except Exception as e:
                        print(f"⚠️ Lỗi đọc work log tháng {month_data['month']}: {e}")

                if month_has_data:
                    months_with_data += 1
                    months_with_data_list.append(month_data['month'])

            # Tính các chỉ số trung bình
            avg_orders_per_month = round(total_orders / max(months_with_data, 1), 1) if months_with_data > 0 else 0
            avg_revenue_per_month = round(total_revenue / max(months_with_data, 1), 0) if months_with_data > 0 else 0
            avg_profit_per_month = round(total_profit / max(months_with_data, 1), 0) if months_with_data > 0 else 0

            summary = {
                'year': current_year,
                'employee_name': employee_name,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'total_profit': total_profit,
                'total_fraud': int(total_fraud),
                'months_with_data': months_with_data,
                'months_with_data_list': months_with_data_list,
                'avg_orders_per_month': avg_orders_per_month,
                'avg_revenue_per_month': avg_revenue_per_month,
                'avg_profit_per_month': avg_profit_per_month,
                'fraud_rate': round((total_fraud / max(total_orders, 1)) * 100, 2) if total_orders > 0 else 0,
                'profit_margin': round((total_profit / max(total_revenue, 1)) * 100, 2) if total_revenue > 0 else 0,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }

            print(f"✅ Đã tổng hợp dữ liệu năm {current_year}:")
            print(f"   📅 Tháng có dữ liệu: {months_with_data}/12")
            print(f"   📦 Tổng đơn hàng: {total_orders:,}")
            print(f"   💰 Tổng doanh thu: {total_revenue:,.0f} VND")
            print(f"   💵 Tổng lợi nhuận: {total_profit:,.0f} VND")
            print(f"   ⚠️ Tổng gian lận: {int(total_fraud)}")

            return summary

        except Exception as e:
            print(f"❌ Lỗi tổng hợp dữ liệu năm: {e}")
            import traceback
            traceback.print_exc()
            return None

