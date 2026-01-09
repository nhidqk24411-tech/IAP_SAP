from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTableWidgetItem, QMainWindow, QPushButton, QHBoxLayout

from ui_mg_emplist import Ui_MainWindow as ui_emplist

class Emplist(QMainWindow):
    def __init__(self):
        super().__init__()

    def setupUi(self):
        self.ui = ui_emplist()
        self.ui.setupUi(self)

        self.ui.tableWidget.setColumnCount(4)
        self.ui.tableWidget.setHorizontalHeaderLabels(["Employee Name", "Employee ID", "Department",""])
        font = QFont()
        font.setPointSize(8)
        font.setBold(True)
        self.ui.tableWidget.horizontalHeaderItem(0).setFont(font)
        self.ui.tableWidget.horizontalHeaderItem(1).setFont(font)
        self.ui.tableWidget.horizontalHeaderItem(2).setFont(font)
        self.ui.tableWidget.horizontalHeaderItem(3).setFont(font)
        self.ui.tableWidget.setColumnWidth(0, 135)
        self.ui.tableWidget.setColumnWidth(1, 135)
        self.ui.tableWidget.setColumnWidth(2, 135)
        self.ui.tableWidget.setColumnWidth(3, 100)

        style_sheet = """QTableWidget {border:2px solid #1f5cab;
                                       border-radius: 10px}"""
        self.ui.tableWidget.setStyleSheet(style_sheet)

        self.load_data()

    def load_data(self):
        data = [
        ("Alexander", "086539265", "Sales"),
        ("Taylor", "055389828", "Sales"),
        ("David", "087326828", "Sales"),
        ("Jessica", "098253452", "Sales"),
        ("William", "097534189", "Sales"),
        ]
        self.ui.tableWidget.setRowCount(len(data))

        for row, (name, emp_id, dept) in enumerate(data):
            name_item = QTableWidgetItem(name)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tableWidget.setItem(row, 0, name_item)

            id_item = QTableWidgetItem(emp_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tableWidget.setItem(row, 1, id_item)

            dept_item = QTableWidgetItem(dept)
            dept_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.ui.tableWidget.setItem(row, 2, dept_item)

            btn = QPushButton("View")
            btn.setFixedSize(60, 24)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                        QPushButton {
                            background-color: #1f5cab;
                            color: white;
                            border-radius: 10px;
                            padding: 2px 6px;
                        }
                        QPushButton:hover {
                            background-color: #174a9c;
                        }
                        """)
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(btn)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.ui.tableWidget.setCellWidget(row, 3, container)
