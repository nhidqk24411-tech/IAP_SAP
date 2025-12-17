import sys
import cv2

from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtCore import Qt
from ui_faceid import Ui_MainWindow

class FaceIDWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Lấy size từ QLabel
        self.camera_size: int = self.ui.labelCamera.width()

        # Open webcam
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            print("Không mở được webcam")
            sys.exit(1)

        # Timer cập nhật frame
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)

        label_w = self.ui.labelCamera.width()
        label_h = self.ui.labelCamera.height()

        # === Crop theo tỉ lệ OVAL (quan trọng) ===
        frame_h, frame_w, _ = frame.shape
        label_ratio = label_w / label_h
        frame_ratio = frame_w / frame_h

        if frame_ratio > label_ratio:
            # Frame quá rộng → cắt ngang
            new_w = int(frame_h * label_ratio)
            x = (frame_w - new_w) // 2
            frame = frame[:, x:x + new_w]
        else:
            # Frame quá cao → cắt dọc
            new_h = int(frame_w / label_ratio)
            y = (frame_h - new_h) // 2
            frame = frame[y:y + new_h, :]

        # Resize đúng kích thước QLabel
        frame = cv2.resize(frame, (label_w, label_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        h, w, ch = frame.shape
        qimg = QImage(frame.data, w, h, ch * w, QImage.Format.Format_RGB888)

        #VẼ OVAL BẰNG QPainter
        pixmap = QPixmap(label_w, label_h)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addEllipse(0, 0, label_w, label_h)  # OVAL
        painter.setClipPath(path)

        painter.drawImage(0, 0, qimg)
        painter.end()

        self.ui.labelCamera.setPixmap(pixmap)

    def closeEvent(self, event):
        if self.cap.isOpened():
            self.cap.release()
        event.accept()


