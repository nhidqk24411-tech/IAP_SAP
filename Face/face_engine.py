"""
face_engine.py
Face Recognition Engine - MobileFaceNet compatible
"""

import os
import json
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

SAVE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Face\Save_file"


class FaceRecognitionML:
    def __init__(self,
                 db_embeddings_path=None,
                 db_names_path=None,
                 db_ids_path=None):

        print("📂 Loading face database...")

        db_embeddings_path = db_embeddings_path or os.path.join(SAVE_DIR, "embeddings.npy")
        db_names_path = db_names_path or os.path.join(SAVE_DIR, "names.json")
        db_ids_path = db_ids_path or os.path.join(SAVE_DIR, "ids.json")

        # Load embeddings
        if os.path.exists(db_embeddings_path):
            self.db_embeddings = np.load(db_embeddings_path)
            if self.db_embeddings.ndim == 1:
                self.db_embeddings = self.db_embeddings.reshape(1, -1)
        else:
            self.db_embeddings = np.empty((0, 128))

        # Load names
        if os.path.exists(db_names_path):
            with open(db_names_path, "r", encoding="utf-8") as f:
                self.db_names = json.load(f)
        else:
            self.db_names = []

        # Load ids
        if os.path.exists(db_ids_path):
            with open(db_ids_path, "r", encoding="utf-8") as f:
                self.db_ids = json.load(f)
        else:
            self.db_ids = self.db_names

        # Normalize DB embeddings
        if len(self.db_embeddings) > 0:
            self.db_embeddings = self._normalize(self.db_embeddings)

        print(f"✅ Database loaded: {len(self.db_names)} users")

    def _normalize(self, emb):
        norms = np.linalg.norm(emb, axis=1, keepdims=True)
        return emb / np.maximum(norms, 1e-10)

    def match_face(self, query_embedding, threshold=0.35):
        if self.db_embeddings.size == 0:
            return {"best_match": None, "matched": False}

        query_embedding = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

        sims = cosine_similarity(
            query_embedding.reshape(1, -1),
            self.db_embeddings
        )[0]

        best_idx = int(np.argmax(sims))
        best_score = float(sims[best_idx])

        if best_score >= threshold:
            return {
                "best_match": {
                    "name": self.db_names[best_idx],
                    "id": self.db_ids[best_idx],
                    "similarity": best_score,
                    "matched": True
                },
                "matched": True
            }

        return {
            "best_match": {
                "name": "Unknown",
                "similarity": best_score,
                "matched": False
            },
            "matched": False
        }

    def get_database_info(self):
        return {
            "num_people": len(self.db_names),
            "embedding_shape": self.db_embeddings.shape
        }
