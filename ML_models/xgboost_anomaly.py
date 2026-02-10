"""
Behavior Anomaly Detection Model
Lasso (Feature Selection) + XGBoost (Binary Classification)

- Learn from historical Excel data
- Retrain safely when new data appears
- Stable, production-friendly
"""

import os
import pickle
import numpy as np
import pandas as pd
import tempfile
import shutil
from typing import Dict, Optional

from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectFromModel
import xgboost as xgb


class BehaviorModel:
    MODEL_PATH = r"C:\Users\legal\PycharmProjects\PythonProject\MainApp\user_behavior_xgb_lasso.pkl"

    ALL_FEATURES = [
        'Velocity', 'Acceleration',
        'XFlips', 'YFlips',
        'TotalDistance', 'MovementTimeSpan',
        'XVelocity', 'YVelocity',
        'XAxisDistance', 'YAxisDistance'
    ]

    MIN_TRAIN_SAMPLES = 20
    RETRAIN_THRESHOLD = 50  # Retrain khi có đủ 50 samples mới

    def __init__(self):
        self.xgb_model = None
        self.scaler = StandardScaler()
        self.selected_features = None
        self.history_df = None
        self.new_data_buffer = []  # Buffer lưu data mới chưa retrain
        self._safe_load_model()

    # =========================
    # TRAINING & RETRAINING
    # =========================
    def add_new_data(self, metrics: Dict) -> bool:
        """
        Thêm data mới vào buffer, tự động retrain khi đủ
        """
        try:
            # Chuyển metrics thành DataFrame row
            df_row = self._metrics_to_dataframe(metrics)
            if df_row is None:
                return False

            # Thêm vào buffer
            self.new_data_buffer.append(df_row)

            print(f"📥 New data added to buffer ({len(self.new_data_buffer)}/{self.RETRAIN_THRESHOLD})")

            # Kiểm tra nếu đủ để retrain
            if len(self.new_data_buffer) >= self.RETRAIN_THRESHOLD:
                return self._retrain_with_buffer()

            return True

        except Exception as e:
            print(f"❌ Error adding new data: {e}")
            return False

    def _retrain_with_buffer(self) -> bool:
        """
        Retrain model với data trong buffer
        """
        if not self.new_data_buffer:
            print("⚠️ No new data to retrain")
            return False

        try:
            print(f"\n🔄 RETRAINING with {len(self.new_data_buffer)} new samples...")

            # Chuyển buffer thành DataFrame
            df_new = pd.DataFrame(self.new_data_buffer)

            # Kiểm tra columns
            missing_cols = set(self.ALL_FEATURES) - set(df_new.columns)
            for col in missing_cols:
                df_new[col] = 0

            df_new = df_new[self.ALL_FEATURES]

            # Kết hợp với history data nếu có
            if self.history_df is not None:
                df_combined = pd.concat([self.history_df, df_new], ignore_index=True)
                print(f"📊 Retraining: {len(self.history_df)} old + {len(df_new)} new = {len(df_combined)} total")
            else:
                df_combined = df_new
                print(f"📊 Training with {len(df_new)} new samples")

            # Train model
            success = self._train_internal(df_combined)

            if success:
                # Xóa buffer sau khi retrain thành công
                self.new_data_buffer = []
                print(f"✅ Model retrained successfully! Total samples: {len(df_combined)}")
                return True
            else:
                print("❌ Retraining failed, keeping buffer")
                return False

        except Exception as e:
            print(f"❌ Retraining error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def train(self, df_normal: pd.DataFrame) -> bool:
        """
        Train model từ đầu hoặc retrain
        """
        return self._train_internal(df_normal)

    def _train_internal(self, df: pd.DataFrame) -> bool:
        """
        Internal training logic
        """
        try:
            print(f"\n🧠 Training Behavior Model (Lasso + XGBoost)")
            print(f"📊 Data shape: {df.shape}")

            # --- 1. PREPARE DATA ---
            df = self._prepare_dataframe(df)
            if df is None or len(df) < self.MIN_TRAIN_SAMPLES:
                print(
                    f"⚠️ Not enough data to train. Need {self.MIN_TRAIN_SAMPLES}, got {len(df) if df is not None else 0}")
                return False

            # Cập nhật history data
            self.history_df = df.copy()

            X_normal = df[self.ALL_FEATURES]
            y_normal = np.zeros(len(X_normal))

            # --- 2. SYNTHETIC ANOMALY (CONTROLLED) ---
            X_anomaly = self._generate_anomaly(X_normal)
            y_anomaly = np.ones(len(X_anomaly))

            X = pd.concat([X_normal, X_anomaly], ignore_index=True)
            y = np.concatenate([y_normal, y_anomaly])

            # --- 3. SCALING (FOR LASSO ONLY) ---
            self.scaler = StandardScaler()
            X_scaled = self.scaler.fit_transform(X)

            # --- 4. LASSO FEATURE SELECTION ---
            lasso = LassoCV(cv=5, random_state=42).fit(X_scaled, y)
            selector = SelectFromModel(lasso, prefit=True)
            mask = selector.get_support()

            self.selected_features = list(np.array(self.ALL_FEATURES)[mask])

            if not self.selected_features:
                print("❌ Lasso selected no features.")
                return False

            print(f"✅ Selected features: {self.selected_features}")

            # --- 5. TRAIN XGBOOST (NO SCALING) ---
            X_selected = X[self.selected_features]

            self.xgb_model = xgb.XGBClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.9,
                colsample_bytree=0.9,
                eval_metric='logloss',
                random_state=42
            )

            self.xgb_model.fit(X_selected, y)

            # Verify model after training
            if self.xgb_model is None or not hasattr(self.xgb_model, 'predict_proba'):
                print("❌ Model training failed - invalid model created")
                return False

            self._safe_save_model()
            print("🎉 Model trained & saved successfully.")
            return True

        except Exception as e:
            print(f"❌ Training error: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _metrics_to_dataframe(self, metrics: Dict) -> Optional[pd.DataFrame]:
        """
        Chuyển metrics từ UI sang DataFrame row
        """
        try:
            input_map = {
                'Velocity': metrics.get('velocity_ui', 0),
                'Acceleration': metrics.get('acceleration_ui', 0),
                'XFlips': metrics.get('x_flips_ui', 0),
                'YFlips': metrics.get('y_flips_ui', 0),
                'TotalDistance': metrics.get('distance_ui', 0),
                'MovementTimeSpan': metrics.get('movement_time_span_ui', 0),
                'XVelocity': metrics.get('x_axis_velocity_ui', 0),
                'YVelocity': metrics.get('y_axis_velocity_ui', 0),
                'XAxisDistance': metrics.get('x_axis_distance_ui', 0),
                'YAxisDistance': metrics.get('y_axis_distance_ui', 0)
            }

            return pd.DataFrame([input_map])

        except Exception as e:
            print(f"❌ Error converting metrics: {e}")
            return None

    # =========================
    # PREDICTION
    # =========================
    def predict(self, metrics: Dict) -> float:
        # Kiểm tra model có hợp lệ không
        if (self.xgb_model is None or
                not hasattr(self.xgb_model, 'predict_proba') or
                self.selected_features is None or
                len(self.selected_features) == 0):
            print("⚠️ Model not ready, returning default score 0.0")
            return 0.0

        try:
            # Map từ metrics UI sang tên features
            input_map = {
                'Velocity': metrics.get('velocity_ui', 0),
                'Acceleration': metrics.get('acceleration_ui', 0),
                'XFlips': metrics.get('x_flips_ui', 0),
                'YFlips': metrics.get('y_flips_ui', 0),
                'TotalDistance': metrics.get('distance_ui', 0),
                'MovementTimeSpan': metrics.get('movement_time_span_ui', 0),
                'XVelocity': metrics.get('x_axis_velocity_ui', 0),
                'YVelocity': metrics.get('y_axis_velocity_ui', 0),
                'XAxisDistance': metrics.get('x_axis_distance_ui', 0),
                'YAxisDistance': metrics.get('y_axis_distance_ui', 0)
            }

            df = pd.DataFrame([input_map])

            # Đảm bảo có đủ cột
            missing_cols = set(self.selected_features) - set(df.columns)
            if missing_cols:
                print(f"[WARNING] Missing columns: {missing_cols}")
                for col in missing_cols:
                    df[col] = 0

            df = df[self.selected_features]
            prob = self.xgb_model.predict_proba(df)[0][1]

            # TỰ ĐỘNG THÊM DATA VÀO BUFFER
            self.add_new_data(metrics)

            return float(prob)

        except Exception as e:
            print(f"⚠️ Prediction error: {e}")
            import traceback
            traceback.print_exc()
            return 0.0

    # =========================
    # INTERNAL HELPERS
    # =========================
    def _prepare_dataframe(self, df: pd.DataFrame):
        cols = [c for c in self.ALL_FEATURES if c in df.columns]
        if len(cols) < 5:
            print(f"⚠️ Missing columns. Found: {cols}")
            return None

        df = df[cols].fillna(0)
        df = df[df['TotalDistance'] > 10]  # remove idle sessions
        return df

    def _generate_anomaly(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Controlled anomaly:
        - Scale extremes instead of pure noise
        """
        X_anom = X.copy()
        for col in X.columns:
            factor = np.random.uniform(1.5, 3.0, size=len(X))
            X_anom[col] = X[col] * factor
        return X_anom

    # =========================
    # SAVE / LOAD
    # =========================
    def _safe_save_model(self):
        """Lưu model một cách an toàn"""
        try:
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(self.MODEL_PATH) if os.path.dirname(self.MODEL_PATH) else '.')
            os.close(temp_fd)

            with open(temp_path, "wb") as f:
                pickle.dump({
                    "xgb_model": self.xgb_model,
                    "selected_features": self.selected_features,
                    "history_df": self.history_df,
                    "scaler": self.scaler,
                    "new_data_buffer": self.new_data_buffer  # Lưu cả buffer
                }, f, protocol=pickle.HIGHEST_PROTOCOL)

            shutil.move(temp_path, self.MODEL_PATH)
            print(f"✅ Model saved to {self.MODEL_PATH}")

        except Exception as e:
            print(f"❌ Error saving model: {e}")
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)

    def _safe_load_model(self):
        """Load model một cách an toàn"""
        if not os.path.exists(self.MODEL_PATH):
            print("ℹ️ No existing model found.")
            return

        try:
            file_size = os.path.getsize(self.MODEL_PATH)
            if file_size == 0:
                print("⚠️ Model file is empty, removing...")
                os.remove(self.MODEL_PATH)
                return

            with open(self.MODEL_PATH, "rb") as f:
                data = pickle.load(f)

            self.xgb_model = data.get("xgb_model")
            self.selected_features = data.get("selected_features")
            self.history_df = data.get("history_df")
            self.scaler = data.get("scaler", StandardScaler())
            self.new_data_buffer = data.get("new_data_buffer", [])  # Load buffer

            # Kiểm tra model đã load có hợp lệ không
            if (self.xgb_model is not None and
                    hasattr(self.xgb_model, 'predict_proba') and
                    self.selected_features is not None and
                    len(self.selected_features) > 0):
                print(f"✅ Model loaded successfully ({len(self.selected_features)} features)")
                print(f"✅ History samples: {len(self.history_df) if self.history_df is not None else 0}")
                print(f"✅ Buffer samples: {len(self.new_data_buffer)}")
            else:
                print("⚠️ Model file is invalid, resetting...")
                self._reset_model()
                os.remove(self.MODEL_PATH)

        except (EOFError, pickle.UnpicklingError, KeyError, AttributeError) as e:
            print(f"⚠️ Failed to load model due to corrupt file: {e}")
            os.remove(self.MODEL_PATH)
            self._reset_model()
        except Exception as e:
            print(f"⚠️ Unexpected error loading model: {e}")
            self._reset_model()

    def _reset_model(self):
        """Reset model về trạng thái mới"""
        self.xgb_model = None
        self.scaler = StandardScaler()
        self.selected_features = None
        self.history_df = None
        self.new_data_buffer = []

    # =========================
    # DEBUG & INFO
    # =========================
    def get_model_info(self) -> Dict:
        """Lấy thông tin model"""
        return {
            'model_loaded': self.xgb_model is not None,
            'features_count': len(self.selected_features) if self.selected_features else 0,
            'history_samples': len(self.history_df) if self.history_df is not None else 0,
            'buffer_samples': len(self.new_data_buffer),
            'buffer_percentage': f"{len(self.new_data_buffer) * 100 / self.RETRAIN_THRESHOLD:.1f}%",
            'selected_features': self.selected_features
        }