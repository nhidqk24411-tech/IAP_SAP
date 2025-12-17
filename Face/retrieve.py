"""
retrieve_embeddings.py
Tạo database embeddings từ dataset ảnh.
Hỗ trợ thêm nhân viên mới vào database hiện có.
"""

import os
import json
import cv2
import numpy as np
from insightface.app import FaceAnalysis
from pathlib import Path

# ==========================
#  CONFIG
# ==========================
DATASET_DIR = r"C:\Users\PC\Downloads\anh"
EMB_OUT = "embeddings.npy"
NAME_OUT = "names.json"
ID_OUT = "ids.json"
MODEL_NAME = 'buffalo_l'  # Thêm cấu hình model name


def l2_normalize(v):
    """Chuẩn hóa vector về độ dài đơn vị."""
    return v / (np.linalg.norm(v) + 1e-10)


def load_existing_database(emb_file, name_file, id_file):
    """Nạp database embeddings hiện tại nếu có."""
    if os.path.exists(emb_file) and os.path.exists(name_file) and os.path.exists(id_file):
        embeddings = np.load(emb_file)
        with open(name_file, 'r', encoding='utf-8') as f:
            names = json.load(f)
        with open(id_file, 'r', encoding='utf-8') as f:
            ids = json.load(f)
        return embeddings, names, ids
    else:
        return np.array([]), [], []


def save_database(embeddings, names, ids, emb_file, name_file, id_file):
    """Lưu database embeddings."""
    np.save(emb_file, np.array(embeddings))
    with open(name_file, "w", encoding='utf-8') as f:
        json.dump(names, f, indent=4, ensure_ascii=False)
    with open(id_file, "w", encoding='utf-8') as f:
        json.dump(ids, f, indent=4, ensure_ascii=False)


def add_employee_by_id(employee_id, dataset_dir=DATASET_DIR, emb_file=EMB_OUT, name_file=NAME_OUT, id_file=ID_OUT):
    """
    Thêm nhân viên vào database bằng ID.
    ID phải là tên thư mục trong dataset_dir.
    """
    # Nạp database hiện tại
    embeddings, names, ids = load_existing_database(emb_file, name_file, id_file)

    # Kiểm tra xem ID đã tồn tại chưa
    if employee_id in ids:
        print(f"ID {employee_id} đã tồn tại trong database. Cập nhật embedding...")
        # Xóa embedding cũ
        idx = ids.index(employee_id)
        embeddings = np.delete(embeddings, idx, axis=0)
        names.pop(idx)
        ids.pop(idx)

    # Đường dẫn thư mục của nhân viên
    person_dir = os.path.join(dataset_dir, str(employee_id))
    if not os.path.isdir(person_dir):
        print(f"Không tìm thấy thư mục cho ID {employee_id} trong {dataset_dir}")
        return False

    print(f"Processing: {employee_id}")
    person_emb_list = []

    # Khởi tạo model
    app = FaceAnalysis(name=MODEL_NAME, providers=['CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    # Duyệt ảnh của nhân viên
    for img_file in os.listdir(person_dir):
        img_path = os.path.join(person_dir, img_file)
        img = cv2.imread(img_path)

        if img is None:
            print(f"  → Error loading: {img_path}")
            continue

        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        faces = app.get(img_rgb)

        if len(faces) == 0:
            print(f"  → No face detected: {img_path}")
            continue

        # Lấy mặt đầu tiên (giả sử mỗi ảnh chỉ có 1 khuôn mặt trong dataset)
        face = faces[0]
        emb = l2_normalize(face.embedding.astype(np.float32))
        person_emb_list.append(emb)

    # Nếu có ít nhất 1 embedding cho người này, lấy trung bình
    if len(person_emb_list) > 0:
        avg_emb = l2_normalize(np.mean(person_emb_list, axis=0))
        embeddings = np.vstack([embeddings, avg_emb]) if embeddings.size else np.array([avg_emb])
        names.append(str(employee_id))  # Dùng ID làm tên, có thể thay đổi nếu có metadata
        ids.append(employee_id)
        print(f"  → ID: {employee_id}, Images: {len(person_emb_list)}")
    else:
        print(f"  → Skipped (no valid face images)")
        return False

    # Lưu database
    save_database(embeddings, names, ids, emb_file, name_file, id_file)

    print("\n" + "=" * 50)
    print(" DATABASE UPDATED SUCCESSFULLY!")
    print(f" Total people: {len(names)}")
    print("=" * 50)
    return True
