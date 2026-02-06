"""
generate_complete_data.py
Tạo dữ liệu HOÀN CHỈNH cho hệ thống PowerSight - 4 nhân viên, 12 tháng
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import warnings

warnings.filterwarnings('ignore')

# ============================================
# CẤU HÌNH CHÍNH - ĐÃ BỔ SUNG EM004
# ============================================
BASE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Saved_file"

# 4 nhân viên với cấp độ khác nhau
EMPLOYEES_CONFIG = {
    "EM001": {"level": "HIGH", "color": "🟢"},
    "EM002": {"level": "LOW", "color": "🔴"},
    "EM003": {"level": "MEDIUM", "color": "🟡"},
    "EM004": {"level": "MEDIUM", "color": "🟡"}
}

YEARS = [2026]
MONTHS = range(1, 13)  # 12 tháng

# ============================================
# DỮ LIỆU MẪU TỪ FILE GỐC
# ============================================
STATUS_LIST = ["Processing", "Pending", "Completed", "Review"]
PRODUCT_TYPES = ["Furniture", "Software", "Electronics", "Office Supplies"]
PAYMENT_METHODS = ["Credit Card", "Cash", "Installment", "Bank Transfer"]
REGIONS = ["Central", "North", "South", "International"]

# Module cho work logs
MODULES = ["Face", "Mouse", "Browser"]
EVENT_TYPES = {
    "Face": ["FACE_VERIFICATION", "LIVENESS_CHECK", "SPOOFING_DETECTED", "FACE_MATCH", "FACE_MISMATCH"],
    "Mouse": ["MOUSE_SESSION", "ANOMALY_DETECTED", "RAPID_PAUSE_DETECTED", "BEHAVIOR_ANOMALY"],
    "Browser": ["BROWSER_OPEN", "SESSION_START", "RAPID_PAUSE", "TAB_SWITCH", "INACTIVITY_ALERT"]
}


# ============================================
# HÀM TIỆN ÍCH
# ============================================
def setup_directories():
    """Tạo thư mục cho tất cả nhân viên"""
    print("📁 Đang tạo thư mục...")

    for employee in EMPLOYEES_CONFIG.keys():
        # Thư mục nhân viên
        emp_dir = os.path.join(BASE_DIR, employee)
        os.makedirs(emp_dir, exist_ok=True)

        # Thư mục cho từng tháng
        for year in YEARS:
            for month in MONTHS:
                month_dir = os.path.join(emp_dir, f"{year}_{month:02d}")
                os.makedirs(month_dir, exist_ok=True)

                # Thư mục face_captures
                face_dir = os.path.join(month_dir, "face_captures")
                os.makedirs(face_dir, exist_ok=True)

    print("✅ Đã tạo xong thư mục cho 4 nhân viên")


def get_employee_config(employee):
    """Lấy cấu hình theo cấp độ nhân viên"""
    level = EMPLOYEES_CONFIG[employee]["level"]

    if level == "HIGH":  # EM001 - Xuất sắc
        return {
            "orders_per_month": 120,
            "revenue_range": (30000000, 60000000),
            "profit_margin": (0.25, 0.35),
            "completion_rate": 0.75,
            "fraud_events_range": (5, 10),
            "work_sessions": 22,
            "hours_per_day": (7, 9),
            "efficiency": (90, 100),
            "mouse_anomaly_score": (0.05, 0.25)
        }
    elif level == "MEDIUM":  # EM003 và EM004 - Trung bình
        return {
            "orders_per_month": 90,
            "revenue_range": (15000000, 40000000),
            "profit_margin": (0.15, 0.25),
            "completion_rate": 0.60,
            "fraud_events_range": (10, 20),
            "work_sessions": 18,
            "hours_per_day": (5, 7),
            "efficiency": (75, 90),
            "mouse_anomaly_score": (0.25, 0.45)
        }
    else:  # EM002 - Cần cải thiện
        return {
            "orders_per_month": 60,
            "revenue_range": (8000000, 25000000),
            "profit_margin": (0.10, 0.20),
            "completion_rate": 0.45,
            "fraud_events_range": (30, 50),
            "work_sessions": 15,
            "hours_per_day": (3, 6),
            "efficiency": (60, 80),
            "mouse_anomaly_score": (0.45, 0.65)
        }


# ============================================
# TẠO DỮ LIỆU SAP_DATA.XLSX
# ============================================
def generate_orders_data(employee, year, month):
    """Tạo sheet Orders"""
    config = get_employee_config(employee)
    orders = []

    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)

    customer_ids = [f"CUST{random.randint(1000, 9999)}" for _ in range(50)]

    for i in range(config["orders_per_month"]):
        day_offset = random.randint(0, (end_date - start_date).days)
        order_date = start_date + timedelta(days=day_offset)

        revenue = random.randint(*config["revenue_range"])
        profit_margin = random.uniform(*config["profit_margin"])
        profit = int(revenue * profit_margin)

        if random.random() < config["completion_rate"]:
            status = "Completed"
            processing_time = random.randint(10, 60)
        else:
            status = random.choice(["Processing", "Pending", "Review"])
            processing_time = random.randint(60, 180)

        order = {
            "Order_ID": f"ORD{month:02d}{i + 1:04d}",
            "Order_Date": order_date.strftime("%Y-%m-%d"),
            "Customer": random.choice(customer_ids),
            "Revenue": revenue,
            "Profit": profit,
            "Edit_Count": random.randint(0, 3),
            "Processing_Time": processing_time,
            "Status": status,
            "Employee_ID": employee,
            "Product_Type": random.choice(PRODUCT_TYPES),
            "Payment_Method": random.choice(PAYMENT_METHODS),
            "Region": random.choice(REGIONS)
        }
        orders.append(order)

    return pd.DataFrame(orders)


def generate_daily_performance_data(employee, year, month):
    """Tạo sheet Daily_Performance"""
    config = get_employee_config(employee)
    daily_data = []

    if month == 12:
        num_days = 31
    else:
        num_days = (datetime(year, month + 1, 1) - datetime(year, month, 1)).days

    for day in range(1, num_days + 1):
        date = datetime(year, month, day)
        is_weekend = date.weekday() >= 5

        if is_weekend:
            if random.random() < 0.3:
                efficiency = random.uniform(config["efficiency"][0] - 10, config["efficiency"][1] - 5)
                tasks = random.randint(1, 3)
            else:
                efficiency = 0
                tasks = 0
        else:
            efficiency = random.uniform(*config["efficiency"])
            tasks = random.randint(2, 5)

        if tasks > 0:
            revenue_per_task = random.randint(1000000, 5000000)
            total_revenue = tasks * revenue_per_task * (efficiency / 100)
            total_profit = total_revenue * random.uniform(0.1, 0.3)
        else:
            total_revenue = 0
            total_profit = 0

        daily_entry = {
            "Date": date.strftime("%Y-%m-%d"),
            "Efficiency_Score": round(efficiency, 1),
            "Tasks_Completed": tasks,
            "Total_Revenue": int(total_revenue),
            "Total_Profit": int(total_profit)
        }
        daily_data.append(daily_entry)

    return pd.DataFrame(daily_data)


# ============================================
# TẠO DỮ LIỆU WORK_LOGS - ĐÃ BỔ SUNG BROWSER_SESSIONS
# ============================================
def generate_fraud_events_data(employee, year, month):
    """Tạo sheet Fraud_Events"""
    config = get_employee_config(employee)
    fraud_events = []

    num_events = random.randint(*config["fraud_events_range"])

    for i in range(num_events):
        day = random.randint(1, 28)
        hour = random.randint(8, 20)
        minute = random.randint(0, 59)

        timestamp = datetime(year, month, day, hour, minute, random.randint(0, 59))
        module = random.choice(MODULES)
        event_type = random.choice(EVENT_TYPES[module])

        if module == "Mouse":
            details = f"Mouse anomaly detected - Score: {random.uniform(0.7, 0.95):.3f}"
            severity = "CRITICAL"
        elif module == "Face":
            details = f"Face verification failed - Similarity: {random.uniform(0.2, 0.5):.3f}"
            severity = "WARNING"
        else:
            details = f"Browser suspicious activity detected"
            severity = random.choice(["WARNING", "CRITICAL"])

        fraud_event = {
            "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Event_Type": event_type,
            "Details": details,
            "User": employee,  # Sử dụng mã nhân viên thay vì tên
            "Session_ID": f"SESS_{year}{month:02d}{day:02d}_{i:03d}",
            "Severity": severity,
            "IsFraud": 1,
            "Date": timestamp.strftime("%Y-%m-%d"),
            "Time": timestamp.strftime("%H:%M:%S"),
            "Module": module
        }
        fraud_events.append(fraud_event)

    return pd.DataFrame(fraud_events)


def generate_mouse_details_data(employee, year, month):
    """Tạo sheet Mouse_Details"""
    config = get_employee_config(employee)
    mouse_details = []

    work_days = config["work_sessions"]
    sessions_per_day = random.randint(3, 5)
    total_sessions = work_days * sessions_per_day

    session_counter = 0

    for day in range(1, 29):
        date = datetime(year, month, day)
        if date.weekday() >= 5 and random.random() > 0.3:
            continue

        if session_counter >= total_sessions:
            break

        for session in range(sessions_per_day):
            if session_counter >= total_sessions:
                break

            hour = random.randint(9, 17)
            minute = random.randint(0, 59)
            timestamp = datetime(year, month, day, hour, minute, random.randint(0, 59))

            if random.random() < 0.1:
                is_fraud = 1
                anomaly_score = random.uniform(0.8, 0.95)
                severity = "CRITICAL"
            else:
                is_fraud = 0
                anomaly_score = random.uniform(*config["mouse_anomaly_score"])
                severity = "INFO"

            total_events = random.randint(5000, 30000)
            total_distance = random.uniform(5000, 40000)
            x_distance = total_distance * 0.6
            y_distance = total_distance * 0.4
            movement_time = random.uniform(30, 180)

            mouse_detail = {
                "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Event_Type": "MOUSE_SESSION",
                "Details": f"Mouse session - Score: {anomaly_score:.3f}",
                "User": employee,  # Sử dụng mã nhân viên thay vì tên
                "Session_ID": f"MOUSE_{year}{month:02d}{day:02d}_{session:03d}",
                "Severity": severity,
                "IsFraud": is_fraud,
                "Date": timestamp.strftime("%Y-%m-%d"),
                "Time": timestamp.strftime("%H:%M:%S"),
                "Module": "Mouse",
                "TotalEvents": total_events,
                "TotalMoves": total_events,
                "TotalDistance": round(total_distance, 2),
                "XAxisDistance": round(x_distance, 2),
                "YAxisDistance": round(y_distance, 2),
                "XFlips": random.randint(0, 50),
                "YFlips": random.randint(0, 30),
                "MovementTimeSpan": round(movement_time, 2),
                "Velocity": round(total_distance / movement_time, 2),
                "Acceleration": round(random.uniform(5, 50), 2),
                "XVelocity": round(x_distance / movement_time, 2),
                "YVelocity": round(y_distance / movement_time, 2),
                "XAcceleration": round(random.uniform(2, 30), 2),
                "YAcceleration": round(random.uniform(2, 30), 2),
                "DurationSeconds": round(movement_time, 2),
                "AnomalyScore": round(anomaly_score, 3)
            }
            mouse_details.append(mouse_detail)
            session_counter += 1

    return pd.DataFrame(mouse_details)


def generate_browser_sessions_data(employee, year, month):
    """Tạo sheet Browser_Sessions"""
    config = get_employee_config(employee)
    browser_sessions = []

    work_days = config["work_sessions"]
    sessions_counter = 0

    for day in range(1, 29):
        date = datetime(year, month, day)
        if date.weekday() >= 5:
            continue

        if sessions_counter >= work_days:
            break

        num_sessions_today = random.randint(1, 2)

        for session_num in range(num_sessions_today):
            start_hour = random.randint(8, 15)
            start_minute = random.randint(0, 59)
            start_time = datetime(year, month, day, start_hour, start_minute, 0)

            hours_worked = random.uniform(*config["hours_per_day"]) / num_sessions_today
            total_seconds = int(hours_worked * 3600)

            end_time = start_time + timedelta(seconds=total_seconds)
            hours = int(hours_worked)
            minutes = int((hours_worked - hours) * 60)

            browser_session = {
                "Session_ID": f"BROWSER_{year}{month:02d}{day:02d}_{session_num:02d}",
                "User": employee,  # Sử dụng mã nhân viên thay vì tên
                "Session_Start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Session_End": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                "Total_Seconds": total_seconds,
                "Total_Time": f"{hours:02d}:{minutes:02d}:00",
                "Date": start_time.strftime("%Y-%m-%d"),
                "Module": "Browser_Session"
            }
            browser_sessions.append(browser_session)

        sessions_counter += 1

    return pd.DataFrame(browser_sessions)


# ============================================
# HÀM CHÍNH TẠO DỮ LIỆU
# ============================================
def generate_complete_data():
    """Tạo dữ liệu hoàn chỉnh cho tất cả nhân viên và tháng"""
    print("=" * 70)
    print("🚀 TẠO DỮ LIỆU HOÀN CHỈNH - POWER SIGHT SYSTEM")
    print("=" * 70)
    print("👥 Nhân viên: EM001 (Xuất sắc), EM002 (Cần cải thiện), EM003, EM004 (Trung bình)")
    print("📅 Thời gian: 12 tháng năm 2026")
    print("=" * 70)

    setup_directories()
    total_files = 0

    for employee, config in EMPLOYEES_CONFIG.items():
        level = config["level"]
        color = config["color"]

        print(f"\n{color} Đang tạo dữ liệu cho {employee} ({level})...")

        for year in YEARS:
            for month in MONTHS:
                print(f"  📅 Tháng {year}-{month:02d}", end=" ")

                try:
                    month_dir = os.path.join(BASE_DIR, employee, f"{year}_{month:02d}")

                    # ==================== TẠO SAP_DATA.XLSX ====================
                    orders_df = generate_orders_data(employee, year, month)
                    daily_df = generate_daily_performance_data(employee, year, month)

                    sap_file = os.path.join(month_dir, "sap_data.xlsx")
                    with pd.ExcelWriter(sap_file, engine='openpyxl') as writer:
                        orders_df.to_excel(writer, sheet_name='Orders', index=False)
                        daily_df.to_excel(writer, sheet_name='Daily_Performance', index=False)

                    # ==================== TẠO WORK_LOGS.XLSX ====================
                    fraud_df = generate_fraud_events_data(employee, year, month)
                    mouse_df = generate_mouse_details_data(employee, year, month)
                    browser_df = generate_browser_sessions_data(employee, year, month)

                    # Tên file work_logs thống nhất
                    work_logs_file = os.path.join(month_dir, f"work_logs_{employee}_{year}_{month:02d}.xlsx")
                    with pd.ExcelWriter(work_logs_file, engine='openpyxl') as writer:
                        fraud_df.to_excel(writer, sheet_name='Fraud_Events', index=False)
                        mouse_df.to_excel(writer, sheet_name='Mouse_Details', index=False)
                        browser_df.to_excel(writer, sheet_name='Browser_Sessions', index=False)

                    total_files += 2
                    print(f"✅ ({len(orders_df)} đơn, {len(fraud_df)} fraud, {len(browser_df)} phiên)")

                except Exception as e:
                    print(f"❌ Lỗi: {str(e)[:50]}...")
                    continue

    print(f"\n{'=' * 70}")
    print(f"🎉 HOÀN THÀNH! Đã tạo {total_files} file")
    print(f"📁 Vị trí: {BASE_DIR}")

    create_summary_report()
    return total_files


def create_summary_report():
    """Tạo báo cáo tổng hợp"""
    print("\n📊 TẠO BÁO CÁO TỔNG HỢP...")

    summary_data = []

    for employee, config in EMPLOYEES_CONFIG.items():
        level = config["level"]

        if level == "HIGH":
            total_orders = 120 * 12
            total_revenue = total_orders * 45000000
            total_fraud = 30 * 12
            total_work_hours = 8 * 22 * 12
            efficiency = "90-100%"
            rating = "⭐️⭐️⭐️⭐️⭐️"
        elif level == "MEDIUM":
            total_orders = 90 * 12
            total_revenue = total_orders * 27500000
            total_fraud = 55 * 12
            total_work_hours = 6 * 18 * 12
            efficiency = "75-90%"
            rating = "⭐️⭐️⭐️"
        else:
            total_orders = 60 * 12
            total_revenue = total_orders * 16500000
            total_fraud = 85 * 12
            total_work_hours = 4.5 * 15 * 12
            efficiency = "60-80%"
            rating = "⭐️⭐️"

        summary_data.append({
            "Nhân viên": employee,
            "Cấp độ": level,
            "Tổng đơn hàng": f"{total_orders:,}",
            "Tổng doanh thu": f"${total_revenue / 1000000:,.0f}M",
            "Sự kiện gian lận": f"{total_fraud:,}",
            "Giờ làm việc": f"{total_work_hours:,} giờ",
            "Hiệu suất": efficiency,
            "Đánh giá": rating
        })

    summary_df = pd.DataFrame(summary_data)
    report_file = os.path.join(BASE_DIR, "summary_report_2026.xlsx")

    with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Tổng quan', index=False)

        comparison_data = {
            'Chỉ số': ['Doanh thu trung bình/đơn', 'Tỷ lệ hoàn thành', 'Lợi nhuận biên',
                       'Sự kiện gian lận/tháng', 'Giờ làm việc/tháng', 'Hiệu suất làm việc'],
            'EM001 (Xuất sắc)': ['$35-60M', '75%', '25-35%', '20-40', '~176 giờ', '90-100%'],
            'EM002 (Cần cải thiện)': ['$8-25M', '45%', '10-20%', '70-100', '~68 giờ', '60-80%'],
            'EM003 & EM004 (Trung bình)': ['$15-40M', '60%', '15-25%', '40-70', '~108 giờ', '75-90%']
        }

        comparison_df = pd.DataFrame(comparison_data)
        comparison_df.to_excel(writer, sheet_name='So sánh', index=False)

    print(f"✅ Đã lưu báo cáo: {report_file}")
    print("\n" + "=" * 70)
    print("BÁO CÁO TỔNG HỢP DỮ LIỆU 2026")
    print("=" * 70)
    print(summary_df.to_string(index=False))
    print("=" * 70)


def verify_data():
    """Kiểm tra dữ liệu đã tạo"""
    print("\n🔍 KIỂM TRA DỮ LIỆU...")

    for employee in EMPLOYEES_CONFIG.keys():
        print(f"\n{EMPLOYEES_CONFIG[employee]['color']} {employee}:")

        for month in [1, 6, 12]:
            month_dir = os.path.join(BASE_DIR, employee, f"2026_{month:02d}")

            sap_file = os.path.join(month_dir, "sap_data.xlsx")
            if os.path.exists(sap_file):
                try:
                    sap_xls = pd.ExcelFile(sap_file)
                    orders_count = len(pd.read_excel(sap_xls, sheet_name='Orders'))
                    daily_count = len(pd.read_excel(sap_xls, sheet_name='Daily_Performance'))
                    print(f"  Tháng {month}: sap_data.xlsx ✅ ({orders_count} đơn, {daily_count} ngày)")
                except:
                    print(f"  Tháng {month}: sap_data.xlsx ❌")
            else:
                print(f"  Tháng {month}: sap_data.xlsx ❌ KHÔNG TỒN TẠI")

            work_file = os.path.join(month_dir, f"work_logs_{employee}_2026_{month:02d}.xlsx")
            if os.path.exists(work_file):
                try:
                    work_xls = pd.ExcelFile(work_file)
                    fraud_count = len(pd.read_excel(work_xls, sheet_name='Fraud_Events'))
                    mouse_count = len(pd.read_excel(work_xls, sheet_name='Mouse_Details'))
                    browser_count = len(pd.read_excel(work_xls, sheet_name='Browser_Sessions'))
                    print(f"  Tháng {month}: work_logs.xlsx ✅ ({fraud_count} fraud, {mouse_count} chuột, {browser_count} phiên)")
                except:
                    print(f"  Tháng {month}: work_logs.xlsx ❌")
            else:
                print(f"  Tháng {month}: work_logs.xlsx ❌ KHÔNG TỒN TẠI")

    print("\n✅ Kiểm tra hoàn tất!")


# ============================================
# HÀM MAIN
# ============================================
if __name__ == "__main__":
    print("=" * 70)
    print("POWER SIGHT - CÔNG CỤ TẠO DỮ LIỆU HOÀN CHỈNH")
    print("=" * 70)

    try:
        import openpyxl
        print("✅ openpyxl: ĐÃ SẴN SÀNG")
    except:
        print("❌ openpyxl: CHƯA CÓ. Cài đặt: pip install openpyxl")
        exit(1)

    print(f"\n⚠️  Bạn sắp tạo dữ liệu cho:")
    print(f"   • 4 nhân viên: EM001, EM002, EM003, EM004")
    print(f"   • 12 tháng năm 2026")
    print(f"   • Tổng số file: 96 file Excel")
    print(f"\n📁 Vị trí lưu: {BASE_DIR}")

    confirm = input("\n⚠️  Tiếp tục? (yes/no): ")

    if confirm.lower() == 'yes':
        total_files = generate_complete_data()
        verify_data()

        print(f"\n{'=' * 70}")
        print("🎉 TẤT CẢ ĐÃ HOÀN THÀNH!")
        print(f"📊 Tổng số file đã tạo: {total_files}")
        print(f"👥 4 nhân viên với 3 cấp độ khác nhau")
        print(f"📅 12 tháng dữ liệu năm 2026")
        print(f"📁 Kiểm tra thư mục: {BASE_DIR}")
        print("=" * 70)

        try:
            os.startfile(BASE_DIR)
            print("📂 Đã mở thư mục chứa dữ liệu")
        except:
            pass

    else:
        print("❌ Đã hủy tạo dữ liệu")