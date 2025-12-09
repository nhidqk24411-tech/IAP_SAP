"""
Đọc/ghi file Excel theo style bạn đã đưa
Tương tự XuLyDocGhiFile.py
"""

import pandas as pd
from typing import List, Dict, Any
from models.MouseResult import MouseResult
import os


class MouseExcelHandler:
    """Xử lý Excel cho dữ liệu chuột"""

    @staticmethod
    def read_results_from_excel(file_path: str, sheet_name: str = "MouseResults"):
        """
        Đọc kết quả từ Excel
        Tương tự XuLyDocGhiFile.readData()
        """
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            results = []

            for _, row in df.iterrows():
                # Tạo MouseResult từ dòng Excel
                # (Cần thêm logic parse phù hợp với cấu trúc Excel của bạn)
                pass

            return results
        except Exception as e:
            print(f"Lỗi đọc Excel: {e}")
            return []

    @staticmethod
    def write_results_to_excel(file_path: str, sheet_name: str, results: List[MouseResult]):
        """
        Ghi kết quả vào Excel
        Tương tự XuLyDocGhiFile.writeDate()
        """
        try:
            # Chuyển danh sách MouseResult thành list dict
            data = []
            for result in results:
                data.append(result.to_dict())

            df = pd.DataFrame(data)

            # Kiểm tra file tồn tại
            if os.path.exists(file_path):
                # Append vào file có sẵn
                with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
                    # Tìm dòng cuối cùng
                    if sheet_name in writer.sheets:
                        startrow = writer.sheets[sheet_name].max_row
                    else:
                        startrow = 0
                        print(f"⚠️ Sheet '{sheet_name}' không tồn tại, tạo mới")

                    df.to_excel(
                        writer,
                        sheet_name=sheet_name,
                        index=False,
                        header=(startrow == 0),  # Chỉ ghi header nếu sheet mới
                        startrow=startrow
                    )
            else:
                # Tạo file mới
                df.to_excel(file_path, sheet_name=sheet_name, index=False)

            print(f"✓ Đã ghi {len(results)} kết quả vào {file_path}")
            return True

        except Exception as e:
            print(f"✗ Lỗi ghi Excel: {e}")
            import traceback
            traceback.print_exc()
            return False

    @staticmethod
    def write_detailed_report(file_path: str, result: MouseResult, include_raw_events: bool = False):
        """
        Ghi báo cáo chi tiết với nhiều sheets
        """
        try:
            with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                # 1. Sheet tổng quan
                summary_df = pd.DataFrame([result.to_dict()])
                summary_df.to_excel(writer, sheet_name='Summary', index=False)

                # 2. Sheet alerts
                if result.alerts:
                    alerts_df = pd.DataFrame(result.alerts)
                    alerts_df.to_excel(writer, sheet_name='Alerts', index=False)

                # 3. Sheet metrics chi tiết
                metrics_data = {
                    'Metric': [
                        'Total Distance', 'X Distance', 'Y Distance',
                        'X Flips', 'Y Flips', 'Duration', 'Movement Span',
                        'Activity Ratio'
                    ],
                    'Value': [
                        result.total_distance, result.x_axis_distance, result.y_axis_distance,
                        result.x_flips, result.y_flips, result.duration_seconds,
                        result.movement_time_span,
                        result.movement_time_span / result.duration_seconds if result.duration_seconds > 0 else 0
                    ]
                }
                metrics_df = pd.DataFrame(metrics_data)
                metrics_df.to_excel(writer, sheet_name='Metrics', index=False)

            print(f"✓ Đã ghi báo cáo chi tiết: {file_path}")
            return True

        except Exception as e:
            print(f"✗ Lỗi ghi báo cáo: {e}")
            return False