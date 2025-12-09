"""
File chạy chính - Kết nối tất cả lại
"""

import sys
import os
from datetime import datetime

# Thêm path để import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from process import LogProcessor
from XulyExcel import MouseExcelHandler
from models.MouseResult import MouseResult


def run_mouse_analysis():
    """Chạy phân tích chuột từ A-Z"""
    print("=" * 60)
    print("MOUSE ACTIVITY ANALYZER")
    print("=" * 60)

    # 1. Xử lý log file
    print("📁 Bước 1: Đọc và xử lý file log...")
    processor = LogProcessor("mouse_events.log")
    result = processor.process(session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    if not result:
        print("✗ Không thể xử lý dữ liệu")
        return

    # 2. Hiển thị kết quả
    result.print_summary()

    # 3. Ghi vào Excel
    print("\n💾 Bước 2: Xuất kết quả ra Excel...")

    # Tạo tên file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_file = f"mouse_analysis_{timestamp}.xlsx"

    # Ghi vào file Excel (append mode)
    success = MouseExcelHandler.write_results_to_excel(
        file_path="mouse_results.xlsx",
        sheet_name="Results",
        results=[result]  # Chuyển thành list
    )

    if success:
        print(f"✓ Đã lưu kết quả vào: mouse_results.xlsx")

        # Tạo báo cáo chi tiết
        detailed_file = f"reports/detailed_{timestamp}.xlsx"
        os.makedirs("reports", exist_ok=True)

        MouseExcelHandler.write_detailed_report(detailed_file, result)
        print(f"✓ Báo cáo chi tiết: {detailed_file}")
    else:
        print("✗ Lỗi khi ghi Excel")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETED")
    print("=" * 60)


def run_mouse_tracking():
    """Chạy tracking chuột real-time (code cũ của bạn)"""
    print("Tracking chuột trong 30 giây...")

    # Import và chạy code tracking cũ
    from mouse_tracker_original import run_tracking
    run_tracking(duration_seconds=30)

    # Sau khi tracking xong, phân tích ngay
    print("\n" + "=" * 60)
    print("TRACKING COMPLETED - NOW ANALYZING...")
    print("=" * 60)

    run_mouse_analysis()


if __name__ == "__main__":
    # Menu chọn chức năng
    print("Chọn chức năng:")
    print("1. Phân tích file log có sẵn")
    print("2. Chạy tracking mới + phân tích")
    print("3. Xuất báo cáo chi tiết từ file log")

    choice = input("Nhập lựa chọn (1-3): ").strip()

    if choice == "1":
        run_mouse_analysis()
    elif choice == "2":
        run_mouse_tracking()
    elif choice == "3":
        # Chỉ xuất báo cáo
        processor = LogProcessor("mouse_events.log")
        result = processor.process()
        if result:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            MouseExcelHandler.write_detailed_report(
                f"reports/report_{timestamp}.xlsx",
                result
            )
    else:
        print("Lựa chọn không hợp lệ")