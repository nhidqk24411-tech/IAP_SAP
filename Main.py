from datetime import datetime
import os
from Mouse.Module.mouse_tracker import run_tracking
from Mouse.Module.Process_mouse_data import LogProcessor
from Mouse.Module.Process_Excel import MouseExcelHandler


def main():
    print("Bắt đầu tracking chuột...")

    # Tạo session_id DUY NHẤT cho cả log và Excel
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Tạo đường dẫn log file UNIQUE cho session này
    log_filename = f"mouse_events_{session_id}.log"
    path = f"Saved_file/{log_filename}"

    # Tạo thư mục Saved_file nếu chưa tồn tại
    os.makedirs("Saved_file", exist_ok=True)

    print(f"Session ID: {session_id}")
    print(f"Log file: {log_filename}")

    # 1. Tracking chuột - truyền đường dẫn log cụ thể
    run_tracking(duration_seconds=10, log_file_path=path)

    print("Tracking hoàn tất. Đang phân tích...")

    # 2. Phân tích dữ liệu - dùng log file vừa tạo
    processor = LogProcessor(log_file_path=path)
    result = processor.process(session_id=f"session_{session_id}")

    if not result:
        print("Không có dữ liệu để phân tích")
        return

    # 3. Xuất Excel - cùng session_id với log
    handler = MouseExcelHandler()

    # Tạo tên file Excel tương ứng
    excel_filename = f"mouse_report_{session_id}.xlsx"
    excel_path = f"Saved_file/{excel_filename}"

    success = handler.write_detailed_report(
        excel_path,
        result
    )

    if success:
        print(f" Đã xuất file: {excel_filename}")
        print(f" Log file: {log_filename}")
        print(f" Excel file: {excel_filename}")
    else:
        print(" Lỗi khi xuất file Excel")


if __name__ == "__main__":
    main()