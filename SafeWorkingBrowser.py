import sys
from PyQt6.QtCore import QUrl, Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QTabWidget, QPushButton, QLabel, QMessageBox
)
from PyQt6.QtGui import QFont, QIcon


class SafeWebEngineView(QWebEngineView):
    """WebEngineView với kiểm tra URL linh hoạt và cấu hình đầy đủ cho Google Workspace"""

    def __init__(self, allowed_domains, parent=None, is_default_tab=False):
        super().__init__(parent)
        self.allowed_domains = allowed_domains
        self.is_default_tab = is_default_tab  # Lưu trạng thái tab mặc định

        # Cấu hình nâng cao cho Google Workspace
        settings = self.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Cấu hình profile cho Google
        profile = self.page().profile()
        profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        # Cho phép tất cả cookies của Google
        profile.cookieStore().deleteAllCookies()

        self.urlChanged.connect(self.check_url)

    def check_url(self, url):
        """Kiểm tra domain có được phép không"""
        current_url = url.toString()
        if not current_url:
            return

        # Lấy host từ URL
        current_host = QUrl(current_url).host()

        # Kiểm tra xem host có kết thúc bằng domain được phép không
        is_allowed = any(current_host.endswith(domain) for domain in self.allowed_domains)

        if not is_allowed and current_host:
            print(f"Đã chặn truy cập: {current_url}")
            # Quay về trang chính của tab
            if "google" in self.allowed_domains[0]:
                self.setUrl(QUrl("https://mail.google.com"))
            else:
                self.setUrl(QUrl(self.allowed_domains[0]))


class TimerWidget(QWidget):
    """Widget đồng hồ đếm thời gian với thiết kế hiện đại"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.elapsed_time = 0
        self.is_running = True

        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Nhãn thời gian với font đẹp
        self.time_label = QLabel("00:00:00")
        self.time_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.time_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4285F4, stop:1 #34A853);
                padding: 8px 20px;
                border-radius: 8px;
                border: 1px solid rgba(255, 255, 255, 0.2);
                min-width: 110px;
                text-align: center;
                letter-spacing: 1px;
            }
        """)

        # Nút Pause
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setFixedWidth(100)
        self.pause_btn.setFont(QFont("Arial", 10))
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #5F6368;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4285F4;
            }
            QPushButton:pressed {
                background-color: #3367D6;
            }
        """)
        self.pause_btn.clicked.connect(self.toggle_timer)

        layout.addWidget(self.time_label)
        layout.addWidget(self.pause_btn)

        self.setLayout(layout)

        # Timer cập nhật mỗi giây
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)

    def update_timer(self):
        if self.is_running:
            self.elapsed_time += 1
            hours = self.elapsed_time // 3600
            minutes = (self.elapsed_time % 3600) // 60
            seconds = self.elapsed_time % 60
            self.time_label.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")

    def toggle_timer(self):
        self.is_running = not self.is_running
        if self.is_running:
            self.pause_btn.setText("⏸ Pause")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5F6368;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #4285F4;
                }
            """)
        else:
            self.pause_btn.setText("▶ Resume")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #EA4335;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #D23A2D;
                }
            """)

    def reset_timer(self):
        self.elapsed_time = 0
        self.time_label.setText("00:00:00")
        self.is_running = True
        self.pause_btn.setText("⏸ Pause")
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #5F6368;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4285F4;
            }
        """)


