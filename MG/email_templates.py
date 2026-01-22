"""
Email templates for PowerSight Manager Chatbot
"""
from datetime import datetime


class EmailTemplates:
    @staticmethod
    def get_improvement_email_template(employee_name, manager_name, recommendations, employee_id=None):
        """Template email cải thiện hiệu suất"""
        current_date = datetime.now().strftime("%d/%m/%Y")

        return f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; }}
        .header {{ background-color: #2563eb; color: white; padding: 25px; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 25px; background-color: #f8fafc; }}
        .recommendations {{ background-color: white; border-left: 4px solid #10b981; padding: 20px; margin: 20px 0; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .footer {{ background-color: #f1f5f9; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #64748b; }}
        .highlight {{ background-color: #fef3c7; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .action-item {{ background-color: #dbeafe; padding: 10px; margin: 5px 0; border-radius: 3px; }}
        h1 {{ margin: 0; }}
        h2 {{ color: #1e40af; }}
        ul {{ padding-left: 20px; }}
        .employee-id {{ color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📈 Kế Hoạch Cải Thiện Hiệu Suất</h1>
        <p>Ngày: {current_date}</p>
    </div>

    <div class="content">
        <h2>Kính gửi Anh/Chị {employee_name},</h2>
        <div class="employee-id">Mã nhân viên: {employee_id if employee_id else 'N/A'}</div>

        <p>Dựa trên đánh giá hiệu suất công việc, chúng tôi đã xác định một số lĩnh vực có thể cải thiện để giúp bạn đạt được kết quả tốt hơn.</p>

        <div class="highlight">
            <strong>🎯 Mục tiêu chính:</strong> Tối ưu hóa hiệu suất và đóng góp vào mục tiêu chung của team.
        </div>

        <div class="recommendations">
            <h3>📋 Đề Xuất Cải Thiện:</h3>
            {recommendations}
        </div>

        <h3>📅 Kế Hoạch Hành Động:</h3>
        <ul>
            <li><strong>Thời gian thực hiện:</strong> 30 ngày tới</li>
            <li><strong>Đánh giá giữa kỳ:</strong> Sau 15 ngày</li>
            <li><strong>Đánh giá cuối kỳ:</strong> Sau 30 ngày</li>
        </ul>

        <h3>🤝 Hỗ Trợ Có Sẵn:</h3>
        <div class="action-item">1. Đào tạo trực tuyến về kỹ năng chuyên môn</div>
        <div class="action-item">2. Coaching 1-1 với quản lý</div>
        <div class="action-item">3. Tài nguyên học tập và tài liệu tham khảo</div>

        <p style="margin-top: 25px;">Chúng tôi tin tưởng vào khả năng của bạn và sẽ hỗ trợ bạn trong suốt quá trình này.</p>

        <p style="font-weight: bold;">Trân trọng,<br>
        {manager_name}<br>
        Quản lý</p>
    </div>

    <div class="footer">
        <p>📧 Email được gửi tự động từ hệ thống PowerSight Manager Chatbot</p>
        <p>📍 Vui lòng không trả lời email này</p>
        <p>© {datetime.now().year} PowerSight. All rights reserved.</p>
    </div>
</body>
</html>
"""

    @staticmethod
    def get_simple_text_template(employee_name, recommendations):
        """Template đơn giản cho text email"""
        return f"""
Kính gửi Anh/Chị {employee_name},

Dựa trên đánh giá hiệu suất công việc, dưới đây là các đề xuất cải thiện:

{recommendations}

Thời gian thực hiện: 30 ngày tới.
Đánh giá: Sau 15 ngày và 30 ngày.

Trân trọng,
Quản lý
"""