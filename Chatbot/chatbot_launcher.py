#!/usr/bin/env python3
"""
Chatbot Launcher Fixed - Dùng toàn bộ chatbot system
"""

import sys
import os
from pathlib import Path

# Thêm đường dẫn
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *


class ChatbotLauncher:
    """Khởi chạy toàn bộ chatbot system"""

    @staticmethod
    def launch_full_chatbot(user_name, parent_window=None):
        """Khởi chạy full chatbot system"""
        print(f"🚀 LAUNCHING FULL CHATBOT SYSTEM for {user_name}")

        try:
            # Test import all modules
            print("\n🔧 Testing module imports...")

            try:
                # Test config
                from config import Config
                print("✅ config.py: OK")

                # Validate Gemini config mới
                print("🔧 Validating Google GenAI configuration...")
                Config.validate_gemini_config()

                # Override default employee name
                Config.DEFAULT_EMPLOYEE_NAME = user_name
                print(f"   Set employee: {user_name}")
            except Exception as e:
                print(f"❌ config.py: {e}")
                return None

            # 2. Test employee_chatbot - ĐÃ SỬA IMPORT
            try:
                from employee_chatbot import EmployeeChatbotGUI
                print("✅ employee_chatbot.py: OK")
            except Exception as e:
                print(f"❌ employee_chatbot.py: {e}")
                import traceback
                traceback.print_exc()
                return None

            # 3. Test other modules
            try:
                from gemini_analyzer import GeminiAnalyzer
                print("✅ gemini_analyzer.py: OK")
            except Exception as e:
                print(f"⚠️ gemini_analyzer.py: {e}")

            try:
                from data_processor import DataProcessor
                print("✅ data_processor.py: OK")
            except Exception as e:
                print(f"⚠️ data_processor.py: {e}")

            try:
                from dashboard import PerformanceDashboard  # ĐÃ SỬA
                print("✅ dashboard.py: OK")
            except Exception as e:
                print(f"⚠️ dashboard.py: {e}")

            # Tạo chatbot window
            print(f"\n🎯 Creating EmployeeChatbotGUI for {user_name}...")
            chatbot_window = EmployeeChatbotGUI(user_name)

            # Thiết lập window độc lập
            chatbot_window.setWindowFlags(Qt.WindowType.Window)

            print("✅ Full chatbot system created successfully")
            return chatbot_window

        except Exception as e:
            print(f"❌ ERROR launching full chatbot: {e}")
            import traceback
            traceback.print_exc()
            return None

    @staticmethod
    def show_chatbot_fullscreen(user_name, parent_window=None):
        """Hiển thị chatbot fullscreen"""
        chatbot = ChatbotLauncher.launch_full_chatbot(user_name, parent_window)

        if not chatbot:
            QMessageBox.critical(parent_window, "Lỗi",
                                 "Không thể khởi động chatbot system")
            return None

        try:
            # Lấy kích thước màn hình
            screen = QApplication.primaryScreen()
            screen_geometry = screen.geometry()

            # Thiết lập kích thước (90% màn hình)
            width = int(screen_geometry.width() * 0.9)
            height = int(screen_geometry.height() * 0.85)

            # Resize và di chuyển
            chatbot.resize(width, height)
            chatbot.move(
                (screen_geometry.width() - width) // 2,
                (screen_geometry.height() - height) // 2
            )

            # Hiển thị
            chatbot.show()
            chatbot.raise_()
            chatbot.activateWindow()

            print(f"✅ Chatbot displayed at {width}x{height}")

            # Minimize parent nếu có
            if parent_window:
                parent_window.showMinimized()
                print("🏠 Parent window minimized")

            return chatbot

        except Exception as e:
            print(f"❌ Error showing chatbot: {e}")
            return None


if __name__ == "__main__":
    # Test
    app = QApplication(sys.argv)

    print("🔧 Testing ChatbotLauncherFixed...")
    chatbot = ChatbotLauncher.launch_full_chatbot("Giang")

    if chatbot:
        chatbot.show()
        sys.exit(app.exec())
    else:
        print("❌ Failed to launch chatbot")