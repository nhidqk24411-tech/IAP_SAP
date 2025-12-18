import pandas as pd
import os
import glob
from typing import List, Optional
from Mouse.Models.MouseResult import MouseResult


class MouseExcelHandler:
    """Xử lý Excel: Ghi báo cáo và Đọc dữ liệu huấn luyện"""

    SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Saved_file")

    @staticmethod
    def load_training_data() -> Optional[pd.DataFrame]:
        """
        Đọc TẤT CẢ file Excel trong thư mục Saved_file để làm dữ liệu huấn luyện.
        Tìm sheet chứa dữ liệu training (All_Sessions, Metrics_Detail, hoặc sheet đầu tiên).
        """
        if not os.path.exists(MouseExcelHandler.SAVE_DIR):
            print(f"⚠️ Directory not found: {MouseExcelHandler.SAVE_DIR}")
            print(f"📁 Creating directory: {MouseExcelHandler.SAVE_DIR}")
            os.makedirs(MouseExcelHandler.SAVE_DIR, exist_ok=True)
            return None

        # Lấy tất cả file .xlsx
        all_files = glob.glob(os.path.join(MouseExcelHandler.SAVE_DIR, "*.xlsx"))
        if not all_files:
            print("⚠️ No Excel files found for training.")
            return None

        print(f"📚 Found {len(all_files)} Excel files. Loading...")

        df_list = []
        ALL_FEATURES = [
            'Velocity', 'Acceleration',
            'XFlips', 'YFlips',
            'TotalDistance', 'MovementTimeSpan',
            'XVelocity', 'YVelocity',
            'XAxisDistance', 'YAxisDistance'
        ]

        for file in all_files:
            try:
                # Đọc tất cả sheet trong file
                xls = pd.ExcelFile(file)
                for sheet_name in xls.sheet_names:
                    try:
                        df = pd.read_excel(file, sheet_name=sheet_name)
                        # Kiểm tra xem có chứa ít nhất một cột trong ALL_FEATURES không
                        if any(col in df.columns for col in ALL_FEATURES):
                            print(f"   - Sheet '{sheet_name}' in file {os.path.basename(file)} contains training data.")
                            df_list.append(df)
                            break  # Chỉ lấy một sheet từ mỗi file
                    except Exception as e:
                        print(f"   - Error reading sheet '{sheet_name}' in {os.path.basename(file)}: {e}")
            except Exception as e:
                print(f" - Error reading file {os.path.basename(file)}: {e}")

        if not df_list:
            print("⚠️ No training data found in any sheet.")
            return None

        final_df = pd.concat(df_list, ignore_index=True)
        print(f"✅ Loaded {len(final_df)} rows of historical data.")
        print(f"📊 Columns in data: {final_df.columns.tolist()}")
        return final_df

    @staticmethod
    def export_multiple_sessions(sessions: List[MouseResult], filename_prefix="mouse_analysis"):
        # Tạo thư mục nếu chưa tồn tại
        os.makedirs(MouseExcelHandler.SAVE_DIR, exist_ok=True)

        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(MouseExcelHandler.SAVE_DIR, f"{filename_prefix}_{timestamp}.xlsx")

        try:
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Sheet 1: Data raw metrics
                data = [s.to_dict() for s in sessions]
                pd.DataFrame(data).to_excel(writer, sheet_name='All_Sessions', index=False)

                # Sheet 2: Alerts (nếu có)
                alerts = []
                for s in sessions:
                    for a in s.alerts:
                        alerts.append({'Session': s.session_id, **a})
                if alerts:
                    pd.DataFrame(alerts).to_excel(writer, sheet_name='Alerts', index=False)

            print(f"💾 File saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Error saving file: {e}")
            import traceback
            traceback.print_exc()
            return None