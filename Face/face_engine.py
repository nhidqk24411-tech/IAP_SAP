# FILE: face_engine.py
# (Trước đây là main.py - Đổi tên để làm module)

import numpy as np
import json
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
import cv2


class FaceRecognitionML:
    def __init__(self, db_embeddings_path: str, db_names_path: str, db_ids_path: str = None):
        # Load database
        self.db_embeddings = np.load(db_embeddings_path)
        with open(db_names_path, 'r', encoding='utf-8') as f:
            self.db_names = json.load(f)

        # Hỗ trợ trường hợp không có file ids (dùng file names thay thế tạm)
        # Logic này được thêm vào để code linh hoạt hơn
        if db_ids_path:
            try:
                with open(db_ids_path, 'r', encoding='utf-8') as f:
                    self.db_ids = json.load(f)
            except FileNotFoundError:
                self.db_ids = self.db_names
        else:
            self.db_ids = self.db_names

        self.db_embeddings = self._normalize_embeddings(self.db_embeddings)
        print(f"Loaded database: {len(self.db_names)} people")

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        return embeddings / np.maximum(norms, 1e-10)

    def _preprocess_embedding(self, embedding: np.ndarray) -> np.ndarray:
        embedding = np.array(embedding, dtype=np.float32).flatten()
        return embedding / (np.linalg.norm(embedding) + 1e-10)

    def match_face(self, query_embedding: np.ndarray, threshold: float = 0.35, top_k: int = 1) -> Dict:
        """
        Hàm so khớp embedding truyền vào với database
        """
        query_norm = self._preprocess_embedding(query_embedding)

        # Tính toán cosine similarity
        similarities = cosine_similarity([query_norm], self.db_embeddings)[0]

        # Tìm các kết quả tốt nhất
        top_indices = np.argsort(similarities)[::-1][:top_k]

        results = []
        for idx in top_indices:
            # Kiểm tra boundary để tránh lỗi index nếu database trống hoặc nhỏ
            if idx < len(self.db_names):
                results.append({
                    'id': self.db_ids[idx] if idx < len(self.db_ids) else "Unknown",
                    'name': self.db_names[idx],
                    'similarity': float(similarities[idx]),
                    'matched': similarities[idx] >= threshold
                })

        best_match = results[0] if results else None

        return {
            'best_match': best_match,
            'top_matches': results,
            'threshold': threshold
        }

    # --- CÁC HÀM DƯỚI ĐÂY ĐÃ ĐƯỢC KHÔI PHỤC ---

    def adaptive_threshold(self, quality_score: float) -> float:
        """
        Điều chỉnh threshold dựa trên chất lượng khuôn mặt.
        """
        base_threshold = 0.35
        if quality_score > 0.8:  # Chất lượng cao -> Giảm ngưỡng (dễ chấp nhận hơn vì ảnh rõ)
            return base_threshold - 0.05
        elif quality_score < 0.4:  # Chất lượng thấp -> Tăng ngưỡng (khắt khe hơn)
            return base_threshold + 0.1
        return base_threshold

    def analyze_face_quality(self, face_image: np.ndarray) -> float:
        """
        Phân tích chất lượng khuôn mặt (0-1).
        Hàm này cần thiết nếu bạn muốn lọc ảnh mờ từ Camera trước khi nhận diện.
        """
        if face_image is None or face_image.size == 0:
            return 0.0

        # Chuyển sang ảnh xám
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image

        # 1. Kiểm tra độ blur (Laplacian variance)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Chuẩn hóa điểm blur (ví dụ > 100 là rõ)
        blur_score = min(blur_value / 100.0, 1.0)

        # 2. Kiểm tra độ tương phản
        contrast = gray.std()
        contrast_score = min(contrast / 50.0, 1.0)

        # 3. Kiểm tra độ sáng (lý tưởng là quanh 128)
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128.0

        # Tính tổng điểm (trọng số có thể tùy chỉnh)
        total_score = (blur_score * 0.4 + contrast_score * 0.3 + brightness_score * 0.3)

        return float(total_score)

    def verify_multiple_angles(self, embeddings_list: List[np.ndarray]) -> Dict:
        """
        Xác thực dựa trên danh sách các embedding (ví dụ: lấy từ 5 frame liên tiếp).
        Giúp tăng độ chính xác thay vì chỉ dựa vào 1 frame.
        """
        if not embeddings_list:
            return {'verified': False, 'confidence': 0.0}

        # Chuẩn hóa tất cả embeddings
        normalized_embs = [self._preprocess_embedding(emb) for emb in embeddings_list]

        # So sánh với database
        all_scores = []
        for emb in normalized_embs:
            similarities = cosine_similarity([emb], self.db_embeddings)[0]
            all_scores.append(np.max(similarities))

        # Lấy điểm trung bình và cao nhất
        avg_score = np.mean(all_scores)
        max_score = np.max(all_scores)

        # Quyết định dựa trên cả hai
        final_threshold = 0.30  # Threshold thấp hơn cho multiple angles
        verified = avg_score >= final_threshold and max_score >= 0.35

        return {
            'verified': verified,
            'confidence': float(avg_score),
            'max_confidence': float(max_score),
            'scores': [float(s) for s in all_scores]
        }