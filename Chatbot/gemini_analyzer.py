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
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",  # Có thể dùng nếu muốn test tính năng mới nhất

        # Gemini 2.5 Series (Stable & Production Ready)
        "gemini-2.5-flash",  # Cân bằng tốt nhất giữa tốc độ/giá/trí tuệ # Tối ưu chi phí cực thấp
        "gemini-2.5-pro",  # Bản ổn định cho các tác vụ suy luận logic

        # Gemini 2.0 Series (Legacy / LTS)
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-pro",
    ]

    # Độ ưu tiên model (cao nhất = 100)
    MODEL_PRIORITY = {
        "gemini-2.5-flash-lite": 100,
        "gemini-3-flash-preview": 95,
        "gemini-3-pro-preview": 90,
        "gemini-2.5-flash": 85,
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
    # Thêm vào class GeminiAnalyzer trong gemini_analyzer.py

    # Thêm hàm mới để định dạng email đẹp hơn
    def generate_email_content(self, employees_data, email_type="improvement"):
        """Tạo nội dung email dựa trên dữ liệu nhân viên bằng Gemini - CẢI THIỆN ĐỊNH DẠNG"""
        try:
            # Tạo prompt dựa trên số lượng nhân viên
            if len(employees_data) == 1:
                prompt = self._create_single_employee_email_prompt_improved(employees_data[0])
            else:
                prompt = self._create_multiple_employees_email_prompt_improved(employees_data)

            if self.use_demo_mode or not self.genai_client:
                return self._get_fallback_email_content_improved(employees_data)

            # Gọi Gemini với model hiện tại
            try:
                response = self.genai_client.models.generate_content(
                    model=self.active_model if self.active_model else "gemini-2.0-flash",
                    contents=prompt
                )

                if response and response.text:
                    return self._format_email_response(response.text, employees_data)
                else:
                    return self._get_fallback_email_content_improved(employees_data)

            except Exception as api_error:
                print(f"⚠️ Gemini API error: {api_error}")
                return self._get_fallback_email_content_improved(employees_data)

        except Exception as e:
            print(f"❌ Lỗi tạo email content: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_email_content_improved(employees_data)

    def _create_single_employee_email_prompt_improved(self, employee_data):
        """Tạo prompt cho email 1 nhân viên - Định dạng tốt hơn"""
        metrics = employee_data.get('metrics', {})
        strengths = metrics.get('strengths', [])
        weaknesses = metrics.get('weaknesses', [])
        emp_name = employee_data.get('name', '')
        emp_id = employee_data.get('id', '')

        # Format metrics để hiển thị đẹp
        metrics_summary = f"""
    DỮ LIỆU HIỆU SUẤT NHÂN VIÊN:
    • Tên: {emp_name} (Mã: {emp_id})
    • Xếp hạng: {metrics.get('rank', 'Chưa xếp hạng')} {metrics.get('rank_emoji', '')}
    • Điểm tổng thể: {metrics.get('overall_score', 0)}/100
    • Tổng đơn hàng: {metrics.get('total_orders', 0)}
    • Đã hoàn thành: {metrics.get('completed_orders', 0)} ({metrics.get('completion_rate', 0)}%)
    • Doanh thu: {metrics.get('total_revenue', 0):,.0f} VND
    • Lợi nhuận: {metrics.get('total_profit', 0):,.0f} VND
    • Sự kiện gian lận: {metrics.get('total_fraud', 0)}
    • Thời gian làm việc: {metrics.get('working_hours', 0):.1f} giờ
    """

        if strengths:
            metrics_summary += f"• Điểm mạnh: {', '.join(strengths)}\n"
        if weaknesses:
            metrics_summary += f"• Điểm cần cải thiện: {', '.join(weaknesses)}\n"

        return f"""
    Bạn là quản lý trong công ty. Hãy viết một email nhắc nhở công việc cho nhân viên dựa trên dữ liệu hiệu suất.

    {metrics_summary}

    YÊU CẦU VIẾT EMAIL (PHẢI TUÂN THỦ ĐỊNH DẠNG SAU):
    1. TIÊU ĐỀ EMAIL: Chỉ 1 dòng, không có ký tự đặc biệt, không quá dài
    2. NỘI DUNG EMAIL: Định dạng rõ ràng, dễ đọc
       - Dòng 1: Chào hỏi
       - Dòng 2-4: Đánh giá tích cực (nếu có)
       - Dòng 5-7: Đề xuất cải thiện (nếu có)
       - Dòng 8-10: Đề xuất hành động cụ thể
       - Dòng cuối: Kết thúc lịch sự
    3. KHÔNG SỬ DỤNG MARKDOWN, CHỈ DÙNG TEXT THUẦN
    4. MỖI ĐOẠN CÁCH NHAU BẰNG 1 DÒNG TRỐNG
    5. KHÔNG CÓ KÝ TỰ ĐẶC BIỆT NHƯ *, -, #, **
    6. DÙNG TIẾNG VIỆT TỰ NHIÊN, CHUYÊN NGHIỆP

    TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG SAU (KHÔNG THÊM BẤT KỲ TEXT NÀO KHÁC):

    TIÊU ĐỀ: [tiêu đề email, tối đa 10 từ]

    [nội dung email, mỗi đoạn cách nhau 1 dòng trống, không có bullet points]
    """

    def _create_multiple_employees_email_prompt_improved(self, employees_data):
        """Tạo prompt cho email nhiều nhân viên - Định dạng tốt hơn"""
        employees_summary = []
        for i, emp in enumerate(employees_data):
            metrics = emp.get('metrics', {})
            employees_summary.append(f"""
    Nhân viên {i + 1}: {emp.get('name', '')} (Mã: {emp.get('id', '')})
    • Xếp hạng: {metrics.get('rank', 'Chưa xếp hạng')} {metrics.get('rank_emoji', '')}
    • Điểm: {metrics.get('overall_score', 0)}/100
    • Đơn hàng: {metrics.get('total_orders', 0)}
    • Hoàn thành: {metrics.get('completion_rate', 0)}%
    • Doanh thu: {metrics.get('total_revenue', 0):,.0f} VND
    • Gian lận: {metrics.get('total_fraud', 0)}
    """)

        # Tính toán thống kê nhóm
        total_employees = len(employees_data)
        excellent_count = len([e for e in employees_data if e.get('metrics', {}).get('rank') == 'Xuất sắc'])
        good_count = len([e for e in employees_data if e.get('metrics', {}).get('rank') in ['Tốt', 'Khá']])
        need_improvement_count = len(
            [e for e in employees_data if e.get('metrics', {}).get('rank') in ['Trung bình', 'Cần cải thiện']])
        avg_score = sum(e.get('metrics', {}).get('overall_score', 0) for e in employees_data) / total_employees

        group_stats = f"""
    THỐNG KÊ NHÓM ({total_employees} nhân viên):
    • Xuất sắc: {excellent_count} nhân viên
    • Tốt/Khá: {good_count} nhân viên
    • Cần cải thiện: {need_improvement_count} nhân viên
    • Điểm trung bình: {avg_score:.1f}/100

    CHI TIẾT TỪNG NHÂN VIÊN:
    {''.join(employees_summary)}
    """

        return f"""
    Bạn là quản lý trong công ty. Hãy viết một email nhắc nhở công việc cho một nhóm nhân viên dựa trên dữ liệu hiệu suất.

    {group_stats}

    YÊU CẦU VIẾT EMAIL (PHẢI TUÂN THỦ ĐỊNH DẠNG SAU):
    1. TIÊU ĐỀ EMAIL: Chỉ 1 dòng, không có ký tự đặc biệt, tập trung vào nhóm
    2. NỘI DUNG EMAIL: Định dạng rõ ràng, dễ đọc
       - Dòng 1: Chào hỏi cả nhóm
       - Dòng 2-4: Đánh giá chung về nhóm
       - Dòng 5-7: Điểm tích cực của nhóm
       - Dòng 8-10: Điểm cần cải thiện của nhóm
       - Dòng 11-13: Đề xuất hành động cho nhóm
       - Dòng cuối: Kết thúc lịch sự
    3. KHÔNG SỬ DỤNG MARKDOWN, CHỈ DÙNG TEXT THUẦN
    4. MỖI ĐOẠN CÁCH NHAU BẰNG 1 DÒNG TRỐNG
    5. KHÔNG CÓ KÝ TỰ ĐẶC BIỆT NHƯ *, -, #, **
    6. KHÔNG LIỆT KÊ TỪNG NHÂN VIÊN TRONG EMAIL
    7. DÙNG TIẾNG VIỆT TỰ NHIÊN, CHUYÊN NGHIỆP

    TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG SAU (KHÔNG THÊM BẤT KỲ TEXT NÀO KHÁC):

    TIÊU ĐỀ: [tiêu đề email, tối đa 10 từ]

    [nội dung email, mỗi đoạn cách nhau 1 dòng trống, không có bullet points]
    """

    def _format_email_response(self, response_text, employees_data):
        """Định dạng lại phản hồi từ Gemini cho đẹp"""
        # Loại bỏ các ký tự markdown
        cleaned_text = response_text.replace('**', '').replace('*', '').replace('#', '').replace('- ', '')

        # Tách các dòng
        lines = cleaned_text.split('\n')

        # Loại bỏ dòng trống đầu và cuối
        while lines and lines[0].strip() == '':
            lines.pop(0)
        while lines and lines[-1].strip() == '':
            lines.pop(-1)

        # Chuẩn hóa khoảng trắng
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line:  # Chỉ thêm dòng không trống
                formatted_lines.append(line)
            elif formatted_lines and formatted_lines[-1] != '':  # Thêm 1 dòng trống giữa các đoạn
                formatted_lines.append('')

        # Đảm bảo không có 2 dòng trống liên tiếp
        final_lines = []
        prev_was_blank = False
        for line in formatted_lines:
            if line == '':
                if not prev_was_blank:
                    final_lines.append(line)
                    prev_was_blank = True
            else:
                final_lines.append(line)
                prev_was_blank = False

        # Ghép lại
        result = '\n'.join(final_lines)

        # Kiểm tra và thêm TIÊU ĐỀ: nếu chưa có
        if not result.startswith('TIÊU ĐỀ:'):
            # Tạo tiêu đề mặc định
            if len(employees_data) == 1:
                emp_name = employees_data[0].get('name', 'Nhân viên')
                result = f"TIÊU ĐỀ: Đánh giá hiệu suất - {emp_name}\n\n{result}"
            else:
                result = f"TIÊU ĐỀ: Đánh giá hiệu suất nhóm\n\n{result}"

        return result

    def _get_fallback_email_content_improved(self, employees_data):
        """Nội dung email mặc định khi Gemini lỗi - Định dạng đẹp"""
        if len(employees_data) == 1:
            emp = employees_data[0]
            return f"""TIÊU ĐỀ: Đánh giá hiệu suất công việc

    Kính gửi Anh/Chị {emp.get('name', '')},

    Chúng tôi ghi nhận những đóng góp của bạn trong thời gian qua.

    Dựa trên phân tích hiệu suất, chúng tôi đề xuất một số điểm cải thiện để nâng cao hiệu quả công việc.

    Vui lòng tham gia buổi trao đổi với quản lý để thảo luận chi tiết về kế hoạch phát triển.

    Trân trọng,
    Quản lý"""
        else:
            names = ", ".join([e.get('name', '') for e in employees_data])
            return f"""TIÊU ĐỀ: Đánh giá hiệu suất nhóm

    Kính gửi các Anh/Chị,

    Chúng tôi xin gửi đánh giá hiệu suất chung cho nhóm.

    Qua phân tích, nhóm đã có những tiến bộ đáng kể. Tuy nhiên, vẫn còn một số điểm cần cải thiện để đạt mục tiêu chung.

    Chúng tôi đề xuất tổ chức buổi họp nhóm để cùng thảo luận giải pháp.

    Trân trọng,
    Quản lý"""

    def create_smart_prompt(self, question: str, context_data: Dict) -> str:
        """Tạo prompt thông minh cho nhiều loại câu hỏi"""

        # Trích xuất thông tin cơ bản
        basic_insights = self.extract_basic_insights(context_data)

        # Trích xuất thông tin cả năm
        year_insights = self.extract_year_insights(context_data)

        # Lấy thông tin chi tiết nhân viên từ context (nếu có)
        employees_detail = context_data.get("employees_detail", [])
        employees_insights = self.format_employees_insights(employees_detail)

        # Xác định loại câu hỏi
        question_type = self.detect_question_type(question)

        # Tạo prompt dựa trên loại câu hỏi
        if question_type == "employee_specific":
            prompt = self._create_employee_specific_prompt(question, context_data, basic_insights, year_insights,
                                                           employees_insights)
        elif question_type == "comparison":
            prompt = self._create_comparison_prompt(question, context_data, basic_insights, year_insights,
                                                    employees_insights)
        elif question_type == "ranking":
            prompt = self._create_ranking_prompt(question, context_data, basic_insights, year_insights,
                                                 employees_insights)
        elif question_type == "analysis":
            prompt = self._create_analysis_prompt(question, context_data, basic_insights, year_insights,
                                                  employees_insights)
        else:
            prompt = self._create_general_prompt(question, context_data, basic_insights, year_insights,
                                                 employees_insights)

        return prompt

    def detect_question_type(self, question: str) -> str:
        """Phát hiện loại câu hỏi"""
        question_lower = question.lower()

        # Câu hỏi về nhân viên cụ thể
        employee_patterns = ['em001', 'em002', 'em003', 'em004', 'nhân viên', 'của em', 'của nhân viên']
        if any(pattern in question_lower for pattern in employee_patterns):
            return "employee_specific"

        # Câu hỏi so sánh
        comparison_patterns = ['so sánh', 'đối chiếu', 'giữa', 'và', 'cùng lúc', 'nhiều nhân viên']
        if any(pattern in question_lower for pattern in comparison_patterns):
            return "comparison"

        # Câu hỏi xếp hạng
        ranking_patterns = ['cao nhất', 'thấp nhất', 'tốt nhất', 'kém nhất', 'xếp hạng', 'top', 'đứng đầu', 'cuối bảng']
        if any(pattern in question_lower for pattern in ranking_patterns):
            return "ranking"

        # Câu hỏi phân tích
        analysis_patterns = ['phân tích', 'đánh giá', 'khả năng', 'hiệu suất', 'năng lực', 'công việc']
        if any(pattern in question_lower for pattern in analysis_patterns):
            return "analysis"

        return "general"

    def _create_employee_specific_prompt(self, question, context_data, basic_insights, year_insights,
                                         employees_insights):
        """Prompt cho câu hỏi về nhân viên cụ thể"""
        # Trích xuất mã nhân viên từ câu hỏi
        import re
        emp_pattern = r'EM\d{3}'
        emp_matches = re.findall(emp_pattern, question.upper())

        emp_info_section = ""
        if emp_matches:
            emp_ids = emp_matches
            emp_info_section = f"\n\n📌 THÔNG TIN NHÂN VIÊN ĐƯỢC HỎI:\n"
            for emp_id in emp_ids[:3]:  # Giới hạn 3 nhân viên
                # Tìm nhân viên trong danh sách
                emp_found = False
                for emp in context_data.get("employees_detail", []):
                    if emp.get('id', '').upper() == emp_id:
                        emp_info_section += f"\n• {emp_id} - {emp.get('name', 'N/A')}:\n"
                        metrics = emp.get('metrics', {})
                        if metrics:
                            emp_info_section += f"  - Xếp hạng: {metrics.get('rank', 'N/A')}\n"
                            emp_info_section += f"  - Điểm: {metrics.get('overall_score', 0)}/100\n"
                            emp_info_section += f"  - Đơn hàng: {metrics.get('total_orders', 0)}\n"
                            emp_info_section += f"  - Hoàn thành: {metrics.get('completion_rate', 0)}%\n"
                            emp_info_section += f"  - Gian lận: {metrics.get('total_fraud', 0)}\n"
                        emp_found = True
                        break
                if not emp_found:
                    emp_info_section += f"\n• {emp_id}: Không có trong danh sách hiện tại\n"

        return f"""
    Bạn là **PowerSight AI** – chuyên gia phân tích hiệu suất nhân viên.

    ====================================
    📊 DỮ LIỆU HIỆN CÓ
    ====================================
    {basic_insights}

    {year_insights}

    {employees_insights}
    {emp_info_section}

    ====================================
    ❓ CÂU HỎI CỦA QUẢN LÝ
    ====================================
    "{question}"

    ====================================
    🧠 HƯỚNG DẪN PHÂN TÍCH
    ====================================
    Đây là câu hỏi về NHÂN VIÊN CỤ THỂ. Hãy:

    1️⃣ **XÁC ĐỊNH NHÂN VIÊN:** Tìm mã nhân viên trong câu hỏi
    2️⃣ **PHÂN TÍCH CHI TIẾT:** 
       - Hiệu suất tổng thể
       - Điểm mạnh/điểm yếu
       - Đơn hàng & doanh thu
       - Gian lận & rủi ro
    3️⃣ **ĐỀ XUẤT HÀNH ĐỘNG:**
       - Biện pháp cải thiện (nếu cần)
       - Kế hoạch phát triển
    4️⃣ **TRẢ LỜI CỤ THỂ:** Tập trung vào nhân viên được hỏi

    ====================================
    📝 CẤU TRÚC TRẢ LỜI
    ====================================
    **1. THÔNG TIN NHÂN VIÊN**
    - Mã & tên nhân viên
    - Vị trí & vai trò

    **2. PHÂN TÍCH HIỆU SUẤT**
    - Xếp hạng & điểm số
    - Thành tích nổi bật
    - Điểm cần cải thiện

    **3. DỮ LIỆU CHI TIẾT**
    - Số liệu đơn hàng
    - Tình trạng công việc
    - Vấn đề phát sinh

    **4. ĐỀ XUẤT & KHUYẾN NGHỊ**
    - Hành động trước mắt
    - Kế hoạch dài hạn
    - Hỗ trợ cần thiết

    ====================================
    🎯 YÊU CẦU
    ====================================
    - Trả lời bằng tiếng Việt tự nhiên
    - Sử dụng số liệu cụ thể (nếu có)
    - Đưa ra phân tích thực tế
    - Có khuyến nghị hành động
    - Giọng văn chuyên nghiệp, xây dựng
    """

    def _create_comparison_prompt(self, question, context_data, basic_insights, year_insights, employees_insights):
        """Prompt cho câu hỏi so sánh"""
        return f"""
    Bạn là **PowerSight AI** – chuyên gia so sánh và đánh giá nhân viên.

    ====================================
    📊 DỮ LIỆU HIỆN CÓ
    ====================================
    {basic_insights}

    {year_insights}

    {employees_insights}

    ====================================
    ❓ CÂU HỎI CỦA QUẢN LÝ
    ====================================
    "{question}"

    ====================================
    🧠 HƯỚNG DẪN PHÂN TÍCH
    ====================================
    Đây là câu hỏi SO SÁNH NHÂN VIÊN. Hãy:

    1️⃣ **XÁC ĐỊNH ĐỐI TƯỢNG:** Tìm các nhân viên cần so sánh
    2️⃣ **THIẾT LẬP TIÊU CHÍ:** 
       - Hiệu suất tổng thể
       - Số lượng đơn hàng
       - Chất lượng công việc
       - Tuân thủ quy định
    3️⃣ **SO SÁNH CHI TIẾT:** 
       - Điểm giống nhau
       - Điểm khác biệt
       - Ưu điểm của từng người
       - Nhược điểm cần cải thiện
    4️⃣ **ĐÚC KẾT:** 
       - Ai làm tốt hơn ở lĩnh vực nào
       - Ai cần hỗ trợ gì

    ====================================
    📝 CẤU TRÚC TRẢ LỜI
    ====================================
    **1. BẢNG SO SÁNH TỔNG QUAN**
    - Bảng điểm các tiêu chí
    - Xếp hạng tương đối

    **2. PHÂN TÍCH THEO TIÊU CHÍ**
    - Hiệu suất làm việc
    - Chất lượng đầu ra
    - Thái độ & tuân thủ
    - Khả năng phát triển

    **3. ĐIỂM MẠNH RIÊNG**
    - Điểm nổi bật của từng người
    - Thế mạnh chuyên môn

    **4. ĐIỂM CẦN CẢI THIỆN**
    - Vấn đề chung
    - Vấn đề riêng từng người

    **5. KHUYẾN NGHỊ PHÂN CÔNG**
    - Công việc phù hợp với ai
    - Đào tạo cần thiết

    ====================================
    🎯 YÊU CẦU
    ====================================
    - Dùng bảng so sánh khi cần
    - Đưa ra số liệu cụ thể
    - Phân tích công bằng, khách quan
    - Có đề xuất thực tế
    - Trả lời bằng tiếng Việt
    """

    def _create_ranking_prompt(self, question, context_data, basic_insights, year_insights, employees_insights):
        """Prompt cho câu hỏi xếp hạng"""
        return f"""
    Bạn là **PowerSight AI** – chuyên gia xếp hạng và đánh giá hiệu suất.

    ====================================
    📊 DỮ LIỆU HIỆN CÓ
    ====================================
    {basic_insights}

    {year_insights}

    {employees_insights}

    ====================================
    ❓ CÂU HỎI CỦA QUẢN LÝ
    ====================================
    "{question}"

    ====================================
    🧠 HƯỚNG DẪN PHÂN TÍCH
    ====================================
    Đây là câu hỏi XẾP HẠNG NHÂN VIÊN. Hãy:

    1️⃣ **XÁC ĐỊNH TIÊU CHÍ:** 
       - Hiệu suất tổng thể
       - Số đơn hàng
       - Doanh thu
       - Tỷ lệ hoàn thành
       - Tỷ lệ gian lận
    2️⃣ **THU THẬP DỮ LIỆU:** 
       - Lấy số liệu của tất cả nhân viên
       - Tính toán các chỉ số
    3️⃣ **SẮP XẾP THEO TIÊU CHÍ:** 
       - Xếp từ cao đến thấp
       - Phân loại nhóm (Xuất sắc/Tốt/Khá/Trung bình/Yếu)
    4️⃣ **PHÂN TÍCH KẾT QUẢ:** 
       - Nhận xét chung
       - Điểm nổi bật
       - Vấn đề cần quan tâm

    ====================================
    📝 CẤU TRÚC TRẢ LỜI
    ====================================
    **1. BẢNG XẾP HẠNG CHI TIẾT**
    - Top 5 cao nhất
    - Top 5 thấp nhất
    - Xếp hạng đầy đủ (nếu ít nhân viên)

    **2. PHÂN TÍCH TỪNG NHÓM**
    - Nhóm xuất sắc: Điểm mạnh & bài học
    - Nhóm trung bình: Nguyên nhân & giải pháp
    - Nhóm yếu: Vấn đề & hỗ trợ cần thiết

    **3. NHẬN XÉT TỔNG QUAN**
    - Xu hướng chung của team
    - Điểm mạnh tập thể
    - Điểm yếu cần khắc phục

    **4. KẾ HOẠCH HÀNH ĐỘNG**
    - Đào tạo cho nhóm yếu
    - Phát huy nhóm xuất sắc
    - Mục tiêu cải thiện

    ====================================
    🎯 YÊU CẦU
    ====================================
    - Đưa ra bảng xếp hạng rõ ràng
    - Giải thích tiêu chí xếp hạng
    - Có số liệu minh chứng
    - Đề xuất hành động cụ thể
    - Trả lời bằng tiếng Việt
    """

    def _create_analysis_prompt(self, question, context_data, basic_insights, year_insights, employees_insights):
        """Prompt cho câu hỏi phân tích"""
        return f"""
    Bạn là **PowerSight AI** – chuyên gia phân tích dữ liệu và đưa ra chiến lược.

    ====================================
    📊 DỮ LIỆU HIỆN CÓ
    ====================================
    {basic_insights}

    {year_insights}

    {employees_insights}

    ====================================
    ❓ CÂU HỎI CỦA QUẢN LÝ
    ====================================
    "{question}"

    ====================================
    🧠 HƯỚNG DẪN PHÂN TÍCH
    ====================================
    Đây là câu hỏi PHÂN TÍCH CHUYÊN SÂU. Hãy:

    1️⃣ **PHÂN TÍCH ĐA CHIỀU:**
       - Hiệu suất cá nhân & team
       - Xu hướng theo thời gian
       - So sánh với mục tiêu
       - Đánh giá rủi ro
    2️⃣ **NHẬN DIỆN VẤN ĐỀ:**
       - Điểm nghẽn trong quy trình
       - Nguyên nhân hiệu suất thấp
       - Rủi ro tiềm ẩn
    3️⃣ **ĐỀ XUẤT GIẢI PHÁP:**
       - Giải pháp ngắn hạn
       - Chiến lược dài hạn
       - Kế hoạch hành động cụ thể

    ====================================
    📝 CẤU TRÚC TRẢ LỜI
    ====================================
    **1. PHÂN TÍCH HIỆN TRẠNG**
    - Số liệu thực tế
    - So với mục tiêu/KPI
    - Xu hướng biến động

    **2. NHẬN DIỆN VẤN ĐỀ**
    - Vấn đề chính
    - Nguyên nhân gốc rễ
    - Ảnh hưởng đến kinh doanh

    **3. PHÂN TÍCH SWOT**
    - Điểm mạnh (Strengths)
    - Điểm yếu (Weaknesses)
    - Cơ hội (Opportunities)
    - Thách thức (Threats)

    **4. ĐỀ XUẤT GIẢI PHÁP**
    - Hành động khẩn cấp
    - Cải tiến quy trình
    - Đào tạo & phát triển
    - Giám sát & đánh giá

    **5. KẾ HOẠCH TRIỂN KHAI**
    - Timeline thực hiện
    - Người chịu trách nhiệm
    - Chỉ số đo lường kết quả

    ====================================
    🎯 YÊU CẦU
    ====================================
    - Phân tích sâu, có chiều sâu
    - Dùng số liệu thuyết phục
    - Đề xuất thực tế, khả thi
    - Có timeline cụ thể
    - Trả lời bằng tiếng Việt
    """

    def _create_general_prompt(self, question, context_data, basic_insights, year_insights, employees_insights):
        """Prompt cho câu hỏi chung"""
        return f"""
    Bạn là **PowerSight AI** – trợ lý thông minh cho quản lý.

    ====================================
    📊 DỮ LIỆU HIỆN CÓ
    ====================================
    {basic_insights}

    {year_insights}

    {employees_insights}

    ====================================
    ❓ CÂU HỎI CỦA QUẢN LÝ
    ====================================
    "{question}"

    ====================================
    🧠 HƯỚNG DẪN TRẢ LỜI
    ====================================
    Hãy trả lời câu hỏi dựa trên dữ liệu hiện có:

    1️⃣ **HIỂU CÂU HỎI:** Xác định nhu cầu thực sự
    2️⃣ **TRUY XUẤT DỮ LIỆU:** Tìm thông tin liên quan
    3️⃣ **PHÂN TÍCH & XỬ LÝ:** Đưa ra insight có giá trị
    4️⃣ **TRÌNH BÀY RÕ RÀNG:** Dễ hiểu, có cấu trúc

    ====================================
    📝 CẤU TRÚC TRẢ LỜI ĐỀ XUẤT
    ====================================
    **1. TRẢ LỜI TRỰC TIẾP**
    - Câu trả lời ngắn gọn
    - Nội dung chính xác

    **2. CHI TIẾT BỔ SUNG**
    - Số liệu liên quan
    - Phân tích chuyên sâu
    - Ngữ cảnh quan trọng

    **3. KHUYẾN NGHỊ (NẾU CẦN)**
    - Hành động đề xuất
    - Tài nguyên tham khảo
    - Bước tiếp theo

    ====================================
    🎯 YÊU CẦU
    ====================================
    - Trả lời đúng trọng tâm
    - Sử dụng dữ liệu khi có
    - Giọng văn chuyên nghiệp
    - Cấu trúc rõ ràng
    - Tiếng Việt tự nhiên
    """

    def format_employees_insights(self, employees_detail):
        """Định dạng thông tin chi tiết nhân viên"""
        if not employees_detail:
            return "📌 **KHÔNG CÓ DỮ LIỆU NHÂN VIÊN CHI TIẾT**"

        insights = ["📌 **THÔNG TIN NHÂN VIÊN CHI TIẾT:**"]

        for emp in employees_detail[:10]:  # Giới hạn 10 nhân viên
            emp_id = emp.get('id', 'N/A')
            emp_name = emp.get('name', 'N/A')
            metrics = emp.get('metrics', {})

            if metrics:
                insight_line = f"\n• **{emp_id} - {emp_name}**:"
                insight_line += f"\n  - Xếp hạng: {metrics.get('rank', 'N/A')} {metrics.get('rank_emoji', '')}"
                insight_line += f"\n  - Điểm: {metrics.get('overall_score', 0)}/100"
                insight_line += f"\n  - Đơn hàng: {metrics.get('total_orders', 0)}"
                insight_line += f"\n  - Hoàn thành: {metrics.get('completion_rate', 0)}%"
                insight_line += f"\n  - Doanh thu: {metrics.get('total_revenue', 0):,.0f} VND"
                insight_line += f"\n  - Gian lận: {metrics.get('total_fraud', 0)}"
            else:
                insight_line = f"\n• **{emp_id} - {emp_name}**: Không có dữ liệu hiệu suất"

            insights.append(insight_line)

        if len(employees_detail) > 10:
            insights.append(f"\n... và {len(employees_detail) - 10} nhân viên khác")

        return "\n".join(insights)
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

    # Thêm vào class GeminiAnalyzer trong gemini_analyzer.py

    def generate_custom_email_content(self, employees_data, custom_request, email_type="custom", year=None, month=None):
        """Tạo nội dung email tùy chỉnh dựa trên yêu cầu VÀ THỜI GIAN"""
        try:
            if self.use_demo_mode or not self.genai_client:
                return self._get_fallback_custom_email(employees_data, custom_request, email_type, year, month)

            prompt = self._create_custom_email_prompt(employees_data, custom_request, email_type, year, month)

            response = self.genai_client.models.generate_content(
                model=self.active_model if self.active_model else "gemini-2.0-flash",
                contents=prompt
            )

            if response and response.text:
                return self._format_email_response(response.text, employees_data)
            else:
                return self._get_fallback_custom_email(employees_data, custom_request, email_type, year, month)

        except Exception as e:
            print(f"❌ Lỗi tạo email tùy chỉnh: {e}")
            import traceback
            traceback.print_exc()
            return self._get_fallback_custom_email(employees_data, custom_request, email_type, year, month)

    def _create_custom_email_prompt(self, employees_data, custom_request, email_type="custom", year=None, month=None):
        """Tạo prompt cho email tùy chỉnh VỚI THỜI GIAN"""
        if len(employees_data) == 1:
            return self._create_single_custom_email_prompt(employees_data[0], custom_request, email_type, year, month)
        else:
            return self._create_multiple_custom_email_prompt(employees_data, custom_request, email_type, year, month)
    def _create_single_custom_email_prompt(self, employee_data, custom_request, email_type, year, month):
        """Tạo prompt cho email tùy chỉnh 1 nhân viên VỚI THỜI GIAN"""
        emp_name = employee_data.get('name', '')
        emp_id = employee_data.get('id', '')
        metrics = employee_data.get('metrics', {})

        # Thông tin thời gian
        time_info = ""
        if year and month:
            time_info = f"THỜI GIAN: Tháng {month}/{year}\n"
        elif year:
            time_info = f"THỜI GIAN: Năm {year}\n"

        # Thông tin hiệu suất nếu có
        perf_info = ""
        if metrics:
            perf_info = f"""
    THÔNG TIN HIỆU SUẤT:
    • Điểm tổng thể: {metrics.get('overall_score', 0)}/100
    • Xếp hạng: {metrics.get('rank', 'N/A')}
    • Đơn hàng: {metrics.get('total_orders', 0)}
    • Doanh thu: {metrics.get('total_revenue', 0):,.0f} VND
    • Gian lận: {metrics.get('total_fraud', 0)}
    """

        return f"""
    Bạn là quản lý trong công ty. Hãy viết một email {email_type.upper()} gửi đến nhân viên.

    THÔNG TIN NHÂN VIÊN:
    • Tên: {emp_name}
    • Mã: {emp_id}

    {time_info}
    {perf_info}

    YÊU CẦU CỤ THỂ: "{custom_request}"

    LOẠI EMAIL: {email_type.upper()}

    YÊU CẦU VIẾT EMAIL (PHẢI TUÂN THỦ):
    1. TIÊU ĐỀ: Phù hợp với loại email {email_type} và yêu cầu
    2. NỘI DUNG: 
       - Ngữ điệu phù hợp với loại email ({email_type})
       - Chuyên nghiệp nhưng phù hợp với ngữ cảnh
       - Đề cập đến thông tin thời gian nếu có
       - Có thể kèm số liệu hiệu suất nếu liên quan
    3. ĐỊNH DẠNG: Không markdown, chỉ text thuần, đoạn cách nhau 1 dòng trống

    TRẢ LỜI THEO ĐỊNH DẠNG:

    TIÊU ĐỀ: [tiêu đề email]

    [nội dung email]
    """

    def _get_fallback_custom_email(self, employees_data, custom_request, email_type, year, month):
        """Email tùy chỉnh mặc định khi AI lỗi - CÓ THỜI GIAN"""
        if len(employees_data) == 1:
            emp = employees_data[0]

            # Thông tin thời gian
            time_ref = ""
            if year and month:
                time_ref = f" (Tháng {month}/{year})"
            elif year:
                time_ref = f" (Năm {year})"

            subject = f"{email_type.upper()}: {custom_request[:30]}..."
            body = f"""Kính gửi Anh/Chị {emp.get('name', '')},

    Đây là email {email_type} dựa trên yêu cầu: "{custom_request}"

    Thông tin tham khảo{time_ref}:
    - Mã nhân viên: {emp.get('id', '')}
    - Thời gian: {datetime.now().strftime('%d/%m/%Y')}

    Nội dung chi tiết sẽ được trao đổi trong buổi họp sắp tới.

    Trân trọng,
    Quản lý"""

            return f"TIÊU ĐỀ: {subject}\n\n{body}"
        else:
            names = ", ".join([e.get('name', '') for e in employees_data])
            time_ref = ""
            if year and month:
                time_ref = f" (Tháng {month}/{year})"
            elif year:
                time_ref = f" (Năm {year})"

            subject = f"{email_type.upper()}: Thông báo cho nhóm"
            body = f"""Kính gửi các Anh/Chị,

    Đây là email {email_type} dựa trên yêu cầu: "{custom_request}"

    Thông tin tham khảo{time_ref}:
    - Gửi đến: {names}
    - Thời gian: {datetime.now().strftime('%d/%m/%Y')}

    Nội dung chi tiết sẽ được trao đổi trong buổi họp sắp tới.

    Trân trọng,
    Quản lý"""

            return f"TIÊU ĐỀ: {subject}\n\n{body}"

    def _create_multiple_custom_email_prompt(self, employees_data, custom_request, email_type="custom", year=None,
                                             month=None):
        """Tạo prompt cho email tùy chỉnh nhiều nhân viên VỚI THỜI GIAN"""
        employees_list = "\n".join([f"• {e.get('name', '')} (Mã: {e.get('id', '')})" for e in employees_data])

        # Thông tin thời gian
        time_info = ""
        if year and month:
            time_info = f"THỜI GIAN: Tháng {month}/{year}\n"
        elif year:
            time_info = f"THỜI GIAN: Năm {year}\n"

        return f"""
        Bạn là quản lý trong công ty. Hãy viết một email {email_type.upper()} dựa trên yêu cầu cụ thể sau:

        YÊU CẦU: "{custom_request}"

        DANH SÁCH NHÂN VIÊN NHẬN:
        {employees_list}

        {time_info}
        LOẠI EMAIL: {email_type.upper()}

        YÊU CẦU VIẾT EMAIL (PHẢI TUÂN THỦ ĐỊNH DẠNG SAU):
        1. TIÊU ĐỀ EMAIL: Chỉ 1 dòng, phù hợp với yêu cầu và loại email {email_type}
        2. NỘI DUNG EMAIL: Định dạng rõ ràng, chuyên nghiệp, gửi đến tất cả nhân viên
        3. KHÔNG SỬ DỤNG MARKDOWN, CHỈ DÙNG TEXT THUẦN
        4. MỖI ĐOẠN CÁCH NHAU BẰNG 1 DÒNG TRỐNG
        5. DÙNG TIẾNG VIỆT TỰ NHIÊN, CHUYÊN NGHIỆP

        TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG SAU (KHÔNG THÊM BẤT KỲ TEXT NÀO KHÁC):

        TIÊU ĐỀ: [tiêu đề email, tối đa 10 từ]

        [nội dung email, mỗi đoạn cách nhau 1 dòng trống]
        """
    def generate_employee_complaint_email(self, employee_name, issue_description, email_type, manager_email):
        """Tạo email khiếu nại/đề xuất từ nhân viên"""
        try:
            if self.use_demo_mode or not self.genai_client:
                return self._get_fallback_employee_complaint_email(employee_name, issue_description, email_type)

            prompt = self._create_employee_complaint_prompt(employee_name, issue_description, email_type,
                                                            manager_email)

            response = self.genai_client.models.generate_content(
                model=self.active_model if self.active_model else "gemini-2.0-flash",
                contents=prompt
            )

            if response and response.text:
                return self._format_email_response(response.text, [{'name': employee_name}])
            else:
                return self._get_fallback_employee_complaint_email(employee_name, issue_description, email_type)

        except Exception as e:
            print(f"❌ Lỗi tạo email khiếu nại: {e}")
            return self._get_fallback_employee_complaint_email(employee_name, issue_description, email_type)

    def _create_employee_complaint_prompt(self, employee_name, issue_description, email_type, manager_email):
        """Tạo prompt cho email khiếu nại từ nhân viên"""
        return f"""
        Bạn là nhân viên {employee_name}. Hãy viết một email {email_type} gửi đến quản lý ({manager_email}).

        NỘI DUNG {email_type.upper()}: 
        {issue_description}

        YÊU CẦU VIẾT EMAIL (PHẢI TUÂN THỦ ĐỊNH DẠNG SAU):
        1. TIÊU ĐỀ EMAIL: Chỉ 1 dòng, phù hợp với nội dung {email_type}
        2. NỘI DUNG EMAIL: 
           - Lời chào lịch sự
           - Giới thiệu bản thân
           - Trình bày {email_type} rõ ràng, chi tiết
           - Đề xuất giải pháp (nếu có)
           - Lời kết lịch sự
        3. KHÔNG SỬ DỤNG MARKDOWN, CHỈ DÙNG TEXT THUẦN
        4. MỖI ĐOẠN CÁCH NHAU BẰNG 1 DÒNG TRỐNG
        5. DÙNG TIẾNG VIỆT TỰ NHIÊN, TRANG TRỌNG
        6. KÝ TÊN: {employee_name}

        TRẢ LỜI THEO ĐÚNG ĐỊNH DẠNG SAU (KHÔNG THÊM BẤT KỲ TEXT NÀO KHÁC):

        TIÊU ĐỀ: [tiêu đề email, tối đa 10 từ]

        [nội dung email, mỗi đoạn cách nhau 1 dòng trống]
        """

    def _get_fallback_employee_complaint_email(self, employee_name, issue_description, email_type):
        """Email khiếu nại mặc định khi AI lỗi"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M")

        subject = f"{email_type.upper()} từ nhân viên {employee_name}"
        body = f"""Kính gửi Quản lý,

Tôi là {employee_name}, xin gửi {email_type} sau:

{issue_description}

Thời gian: {current_time}

Mong nhận được phản hồi từ Quản lý.

Trân trọng,
{employee_name}"""

        return f"TIÊU ĐỀ: {subject}\n\n{body}"

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