import os
import json
import cv2
import numpy as np
from insightface.app import FaceAnalysis

# ==========================
#  CONFIG
# ==========================
DATASET_DIR = r"C:\Users\PC\Downloads\anh"
     # thư mục chứa ảnh của từng người
EMB_OUT = "embeddings.npy"      # file lưu embedding database
NAME_OUT = "names.json"         # file lưu danh sách tên


# ==========================
#  HÀM: Chuẩn hóa vector
# ==========================
def l2_normalize(v):
    return v / (np.linalg.norm(v) + 1e-10)


# ==========================
#  HÀM: Tạo embeddings từ ảnh
# ==========================
def create_face_database():
    # Load model
    print("Initializing InsightFace...")
    app = FaceAnalysis()
    app.prepare(ctx_id=0, det_size=(640, 640))

    embeddings = []
    names = []

    # Duyệt qua từng người trong thư mục dataset
    for person_name in os.listdir(DATASET_DIR):
        person_dir = os.path.join(DATASET_DIR, person_name)

        if not os.path.isdir(person_dir):
            continue

        print(f"\nProcessing person: {person_name}")
        person_emb_list = []

        # Duyệt ảnh của từng người
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

            # Lấy mặt đầu tiên
            face = faces[0]

            emb = l2_normalize(face.embedding.astype(np.float32))
            person_emb_list.append(emb)

        # Nếu người này có embedding thì lấy trung bình
        if len(person_emb_list) > 0:
            avg_emb = l2_normalize(np.mean(person_emb_list, axis=0))
            embeddings.append(avg_emb)
            names.append(person_name)
            print(f"  → OK: {len(person_emb_list)} images used")
        else:
            print(f"  → Skipped (no valid face images)")

    # Lưu file
    np.save(EMB_OUT, np.array(embeddings))
    with open(NAME_OUT, "w") as f:
        json.dump(names, f, indent=4)

    print("\n============================")
    print(" Database created successfully!")
    print(" Saved files:")
    print(f"   → {EMB_OUT}")
    print(f"   → {NAME_OUT}")
    print("============================")


# ==========================
#  MAIN
# ==========================
if __name__ == "__main__":
    create_face_database()
