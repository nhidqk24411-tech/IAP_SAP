import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# =========================
# CONFIG ĐƠN GIẢN
# =========================
np.random.seed(42)
random.seed(42)

NUM_SESSIONS = 1000
FRAUD_RATIO = 0.15
NORMAL_RATIO = 0.85
USER = "Giang"
BASE_TIME = datetime(2025, 12, 1, 9, 0, 0)

rows_all_events = []
rows_alerts = []


# =========================
# HÀM TÍNH BEHAVIOR THUẦN TÚY
# =========================

def calculate_mouse_metrics(movement_span: float, total_distance: float,
                            x_ratio: float, is_normal: bool) -> dict:
    """
    Tính toán metrics thuần túy dựa trên behavior
    KHÔNG phụ thuộc thời gian, chỉ phụ thuộc movement pattern
    """

    # 1. Tính basic metrics (theo paper)
    x_distance = total_distance * x_ratio
    y_distance = total_distance * (1 - x_ratio)

    velocity = total_distance / movement_span if movement_span > 0 else 0
    x_velocity = x_distance / movement_span if movement_span > 0 else 0
    y_velocity = y_distance / movement_span if movement_span > 0 else 0

    # 2. Tính flips dựa trên behavior type
    if is_normal:
        # Normal: nhiều flips tự nhiên
        base_flips = int(total_distance / 150)  # Cứ 150 pixels có thể flip
        x_flips = np.random.randint(int(base_flips * 0.7), int(base_flips * 1.5))
        y_flips = np.random.randint(int(base_flips * 0.7), int(base_flips * 1.5))
    else:
        # Fraud: ít flips (macro/bot) hoặc nhiều flips (rapid clicker)
        # 70% ít flips, 30% nhiều flips
        if np.random.random() < 0.7:
            # Ít flips (macro, bot, jiggler)
            x_flips = np.random.randint(2, 10)
            y_flips = np.random.randint(2, 10)
        else:
            # Nhiều flips (rapid clicker)
            x_flips = np.random.randint(50, 150)
            y_flips = np.random.randint(50, 150)

    # 3. Tính acceleration (thay đổi velocity)
    # Normal: acceleration biến động nhiều
    # Fraud: acceleration rất thấp (đều đặn) hoặc rất cao (click nhanh)
    if is_normal:
        acceleration = velocity * np.random.uniform(0.5, 2.0)
    else:
        if x_flips < 20:  # Ít flips → acceleration thấp
            acceleration = velocity * np.random.uniform(0.05, 0.3)
        else:  # Nhiều flips → acceleration cao
            acceleration = velocity * np.random.uniform(1.5, 3.0)

    # 4. Tính axis accelerations
    x_acceleration = acceleration * np.random.uniform(0.4, 0.6)
    y_acceleration = acceleration * np.random.uniform(0.4, 0.6)

    # 5. Số events (fraud thường có pattern khác)
    if is_normal:
        total_events = int(total_distance / 10)  # ~10 pixels/event
        total_events += np.random.randint(-200, 200)
    else:
        if x_flips < 20:  # Ít flips → ít events
            total_events = int(total_distance / 20)
        else:  # Nhiều flips → nhiều events
            total_events = int(total_distance / 5)

    return {
        'movement_span': movement_span,
        'total_distance': total_distance,
        'x_distance': x_distance,
        'y_distance': y_distance,
        'velocity': velocity,
        'x_velocity': x_velocity,
        'y_velocity': y_velocity,
        'acceleration': acceleration,
        'x_acceleration': x_acceleration,
        'y_acceleration': y_acceleration,
        'x_flips': x_flips,
        'y_flips': y_flips,
        'total_events': max(100, total_events)  # Ít nhất 100 events
    }


# =========================
# TẠO NORMAL SESSION (BEHAVIOR TỰ NHIÊN)
# =========================

