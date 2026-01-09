# gemini_analyzer.py - Gemini API (google.genai) + quota-aware fallback
# Optimized for flexible, mentor-style, XAI responses (no data repetition)
# Cập nhật để lấy dữ liệu từ DataProcessor

import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config


class GeminiAnalyzer:
    """Phân tích với Gemini AI - Ưu tiên model hiện đại nhất + quota cao"""

    # ------------------------------------------------------------------
    # Danh sách model được ưu tiên (hiện đại nhất trước)
    VALID_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",  # Có thể dùng nếu muốn test tính năng mới nhất

        # Gemini 2.5 Series (Stable & Production Ready)
        "gemini-2.5-flash",  # Cân bằng tốt nhất giữa tốc độ/giá/trí tuệ
        "gemini-2.5-flash-lite",  # Tối ưu chi phí cực thấp
        "gemini-2.5-pro",  # Bản ổn định cho các tác vụ suy luận logic

        # Gemini 2.0 Series (Legacy / LTS)
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro",
    ]

    # Độ ưu tiên model (cao nhất = 100)
    MODEL_PRIORITY = {
        "gemini-3-flash-preview": 100,
        "gemini-3-pro-preview": 95,
        "gemini-2.5-flash": 90,
        "gemini-2.5-flash-lite": 85,
        "gemini-2.5-pro": 80,
        "gemini-2.0-flash": 75,
        "gemini-2.0-flash-lite": 70,
        "gemini-2.0-pro": 65,
    }

    def __init__(self):
        self.genai_client = None
        self.active_model = None
        self.use_demo_mode = True
        self.api_type = "DEMO"

        print("🚀 Khởi tạo Gemini Analyzer (Modern Version)...")

        if not Config.GEMINI_API_KEY or Config.GEMINI_API_KEY in ("", "YOUR_API_KEY_HERE"):
            print("⚠️ Không có API Key, DEMO mode")
            return

        try:
            from google import genai
            self.genai_client = genai.Client(api_key=Config.GEMINI_API_KEY)
            self.find_best_model()

            if not self.use_demo_mode:
                print(f"✅ Dùng model: {self.active_model}")
            else:
                print("⚠️ Không có model phù hợp, DEMO")

        except Exception as e:
            print(f"❌ Lỗi khởi tạo Gemini: {e}")

    # ------------------------------------------------------------------

    def find_best_model(self):
        """Chọn model hiện đại nhất + quota cao nhất"""
        try:
            models = list(self.genai_client.models.list())
            available = []
            model_details = {}

            for m in models:
                short = m.name.split("/")[-1]
                if short in self.VALID_MODELS:
                    available.append(short)
                    model_details[short] = {
                        "name": m.name,
                        "display_name": m.display_name if hasattr(m, 'display_name') else short,
                        "version": m.version if hasattr(m, 'version') else "unknown",
                        "description": m.description if hasattr(m, 'description') else "",
                    }

            if not available:
                print("⚠️ Không tìm thấy model hợp lệ trong danh sách")
                return

            # Sắp xếp theo độ ưu tiên
            available.sort(key=lambda x: self.MODEL_PRIORITY.get(x, 0), reverse=True)

            self.active_model = available[0]
            self.use_demo_mode = False
            self.api_type = "API"

            print("📊 Model khả dụng (theo độ ưu tiên):")
            for i, m in enumerate(available[:5]):
                priority = self.MODEL_PRIORITY.get(m, 0)
                status = "✅ ĐANG CHỌN" if i == 0 else ""
                print(f"  {i + 1}. {m} (Priority: {priority}) {status}")

                if i == 0 and m in model_details:
                    details = model_details[m]
                    print(f"     📝 {details['display_name']}")
                    if details['description']:
                        print(f"     ℹ️  {details['description'][:100]}...")

        except Exception as e:
            print(f"❌ Lỗi chọn model: {e}")

    # ------------------------------------------------------------------

    def analyze_question(self, question: str, context_data: Dict[str, Any]) -> str:
        if self.use_demo_mode:
            return self.get_demo_response(question, context_data)

        prompt = self.create_smart_prompt(question, context_data)

        # Sắp xếp model theo độ ưu tiên
        models_to_try = sorted(
            self.VALID_MODELS,
            key=lambda x: self.MODEL_PRIORITY.get(x, 0),
            reverse=True
        )

        for model in models_to_try:
            try:
                print(f"📤 Gửi {model} (Priority: {self.MODEL_PRIORITY.get(model, 'N/A')})")
                response = self.genai_client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                text = response.text or ""
                self.active_model = model

                # Log token usage nếu có
                if hasattr(response, 'usage_metadata'):
                    usage = response.usage_metadata
                    print(
                        f"📊 Token usage: {usage.prompt_token_count} prompt, {usage.candidates_token_count} completion")

                return self.format_response(text, question)

            except Exception as e:
                if self.is_quota_error(e):
                    print(f"⚠️ {model} hết quota → thử model khác")
                    continue
                elif self.is_model_not_found_error(e):
                    print(f"⚠️ {model} không khả dụng → bỏ qua")
                    continue
                print(f"❌ Lỗi {model}: {str(e)[:100]}...")
                break

        return self.get_demo_response(question, context_data)

    # ------------------------------------------------------------------

    def is_quota_error(self, e: Exception) -> bool:
        error_str = str(e).lower()
        return any(k in error_str for k in ["quota", "429", "resource_exhausted", "rate limit"])

    def is_model_not_found_error(self, e: Exception) -> bool:
        error_str = str(e).lower()
        return any(k in error_str for k in ["not found", "invalid model", "model not available", "404"])

    # ------------------------------------------------------------------
    # XAI + Career Coach Prompt (Linh hoạt cho nhiều loại câu hỏi)

    def create_smart_prompt(self, question: str, context_data: Dict) -> str:
        # Trích xuất insights từ dữ liệu cả năm
        basic_insights = self.extract_basic_insights(context_data)

        # Trích xuất thêm insights từ dữ liệu cả năm nếu có
        year_insights = self.extract_year_insights(context_data)

        return f"""
           Bạn là **PowerSight AI** – một **Coach chiến lược, Advisor phân tích dữ liệu và Partner đồng hành phát triển**.

           Vai trò của bạn không chỉ là trả lời câu hỏi, mà là:
           - Hiểu **mục tiêu thực sự** đằng sau câu hỏi
           - Đưa ra **nhận định có chiều sâu dựa trên dữ liệu cả năm**
           - Đồng hành cùng nhân viên để **ra quyết định tốt hơn và phát triển bền vững**

           =============================
           🎯 NGUYÊN TẮC LÀM VIỆC CỐT LÕI
           =============================
           - Trả lời **TRỰC TIẾP – ĐÚNG TRỌNG TÂM** trước tiên
           - Chỉ sử dụng **dữ liệu CÓ GIÁ TRỊ cho quyết định**
           - **Không liệt kê dữ liệu thừa**, không kể lại báo cáo
           - Khi dữ liệu chưa đủ: **chỉ rõ khoảng trống và rủi ro**
           - Phân tích với tư duy của **coach & consultant thực tế**, không lý thuyết giáo khoa
           - **Phân tích theo xu hướng tháng** khi có dữ liệu cả năm

           =============================
           👤 BỐI CẢNH PHÂN TÍCH
           =============================
           - Nhân viên: {context_data.get('employee_name', 'Chưa xác định')}
           - Thời điểm phân tích: {context_data.get('data_timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}

           =============================
           📊 DỮ LIỆU HIỆN CÓ
           =============================
           {basic_insights}

           {year_insights}

           =============================
           📁 DỮ LIỆU CHI TIẾT CÓ THỂ KHAI THÁC
           =============================
           {self.prepare_detailed_data(context_data)}

           =============================
           ❓ VẤN ĐỀ / CÂU HỎI ĐANG ĐƯỢC QUAN TÂM
           =============================
           "{question}"

           =============================
           🧠 CÁCH TIẾP CẬN VẤN ĐỀ (LINH HOẠT THEO NGỮ CẢNH)
           =============================

           🔹 NẾU CÂU HỎI LIÊN QUAN HIỆU SUẤT / PHÁT TRIỂN CÁ NHÂN:
           - Nhận diện **điểm mạnh cốt lõi cần tiếp tục phát huy**
           - Chỉ ra **điểm nghẽn lớn nhất đang kìm hiệu suất** (phân tích theo tháng nếu có dữ liệu cả năm)
           - Đề xuất **1–2 hành động thực tế, có thể triển khai ngay**
           - Gợi ý **mốc thời gian hợp lý** để thấy kết quả

           🔹 NẾU CÂU HỎI LIÊN QUAN DỮ LIỆU SAP (đơn hàng, doanh thu, lợi nhuận):
           - Trả lời **đúng số liệu liên quan trực tiếp** (theo tháng nếu có dữ liệu cả năm)
           - Nhận định **xu hướng & tác động kinh doanh** qua các tháng (nếu có dữ liệu cả năm)
           - Đề xuất **hướng tối ưu ưu tiên cao**, tránh dàn trải

           🔹 NẾU CÂU HỎI LIÊN QUAN RỦI RO / GIAN LẬN:
           - Xác định **nguồn rủi ro từ dữ liệu** (theo tháng nếu có dữ liệu cả năm)
           - Đánh giá **mức độ ảnh hưởng đến hiệu suất / uy tín**
           - Đề xuất **biện pháp kiểm soát thực tế**, không hình thức

           🔹 NẾU CÂU HỎI LIÊN QUAN MỤC TIÊU / KẾ HOẠCH:
           - Giúp làm rõ **mục tiêu thực sự cần đạt**
           - Đề xuất mục tiêu theo **SMART**, tránh mục tiêu ảo
           - Chỉ rõ **KPI then chốt** và bước đi tiếp theo

           =============================
           📝 CẤU TRÚC CÂU TRẢ LỜI (BẮT BUỘC TUÂN THỦ)
           =============================

           1️⃣ **TRẢ LỜI TRỰC TIẾP**
           → 1–2 câu trả lời đúng trọng tâm vấn đề

           2️⃣ **DỮ LIỆU THEN CHỐT**
           → Chỉ nêu số liệu ảnh hưởng đến kết luận (có thể theo tháng nếu có dữ liệu cả năm)

           3️⃣ **NHẬN ĐỊNH CHUYÊN GIA**
           → Phân tích ngắn gọn "vì sao điều này quan trọng"

           4️⃣ **HÀNH ĐỘNG KHUYẾN NGHỊ**
           → 1–3 bước cụ thể, khả thi, ưu tiên tác động cao

           =============================
           🎙️ VĂN PHONG & THÁI ĐỘ
           =============================
           - Như một **coach đồng hành**, không phán xét
           - Như một **advisor dữ liệu**, không cảm tính
           - Như một **partner**, cùng hướng đến kết quả
           - Rõ ràng, súc tích, tập trung giải pháp
           - Tiếng Việt tự nhiên, chuyên nghiệp
           """

    def extract_year_insights(self, data: Dict[str, Any]) -> str:
        """Trích xuất insights từ dữ liệu cả năm"""
        try:
            year_data = data.get('year_data', {})
            if not year_data or 'summary' not in year_data:
                return ""

            summary = year_data['summary']
            year = summary.get('year', datetime.now().year)
            months_with_data = summary.get('months_with_data', 0)
            total_orders = summary.get('total_orders', 0)
            total_revenue = summary.get('total_revenue', 0)
            total_profit = summary.get('total_profit', 0)
            total_fraud = summary.get('total_fraud', 0)
            completion_rate = summary.get('completion_rate', 0)
            best_month = summary.get('best_month', 0)
            best_month_revenue = summary.get('best_month_revenue', 0)

            insights = []
            insights.append(f"📅 **DỮ LIỆU CẢ NĂM {year} ({months_with_data}/12 tháng có dữ liệu):**")
            insights.append(f"   • Tổng đơn hàng cả năm: {total_orders:,}")
            insights.append(f"   • Tổng doanh thu cả năm: {total_revenue:,.0f} VND")
            insights.append(f"   • Tổng lợi nhuận cả năm: {total_profit:,.0f} VND")
            insights.append(f"   • Tổng gian lận cả năm: {total_fraud}")
            if completion_rate > 0:
                insights.append(f"   • Tỷ lệ hoàn thành cả năm: {completion_rate:.1f}%")
            if best_month > 0:
                insights.append(f"   • Tháng hiệu quả nhất: Tháng {best_month} ({best_month_revenue:,.0f} VND)")

            return "\n".join(insights)

        except Exception as e:
            print(f"⚠️ Lỗi trích xuất year insights: {e}")
            return ""
    def extract_basic_insights(self, data: Dict[str, Any]) -> str:
        """Trích xuất insights cơ bản từ dữ liệu thực tế"""
        insights = []

        # Lấy metrics thực tế
        m = data.get("metrics", {})

        # Thêm các chỉ số thực tế
        insights.append(f"📦 Tổng đơn hàng: {m.get('total_orders', 0):,}")
        insights.append(f"✅ Đã hoàn thành: {m.get('completed_orders', 0):,} ({m.get('completion_rate', 0)}%)")
        insights.append(f"⏳ Chờ xử lý: {m.get('pending_orders', 0):,}")
        insights.append(f"💰 Doanh thu: {m.get('total_revenue', 0):,.0f} VND")
        insights.append(f"💵 Lợi nhuận: {m.get('total_profit', 0):,.0f} VND")
        insights.append(f"⚠️ Sự kiện gian lận: {m.get('fraud_count', 0)}")

        if m.get('profit_margin', 0) > 0:
            insights.append(f"📈 Tỷ suất lợi nhuận: {m.get('profit_margin', 0):.1f}%")

        if m.get('on_time_delivery', 0) > 0:
            insights.append(f"🚚 Giao hàng đúng hạn: {m.get('on_time_delivery', 0):.1f}%")

        return "📌 " + "\n📌 ".join(insights)
    def prepare_detailed_data(self, context_data: Dict[str, Any]) -> str:
        """Chuẩn bị dữ liệu chi tiết từ DataProcessor để AI tham khảo"""
        sap = context_data.get("sap_data", {})
        wl = context_data.get("work_log", {})
        year_data = context_data.get("year_data", {})
        details = []

        # Thông tin từ summary
        if sap.get('summary', {}):
            summary = sap['summary']
            details.append(f"📦 Tổng đơn hàng: {summary.get('total_orders', 0):,}")
            details.append(f"✅ Đã hoàn thành: {summary.get('completed_orders', 0):,}")
            details.append(f"⏳ Chờ xử lý: {summary.get('pending_orders_count', 0):,}")
            details.append(f"💰 Doanh thu: {summary.get('total_revenue', 0):,.0f} VND")
            details.append(f"💵 Lợi nhuận: {summary.get('total_profit', 0):,.0f} VND")

            # Thống kê theo vùng
            region_stats = summary.get('region_stats', {})
            if region_stats:
                region_list = [f'{k}: {v}' for k, v in list(region_stats.items())[:3]]
                details.append(f"📍 Top vùng: {', '.join(region_list)}")

            # Thống kê theo sản phẩm
            product_stats = summary.get('product_stats', {})
            if product_stats:
                product_list = [f'{k}: {v}' for k, v in list(product_stats.items())[:3]]
                details.append(f"📊 Top sản phẩm: {', '.join(product_list)}")

        # Thông tin từ dữ liệu cả năm
        if year_data:
            sap_sheets = year_data.get('sap_data', {}).get('sheets', {})
            work_log_sheets = year_data.get('work_log', {}).get('sheets', {})

            # Thông tin đơn hàng cả năm
            if 'Orders' in sap_sheets and sap_sheets['Orders'] is not None:
                orders_df = sap_sheets['Orders']
                if not orders_df.empty:
                    details.append(f"📅 Đơn hàng cả năm: {len(orders_df):,} đơn")

                    # Phân tích theo tháng
                    if 'Month' in orders_df.columns:
                        monthly_summary = orders_df.groupby('Month').size()
                        top_months = monthly_summary.nlargest(3)
                        details.append(
                            f"📈 Top tháng đơn hàng: {', '.join([f'Tháng {m}: {c}' for m, c in top_months.items()])}")

            # Thông tin gian lận cả năm
            if 'Fraud_Events' in work_log_sheets and work_log_sheets['Fraud_Events'] is not None:
                fraud_df = work_log_sheets['Fraud_Events']
                if not fraud_df.empty:
                    details.append(f"⚠️ Gian lận cả năm: {len(fraud_df):,} sự kiện")

                    # Phân tích theo tháng
                    if 'Month' in fraud_df.columns:
                        monthly_fraud = fraud_df.groupby('Month').size()
                        if not monthly_fraud.empty:
                            worst_month = monthly_fraud.idxmax()
                            details.append(f"📉 Tháng nhiều gian lận nhất: Tháng {worst_month}")

        # Ví dụ về đơn hàng
        pending_orders = sap.get('summary', {}).get('pending_orders', [])
        if pending_orders:
            sample_orders = []
            for i, order in enumerate(pending_orders[:3]):
                if isinstance(order, dict):
                    sample_orders.append(
                        f"  {i + 1}. {order.get('Order_ID', 'N/A')} - {order.get('Status', 'N/A')} - {order.get('Customer', 'N/A')}")
            if sample_orders:
                details.append("📋 Mẫu đơn hàng chờ xử lý:\n" + "\n".join(sample_orders))

        # Thông tin work log
        if wl.get('summary', {}):
            wl_summary = wl['summary']
            details.append(f"⚡ Sự kiện gian lận: {wl_summary.get('fraud_count', 0)}")
            details.append(f"🕒 Tổng thời gian làm việc: {wl_summary.get('total_work_hours', 0)} giờ")
            details.append(f"⚠️ Cảnh báo nghiêm trọng: {wl_summary.get('critical_count', 0)}")

        if not details:
            return "Không có dữ liệu chi tiết"

        return "\n".join(details)

    # ------------------------------------------------------------------

    def format_response(self, response: str, question: str) -> str:
        return (
            "◆ POWER SIGHT AI ◆\n"
            "────────────────────────\n"
            f"• Thời gian: {datetime.now():%d/%m/%Y %H:%M}\n"
            f"• Chế độ xử lý: {self.api_type}\n"
            f"• Model: {self.active_model or 'DEMO'}\n"
            "────────────────────────\n\n"
            "❓ CÂU HỎI\n"
            f"{question}\n\n"
            "📊 PHÂN TÍCH & TRẢ LỜI\n"
            f"{response}\n\n"
            "────────────────────────\n"
            "ℹ️ Ghi chú: Phân tích được tạo bởi AI dựa trên dữ liệu cả năm, nên đối chiếu với thực tế vận hành."
        )

    def get_demo_response(self, question: str, context_data: Dict) -> str:
        return self.format_response(
            "**DEMO MODE** – Hệ thống đang ở chế độ trình diễn.\n\n"
            "📝 *Để sử dụng tính năng đầy đủ, vui lòng:*\n"
            "1. Cấu hình API Key trong file config.py\n"
            "2. Chọn model phù hợp trong VALID_MODELS\n"
            "3. Đảm bảo quota API còn hạn\n\n"
            "🔧 *Ví dụ phân tích thực tế sẽ bao gồm:*\n"
            "- Phân tích SWOT chi tiết dựa trên dữ liệu cả năm\n"
            "- Chiến lược hành động SMART theo tháng\n"
            "- KPIs đo lường tiến bộ\n"
            "- Tư vấn phát triển nghề nghiệp dựa trên xu hướng",
            question
        )

    # ------------------------------------------------------------------
    # Tiện ích bổ sung

    def get_model_info(self) -> Dict:
        """Lấy thông tin về model đang sử dụng"""
        return {
            "active_model": self.active_model,
            "api_type": self.api_type,
            "is_demo": self.use_demo_mode,
            "priority": self.MODEL_PRIORITY.get(self.active_model, "N/A"),
            "valid_models_count": len(self.VALID_MODELS),
        }