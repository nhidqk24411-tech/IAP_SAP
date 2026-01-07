"""
main_face_simple.py - Face recognition system chỉ làm single check
"""

import cv2
import numpy as np
import os
import json
import time
from datetime import datetime

from insightface.app import FaceAnalysis

from Face.face_engine import FaceRecognitionML
from Face.face_verification import FaceVerification

SAVE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Face\Save_file"


class FaceSingleCheck:
    """Hệ thống face chỉ làm single check một lần"""

    SIMILARITY_THRESHOLD = 0.35

    def __init__(self, user_name=None, global_logger=None):  # THÊM THAM SỐ global_logger
        self.detector = None
        self.engine = None
        self.verifier = None
        self.user_name = user_name  # LƯU TÊN USER NẾU CÓ
        self.global_logger = global_logger  # LƯU GLOBAL LOGGER
        self._init_models()

    def _init_models(self):
        """Khởi tạo models"""
        print("🔍 Initializing Face Single Check System...")

        # Hiển thị user name nếu có (cho debug)
        if self.user_name is not None:
            print(f"   Initialized for user: {self.user_name}")

        self.detector = FaceAnalysis(providers=["CPUExecutionProvider"])
        self.detector.prepare(ctx_id=0, det_size=(640, 640))
        print("✅ Face detector loaded")

        self.engine = FaceRecognitionML()
        print(f"✅ Face engine loaded ({len(self.engine.db_names)} users)")

        # Khởi tạo FaceVerification với user_name và global_logger
        self.verifier = FaceVerification(self.detector, user_name=self.user_name, global_logger=self.global_logger)
        print("✅ Face verification loaded")

    def check_single_face(self, frame):
        """Check face một lần từ frame - trả về kết quả"""
        if frame is None:
            return None

        try:
            img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = self.detector.get(img_rgb)

            if not faces:
                return {
                    "success": False,
                    "message": "No face detected",
                    "name": "Unknown",
                    "similarity": 0.0,
                    "matched": False
                }

            face = faces[0]
            bbox = face.bbox.astype(int).tolist()
            landmarks = face.kps
            embedding = face.embedding
            embedding = embedding / (np.linalg.norm(embedding) + 1e-10)

            # Match face trước để có tên và similarity
            result = self.engine.match_face(
                embedding,
                threshold=self.SIMILARITY_THRESHOLD
            )

            best = result.get("best_match")
            user_name = best.get("name", "Unknown") if best else "Unknown"
            similarity = best.get("similarity", 0.0) if best else 0.0

            # Liveness check
            is_live, live_msg = self.verifier.check_liveness_basic(
                frame=frame,
                bbox=bbox,
                landmarks=landmarks,
                face_id=None,
                similarity=similarity
            )

            if not is_live:
                return {
                    "success": False,
                    "message": f"Liveness check failed: {live_msg}",
                    "name": user_name,
                    "similarity": similarity,
                    "matched": False
                }

            # Spoof check
            is_real, spoof_msg = self.verifier.check_spoofing(
                frame, bbox, similarity
            )
            if not is_real:
                return {
                    "success": False,
                    "message": f"Spoof detected: {spoof_msg}",
                    "name": user_name,
                    "similarity": similarity,
                    "matched": False
                }

            # Nếu pass tất cả check
            if best and best.get("matched", False):
                # Lưu ảnh SUCCESS
                self.verifier._save_capture_image(frame, bbox, "SUCCESS")

                return {
                    "success": True,
                    "message": "Face check successful",
                    "name": user_name,
                    "similarity": similarity,
                    "matched": True,
                    "timestamp": datetime.now().strftime("%H:%M:%S")
                }
            else:
                # Lưu ảnh FAILED (không match trong DB)
                self.verifier._save_capture_image(frame, bbox, "NO_MATCH")

                return {
                    "success": False,
                    "message": "No match found in database",
                    "name": "Unknown",
                    "similarity": similarity,
                    "matched": False
                }

        except Exception as e:
            print(f"❌ Face check error: {e}")
            return {
                "success": False,
                "message": f"System error: {str(e)}",
                "name": "Unknown",
                "similarity": 0.0,
                "matched": False
            }

    def verify_user(self, frame, expected_user=None):
        """Verify user với user mong đợi"""
        result = self.check_single_face(frame)

        if not result["success"]:
            return False, result["message"]

        if not result["matched"]:
            return False, "Face not recognized in database"

        detected_user = result["name"]
        similarity = result["similarity"]

        if expected_user and detected_user != expected_user:
            # Lưu ảnh USER_MISMATCH
            self.verifier._save_capture_image(
                frame,
                [0, 0, frame.shape[1], frame.shape[0]],  # Full frame
                "USER_MISMATCH"
            )
            return False, f"User mismatch: {detected_user} (expected: {expected_user})"

        return True, f"Verified as {detected_user} ({similarity:.2%})"

    def check_from_camera(self):
        """Check face trực tiếp từ camera (mở và đóng ngay)"""
        camera = None
        try:
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                return {
                    "success": False,
                    "message": "Cannot open camera",
                    "name": "Unknown",
                    "similarity": 0.0,
                    "matched": False
                }

            # Đọc frame
            ret, frame = camera.read()
            if not ret:
                return {
                    "success": False,
                    "message": "Failed to capture frame",
                    "name": "Unknown",
                    "similarity": 0.0,
                    "matched": False
                }

            return self.check_single_face(frame)

        except Exception as e:
            print(f"❌ Camera check error: {e}")
            return {
                "success": False,
                "message": f"Camera error: {str(e)}",
                "name": "Unknown",
                "similarity": 0.0,
                "matched": False
            }
        finally:
            if camera is not None:
                camera.release()