def generate_normal_session(session_id):
    """Tạo session với behavior chuột tự nhiên"""

    # Tham số ngẫu nhiên cho normal behavior
    movement_span = np.random.uniform(30, 60)  # 30-60 giây
    total_distance = np.random.uniform(5000, 30000)  # pixels

    # X/Y ratio tự nhiên (không quá cân bằng)
    x_ratio = np.random.beta(3, 3)  # Phân bố quanh 0.5 nhưng biến động

    # Tính metrics
    metrics = calculate_mouse_metrics(
        movement_span=movement_span,
        total_distance=total_distance,
        x_ratio=x_ratio,
        is_normal=True
    )

    # Anomaly score thấp (vì là normal)
    anomaly_score = np.random.beta(2, 8)  # Phân bố lệch về 0

    # Timestamp (chỉ để logging, không ảnh hưởng fraud detection)
    hour = np.random.randint(9, 17)
    minute = np.random.randint(0, 60)
    second = np.random.randint(0, 60)
    timestamp = BASE_TIME.replace(
        day=np.random.randint(1, 29),
        hour=hour,
        minute=minute,
        second=second
    )

    session_id_str = f"NORMAL_{session_id:04d}_{timestamp.strftime('%H%M%S')}"

    return {
        # Metadata (chỉ để tracking)
        "Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "Event_Type": "MOUSE_SESSION",
        "Details": f"Normal mouse behavior",
        "User": USER,
        "Session_ID": session_id_str,
        "Severity": "INFO",
        "IsFraud": False,
        "Date": timestamp.strftime('%Y-%m-%d'),
        "Time": timestamp.strftime('%H:%M:%S'),
        "Module": "Mouse",

        # Behavior metrics (QUAN TRỌNG)
        "TotalEvents": metrics['total_events'],
        "TotalMoves": metrics['total_events'],
        "TotalDistance": round(metrics['total_distance'], 2),
        "XAxisDistance": round(metrics['x_distance'], 2),
        "YAxisDistance": round(metrics['y_distance'], 2),
        "XFlips": metrics['x_flips'],
        "YFlips": metrics['y_flips'],
        "MovementTimeSpan": round(metrics['movement_span'], 2),
        "Velocity": round(metrics['velocity'], 2),
        "Acceleration": round(abs(metrics['acceleration']), 2),
        "XVelocity": round(metrics['x_velocity'], 2),
        "YVelocity": round(metrics['y_velocity'], 2),
        "XAcceleration": round(abs(metrics['x_acceleration']), 2),
        "YAcceleration": round(abs(metrics['y_acceleration']), 2),
        "DurationSeconds": round(metrics['movement_span'], 2),
        "AnomalyScore": round(anomaly_score, 3)
    }


# =========================
# TẠO FRAUD SESSION (BEHAVIOR BẤT THƯỜNG)
# =========================

