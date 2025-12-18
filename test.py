import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# =========================
# CONFIG
# =========================
np.random.seed(42)
random.seed(42)

NUM_SESSIONS_PER_TYPE = 150
BASE_TIME = datetime.now()

rows = []


# =========================
# BASE ROW
# =========================
def base_row(session_id, start, duration=60):
    return {
        'SessionID': session_id,
        'StartTime': start,
        'EndTime': start + timedelta(seconds=duration),
        'Duration(s)': duration
    }


# =========================
# LABEL = 0 → HUMAN NORMAL
# =========================
def gen_human(i):
    duration = 60
    move_span = np.random.uniform(35, 58)
    total_dist = np.random.uniform(6000, 30000)
    velocity = total_dist / move_span

    return {
        **base_row(f"HUMAN_{i:04d}", BASE_TIME + timedelta(minutes=i)),
        'TotalEvents': np.random.randint(800, 3000),
        'TotalMoves': np.random.randint(800, 3000),
        'TotalDistance': round(total_dist, 2),
        'XAxisDistance': round(total_dist * np.random.uniform(0.4, 0.6), 2),  # ĐỔI TÊN
        'YAxisDistance': round(total_dist * np.random.uniform(0.4, 0.6), 2),  # ĐỔI TÊN
        'XFlips': np.random.randint(30, 120),
        'YFlips': np.random.randint(30, 120),
        'MovementTimeSpan': round(move_span, 2),
        'Velocity': round(velocity, 2),
        'Acceleration': round(velocity * np.random.uniform(0.7, 2.0), 2),
        'XVelocity': round(velocity * np.random.uniform(0.4, 0.7), 2),
        'YVelocity': round(velocity * np.random.uniform(0.4, 0.7), 2),
        'Label': 0
    }


# =========================
# LABEL = 1 → BOT / FRAUD
# =========================
def gen_bot_macro(i):
    duration = 60
    move_span = np.random.uniform(55, 60)
    velocity = np.random.uniform(450, 650)
    total_dist = velocity * move_span

    return {
        **base_row(f"BOT_MACRO_{i:04d}", BASE_TIME + timedelta(minutes=i)),
        'TotalEvents': np.random.randint(300, 600),
        'TotalMoves': np.random.randint(300, 600),
        'TotalDistance': round(total_dist, 2),
        'XAxisDistance': round(total_dist * 0.5, 2),  # ĐỔI TÊN
        'YAxisDistance': round(total_dist * 0.5, 2),  # ĐỔI TÊN
        'XFlips': np.random.randint(2, 6),
        'YFlips': np.random.randint(2, 6),
        'MovementTimeSpan': round(move_span, 2),
        'Velocity': round(velocity, 2),
        'Acceleration': round(velocity * 0.05, 2),
        'XVelocity': round(velocity * 0.5, 2),
        'YVelocity': round(velocity * 0.5, 2),
        'Label': 1
    }


def gen_bot_jitter(i):
    duration = 60
    move_span = np.random.uniform(50, 60)
    total_dist = np.random.uniform(4000, 7000)
    velocity = total_dist / move_span

    return {
        **base_row(f"BOT_JITTER_{i:04d}", BASE_TIME + timedelta(minutes=i)),
        'TotalEvents': np.random.randint(1500, 3000),
        'TotalMoves': np.random.randint(1500, 3000),
        'TotalDistance': round(total_dist, 2),
        'XAxisDistance': round(total_dist * np.random.uniform(0.48, 0.52), 2),  # ĐỔI TÊN
        'YAxisDistance': round(total_dist * np.random.uniform(0.48, 0.52), 2),  # ĐỔI TÊN
        'XFlips': np.random.randint(5, 15),
        'YFlips': np.random.randint(5, 15),
        'MovementTimeSpan': round(move_span, 2),
        'Velocity': round(velocity, 2),
        'Acceleration': round(velocity * 0.1, 2),
        'XVelocity': round(velocity * 0.5, 2),
        'YVelocity': round(velocity * 0.5, 2),
        'Label': 1
    }


def gen_afk_fake(i):
    duration = 60
    move_span = np.random.uniform(5, 15)
    total_dist = np.random.uniform(300, 800)
    velocity = total_dist / move_span

    return {
        **base_row(f"AFK_FAKE_{i:04d}", BASE_TIME + timedelta(minutes=i)),
        'TotalEvents': np.random.randint(50, 200),
        'TotalMoves': np.random.randint(50, 200),
        'TotalDistance': round(total_dist, 2),
        'XAxisDistance': round(total_dist * 0.5, 2),  # ĐỔI TÊN
        'YAxisDistance': round(total_dist * 0.5, 2),  # ĐỔI TÊN
        'XFlips': np.random.randint(1, 4),
        'YFlips': np.random.randint(1, 4),
        'MovementTimeSpan': round(move_span, 2),
        'Velocity': round(velocity, 2),
        'Acceleration': round(velocity * 0.02, 2),
        'XVelocity': round(velocity * 0.5, 2),
        'YVelocity': round(velocity * 0.5, 2),
        'Label': 1
    }


# =========================
# GENERATE DATASET
# =========================
for i in range(NUM_SESSIONS_PER_TYPE):
    rows.append(gen_human(i))
    rows.append(gen_bot_macro(i))
    rows.append(gen_bot_jitter(i))
    rows.append(gen_afk_fake(i))

df = pd.DataFrame(rows)

# Shuffle dataset
df = df.sample(frac=1).reset_index(drop=True)

# Tạo thư mục nếu chưa tồn tại
output_dir = "Mouse/Saved_file"
os.makedirs(output_dir, exist_ok=True)

# Save
output_path = os.path.join(output_dir, "training_data_mouse_binary_label.xlsx")
df.to_excel(output_path, sheet_name="Binary_Labeled_Sessions", index=False)

print(f"✅ Dataset generated: {output_path}")
print(f"📊 Dataset shape: {df.shape}")
print("\nLabel distribution:")
print(df['Label'].value_counts())
print("\n📋 Columns available:")
print(df.columns.tolist())
print("\n🔍 Checking for required columns:")
required_columns = [
    'Velocity', 'Acceleration',
    'XFlips', 'YFlips',
    'TotalDistance', 'MovementTimeSpan',
    'XVelocity', 'YVelocity',
    'XAxisDistance', 'YAxisDistance'
]

for col in required_columns:
    status = "✅" if col in df.columns else "❌"
    print(f"{status} {col}")