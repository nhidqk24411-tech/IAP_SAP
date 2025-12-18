from PyQt6 import QtCore, QtWidgets
from Interface.UI_HOME_emp import Ui_MainWindow
import sys
import subprocess
import os
from datetime import datetime


class Home_empEX(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)

        self.setWindowTitle("PowerSight - Employee Dashboard")
        self.setFixedSize(800, 512)

        self.is_working = False
        self.session_process = None

        self.pushButton_8.clicked.connect(self.start_work_session)
        self.update_time()

    def update_time(self):
        self.label_3.setText(f"Time: {datetime.now():%H:%M:%S}")
        QtCore.QTimer.singleShot(1000, self.update_time)

    # =========================
    # SESSION CONTROL
    # =========================
    def start_work_session(self):
        if self.is_working:
            return

        launcher = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Session_launcher.py"
        )

        self.session_process = subprocess.Popen(
            [sys.executable, launcher]
        )

        self.is_working = True
        self.update_ui(True)

        self.monitor_timer = QtCore.QTimer()
        self.monitor_timer.timeout.connect(self.check_session)
        self.monitor_timer.start(2000)

    def check_session(self):
        if self.session_process and self.session_process.poll() is not None:
            self.monitor_timer.stop()
            self.session_process = None
            self.is_working = False
            self.update_ui(False)

            QtWidgets.QMessageBox.information(
                self, "Finished", "Session ended. Data saved."
            )

    # =========================
    # UI STATE
    # =========================
    def update_ui(self, working):
        if working:
            self.pushButton_8.setText("Session Running...")
            self.pushButton_8.setEnabled(False)
            self.khichle.setText("Browser opened. Mouse tracking starts in 5 minutes.")
        else:
            self.pushButton_8.setText("Start Working Session")
            self.pushButton_8.setEnabled(True)
            self.khichle.setText("Ready for next session.")

    # =========================
    # SAFE CLOSE
    # =========================
    def closeEvent(self, event):
        if self.is_working:
            reply = QtWidgets.QMessageBox.question(
                self, "Exit",
                "Session is running. Exit anyway?",
                QtWidgets.QMessageBox.StandardButton.Yes |
                QtWidgets.QMessageBox.StandardButton.No
            )

            if reply == QtWidgets.QMessageBox.StandardButton.No:
                event.ignore()
                return

            if self.session_process:
                self.session_process.terminate()

        event.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = Home_empEX()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
