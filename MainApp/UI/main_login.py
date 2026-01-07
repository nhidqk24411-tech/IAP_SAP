from PyQt6.QtWidgets import QMainWindow
from main_faceid import FaceIDWindow
from UI_LOGIN import Ui_MainWindow as ui_login

class Login(QMainWindow):
    def __init__(self):
        super().__init__()

    def setupUi(self):
        self.ui = ui_login()
        self.ui.setupUi(self)
        self.ui.pushButton_faceid.clicked.connect(self.open_faceid)

    def open_faceid(self):
        self.hide()
        self.faceid = FaceIDWindow()
        self.faceid.show()