def generate_fraud_session(session_id, fraud_type):
    """Tạo session với behavior chuột bất thường"""

    # Xác định behavior pattern dựa trên fraud type
    if fraud_type == "macro_automation":
        # Macro: đều đặn, ít biến động
        movement_span = np.random.uniform(55, 60)
        total_distance = np.random.uniform(20000, 30000)
        x_ratio = 0.5  # Quá cân bằng
        anomaly_score = np.random.uniform(0.8, 0.95)

    elif fraud_type == "bot_script":
        # Bot: pattern lặp, perfect
        movement_span = np.random.uniform(58, 60)
        total_distance = np.random.uniform(25000, 35000)
        x_ratio = 0.48  # Gần perfect
        anomaly_score = np.random.uniform(0.85, 0.98)

    elif fraud_type == "afk_jiggler":
        # Jiggler: ít di chuyển
        movement_span = np.random.uniform(58, 60)
        total_distance = np.random.uniform(1000, 5000)  # Rất ít
        x_ratio = np.random.uniform(0.45, 0.55)
        anomaly_score = np.random.uniform(0.7, 0.9)

    elif fraud_type == "rapid_clicker":
        # Click nhanh: nhiều flips
        movement_span = np.random.uniform(50, 60)
        total_distance = np.random.uniform(40000, 60000)  # Nhiều
        x_ratio = np.random.uniform(0.4, 0.6)
        anomaly_score = np.random.uniform(0.9, 1.0)

    elif fraud_type == "perfect_trajectory":
        # Đường hoàn hảo
        movement_span = np.random.uniform(56, 60)
        total_distance = np.random.uniform(22000, 28000)
        x_ratio = 0.5  # Perfect
        anomaly_score = np.random.uniform(0.95, 1.0)

    # Tính metrics với is_normal=False
    metrics = calculate_mouse_metrics(
        movement_span=movement_span,
        total_distance=total_distance,
        x_ratio=x_ratio,
        is_normal=False
    )

    # Timestamp (không quan trọng)
    timestamp = BASE_TIME.replace(
        day=np.random.randint(1, 29),
        hour=np.random.randint(9, 17),
        minute=np.random.randint(0, 60),
        second=np.random.randint(0, 60)
    )

    session_id_str = f"FRAUD_{session_id:04d}_{timestamp.strftime('%H%M%S')}"
    alert_severity = "CRITICAL" if anomaly_score > 0.9 else "WARNING"

    # Thêm alert
    rows_alerts.append({
        "Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "Event_Type": "MOUSE_SESSION",
        "Details": f"{fraud_type} detected",
        "User": USER,
        "Session_ID": session_id_str,
        "Severity": alert_severity,
        "IsFraud": True,
        "Date": timestamp.strftime('%Y-%m-%d'),
        "Time": timestamp.strftime('%H:%M:%S'),
        "Module": "Mouse"
    })

    return {
        # Metadata
        "Timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'),
        "Event_Type": "MOUSE_SESSION",
        "Details": f"{fraud_type} - Score: {anomaly_score:.3f}",
        "User": USER,
        "Session_ID": session_id_str,
        "Severity": alert_severity,
        "IsFraud": True,
        "Date": timestamp.strftime('%Y-%m-%d'),
        "Time": timestamp.strftime('%H:%M:%S'),
        "Module": "Mouse",

        # Behavior metrics (BẤT THƯỜNG)
        "TotalEvents": metrics['total_events'],
        "TotalMoves": metrics['total_events'],
        "TotalDistance": round(metrics['total_distance'], 2),
        "XAxisDistance": round(metrics['x_distance'], 2),
        "YAxisDistance": round(metrics['y_distance'], 2),
        "XFlips": metrics['x_flips'],
        "YFlips": metrics['y_flips'],
        "MovementTimeSpan": round(metrics['movement_span'], 2),
        "Velocity": round(metrics['velocity'], 2),
        "Acceleration": round(abs(metrics['acceleration']), 2),
        "XVelocity": round(metrics['x_velocity'], 2),
        "YVelocity": round(metrics['y_velocity'], 2),
        "XAcceleration": round(abs(metrics['x_acceleration']), 2),
        "YAcceleration": round(abs(metrics['y_acceleration']), 2),
        "DurationSeconds": round(metrics['movement_span'], 2),
        "AnomalyScore": round(anomaly_score, 3)
    }


# =========================
# TẠO DATASET
# =========================
print("🔄 Tạo dataset thuần behavior...")

# Tính số lượng
num_normal = int(NUM_SESSIONS * NORMAL_RATIO)
num_fraud = int(NUM_SESSIONS * FRAUD_RATIO)

# Fraud types và phân bố
fraud_types = ["macro_automation", "bot_script", "afk_jiggler",
               "rapid_clicker", "perfect_trajectory"]
fraud_weights = [0.30, 0.25, 0.20, 0.15, 0.10]

# Tạo normal sessions
print(f"✅ Tạo {num_normal} normal sessions...")
for i in range(num_normal):
    session = generate_normal_session(i)
    rows_all_events.append(session)

# Tạo fraud sessions
print(f"⚠️ Tạo {num_fraud} fraud sessions...")
for i in range(num_fraud):
    fraud_type = random.choices(fraud_types, weights=fraud_weights)[0]
    session = generate_fraud_session(i, fraud_type)
    rows_all_events.append(session)

# Trộn ngẫu nhiên
random.shuffle(rows_all_events)

# =========================
# LƯU KẾT QUẢ
# =========================
print("💾 Lưu dataset...")

