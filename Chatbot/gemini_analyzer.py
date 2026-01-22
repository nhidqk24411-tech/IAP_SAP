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
        "gemini-3-pro-preview": 100,
        "gemini-3-flash-preview": 95,
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

        # Kiểm tra nếu câu hỏi liên quan đến email
        is_email_request = any(keyword in question.lower() for keyword in [
            'gửi mail', 'send email', 'gửi email', 'thông báo', 'notify',
            'thông báo cho', 'inform', 'email cho', 'gửi thư'
        ])

        # Thêm email guidance nếu cần
        email_guidance = ""
        if is_email_request:
            email_guidance = """
              🔹 **HƯỚNG DẪN XỬ LÝ YÊU CẦU EMAIL:**

              Người dùng muốn gửi email. Bạn nên:

              1️⃣ **PHÂN TÍCH YÊU CẦU:**
              - Xác định mục đích: thông báo, cảnh báo, ghi nhận, hay hướng dẫn cải thiện?
              - Đề xuất nội dung phù hợp dựa trên dữ liệu hiệu suất

              2️⃣ **ĐỀ XUẤT NỘI DUNG:**
              - Cung cấp mẫu email chuyên nghiệp
              - Bao gồm các điểm chính cần truyền đạt
              - Đề xuất timeline và hành động cụ thể

              3️⃣ **HƯỚNG DẪN TIẾP THEO:**
              - Gợi ý sử dụng chức năng gửi email tích hợp trong chatbot
              - Nhắc kiểm tra nội dung trước khi gửi

              📧 **MẪU EMAIL MẪU:**
              ```
              Tiêu đề: [Loại thông báo] - [Tên nhân viên/department]

              Kính gửi [Tên nhân viên],

              Dựa trên phân tích hiệu suất [thời gian], chúng tôi nhận thấy:

              📊 KẾT QUẢ CHÍNH:
              - [Điểm mạnh/Thành tích]
              - [Điểm cần cải thiện]
              - [Số liệu cụ thể nếu có]

              🎯 ĐỀ XUẤT HÀNH ĐỘNG:
              1. [Hành động 1 - cụ thể, đo lường được]
              2. [Hành động 2 - có timeline rõ ràng]
              3. [Hỗ trợ cần thiết từ quản lý]

              📅 THỜI GIAN: [X] ngày/tuần

              Chúng tôi tin tưởng vào khả năng cải thiện của bạn.

              Trân trọng,
              [Tên quản lý]
              ```
              """

        return f"""
             Bạn là **PowerSight AI** – một **Coach chiến lược, Advisor phân tích dữ liệu và Partner đồng hành phát triển**.

             {email_guidance}

             =============================
             👤 BỐI CẢNH PHÂN TÍCH
             =============================
             - Người dùng: {context_data.get('employee_name', 'Chưa xác định')}
             - Vai trò: {'Quản lý' if context_data.get('is_manager', False) else 'Nhân viên'}
             - Thời điểm: {context_data.get('data_timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}

             =============================
             📊 DỮ LIỆU HIỆN CÓ
             =============================
             {basic_insights}

             {year_insights}

             =============================
             ❓ CÂU HỎI CỦA NGƯỜI DÙNG
             =============================
             "{question}"

             =============================
             {'📧 HƯỚNG XỬ LÝ CHO EMAIL' if is_email_request else '🧠 PHÂN TÍCH CHUYÊN SÂU'}
             =============================
             {'Nếu đây là yêu cầu gửi email, hãy cung cấp mẫu email chi tiết và hướng dẫn sử dụng tính năng gửi email tự động của hệ thống.' if is_email_request else 'Phân tích dựa trên dữ liệu và đưa ra khuyến nghị thực tế.'}

             =============================
             📝 CẤU TRÚC TRẢ LỜI
             =============================

             1️⃣ **TRẢ LỜI TRỰC TIẾP**
             {'→ Đề xuất nội dung email phù hợp' if is_email_request else '→ 1-2 câu trả lời trọng tâm'}

             2️⃣ **PHÂN TÍCH DỮ LIỆU**
             → Sử dụng dữ liệu thực tế để hỗ trợ đề xuất

             3️⃣ **ĐỀ XUẤT HÀNH ĐỘNG**
             {'→ Mẫu email chi tiết + hướng dẫn gửi' if is_email_request else '→ 1-3 hành động cụ thể, khả thi'}

             {'4️⃣ **HƯỚNG DẪN KỸ THUẬT**\n→ Hướng dẫn sử dụng tính năng gửi email tích hợp trong chatbot' if is_email_request else ''}

             =============================
             🎙️ VĂN PHONG
             =============================
             - Chuyên nghiệp, thân thiện
             - Tiếng Việt tự nhiên
             - Tập trung giải pháp
             - Đồng hành cùng phát triển
             """

    def prepare_employee_list(self, employees: list) -> str:
        """Chuẩn bị danh sách nhân viên cho prompt"""
        if not employees:
            return "Không có danh sách nhân viên"

        result = []
        for i, emp in enumerate(employees[:10]):  # Giới hạn 10 nhân viên
            name = emp.get('name', 'N/A')
            emp_id = emp.get('id', 'N/A')
            result.append(f"{i + 1}. {name} (ID: {emp_id})")

        return "\n".join(result)

    def handle_email_suggestion(self, ai_response):
        """Phân tích phản hồi AI và hiển thị option gửi email"""
        if "mẫu email" in ai_response.lower() or "email đề xuất" in ai_response.lower():
            # Hiển thị button để gửi email
            self.show_email_action_buttons(ai_response)

    def show_email_action_buttons(self, ai_response):
        """Hiển thị nút hành động gửi email"""
        # Tạo button trong chat
        button_html = """
        <div style='margin: 10px 0; padding: 15px; background-color: #f0f9ff; border-radius: 8px; border: 1px solid #bae6fd;'>
            <b>📧 GỬI EMAIL NGAY</b>
            <p>Bạn muốn gửi email này đến nhân viên?</p>
            <button onclick='window.pywebview.api.sendEmailNow()' style='
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                margin-right: 10px;
                cursor: pointer;
            '>Gửi ngay</button>
            <button onclick='window.pywebview.api.customizeEmail()' style='
                background-color: #f1f5f9;
                color: #475569;
                border: 1px solid #e2e8f0;
                padding: 8px 16px;
                border-radius: 6px;
                cursor: pointer;
            '>Tùy chỉnh</button>
        </div>
        """

        self.chat_display.append(button_html)

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