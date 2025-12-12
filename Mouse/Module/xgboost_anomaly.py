"""
Module phát hiện bất thường bằng XGBoost
"""
import numpy as np
import pandas as pd
from typing import Dict, Tuple
import pickle
import os


class XGBoostAnomalyDetector:
    """Phát hiện bất thường bằng mô hình XGBoost"""

    def __init__(self, model_path=None):
        self.model = None
        self.scaler = None
        self.feature_columns = [
            'distance_ui',
            'x_axis_distance_ui',
            'y_axis_distance_ui',
            'movement_time_span_ui',
            'x_flips_ui',
            'y_flips_ui',
            'velocity_ui',
            'acceleration_ui',
            'max_deviation_ui'
        ]

        # Tải mô hình nếu có
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
        else:
            # Khởi tạo mô hình mặc định
            print("ℹ️ Sử dụng heuristic detection.")

    def detect_anomaly(self, metrics: Dict) -> Tuple[float, Dict]:
        """
        Phát hiện bất thường từ metrics

        Args:
            metrics: Dictionary chứa các metrics

        Returns:
            Tuple[float, Dict]: Điểm bất thường và features
        """
        # Chuẩn bị features
        features = self._prepare_features(metrics)

        # Nếu có mô hình XGBoost, dùng mô hình
        if self.model is not None:
            try:
                anomaly_score = self._predict_with_model(features)
            except Exception as e:
                print(f"⚠️ Lỗi khi dự đoán: {e}")
                # Dùng heuristic rules nếu lỗi
                anomaly_score = self._heuristic_detection(features, metrics)
        else:
            # Dùng heuristic rules nếu chưa có mô hình
            anomaly_score = self._heuristic_detection(features, metrics)

        # Tính feature importance (giả lập)
        feature_importance = self._calculate_feature_importance(features)

        return anomaly_score, feature_importance

    def _prepare_features(self, metrics: Dict) -> np.ndarray:
        """Chuẩn bị features cho mô hình"""
        features = []

        for col in self.feature_columns:
            value = metrics.get(col, 0)

            # Xử lý missing values
            if value is None or (isinstance(value, float) and np.isnan(value)):
                value = 0

            features.append(float(value))

        return np.array(features).reshape(1, -1)

    def _predict_with_model(self, features: np.ndarray) -> float:
        """Dự đoán bằng mô hình XGBoost"""
        # Scale features nếu có scaler
        if self.scaler:
            features = self.scaler.transform(features)

        # Dự đoán
        prediction = self.model.predict_proba(features)[0]

        # Trả về xác suất là anomaly (class 1)
        return float(prediction[1])

    def _heuristic_detection(self, features: np.ndarray, metrics: Dict) -> float:
        """Phát hiện bất thường bằng heuristic rules - ĐÃ SỬA LOGIC"""
        if len(features[0]) < len(self.feature_columns):
            return 0.0

        # Lấy các features
        distance = features[0][0]
        x_distance = features[0][1]
        y_distance = features[0][2]
        time_span = max(features[0][3], 0.1)  # Tránh chia cho 0
        x_flips = features[0][4]
        y_flips = features[0][5]
        velocity = features[0][6]
        acceleration = features[0][7]
        max_deviation = features[0][8]

        # Lấy duration từ metrics
        duration = metrics.get('duration_ui', time_span)
        if duration <= 0:
            duration = time_span

        # ========== ĐIỀU KIỆN TIÊN QUYẾT: CÓ DI CHUYỂN ĐÁNG KỂ ==========
        MIN_DISTANCE_FOR_ANALYSIS = 50  # px - Chỉ phân tích nếu di chuyển ít nhất 50px
        MIN_TIME_FOR_ANALYSIS = 2.0  # giây - Chỉ phân tích nếu thời gian đủ

        # Nếu di chuyển quá ít -> không phân tích bất thường (trừ inactivity)
        if distance < MIN_DISTANCE_FOR_ANALYSIS or time_span < MIN_TIME_FOR_ANALYSIS:
            # Chỉ kiểm tra inactivity nếu thời gian dài
            if duration > 30 and distance < 20:  # 30s mà di chuyển <20px
                return 0.3  # Inactivity score
            return 0.1  # Bình thường (di chuyển ít)

        # Tính các chỉ số bất thường
        anomaly_scores = []

        # 1. QUÃNG ĐƯỜNG QUÁ NGẮN SO VỚI THỜI GIAN (chỉ khi có di chuyển)
        distance_per_second = distance / time_span if time_span > 0 else 0
        if distance_per_second < 10 and distance > 100:  # Di chuyển nhiều (>100px) nhưng chậm
            anomaly_scores.append(0.3)

        # 2. QUÁ ÍT ĐỔI HƯỚNG (chỉ khi có di chuyển đáng kể)
        total_flips = x_flips + y_flips
        if distance > 150 and time_span > 8:  # Di chuyển nhiều (>150px) trong thời gian dài (>8s)
            flips_per_100px = total_flips / (distance / 100) if distance > 0 else 0
            if flips_per_100px < 0.5:  # Ít hơn 0.5 flip mỗi 100px
                anomaly_scores.append(0.5)
        elif time_span > 5 and total_flips == 0 and distance > 100:
            anomaly_scores.append(0.4)

        # 3. VẬN TỐC QUÁ ĐỀU (chỉ khi có di chuyển)
        if velocity > 20 and abs(acceleration) < 0.5:  # Di chuyển nhanh (>20px/s) nhưng gia tốc rất đều
            anomaly_scores.append(0.3)
        elif velocity > 50 and abs(acceleration) < 1:  # Rất nhanh (>50px/s) nhưng đều
            anomaly_scores.append(0.4)

        # 4. ĐỘ LỆCH QUÁ NHỎ SO VỚI ĐƯỜNG THẲNG (chỉ khi di chuyển xa)
        if distance > 200:  # Chỉ kiểm tra khi di chuyển xa
            deviation_ratio = max_deviation / distance if distance > 0 else 0
            if deviation_ratio < 0.03:  # Độ lệch <3% quãng đường
                anomaly_scores.append(0.6)  # Rất giống bot
            elif deviation_ratio < 0.05 and max_deviation < 15:
                anomaly_scores.append(0.4)

        # 5. THỜI GIAN DI CHUYỂN QUÁ NGẮN SO VỚI TỔNG THỜI GIAN
        activity_ratio = time_span / max(duration, 0.1)
        if activity_ratio < 0.3 and distance > 50:  # Chỉ hoạt động 30% thời gian nhưng có di chuyển
            anomaly_scores.append(0.4)

        # 6. VẬN TỐC KHÔNG TỰ NHIÊN
        if velocity > 1000:  # Quá nhanh (không thực tế)
            anomaly_scores.append(0.8)
        elif velocity > 500:  # Rất nhanh
            anomaly_scores.append(0.6)
        elif velocity < 2 and distance > 300:  # Quá chậm nhưng di chuyển dài
            anomaly_scores.append(0.3)

        # 7. SỰ CÂN BẰNG X/Y KHÔNG TỰ NHIÊN (chỉ khi di chuyển đáng kể)
        if distance > 100:
            x_ratio = x_distance / distance if distance > 0 else 0
            y_ratio = y_distance / distance if distance > 0 else 0

            # Kiểm tra nếu di chuyển chủ yếu theo một trục
            if x_ratio > 0.95 or y_ratio > 0.95:  # >95% theo một trục
                if total_flips < 2:  # Và ít đổi hướng
                    anomaly_scores.append(0.4)
            elif x_ratio < 0.05 or y_ratio < 0.05:  # <5% theo một trục
                if total_flips < 2:
                    anomaly_scores.append(0.3)

        # 8. PATTERN LẶP LẠI (giả lập - thực tế cần data nhiều hơn)
        if velocity > 0 and 0.8 < acceleration < 1.2:  # Gia tốc quá ổn định
            anomaly_scores.append(0.2)

        # ========== TÍNH ĐIỂM TỔNG HỢP ==========
        if anomaly_scores:
            # Trọng số khác nhau cho các loại bất thường
            weights = []
            for i, score in enumerate(anomaly_scores):
                if score > 0.6:  # Bất thường nghiêm trọng
                    weights.append(1.5)
                elif score > 0.4:  # Bất thường trung bình
                    weights.append(1.2)
                else:  # Bất thường nhẹ
                    weights.append(1.0)

            weighted_sum = sum(s * w for s, w in zip(anomaly_scores, weights))
            total_weight = sum(weights)
            anomaly_score = min(0.95, weighted_sum / total_weight)

            # Điều chỉnh dựa trên mức độ di chuyển
            if distance < 200:  # Di chuyển ít -> giảm điểm bất thường
                anomaly_score *= 0.7
            elif distance > 1000:  # Di chuyển nhiều -> tăng độ tin cậy
                anomaly_score = min(0.95, anomaly_score * 1.1)

        else:
            anomaly_score = 0.1  # Mặc định là bình thường

        # ========== ĐIỀU CHỈNH CUỐI ==========
        # Nếu di chuyển rất ít nhưng bị cảnh báo -> giảm điểm
        if distance < 80 and anomaly_score > 0.3:
            anomaly_score = 0.2  # Hạ xuống mức thấp

        # Nếu không có di chuyển thực sự
        if distance < 30:
            if duration > 60:  # 1 phút không di chuyển
                return 0.4  # Inactivity
            else:
                return max(0.05, anomaly_score * 0.5)  # Giảm đáng kể

        return max(0.05, min(0.95, anomaly_score))  # Đảm bảo trong khoảng 0.05-0.95
    def _calculate_feature_importance(self, features: np.ndarray) -> Dict:
        """Tính feature importance (giả lập)"""
        importance = {}

        for i, col in enumerate(self.feature_columns):
            if i < len(features[0]):
                value = features[0][i]

                # Tính importance dựa trên độ lệch so với trung bình
                # Giả lập các giá trị trung bình mẫu
                avg_values = {
                    'distance_ui': 500,
                    'x_axis_distance_ui': 250,
                    'y_axis_distance_ui': 250,
                    'movement_time_span_ui': 15,
                    'x_flips_ui': 5,
                    'y_flips_ui': 5,
                    'velocity_ui': 50,
                    'acceleration_ui': 20,
                    'max_deviation_ui': 20
                }

                avg = avg_values.get(col, 0)
                if avg > 0:
                    deviation = abs(value - avg) / avg
                    importance[col] = min(1.0, deviation)
                else:
                    importance[col] = 0.0

        # Sắp xếp theo importance
        sorted_importance = dict(sorted(
            importance.items(),
            key=lambda x: x[1],
            reverse=True
        ))

        return sorted_importance

    def train_model(self, training_data: pd.DataFrame, labels: pd.Series):
        """Train mô hình XGBoost"""
        try:
            import xgboost as xgb
            from sklearn.model_selection import train_test_split
            from sklearn.preprocessing import StandardScaler
            from sklearn.metrics import classification_report

            # Chuẩn bị dữ liệu
            X = training_data[self.feature_columns]
            y = labels

            # Scale features
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X_scaled, y, test_size=0.2, random_state=42
            )

            # Train XGBoost
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=5,
                learning_rate=0.1,
                random_state=42
            )

            self.model.fit(X_train, y_train)

            # Đánh giá
            y_pred = self.model.predict(X_test)
            print("✅ Đã train XGBoost model:")
            print(classification_report(y_test, y_pred))

            # Lưu mô hình
            self.save_model("mouse_anomaly_model.pkl")

            return True

        except ImportError:
            print("⚠️ Chưa cài đặt xgboost. Chạy: pip install xgboost")
            return False
        except Exception as e:
            print(f"❌ Lỗi khi train model: {e}")
            return False

    def save_model(self, filepath: str):
        """Lưu mô hình"""
        try:
            with open(filepath, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler,
                    'feature_columns': self.feature_columns
                }, f)
            print(f"✅ Đã lưu model: {filepath}")
        except Exception as e:
            print(f"❌ Lỗi lưu model: {e}")

    def load_model(self, filepath: str):
        """Tải mô hình"""
        try:
            with open(filepath, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
                self.feature_columns = data.get('feature_columns', self.feature_columns)
            print(f"✅ Đã tải model: {filepath}")
        except Exception as e:
            print(f"❌ Lỗi tải model: {e}")

    def update_with_real_time_data(self, metrics_stream: list):
        """
        Cập nhật mô hình với dữ liệu real-time

        Args:
            metrics_stream: List các metrics dictionary theo thời gian
        """
        if len(metrics_stream) < 100:
            print("ℹ️ Cần ít nhất 100 samples để update model")
            return

        # Chuyển đổi sang DataFrame
        df = pd.DataFrame(metrics_stream)

        # Tạo labels tự động dựa trên heuristic
        # Giả sử 5% samples đầu là bất thường để demo
        labels = np.zeros(len(df))
        anomaly_indices = np.random.choice(
            len(df),
            size=int(0.05 * len(df)),
            replace=False
        )
        labels[anomaly_indices] = 1

        # Train model
        self.train_model(df, pd.Series(labels))