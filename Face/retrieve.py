# retrieve.py
# Create face database using InsightFace embedding (NO MobileFaceNet)

import os
import json
import cv2
import numpy as np
from insightface.app import FaceAnalysis

# =====================
# PATH CONFIG
# =====================
DATASET_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Face\anh"
SAVE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Face\Save_file"

os.makedirs(SAVE_DIR, exist_ok=True)


def create_database():
    print("=" * 60)
    print("🛠️  CREATE FACE DATABASE (InsightFace)")
    print("=" * 60)

    if not os.path.exists(DATASET_DIR):
        print(f"❌ Dataset not found: {DATASET_DIR}")
        return False

    detector = FaceAnalysis(providers=["CPUExecutionProvider"])
    detector.prepare(ctx_id=0, det_size=(640, 640))

    all_embeddings = []
    all_names = []
    all_ids = []

    persons = [
        d for d in os.listdir(DATASET_DIR)
        if os.path.isdir(os.path.join(DATASET_DIR, d))
    ]

    print(f"📁 Found {len(persons)} persons")

    for person_id in persons:
        person_path = os.path.join(DATASET_DIR, person_id)
        images = [
            f for f in os.listdir(person_path)
            if f.lower().endswith((".jpg", ".png", ".jpeg"))
        ]

        if not images:
            continue

        print(f"\n👤 Processing: {person_id}")
        embeddings = []

        for img_name in images[:5]:
            img_path = os.path.join(person_path, img_name)
            img = cv2.imread(img_path)
            if img is None:
                continue

            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            faces = detector.get(img_rgb)
            if not faces:
                continue

            face = faces[0]
            emb = face.embedding
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            embeddings.append(emb)

        if embeddings:
            mean_emb = np.mean(embeddings, axis=0)
            mean_emb = mean_emb / (np.linalg.norm(mean_emb) + 1e-10)

            all_embeddings.append(mean_emb)
            all_names.append(person_id)
            all_ids.append(person_id)

            print(f"   ✅ {len(embeddings)} images processed")

    if not all_embeddings:
        print("❌ No embeddings created")
        return False

    embeddings_array = np.array(all_embeddings)

    np.save(os.path.join(SAVE_DIR, "embeddings.npy"), embeddings_array)
    with open(os.path.join(SAVE_DIR, "names.json"), "w", encoding="utf-8") as f:
        json.dump(all_names, f, indent=2, ensure_ascii=False)
    with open(os.path.join(SAVE_DIR, "ids.json"), "w", encoding="utf-8") as f:
        json.dump(all_ids, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 50)
    print("✅ DATABASE CREATED SUCCESSFULLY")
    print(f"👥 Persons: {len(all_names)}")
    print(f"📐 Embeddings shape: {embeddings_array.shape}")
    print(f"💾 Saved to: {SAVE_DIR}")
    print("=" * 50)

    return True


if __name__ == "__main__":
    create_database()
