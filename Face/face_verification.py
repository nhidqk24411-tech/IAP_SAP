"""
face_verification.py
Face verification với global logging
"""

import cv2
import numpy as np
import time
import os
import pandas as pd
from datetime import datetime
from typing import Tuple, Optional
import traceback


class FaceVerification:
    def __init__(self, detection_model, user_name: str = "", global_logger=None):
        self.detection_model = detection_model
        self.user_name = user_name
        self.global_logger = global_logger

        print(f"🔍 Initializing FaceVerification for user: {user_name}")

        # Chỉ tạo thư mục capture nếu cần
        if user_name and user_name.strip():
            # Đường dẫn capture sẽ lấy từ global logger hoặc tạo mới
            self.CAPTURE_DIR = None
            if global_logger and hasattr(global_logger, 'PATHS'):
                self.CAPTURE_DIR = global_logger.PATHS.get('face_captures')

            if not self.CAPTURE_DIR:
                # Fallback: tạo đường dẫn mặc định
                self.BASE_DIR = r"C:\Users\legal\PycharmProjects\PythonProject\Saved_file"
                self.user_dir = os.path.join(self.BASE_DIR, user_name)
                current_date = datetime.now()
                current_year_month = current_date.strftime("%Y_%m")
                self.CAPTURE_DIR = os.path.join(self.user_dir, current_year_month, "face_captures")

            os.makedirs(self.CAPTURE_DIR, exist_ok=True)
            print(f"✅ Face capture directory ready: {self.CAPTURE_DIR}")

        # Các tham số detection (giữ nguyên)
        self.blur_threshold = 50
        self.face_movement_threshold = 3.0
        self.min_face_size = 80
        self.brightness_min = 40
        self.brightness_max = 200
        self.saturation_threshold = 20
        self.contrast_threshold = 20
        self.failure_count = 0
        self.max_consecutive_failures = 3
        self.prev_landmarks = None
        self.prev_face_id = None

    def check_liveness_basic(
            self,
            frame: np.ndarray,
            bbox: list,
            landmarks: np.ndarray,
            face_id: Optional[str] = None,
            similarity: float = 0.0
    ) -> Tuple[bool, str]:
        """Liveness check với global logging"""
        x1, y1, x2, y2 = bbox
        face_roi = frame[y1:y2, x1:x2]

        if face_roi.size == 0:
            return False, "Invalid face ROI"

        if face_id != self.prev_face_id:
            self.prev_landmarks = None
            self.prev_face_id = face_id

        try:
            # 1. Tính toán các metrics
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)

            # Tính blur
            blur = cv2.Laplacian(gray, cv2.CV_64F).var()

            # Tính brightness
            brightness = np.mean(gray)

            # Tính kích thước
            h, w = face_roi.shape[:2]

            # 2. Kiểm tra điều kiện ánh sáng
            if brightness < self.brightness_min:
                reason = f"Image too dark (brightness: {brightness:.1f})"
                if self.global_logger:
                    self.global_logger.log_face_alert(
                        event_type="LIVENESS_FAILURE",
                        details=reason,
                        severity="INFO",
                        is_fraud=False,
                        similarity=similarity
                    )
                return False, reason

            if brightness > self.brightness_max:
                reason = f"Image too bright (brightness: {brightness:.1f})"
                if self.global_logger:
                    self.global_logger.log_face_alert(
                        event_type="LIVENESS_FAILURE",
                        details=reason,
                        severity="INFO",
                        is_fraud=False,
                        similarity=similarity
                    )
                return False, reason

            # 3. Kiểm tra blur
            if blur < self.blur_threshold:
                self.failure_count += 1
                if self.failure_count >= self.max_consecutive_failures:
                    if self.global_logger:
                        self.global_logger.log_face_alert(
                            event_type="LIVENESS_FAILURE",
                            details=f"Blurred face detected - Value: {blur:.1f}",
                            severity="WARNING",
                            is_fraud=True,
                            similarity=similarity
                        )
                    return False, "Blurred face"
                else:
                    return False, f"Slightly blurred (attempt {self.failure_count}/{self.max_consecutive_failures})"

            # 4. Reset failure count nếu pass blur check
            self.failure_count = 0

            # 5. Kiểm tra kích thước khuôn mặt
            if w < self.min_face_size or h < self.min_face_size:
                return False, "Face too small"

            # 6. Kiểm tra movement
            movement = None
            if self.prev_landmarks is not None:
                movement = np.mean(np.abs(landmarks - self.prev_landmarks))

            self.prev_landmarks = landmarks.copy()

            # 7. Log liveness success nếu có global_logger
            if self.global_logger and similarity > 0.5:
                self.global_logger.log_face_alert(
                    event_type="LIVENESS_SUCCESS",
                    details=f"Liveness check passed - Brightness: {brightness:.1f}, Blur: {blur:.1f}",
                    severity="INFO",
                    is_fraud=False,
                    similarity=similarity
                )

            return True, f"Live face (brightness: {brightness:.1f}, blur: {blur:.1f})"

        except Exception as e:
            print(f"❌ Liveness error: {e}")
            traceback.print_exc()
            return False, "Liveness error"

    def check_spoofing(
            self,
            frame: np.ndarray,
            bbox: list,
            similarity: float = 0.0
    ) -> Tuple[bool, str]:
        """Spoof check với global logging"""
        x1, y1, x2, y2 = bbox
        face_roi = frame[y1:y2, x1:x2]

        if face_roi.size == 0:
            return False, "Invalid ROI"

        try:
            # 1. Saturation check
            hsv = cv2.cvtColor(face_roi, cv2.COLOR_BGR2HSV)
            saturation = np.mean(hsv[:, :, 1])

            if saturation < self.saturation_threshold:
                # Kiểm tra brightness trước khi đánh dấu spoofing
                gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)

                # Nếu ảnh tối, saturation thấp là bình thường
                if brightness < 50:
                    return True, "Low saturation due to dark environment"

                if self.global_logger:
                    self.global_logger.log_face_alert(
                        event_type="SPOOFING_WARNING",
                        details=f"Low saturation detected - Value: {saturation:.1f}",
                        severity="INFO",
                        is_fraud=False,
                        similarity=similarity
                    )
                return False, "Possible printed photo"

            # 2. Contrast check
            gray = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            contrast = gray.std()

            if contrast < self.contrast_threshold:
                brightness = np.mean(gray)

                # Nếu ảnh tối, contrast thấp là bình thường
                if brightness < 50:
                    return True, "Low contrast due to dark environment"

                if self.global_logger:
                    self.global_logger.log_face_alert(
                        event_type="SPOOFING_WARNING",
                        details=f"Low contrast detected - Value: {contrast:.1f}",
                        severity="INFO",
                        is_fraud=False,
                        similarity=similarity
                    )
                return False, "Low contrast spoof"

            # 3. Brightness check
            brightness = np.mean(gray)
            if brightness < 30 or brightness > 220:
                return True, "Extreme lighting condition"

            # 4. Log spoofing check success nếu có global_logger
            if self.global_logger and similarity > 0.5:
                self.global_logger.log_face_alert(
                    event_type="SPOOFING_CHECK_PASSED",
                    details=f"Spoofing check passed - Saturation: {saturation:.1f}, Contrast: {contrast:.1f}",
                    severity="INFO",
                    is_fraud=False,
                    similarity=similarity
                )

            return True, f"No spoof detected (saturation: {saturation:.1f}, contrast: {contrast:.1f})"

        except Exception as e:
            print(f"❌ Spoof check error: {e}")
            return True, "Spoof check error"

    def _save_capture_image(self, frame, bbox, event_type):
        """Lưu ảnh capture vào thư mục tháng"""
        if not self.user_name or not self.user_name.strip():
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{event_type}_{self.user_name}_{timestamp}.jpg"
            filepath = os.path.join(self.CAPTURE_DIR, filename)

            # Vẽ bounding box
            img_copy = frame.copy()
            x1, y1, x2, y2 = bbox
            cv2.rectangle(img_copy, (x1, y1), (x2, y2), (0, 0, 255), 2)
            cv2.putText(img_copy, event_type, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            cv2.imwrite(filepath, img_copy)
            print(f"📸 Saved face capture: {filepath}")
            return filepath

        except Exception as e:
            print(f"❌ Error saving capture: {e}")
            return None

    def _log_fraud_event(self, event_type, similarity, reason):
        """Ghi log gian lận vào global logger"""
        if self.global_logger:
            self.global_logger.log_face_alert(
                event_type=event_type,
                details=reason,
                severity="CRITICAL",
                is_fraud=True,
                similarity=similarity
            )