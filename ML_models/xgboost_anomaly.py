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
from typing import Dict

from sklearn.linear_model import LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.feature_selection import SelectFromModel
import xgboost as xgb


class BehaviorModel:
    MODEL_PATH = "user_behavior_xgb_lasso.pkl"

    ALL_FEATURES = [
        'Velocity', 'Acceleration',
        'XFlips', 'YFlips',
        'TotalDistance', 'MovementTimeSpan',
        'XVelocity', 'YVelocity',
        'XAxisDistance', 'YAxisDistance'
    ]

    MIN_TRAIN_SAMPLES = 20

    def __init__(self):
        self.xgb_model = None
        self.scaler = None
        self.selected_features = None
        self.history_df = None  # Lưu data cũ
        self.load_model()

    # =========================
    # TRAINING
    # =========================
    def train(self, df_normal: pd.DataFrame) -> bool:
        """
        Retrain model from historical + new data
        """
        try:
            print("\n🧠 Training Behavior Model (Lasso + XGBoost)")

            # --- 1. PREPARE DATA ---
            df = self._prepare_dataframe(df_normal)
            if df is None or len(df) < self.MIN_TRAIN_SAMPLES:
                print("⚠️ Not enough data to train.")
                return False

            # Merge with history if exists
            if self.history_df is not None:
                df = pd.concat([self.history_df, df], ignore_index=True)

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

            self.save_model()
            print("🎉 Model trained & saved successfully.")
            return True

        except Exception as e:
            print(f"❌ Training error: {e}")
            import traceback
            traceback.print_exc()
            return False

    # =========================
    # PREDICTION
    # =========================
    def predict(self, metrics: Dict) -> float:
        if not self.xgb_model or not self.selected_features:
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

            # Debug: kiểm tra features
            print(f"[DEBUG] Selected features: {self.selected_features}")
            print(f"[DEBUG] Input dataframe columns: {df.columns.tolist()}")

            # Đảm bảo có đủ cột
            missing_cols = set(self.selected_features) - set(df.columns)
            if missing_cols:
                print(f"[WARNING] Missing columns: {missing_cols}")
                for col in missing_cols:
                    df[col] = 0

            df = df[self.selected_features]
            prob = self.xgb_model.predict_proba(df)[0][1]
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
    def save_model(self):
        with open(self.MODEL_PATH, "wb") as f:
            pickle.dump({
                "xgb_model": self.xgb_model,
                "selected_features": self.selected_features,
                "history_df": self.history_df
            }, f)

    def load_model(self):
        if not os.path.exists(self.MODEL_PATH):
            print("ℹ️ No existing model found.")
            return

        try:
            with open(self.MODEL_PATH, "rb") as f:
                data = pickle.load(f)
                self.xgb_model = data.get("xgb_model")
                self.selected_features = data.get("selected_features")
                self.history_df = data.get("history_df")
            print(f"ℹ️ Model loaded ({len(self.selected_features)} features)")
        except Exception as e:
            print(f"⚠️ Failed to load model: {e}")