# Cột metadata (chỉ để tracking)
common_columns = [
    "Timestamp", "Event_Type", "Details", "User", "Session_ID",
    "Severity", "IsFraud", "Date", "Time", "Module"
]

# Cột behavior metrics (quan trọng cho model)
mouse_columns = [
    "TotalEvents", "TotalMoves", "TotalDistance", "XAxisDistance",
    "YAxisDistance", "XFlips", "YFlips", "MovementTimeSpan",
    "Velocity", "Acceleration", "XVelocity", "YVelocity",
    "XAcceleration", "YAcceleration", "DurationSeconds", "AnomalyScore"
]

all_columns = common_columns + mouse_columns

df_all_events = pd.DataFrame(rows_all_events, columns=all_columns)
df_alerts = pd.DataFrame(rows_alerts, columns=common_columns)

# Tạo thư mục
month_year = BASE_TIME.strftime("%Y_%m")
output_dir = f"Saved_file/{USER}/Mouse/{month_year}"
os.makedirs(output_dir, exist_ok=True)

output_path = os.path.join(output_dir, f"mouse_logs_{USER}_{month_year}.xlsx")

# Lưu Excel
with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
    df_all_events.to_excel(writer, sheet_name='All_Events', index=False)
    df_alerts.to_excel(writer, sheet_name='Alerts', index=False)

    # Summary
    summary_data = {
        'Metric': [
            'Total Sessions', 'Normal Sessions', 'Fraud Sessions',
            'Fraud Ratio', 'Avg Velocity', 'Avg Acceleration',
            'Avg XFlips', 'Avg YFlips', 'Avg AnomalyScore'
        ],
        'Value': [
            len(df_all_events),
            num_normal,
            num_fraud,
            f"{FRAUD_RATIO * 100:.1f}%",
            round(df_all_events['Velocity'].mean(), 2),
            round(df_all_events['Acceleration'].mean(), 2),
            round(df_all_events['XFlips'].mean(), 1),
            round(df_all_events['YFlips'].mean(), 1),
            round(df_all_events['AnomalyScore'].mean(), 3)
        ]
    }
    pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)

# =========================
# XUẤT THỐNG KÊ
# =========================
print("\n" + "=" * 60)
print("✅ DATASET THUẦN BEHAVIOR ĐÃ HOÀN THÀNH")
print("=" * 60)

print(f"\n📊 THỐNG KÊ BEHAVIOR:")
print(f"   • Normal: {num_normal} sessions")
print(f"   • Fraud:  {num_fraud} sessions")

print(f"\n🎯 CÁC LOẠI BEHAVIOR BẤT THƯỜNG:")
for ftype in fraud_types:
    count = len([x for x in rows_all_events if x['Details'].startswith(ftype)])
    if count > 0:
        print(f"   • {ftype}: {count}")

print(f"\n📈 ĐẶC ĐIỂM BEHAVIOR NORMAL vs FRAUD:")
normal_sessions = [x for x in rows_all_events if not x['IsFraud']]
fraud_sessions = [x for x in rows_all_events if x['IsFraud']]

print(f"   Normal - Avg Velocity: {np.mean([s['Velocity'] for s in normal_sessions]):.1f}")
print(f"   Fraud  - Avg Velocity: {np.mean([s['Velocity'] for s in fraud_sessions]):.1f}")
print(f"   Normal - Avg XFlips: {np.mean([s['XFlips'] for s in normal_sessions]):.1f}")
print(f"   Fraud  - Avg XFlips: {np.mean([s['XFlips'] for s in fraud_sessions]):.1f}")
print(f"   Normal - Avg Acceleration: {np.mean([s['Acceleration'] for s in normal_sessions]):.1f}")
print(f"   Fraud  - Avg Acceleration: {np.mean([s['Acceleration'] for s in fraud_sessions]):.1f}")

print(f"\n📁 File: {output_path}")
print(f"   • Chỉ tập trung vào BEHAVIOR thuần túy")
print(f"   • Không phụ thuộc thời gian/ngày")
print(f"   • Sẵn sàng cho training model")