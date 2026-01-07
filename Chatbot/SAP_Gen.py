# create_sample_data.py - Tạo tất cả file dữ liệu mẫu
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os


def create_sap_sample():
    """Tạo file SAP mẫu"""
    # Tạo dữ liệu mẫu cho đơn hàng
    data = []
    start_date = datetime(2026, 1, 1)

    # Tạo dữ liệu cho 100 đơn hàng
    for i in range(1, 101):
        order_date = start_date + timedelta(days=random.randint(0, 29))  # Trong vòng 30 ngày
        revenue = random.randint(10000000, 50000000)  # Doanh thu từ 10 đến 50 triệu
        profit = revenue * random.uniform(0.1, 0.3)  # Lợi nhuận từ 10% đến 30%
        edit_count = random.choices([0, 1, 2, 3, 4, 5], weights=[40, 25, 15, 10, 5, 5])[0]
        processing_time = random.randint(15, 180)  # Thời gian xử lý từ 15 đến 180 phút

        # Xác định trạng thái đơn hàng dựa trên một số yếu tố
        if edit_count == 0 and processing_time < 90:
            status = "Completed"
        elif edit_count <= 2 and processing_time < 120:
            status = random.choice(["Completed", "Processing"])
        else:
            status = random.choice(["Processing", "Pending", "Review"])

        data.append({
            'Order_ID': f'ORD{i:04d}',
            'Order_Date': order_date.strftime('%Y-%m-%d'),
            'Customer': f'CUST{random.randint(1000, 9999)}',
            'Revenue': revenue,
            'Profit': int(profit),
            'Edit_Count': edit_count,
            'Processing_Time': processing_time,
            'Status': status,
            'Employee_ID': 'Giang',  # Mặc định là nhân viên Giang
            'Product_Type': random.choice(['Electronics', 'Furniture', 'Office Supplies', 'Software']),
            'Payment_Method': random.choice(['Credit Card', 'Bank Transfer', 'Cash', 'Installment']),
            'Region': random.choice(['North', 'South', 'Central', 'International'])
        })

    # Tạo DataFrame cho đơn hàng
    df_orders = pd.DataFrame(data)

    # Tạo dữ liệu hiệu suất hàng ngày
    daily_data = []
    for day in range(30):
        date = start_date + timedelta(days=day)
        date_str = date.strftime('%Y-%m-%d')
        day_orders = df_orders[df_orders['Order_Date'] == date_str]

        if len(day_orders) > 0:
            tasks_completed = len(day_orders[day_orders['Status'] == 'Completed'])
            total_revenue = day_orders['Revenue'].sum()
            total_profit = day_orders['Profit'].sum()
            total_processing_time = day_orders['Processing_Time'].sum()

            # Tính điểm hiệu suất: dựa trên tỷ lệ hoàn thành, lợi nhuận, và thời gian xử lý
            completion_rate = tasks_completed / len(day_orders) * 100
            profit_per_hour = total_profit / (total_processing_time / 60) if total_processing_time > 0 else 0
            efficiency_score = min(100, completion_rate * 0.6 + (profit_per_hour / 10000) * 0.4)
        else:
            tasks_completed = 0
            total_revenue = 0
            total_profit = 0
            efficiency_score = random.uniform(70, 85)  # Nếu không có đơn hàng, cho điểm ngẫu nhiên

        daily_data.append({
            'Date': date_str,
            'Efficiency_Score': round(efficiency_score, 1),
            'Tasks_Completed': tasks_completed,
            'Total_Revenue': total_revenue,
            'Total_Profit': total_profit
        })

    df_daily = pd.DataFrame(daily_data)

    # Lưu vào file Excel với 2 sheet
    with pd.ExcelWriter('sap_data.xlsx') as writer:
        df_orders.to_excel(writer, sheet_name='Orders', index=False)
        df_daily.to_excel(writer, sheet_name='Daily_Performance', index=False)

    print("✅ Đã tạo file sap_data.xlsx mẫu với 2 sheet: Orders và Daily_Performance.")

    # In ra một số thống kê
    print("\n📊 Thống kê dữ liệu SAP mẫu:")
    print(f"   • Tổng số đơn hàng: {len(df_orders)}")
    print(f"   • Tổng doanh thu: {df_orders['Revenue'].sum():,.0f} VND")
    print(f"   • Tổng lợi nhuận: {df_orders['Profit'].sum():,.0f} VND")
    print(f"   • Số đơn hàng hoàn thành: {len(df_orders[df_orders['Status'] == 'Completed'])}")
    print(f"   • Tỷ lệ hoàn thành: {len(df_orders[df_orders['Status'] == 'Completed']) / len(df_orders) * 100:.1f}%")
    print(f"   • Số lần chỉnh sửa trung bình: {df_orders['Edit_Count'].mean():.2f}")
    print(f"   • Thời gian xử lý trung bình: {df_orders['Processing_Time'].mean():.1f} phút")
    print(f"   • Điểm hiệu suất trung bình hàng ngày: {df_daily['Efficiency_Score'].mean():.1f}")


if __name__ == "__main__":
    print("🚀 Đang tạo dữ liệu mẫu...")
    print("=" * 50)

    # Tạo thư mục nếu chưa tồn tại
    if not os.path.exists('sample_data'):
        os.makedirs('sample_data')

    # Đổi thư mục làm việc
    os.chdir('sample_data')

    # Tạo file SAP mẫu
    create_sap_sample()

