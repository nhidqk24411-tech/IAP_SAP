"""
face_verification.py
Xác thực khuôn mặt từ webcam với kiểm tra tính "sống" (liveness detection).
"""
import cv2
import numpy as np
import time
from datetime import datetime
import json
from typing import Tuple, Optional


class FaceVerification:
    def __init__(self, detection_model):
        """
        Khởi tạo hệ thống xác thực khuôn mặt.

        Args:
            detection_model: Model phát hiện khuôn mặt từ insightface
        """
        self.detection_model = detection_model

        # Các tham số cho liveness detection
        self.blur_threshold = 100  # Ngưỡng phát hiện blur
        self.face_movement_threshold = 5  # Ngưỡng phát hiện chuyển động
        self.prev_landmarks = None

        # Anti-spoofing parameters
        self.min_face_size = 100  # Kích thước khuôn mặt tối thiểu (pixel)

    def check_liveness_basic(self, frame: np.ndarray, landmarks: np.ndarray) -> Tuple[bool, str]:
        """
        Kiểm tra cơ bản để phát hiện ảnh sống từ webcam.

        Args:
            frame: Ảnh BGR từ webcam
            landmarks: Điểm mốc khuôn mặt

        Returns:
            Tuple (is_live, reason)
        """
        # 1. Kiểm tra độ blur (ảnh chụp màn hình thường rõ hơn ảnh webcam)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur_value = cv2.Laplacian(gray, cv2.CV_64F).var()

        if blur_value < self.blur_threshold:
            return False, f"Image too blurry (value: {blur_value:.1f})"

        # 2. Kiểm tra kích thước khuôn mặt
        face_width = np.max(landmarks[:, 0]) - np.min(landmarks[:, 0])
        face_height = np.max(landmarks[:, 1]) - np.min(landmarks[:, 1])

        if face_width < self.min_face_size or face_height < self.min_face_size:
            return False, f"Face too small (size: {face_width}x{face_height})"

        # 3. Kiểm tra sự chuyển động của khuôn mặt
        if self.prev_landmarks is not None:
            movement = np.mean(np.abs(landmarks - self.prev_landmarks))
            if movement < self.face_movement_threshold:
                return False, f"Face seems static (movement: {movement:.2f})"

        self.prev_landmarks = landmarks.copy()

        # 4. Kiểm tra màu sắc và độ tương phản (ảnh in thường có màu sắc khác)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])

        if saturation < 30:  # Ảnh xám hoặc ảnh in
            return False, f"Low color saturation ({saturation:.1f})"

        return True, "Live face detected"

    def check_screen_recording(self, frame: np.ndarray) -> bool:
        """
        Phát hiện ảnh chụp màn hình dựa trên các đặc điểm.

        Args:
            frame: Ảnh từ webcam

        Returns:
            True nếu có dấu hiệu là ảnh chụp màn hình
        """
        # Kiểm tra tỷ lệ khung hình (webcam thường có tỷ lệ 4:3 hoặc 16:9)
        h, w = frame.shape[:2]
        aspect_ratio = w / h

        # Webcam thông thường có tỷ lệ ~1.33 (4:3) hoặc 1.77 (16:9)
        if not (1.2 < aspect_ratio < 1.9):
            return True  # Có thể là ảnh chụp từ màn hình khác

        # Kiểm tra độ phân giải (webcam thường có độ phân giải thấp hơn)
        if w > 1920 or h > 1080:  # Webcam thường không vượt quá Full HD
            return True

        return False

    def detect_frame_around_face(self, frame: np.ndarray, bbox: list) -> bool:
        """
        Phát hiện khung ảnh xung quanh khuôn mặt (nếu có).
        Trả về True nếu phát hiện khung ảnh.
        """
        x1, y1, x2, y2 = bbox
        # Mở rộng vùng xung quanh bounding box
        margin_x = int((x2 - x1) * 0.5)
        margin_y = int((y2 - y1) * 0.5)
        x1 = max(0, x1 - margin_x)
        y1 = max(0, y1 - margin_y)
        x2 = min(frame.shape[1], x2 + margin_x)
        y2 = min(frame.shape[0], y2 + margin_y)

        roi = frame[y1:y2, x1:x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        # Tìm contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            # Tìm contour lớn nhất
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            # Nếu diện tích contour lớn hơn 1/4 diện tích ROI, có khả năng có khung
            if area > (roi.shape[0] * roi.shape[1]) / 4:
                # Kiểm tra tỷ lệ cạnh của contour (nếu gần hình chữ nhật)
                x, y, w, h = cv2.boundingRect(largest_contour)
                aspect_ratio = w / h
                if 0.7 < aspect_ratio < 1.3:  # Gần hình vuông
                    return True
        return False

    def check_spoofing(self, frame: np.ndarray, bbox: list) -> Tuple[bool, str]:
        """
        Kiểm tra xem ảnh có phải là ảnh chụp (spoofing) hay không.
        Kết hợp nhiều phương pháp: khung ảnh, màu sắc, độ tương phản, v.v.
        """
        # 1. Kiểm tra khung ảnh
        if self.detect_frame_around_face(frame, bbox):
            return False, "Frame around face detected (possible photo)"

        # 2. Kiểm tra histogram màu sắc (ảnh chụp màn hình có thể có histogram khác)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        if np.mean(saturation) < 20:
            return False, "Low saturation (possible printed photo)"

        # 3. Kiểm tra độ tương phản
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        contrast = gray.std()
        if contrast < 30:
            return False, f"Low contrast ({contrast:.1f})"

        # 4. Kiểm tra độ sáng
        brightness = np.mean(gray)
        if brightness < 30 or brightness > 220:
            return False, f"Brightness out of range ({brightness:.1f})"

        return True, "No spoofing detected"

    def check_pose_and_lighting(self, landmarks: np.ndarray, frame: np.ndarray) -> Tuple[bool, str]:
        """
        Kiểm tra góc quay khuôn mặt và điều kiện ánh sáng.
        """
        # 1. Kiểm tra góc quay khuôn mặt dựa trên vị trí mắt và mũi
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        nose = landmarks[2]

        # Tính góc nghiêng
        dX = right_eye[0] - left_eye[0]
        dY = right_eye[1] - left_eye[1]
        angle = np.degrees(np.arctan2(dY, dX))
        if abs(angle) > 15:
            return False, f"Head tilted too much ({angle:.1f} degrees)"

        # Kiểm tra xem khuôn mặt có quay quá nhiều không (dựa trên tỷ lệ giữa khoảng cách mắt và vị trí mũi)
        # Đơn giản: kiểm tra xem mũi có nằm giữa hai mắt không
        if not (left_eye[0] < nose[0] < right_eye[0]):
            return False, "Face not facing forward"

        # 2. Kiểm tra ánh sáng: độ sáng và độ tương phản đã kiểm tra ở hàm spoofing, nhưng có thể kiểm tra thêm
        # Kiểm tra ánh sáng không đều (shadow) bằng cách chia vùng mặt
        # Lấy vùng mặt từ landmarks
        x_coords = landmarks[:, 0]
        y_coords = landmarks[:, 1]
        x1, x2 = int(np.min(x_coords)), int(np.max(x_coords))
        y1, y2 = int(np.min(y_coords)), int(np.max(y_coords))
        face_region = frame[y1:y2, x1:x2]
        if face_region.size == 0:
            return False, "Face region is empty"

        gray_face = cv2.cvtColor(face_region, cv2.COLOR_BGR2GRAY)
        # Tính độ lệch chuẩn của độ sáng trong vùng mặt
        brightness_std = gray_face.std()
        if brightness_std < 10:
            return False, "Lighting too flat (possible diffuse light from screen)"

        return True, "Good pose and lighting"

    def capture_from_webcam(self, camera_id: int = 0, timeout: int = 30) -> Optional[np.ndarray]:
        """
        Chụp ảnh trực tiếp từ webcam với kiểm tra an ninh.

        Args:
            camera_id: ID của webcam
            timeout: Thời gian tối đa chờ (giây)

        Returns:
            Ảnh BGR nếu thành công, None nếu thất bại
        """
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            print("Cannot open webcam!")
            return None

        print("\n" + "=" * 50)
        print("FACE VERIFICATION MODE")
        print("Requirements:")
        print("1. Face must be clearly visible")
        print("2. Good lighting conditions")
        print("3. No screen recording/photos allowed")
        print("=" * 50)
        print("\nPress SPACE to capture, ESC to cancel")

        start_time = time.time()
        last_liveness_check = time.time()
        liveness_checks_passed = 0
        required_checks = 3  # Cần 3 lần kiểm tra liveness thành công

        while True:
            # Kiểm tra timeout
            if time.time() - start_time > timeout:
                print("Timeout! Please try again.")
                break

            ret, frame = cap.read()
            if not ret:
                print("Failed to read from webcam")
                break

            # Hiển thị hướng dẫn
            display_frame = frame.copy()
            cv2.putText(display_frame, "Press SPACE to capture", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.putText(display_frame, f"Time: {int(timeout - (time.time() - start_time))}s",
                        (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(display_frame, f"Liveness checks: {liveness_checks_passed}/{required_checks}",
                        (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

            # Kiểm tra liveness định kỳ
            if time.time() - last_liveness_check > 0.5:  # Kiểm tra mỗi 0.5 giây
                img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = self.detection_model.get(img_rgb)

                if len(faces) > 0:
                    face = faces[0]
                    landmarks = face.kps
                    bbox = face.bbox.astype(int)

                    # Kiểm tra screen recording
                    if self.check_screen_recording(frame):
                        cv2.putText(display_frame, "WARNING: Screen recording detected!",
                                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    # Kiểm tra spoofing (ảnh chụp)
                    is_real, spoof_reason = self.check_spoofing(frame, bbox.tolist())
                    if not is_real:
                        cv2.putText(display_frame, f"SPOOF: {spoof_reason}",
                                    (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    # Kiểm tra góc độ và ánh sáng
                    pose_ok, pose_reason = self.check_pose_and_lighting(landmarks, frame)
                    if not pose_ok:
                        cv2.putText(display_frame, f"POSE: {pose_reason}",
                                    (10, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

                    # Kiểm tra liveness
                    is_live, reason = self.check_liveness_basic(frame, landmarks)

                    if is_live and is_real and pose_ok:
                        liveness_checks_passed += 1
                        color = (0, 255, 0)
                    else:
                        color = (0, 0, 255)

                    cv2.putText(display_frame, f"Status: {reason}",
                                (10, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

                    # Vẽ bounding box và landmarks
                    cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), color, 2)

                    # Vẽ landmarks
                    for (x, y) in landmarks.astype(int):
                        cv2.circle(display_frame, (x, y), 2, (0, 255, 255), -1)

                last_liveness_check = time.time()

            # Hiển thị frame
            cv2.imshow('Face Verification - Webcam Only', display_frame)

            # Xử lý phím
            key = cv2.waitKey(1) & 0xFF

            if key == 27:  # ESC
                print("Cancelled by user")
                break

            if key == 32:  # SPACE
                if liveness_checks_passed >= required_checks:
                    print(f"Liveness checks passed: {liveness_checks_passed}/{required_checks}")
                    cap.release()
                    cv2.destroyAllWindows()
                    return frame
                else:
                    print(f"Need {required_checks} liveness checks, currently: {liveness_checks_passed}")

        cap.release()
        cv2.destroyAllWindows()
        return None

    def extract_face_features(self, frame: np.ndarray) -> Optional[dict]:
        """
        Trích xuất đặc trưng khuôn mặt từ ảnh webcam.

        Args:
            frame: Ảnh BGR từ webcam

        Returns:
            Dictionary chứa thông tin khuôn mặt hoặc None
        """
        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        faces = self.detection_model.get(img_rgb)

        if len(faces) == 0:
            return None

        # Lấy khuôn mặt đầu tiên (giả sử chỉ có 1 người trước webcam)
        face = faces[0]

        features = {
            'bbox': face.bbox.astype(int).tolist(),
            'landmarks': face.kps.tolist(),
            'embedding': face.embedding.tolist(),
            'det_score': float(face.det_score),
            'timestamp': datetime.now().isoformat(),
            'image_shape': frame.shape
        }

        return features
