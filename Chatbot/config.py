# config.py - Cấu hình tối ưu
import os
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
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))
    TEMPERATURE = float(os.getenv("TEMPERATURE", "0.4"))

    # ========== EMPLOYEE ==========
    DEFAULT_EMPLOYEE_NAME = os.getenv("DEFAULT_EMPLOYEE_NAME", "Giang")

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

        if not cls.GEMINI_API_KEY:
            print("❌ LỖI: GEMINI_API_KEY không được tìm thấy")
            return False

        print(f"📱 App: {cls.APP_NAME}")
        print(f"📦 Version: {cls.VERSION}")
        print(f"🤖 Model mặc định: {cls.GEMINI_MODEL}")
        print(f"👤 Employee: {cls.DEFAULT_EMPLOYEE_NAME}")
        print(f"🔑 API Key: {cls.GEMINI_API_KEY[:10]}...{cls.GEMINI_API_KEY[-10:]}")

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

            # Thử import API mới
            try:
                import google.genai as genai
                print("✅ Using google.genai (new API)")

                # API mới không có configure, chỉ cần set API key
                # Test bằng cách tạo client
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

                    return True

                except Exception as e:
                    print(f"❌ Lỗi khi test model: {e}")
                    return False

            except ImportError:
                # Fallback to old API
                print("⚠️ Using deprecated google.generativeai")
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