class ProfessionalWorkBrowser(QMainWindow):
    """Ứng dụng trình duyệt làm việc chuyên nghiệp với chức năng đóng tab"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Professional Workspace Browser")

        # Biến theo dõi trạng thái fullscreen
        self.is_fullscreen = False

        # Domain được phép cho Google Workspace
        self.google_domains = [
            "google.com",
            "googleapis.com",
            "gstatic.com",
            "googleusercontent.com"
        ]

        # Domain được phép cho SAP
        self.sap_domains = [
            "s36.gb.ucc.cit.tum.de",
            "ucc.cit.tum.de",
            "tum.de"
        ]

        # Các ứng dụng Google có thể mở thêm
        self.google_apps = {
            "Google Drive": "https://drive.google.com",
            "Google Docs": "https://docs.google.com",
            "Google Sheets": "https://sheets.google.com",
            "Google Slides": "https://slides.google.com",
            "Google Calendar": "https://calendar.google.com",
            "Google Meet": "https://meet.google.com"
        }

        # Thiết lập font chữ
        self.setup_fonts()

        # Thiết lập màu sắc chủ đạo theo Google Workspace
        self.setStyleSheet("""
            QMainWindow {
                background-color: #202124;
            }
            QStatusBar {
                background-color: #303134;
                color: #E8EAED;
                font-size: 11px;
                padding: 4px;
                border-top: 1px solid #3C4043;
            }
        """)

        # Widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout chính
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === THANH ĐIỀU KHIỂN CHUYÊN NGHIỆP ===
        control_panel = QWidget()
        control_panel.setFixedHeight(70)
        control_panel.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #303134, stop:1 #202124);
                border-bottom: 1px solid #3C4043;
            }
        """)

        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(20, 10, 20, 10)
        control_layout.setSpacing(15)

        # Logo và tiêu đề
        title_container = QWidget()
        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("Power Sight")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #E8EAED;")

        subtitle = QLabel("Secure & Focused Working")
        subtitle.setFont(QFont("Arial", 9))
        subtitle.setStyleSheet("color: #9AA0A6; padding-left: 10px;")

        title_layout.addWidget(title_label)
        title_layout.addWidget(subtitle)

        control_layout.addWidget(title_container)
        control_layout.addSpacing(30)

        # Nút điều hướng
        nav_buttons = [
            ("←", self.go_back, "#5F6368"),
            ("→", self.go_forward, "#5F6368"),
            ("↻", self.refresh_current, "#4285F4"),
        ]

        for icon, handler, color in nav_buttons:
            btn = QPushButton(icon)
            btn.setFixedSize(40, 40)
            btn.setFont(QFont("Arial", 12))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {'#4285F4' if color == '#5F6368' else '#3367D6'};
                }}
            """)
            btn.clicked.connect(handler)
            control_layout.addWidget(btn)

        control_layout.addSpacing(20)

        # Nút New Tab - Mở menu để chọn ứng dụng Google
        self.new_tab_btn = QPushButton("＋ New Tab")
        self.new_tab_btn.setFixedWidth(100)
        self.new_tab_btn.setFont(QFont("Arial", 10))
        self.new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: #FBBC04;
                color: #202124;
                border: none;
                padding: 8px 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F29900;
            }
        """)
        self.new_tab_btn.clicked.connect(self.show_new_tab_menu)
        control_layout.addWidget(self.new_tab_btn)

        # Thông tin trạng thái
        status_container = QWidget()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)

        status_text = QLabel("🔒 Secure Mode | Allowed: Google Workspace & SAP")
        status_text.setFont(QFont("Arial", 9))
        status_text.setStyleSheet("color: #34A853;")

        connection_status = QLabel("✓ Default tabs cannot be closed")
        connection_status.setFont(QFont("Arial", 8))
        connection_status.setStyleSheet("color: #9AA0A6;")

        status_layout.addWidget(status_text)
        status_layout.addWidget(connection_status)

        control_layout.addWidget(status_container)
        control_layout.addStretch()

        # Đồng hồ
        self.timer_widget = TimerWidget()
        control_layout.addWidget(self.timer_widget)

        control_layout.addSpacing(20)

        # Nút Fullscreen
        self.fullscreen_btn = QPushButton("⛶ Fullscreen")
        self.fullscreen_btn.setFixedWidth(120)
        self.fullscreen_btn.setFont(QFont("Arial", 10))
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: #8AB4F8;
                color: #202124;
                border: none;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #AECBFA;
            }
        """)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        control_layout.addWidget(self.fullscreen_btn)

        # Nút Exit
        exit_btn = QPushButton("Exit")
        exit_btn.setFixedWidth(100)
        exit_btn.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #EA4335;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #D23A2D;
            }
        """)
        exit_btn.clicked.connect(self.confirm_exit)
        control_layout.addWidget(exit_btn)

        main_layout.addWidget(control_panel)

        # === KHU VỰC TAB CHÍNH ===
        self.tab_widget = QTabWidget()
        self.tab_widget.setFont(QFont("Arial", 10))
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #202124;
            }
            QTabBar::tab {
                background-color: #303134;
                color: #E8EAED;
                padding: 12px 24px;
                margin-right: 2px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border: 1px solid #3C4043;
                border-bottom: none;
                font-weight: 500;
                min-width: 150px;
            }
            QTabBar::tab:selected {
                background-color: #202124;
                color: #8AB4F8;
                border-bottom: 2px solid #8AB4F8;
            }
            QTabBar::tab:hover:!selected {
                background-color: #3C4043;
            }
        """)
        self.tab_widget.setTabsClosable(True)  # Cho phép đóng tab
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.tab_widget.setDocumentMode(True)

        # Tạo 2 tab mặc định (không thể đóng)
        self.create_default_tabs()

        main_layout.addWidget(self.tab_widget)

        # Thanh trạng thái
        self.statusBar().setFont(QFont("Arial", 9))
        self.statusBar().showMessage("✓ Ready - Default tabs cannot be closed | Press F11 for fullscreen")

        # Mặc định fullscreen
        QTimer.singleShot(500, self.enter_fullscreen)
        # Thêm biến lưu callback
        self.on_close_callback = None

        # Kết nối sự kiện đóng cửa sổ
        self.destroyed.connect(self.on_window_destroyed)

    def setup_fonts(self):
        """Thiết lập font chữ cho ứng dụng"""
        app_font = QFont("Arial", 10)
        QApplication.setFont(app_font)
        print("Using font: Arial")

    def create_default_tabs(self):
        """Tạo các tab mặc định (không thể đóng)"""
        # Tab 1: Gmail
        gmail_browser = SafeWebEngineView(self.google_domains, is_default_tab=True)
        gmail_browser.setUrl(QUrl("https://mail.google.com"))
        self.tab_widget.addTab(gmail_browser, " Gmail")

        # Tab 2: SAP System
        sap_browser = SafeWebEngineView(self.sap_domains, is_default_tab=True)
        sap_url = "https://s36.gb.ucc.cit.tum.de/sap/bc/ui2/flp?sap-client=312&sap-language=EN#Shell-home"
        sap_browser.setUrl(QUrl(sap_url))
        self.tab_widget.addTab(sap_browser, " SAP System")

    def show_new_tab_menu(self):
        """Hiển thị menu chọn ứng dụng Google để mở tab mới"""
        menu = QWidget(self, Qt.WindowType.Popup)
        menu.setStyleSheet("""
            QWidget {
                background-color: #303134;
                border: 1px solid #5F6368;
                border-radius: 8px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout(menu)
        layout.setSpacing(5)

        for app_name, app_url in self.google_apps.items():
            btn = QPushButton(f"➕ {app_name}")
            btn.setFont(QFont("Arial", 10))
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4285F4;
                    color: white;
                    border: none;
                    padding: 10px 15px;
                    border-radius: 5px;
                    text-align: left;
                }
                QPushButton:hover {
                    background-color: #3367D6;
                }
            """)
            btn.clicked.connect(lambda checked, url=app_url, name=app_name: self.add_new_tab(url, name))
            layout.addWidget(btn)

        # Hiển thị menu dưới nút New Tab
        pos = self.new_tab_btn.mapToGlobal(self.new_tab_btn.rect().bottomLeft())
        menu.move(pos)
        menu.show()

    def add_new_tab(self, url, title):
        """Thêm tab mới (có thể đóng được)"""
        browser = SafeWebEngineView(self.google_domains, is_default_tab=False)
        browser.setUrl(QUrl(url))

        # Thêm tab với nút đóng
        index = self.tab_widget.addTab(browser, f" {title}")
        self.tab_widget.setCurrentIndex(index)

        self.statusBar().showMessage(f"✓ Added new tab: {title}", 3000)

    def close_tab(self, index):
        """Xử lý đóng tab - chỉ cho phép đóng tab không phải mặc định"""
        # Kiểm tra xem tab có phải là tab mặc định không
        if index < 2:  # 2 tab đầu tiên là mặc định
            self.statusBar().showMessage("⚠️ Default tabs cannot be closed!", 3000)
            return

        # Xác nhận đóng tab
        reply = QMessageBox.question(
            self, "Close Tab",
            f"Close tab '{self.tab_widget.tabText(index)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            widget = self.tab_widget.widget(index)
            if widget:
                widget.deleteLater()
            self.tab_widget.removeTab(index)
            self.statusBar().showMessage(f"✓ Tab closed", 2000)

    def set_close_callback(self, callback):
        """Thiết lập callback khi đóng cửa sổ"""
        self.on_close_callback = callback

    def on_window_destroyed(self):
        """Xử lý khi cửa sổ bị đóng"""
        if self.on_close_callback:
            self.on_close_callback()

        # Dừng timer nếu có
        if hasattr(self, 'timer_widget'):
            self.timer_widget.timer.stop()

    def go_back(self):
        """Quay lại trang trước"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and current_widget.history().canGoBack():
            current_widget.back()

    def go_forward(self):
        """Tiến tới trang sau"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget and current_widget.history().canGoForward():
            current_widget.forward()

    def refresh_current(self):
        """Làm mới trang hiện tại"""
        current_widget = self.tab_widget.currentWidget()
        if current_widget:
            current_widget.reload()
            self.statusBar().showMessage("🔄 Refreshing current page...", 2000)

    def toggle_fullscreen(self):
        """Chuyển đổi chế độ fullscreen"""
        if self.is_fullscreen:
            self.showNormal()
            self.fullscreen_btn.setText("⛶ Fullscreen")
            self.fullscreen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8AB4F8;
                    color: #202124;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #AECBFA;
                }
            """)
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("Full Windowed")
            self.fullscreen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #34A853;
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2E8B47;
                }
            """)

        self.is_fullscreen = not self.is_fullscreen

    def enter_fullscreen(self):
        """Vào chế độ fullscreen"""
        self.showFullScreen()
        self.is_fullscreen = True
        self.fullscreen_btn.setText("❒ Windowed")
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background-color: #34A853;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2E8B47;
            }
        """)

    def confirm_exit(self):
        """Xác nhận thoát ứng dụng - KHÔNG GHI LOG"""
        reply = QMessageBox.question(
            self, "Exit Workspace Browser",
            "Are you sure you want to exit the Professional Workspace Browser?\n\n"
            f"Total working time: {self.timer_widget.elapsed_time // 3600}h "
            f"{(self.timer_widget.elapsed_time % 3600) // 60}m\n"
            "All unsaved work might be lost.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            QApplication.quit()

    def closeEvent(self, event):
        """Xử lý khi đóng cửa sổ"""
        event.ignore()
        self.confirm_exit()

    def keyPressEvent(self, event):
        """Xử lý phím tắt"""
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_F5:
            self.refresh_current()
        elif event.key() == Qt.Key.Key_Escape and self.is_fullscreen:
            self.showNormal()
            self.is_fullscreen = False
            self.fullscreen_btn.setText("⛶ Fullscreen")
            self.fullscreen_btn.setStyleSheet("""
                QPushButton {
                    background-color: #8AB4F8;
                    color: #202124;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #AECBFA;
                }
            """)
        elif event.key() == Qt.Key.Key_W and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            # Ctrl+W để đóng tab hiện tại (chỉ tab không phải mặc định)
            current_index = self.tab_widget.currentIndex()
            self.close_tab(current_index)
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Thiết lập ứng dụng
    app.setApplicationName("Professional Workspace Browser")
    app.setStyle("Fusion")

    # Tạo và hiển thị cửa sổ
    browser = ProfessionalWorkBrowser()
    browser.show()

    sys.exit(app.exec())