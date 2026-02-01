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

    @staticmethod
    def get_customer_feedback_template(employee_name, employee_id, customer_email="konodio3q@gmail.com"):
        """Template email gửi khách hàng lấy ý kiến phản hồi"""
        current_date = datetime.now().strftime("%d/%m/%Y")

        # Link Google Forms để khách hàng đánh giá
        feedback_form_link = "https://docs.google.com/forms/d/e/1FAIpQLSdCZCPlBjRgJQXrMHlWUb_CCQ-puEy9D-2zzbZa27Qz90J4AA/viewform"

        # Link Google Docs để xem hướng dẫn chi tiết
        docs_link = "https://docs.google.com/forms/d/e/1FAIpQLSdCZCPlBjRgJQXrMHlWUb_CCQ-puEy9D-2zzbZa27Qz90J4AA/viewform"

        return f"""
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 700px; margin: 0 auto; }}
        .header {{ background-color: #10b981; color: white; padding: 25px; border-radius: 10px 10px 0 0; }}
        .content {{ padding: 25px; background-color: #f8fafc; }}
        .footer {{ background-color: #f1f5f9; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; font-size: 12px; color: #64748b; }}
        .feedback-section {{ background-color: white; border: 2px solid #e2e8f0; padding: 20px; margin: 20px 0; border-radius: 8px; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #10b981; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; margin: 10px 5px; }}
        .docs-button {{ background-color: #3b82f6; }}
        .highlight {{ background-color: #f0f9ff; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #3b82f6; }}
        h1 {{ margin: 0; }}
        h2 {{ color: #1e40af; }}
        h3 {{ color: #10b981; }}
        ul {{ padding-left: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📝 Yêu Cầu Phản Hồi Từ Khách Hàng</h1>
        <p>Ngày: {current_date}</p>
    </div>

    <div class="content">
        <h2>Kính gửi Quý khách hàng,</h2>

        <p>Cảm ơn Quý khách đã hợp tác cùng chúng tôi. Để không ngừng nâng cao chất lượng dịch vụ và cải thiện trải nghiệm khách hàng, chúng tôi rất mong nhận được phản hồi từ Quý khách.</p>

        <div class="highlight">
            <p><strong>Thông tin nhân viên phục vụ:</strong></p>
            <ul>
                <li><strong>Họ tên:</strong> {employee_name}</li>
                <li><strong>Mã nhân viên:</strong> {employee_id}</li>
                <li><strong>Ngày làm việc:</strong> {current_date}</li>
            </ul>
        </div>

        <div class="feedback-section">
            <h3>📊 Đánh Giá Nhân Viên</h3>
            <p>Vui lòng đánh giá nhân viên trên các tiêu chí sau:</p>
            <ul>
                <li>Thái độ phục vụ và giao tiếp</li>
                <li>Chuyên môn và hiểu biết sản phẩm/dịch vụ</li>
                <li>Khả năng giải quyết vấn đề</li>
                <li>Tính chuyên nghiệp và đúng hẹn</li>
                <li>Sự hài lòng tổng thể</li>
            </ul>

            <p style="text-align: center; margin: 25px 0;">
                <a href="{feedback_form_link}" class="button" target="_blank">
                    📝 Điền Form Đánh Giá
                </a>
            </p>
        </div>

        <div class="feedback-section">
            <h3>📚 Tài Liệu Hướng Dẫn Chi Tiết</h3>
            <p>Để biết thêm chi tiết về quy trình đánh giá và các tiêu chí cụ thể, vui lòng tham khảo tài liệu hướng dẫn:</p>

            <p style="text-align: center; margin: 20px 0;">
                <a href="{docs_link}" class="button docs-button" target="_blank">
                    📄 Xem Hướng Dẫn Chi Tiết
                </a>
            </p>

            <p><strong>Nội dung tài liệu bao gồm:</strong></p>
            <ul>
                <li>Hướng dẫn chi tiết cách đánh giá</li>
                <li>Thang điểm và tiêu chí đánh giá</li>
                <li>Câu hỏi mẫu và gợi ý phản hồi</li>
                <li>Chính sách bảo mật thông tin</li>
            </ul>
        </div>

        <p>Phản hồi của Quý khách sẽ được giữ kín và chỉ sử dụng cho mục đích cải thiện chất lượng nội bộ. Chúng tôi cam kết bảo vệ thông tin cá nhân của Quý khách.</p>

        <p><strong>Thời hạn phản hồi:</strong> Trong vòng 7 ngày kể từ ngày nhận email.</p>

        <p style="margin-top: 30px;">
            Trân trọng cảm ơn sự hợp tác của Quý khách,<br><br>
            <strong>Bộ phận Quản lý Chất lượng</strong><br>
            Công ty PowerSight<br>
            Email: support@powersight.com<br>
            Điện thoại: (028) 1234 5678
        </p>
    </div>

    <div class="footer">
        <p>📧 Email được gửi tự động từ hệ thống PowerSight - Quản lý Chất lượng Dịch vụ</p>
        <p>📍 Đây là email tự động, vui lòng không trả lời trực tiếp vào email này</p>
        <p>📞 Liên hệ hỗ trợ: support@powersight.com | Hotline: 1800 1234</p>
        <p>© {datetime.now().year} PowerSight. All rights reserved.</p>
    </div>
</body>
</html>
"""

