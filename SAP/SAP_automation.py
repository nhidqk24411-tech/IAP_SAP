import win32com.client
import os, time, subprocess
from dotenv import load_dotenv

load_dotenv()


class SAPDataCollector:
    """Thu thập dữ liệu từ SAP GUI"""

    def __init__(self, user_name="", save_directory=""):
        self.user_name = user_name
        self.save_directory = save_directory
        self.sap_logon_path = r"C:\Program Files (x86)\SAP\FrontEnd\SapGui\saplogon.exe"
        self.session = None
        self.connection = None

    def quick_collect(self):
        """Thu thập dữ liệu nhanh và lưu vào thư mục chỉ định"""
        try:
            print(f"\n🤖 SAP Data Collection Starting...")
            print(f"   User: {self.user_name}")
            print(f"   Save to: {self.save_directory}")

            # Tạo thư mục nếu chưa tồn tại
            os.makedirs(self.save_directory, exist_ok=True)

            # Đường dẫn file đầy đủ
            save_path = os.path.join(self.save_directory, "sap_data.xlsx")
            print(f"   File: {save_path}")

            # 1. Mở SAP Logon
            print("   Step 1: Opening SAP Logon...")
            subprocess.Popen(self.sap_logon_path)
            time.sleep(5)

            # 2. Kết nối SAP
            print("   Step 2: Connecting to SAP...")
            SapGuiAuto = win32com.client.GetObject('SAPGUI')
            if not SapGuiAuto:
                print("❌ Cannot connect to SAP GUI")
                return None

            application = SapGuiAuto.GetScriptingEngine
            self.connection = application.OpenConnection("S36 [S36Z]", True)

            if not self.connection:
                print("❌ Cannot open SAP connection")
                return None

            connection1 = self.connection.Children(0)
            self.session = connection1.Children(0)

            # 3. Maximize cửa sổ
            self.session.findById("wnd[0]").maximize()

            # 4. Đăng nhập với credentials từ .env
            print("   Step 3: Logging in...")
            self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = os.getenv("SAP_CLIENT")
            self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = os.getenv("SAP_USER")
            self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = os.getenv("SAP_PASSWORD")
            self.session.findById("wnd[0]/usr/txtRSYST-LANGU").text = os.getenv("SAP_LANGUAGE")
            self.session.findById("wnd[0]").sendVKey(0)
            time.sleep(2)

            # 5. Thực hiện query
            print("   Step 4: Running query...")

            self.session.findById("wnd[0]/tbar[0]/okcd").text = "sqvi"
            self.session.findById("wnd[0]").sendVKey(0)

            self.session.findById("wnd[0]/usr/ctxtRS38R-QNUM").text = "ZSALE_TEST3"
            self.session.findById("wnd[0]/usr/ctxtRS38R-QNUM").caretPosition = 11
            self.session.findById("wnd[0]/usr/btnP1").press()
            self.session.findById("wnd[0]/usr/txtSP$00001-LOW").text = "LEARN-717"
            self.session.findById("wnd[0]/usr/txtSP$00001-LOW").caretPosition = 9
            self.session.findById("wnd[0]/tbar[1]/btn[8]").press()
            time.sleep(2)

            # 6. Export dữ liệu
            print("   Step 5: Exporting to Excel...")
            self.session.findById("wnd[0]/usr/cntlCONTAINER/shellcont/shell").pressToolbarContextButton("&MB_EXPORT")
            self.session.findById("wnd[0]/usr/cntlCONTAINER/shellcont/shell").selectContextMenuItem("&XXL")
            time.sleep(2)

            # 7. Lưu file - SỬA LỖI CHÍNH Ở ĐÂY
            print("   Step 6: Saving file...")
            self.session.findById("wnd[1]/tbar[0]/btn[20]").press()





            # Thiết lập đường dẫn và tên file
            self.session.findById("wnd[1]/usr/ctxtDY_PATH").text = self.save_directory
            self.session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "sap_data.xlsx"
            self.session.findById("wnd[1]/usr/ctxtDY_FILENAME").caretPosition = 13

            # Kiểm tra nếu file đã tồn tại
            if os.path.exists(save_path):
                print("   ⚠️ File exists, will replace...")
                # Nhấn Save (sẽ hiện dialog replace)
                self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                time.sleep(1)
                # Xác nhận replace nếu có dialog
                try:
                    self.session.findById("wnd[1]/tbar[0]/btn[11]").press()
                    print("   ✅ File replaced")
                except:
                    pass
            else:
                # Nhấn Save bình thường
                self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                print("   ✅ File saved")

            time.sleep(3)

            # 8. Đóng kết nối
            print("   Step 7: Closing SAP connection...")
            try:
                self.connection.CloseSession("ses[0]")
            except:
                pass

            print(f"✅ SAP data collected: {save_path}")
            return save_path

        except Exception as e:
            print(f"❌ SAP collection error: {e}")
            import traceback
            traceback.print_exc()

            # Đảm bảo đóng kết nối nếu có lỗi
            try:
                if self.connection:
                    self.connection.CloseSession("ses[0]")
            except:
                pass

            return None


# Dùng để chạy độc lập (test)
if __name__ == "__main__":
    collector = SAPDataCollector(
        user_name="TEST",
        save_directory=os.path.join(os.path.expanduser("~"), "Downloads")
    )
    result = collector.quick_collect()
    print(f"Result: {result}")