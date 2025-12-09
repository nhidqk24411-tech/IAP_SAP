"""
File tracking chuột gốc của bạn
"""

from pynput.mouse import Listener
from datetime import datetime, timedelta
import logging
import os


def run_tracking(duration_seconds, log_file_path):
    logging.basicConfig(
        filename=log_file_path,
        level=logging.INFO,
        format="%(asctime)s - %(message)s",
    )
    # -------------------------------
    # Thời gian bắt đầu + thời gian kết thúc
    # -------------------------------
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=duration_seconds)

    logging.info("=== Mouse tracking started ===")
    logging.info(f"Start time: {start_time}")

    # -------------------------------
    # Các hàm xử lý sự kiện chuột
    # -------------------------------
    def on_move(x, y):
        logging.info(f"Move: ({x}, {y})")
        return check_timeout()

    def on_click(x, y, button, pressed):
        action = "Pressed" if pressed else "Released"
        logging.info(f"{action} at ({x}, {y})")
        return check_timeout()

    def on_scroll(x, y, dx, dy):
        logging.info(f"Scroll at ({x}, {y}) dx={dx}, dy={dy}")
        return check_timeout()

    # -------------------------------
    # Kiểm tra hết thời gian
    # -------------------------------
    def check_timeout():
        if datetime.now() >= end_time:
            logging.info("=== Auto stopped ===")
            print(f"Tracking stopped — reached {duration_seconds} seconds.")
            return False  # dừng listener
        return True

    # -------------------------------
    # Bắt đầu listener
    # -------------------------------
    print(f"Tracking mouse for {duration_seconds} seconds...")
    print("Move your mouse. The tracker will auto-stop.")

    with Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as listener:
        listener.join()

    logging.info(f"End time: {datetime.now()}")
    logging.info("=== Mouse tracking finished ===")
    print(" Tracking completed. Check mouse_events.log")