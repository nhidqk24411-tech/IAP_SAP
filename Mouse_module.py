from pynput.mouse import Listener
from datetime import datetime, timedelta
import logging
import time

# -------------------------------
# Cấu hình file log
# -------------------------------
logging.basicConfig(
    filename="mouse_events.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

# -------------------------------
# Thời gian bắt đầu + thời gian kết thúc
# -------------------------------
start_time = datetime.now()
end_time = start_time + timedelta(seconds=5)

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
# Kiểm tra hết 20 phút
# -------------------------------
def check_timeout():
    if datetime.now() >= end_time:
        logging.info("=== Auto stopped (5 seconds reached) ===")
        print("Tracking stopped — reached 5 seconds.")
        return False  # dừng listener
    return True

# -------------------------------
# Bắt đầu listener
# -------------------------------
with Listener(on_move=on_move, on_click=on_click, on_scroll=on_scroll) as listener:
    listener.join()

logging.info(f"End time: {datetime.now()}")
logging.info("=== Mouse tracking finished ===")
