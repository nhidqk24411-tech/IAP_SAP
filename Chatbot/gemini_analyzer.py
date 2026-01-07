# gemini_analyzer.py - Gemini API (google.genai) + quota-aware fallback
# Optimized for flexible, mentor-style, XAI responses (no data repetition)

import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config


class GeminiAnalyzer:
    """Phân tích với Gemini AI - Ưu tiên model chưa deprecate + quota cao"""

    # ------------------------------------------------------------------
    # Danh sách model còn hiệu lực (chưa tới hạn deprecation)
    VALID_MODELS = [
        "gemini-3-flash-preview",
        "gemini-3-pro-preview",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
    ]

    # Heuristic quota priority (cao → thấp)
    QUOTA_WEIGHT = {
        "flash-lite": 4,
        "flash": 3,
        "pro": 2,
        "preview": 1,
    }

    def __init__(self):
        self.genai_client = None
        self.active_model = None
        self.use_demo_mode = True
        self.api_type = "DEMO"

        print("🚀 Khởi tạo Gemini Analyzer...")

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

    def model_weight(self, name: str) -> int:
        name = name.lower()
        for key, w in self.QUOTA_WEIGHT.items():
            if key in name:
                return w
        return 0

    def find_best_model(self):
        """Chọn model chưa deprecate + quota cao nhất"""
        try:
            models = list(self.genai_client.models.list())
            available = []

            for m in models:
                short = m.name.split("/")[-1]
                if short in self.VALID_MODELS:
                    available.append(short)

            if not available:
                return

            available.sort(key=self.model_weight, reverse=True)

            self.active_model = available[0]
            self.use_demo_mode = False
            self.api_type = "API"

            print("📊 Model khả dụng (theo quota):")
            for m in available:
                print(f"  - {m} (w={self.model_weight(m)})")

        except Exception as e:
            print(f"❌ Lỗi chọn model: {e}")

    # ------------------------------------------------------------------

    def analyze_question(self, question: str, context_data: Dict[str, Any]) -> str:
        if self.use_demo_mode:
            return self.get_demo_response(question, context_data)

        prompt = self.create_smart_prompt(question, context_data)

        models_to_try = sorted(
            self.VALID_MODELS,
            key=self.model_weight,
            reverse=True
        )

        for model in models_to_try:
            try:
                print(f"📤 Gửi {model}")
                response = self.genai_client.models.generate_content(
                    model=model,
                    contents=prompt
                )

                text = response.text or ""
                self.active_model = model
                return self.format_response(text, question)

            except Exception as e:
                if self.is_quota_error(e):
                    print(f"⚠️ {model} hết quota → thử model khác")
                    continue
                print(f"❌ Lỗi {model}: {e}")
                break

        return self.get_demo_response(question, context_data)

    # ------------------------------------------------------------------

    def is_quota_error(self, e: Exception) -> bool:
        return any(k in str(e).lower() for k in ["quota", "429", "resource_exhausted"])

    # ------------------------------------------------------------------
    # XAI + Career Coach Prompt
    def create_smart_prompt(self, question: str, context_data: Dict) -> str:
        insights = self.extract_insights(context_data)

        return f"""
Bạn là cố vấn nghề nghiệp và hiệu suất làm việc tại PowerSight.
Nhiệm vụ của bạn là giúp nhân viên hiểu rõ nguyên nhân vấn đề, cải thiện kỹ năng và phát triển sự nghiệp.

Quy tắc bắt buộc:
- Không lặp lại dữ liệu thô như work_log, SAP, metrics
- Không liệt kê số liệu nếu không thực sự cần thiết
- Chỉ dùng dữ liệu để giải thích lý do kết luận
- Trả lời linh hoạt theo đúng câu hỏi của nhân viên

Tóm tắt các tín hiệu quan trọng (đã được hệ thống phân tích):
{insights}

Câu hỏi của nhân viên:
{question}

Yêu cầu trả lời theo hướng giải thích rõ ràng (XAI):
1. Nhận định chính, đi thẳng vào vấn đề
2. Vì sao đưa ra nhận định này (dựa trên tín hiệu nào)
3. Yếu tố nào ảnh hưởng mạnh nhất và yếu nhất
4. Rủi ro nghề nghiệp nếu không cải thiện
5. Lời khuyên thực tế, có thể áp dụng trong 1–2 tuần tới

Văn phong:
- Như người cố vấn
- Tích cực, thực tế
- Không phán xét
- Tiếng Việt
"""

    # ------------------------------------------------------------------
    # XAI Insight Extractor (core logic)
    def extract_insights(self, data: Dict[str, Any]) -> str:
        insights = []

        wl = data.get("work_log", {})
        sap = data.get("sap_data", {})
        m = data.get("metrics", {})

        if wl:
            if wl.get("error_count", 0) > 5:
                insights.append("Có sai sót lặp lại trong quá trình làm việc, ảnh hưởng cao.")
            if wl.get("warning_count", 0) > 3:
                insights.append("Quy trình làm việc chưa ổn định, ảnh hưởng trung bình.")
            if wl.get("fraud_count", 0) > 0:
                insights.append("Có dấu hiệu hành vi bất thường, ảnh hưởng rất cao.")

        if sap:
            if sap.get("completion_rate", 100) < 80:
                insights.append("Tỷ lệ hoàn thành công việc thấp hơn kỳ vọng, ảnh hưởng cao.")
            if sap.get("profit", 0) < 0:
                insights.append("Hiệu quả tài chính chưa tốt, ảnh hưởng trung bình.")

        if m:
            if m.get("efficiency", 100) < 60:
                insights.append("Hiệu suất làm việc thấp so với chuẩn, ảnh hưởng cao.")
            if m.get("quality", 100) < 70:
                insights.append("Chất lượng công việc chưa ổn định, ảnh hưởng trung bình.")
            if m.get("compliance", 100) < 80:
                insights.append("Mức độ tuân thủ quy trình chưa tốt, ảnh hưởng trung bình.")

        if not insights:
            return "Hiệu suất tổng thể ổn định, chưa thấy rủi ro đáng kể."

        return "- " + "\n- ".join(insights)

    # ------------------------------------------------------------------

    def format_response(self, response: str, question: str) -> str:
        return (
            "🤖 POWER SIGHT AI\n"
            f"🧠 Model: {self.active_model}\n"
            f"⏰ {datetime.now():%d/%m/%Y %H:%M}\n"
            "━━━━━━━━━━━━━━\n"
            f"Câu hỏi: {question}\n\n"
            f"{response}"
        )

    def get_demo_response(self, question: str, context_data: Dict) -> str:
        return self.format_response(
            "DEMO MODE – Hệ thống chưa được cấu hình API hợp lệ.",
            question
        )
