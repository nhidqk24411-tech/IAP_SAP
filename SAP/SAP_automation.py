import win32com.client
import os, time, subprocess
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class SAPDataCollector:
    def __init__(self, user_name="", save_directory=""):
        self.user_name = user_name
        self.save_directory = save_directory
        self.sap_logon_path = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
        self.session = None
        self.connection = None

    def quick_collect(self):
        try:
            print(f"\n🤖 SAP Data Collection Starting...")
            os.makedirs(self.save_directory, exist_ok=True)
            save_path = os.path.join(self.save_directory, "sap_data.xlsx")

            # --- TÍNH TOÁN KHOẢNG NGÀY THEO FORMAT MM/DD/YYYY ---
            now = datetime.now()
            # Mặc định ngày 1 của tháng hiện tại
            date_start = now.replace(day=1).strftime("%m/01/%Y")
            # Ngày hiện tại
            date_end = now.strftime("%m/%d/%Y")

            print(f"   📅 Filtering Period: {date_start} to {date_end}")

            # 1. Mở SAP Logon
            print("   Step 1: Opening SAP Logon...")
            subprocess.Popen(self.sap_logon_path)
            time.sleep(8)

            # 2. Kết nối SAP
            print("   Step 2: Connecting to SAP...")
            sap_gui_auto = win32com.client.GetObject("SAPGUI")
            application = sap_gui_auto.GetScriptingEngine

            connection_name = "SAP Vista : Pre-configured S/4HANA"
            try:
                self.connection = application.OpenConnection(connection_name, True)
            except:
                conn_string = "/H/saprouter.hcc.in.tum.de/S/3298/H/S36Z/S/3200"
                self.connection = application.OpenConnection(conn_string, True)

            time.sleep(3)
            self.session = self.connection.Children(0)
            self.session.findById("wnd[0]").maximize()

            try:
                # Lấy handle (mã định danh) của cửa sổ SAP
                sap_hwnd = self.session.findById("wnd[0]").Handle

                # Sử dụng WinAPI (ctypes) để đưa cửa sổ lên trên cùng (Foreground)
                import ctypes
                ctypes.windll.user32.ShowWindow(sap_hwnd, 5)  # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(sap_hwnd)

                # Thêm một lệnh của chính SAP để đảm bảo nó được focus
                self.session.findById("wnd[0]").maximize()
            except Exception as e:
                print(f"   ⚠️ Không thể ép giao diện SAP lên trước: {e}")

            # 3. Đăng nhập
            print("   Step 3: Logging in...")
            sap_user = os.getenv("SAP_USER") or "NHIDQ-24411"
            sap_pass = os.getenv("SAP_PASSWORD") or "IPASAP2025"
            sap_client = os.getenv("SAP_CLIENT") or "312"

            # ĐIỀN CLIENT (MANDT) - Đảm bảo dòng này chạy trước User/Pass
            try:
                self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = str(sap_client)
                self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = str(sap_user)
                self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = str(sap_pass)
                self.session.findById("wnd[0]").sendVKey(0)  # Enter
                time.sleep(3)

                # Xử lý popup Multi-logon nếu có
                if self.session.Children.Count > 1:
                    try:
                        self.session.findById("wnd[1]/usr/radMULTI_LOGON_OPT2").select()
                        self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                    except:
                        pass
            except:
                print("   ⚠️ Login fields interaction error (might be already logged in)")

            # 4. Thực hiện Query SQVI
            print("   Step 4: Running query ZSALE_TEST3...")
            self.session.startTransaction("sqvi")
            time.sleep(2)

            self.session.findById("wnd[0]/usr/ctxtRS38R-QNUM").text = "ZSALE_TEST3"
            self.session.findById("wnd[0]").sendVKey(8)  # F8 Execute
            time.sleep(2)

            # --- NHẬP BỘ LỌC (FILTER) VỚI FORMAT MM/DD/YYYY ---
            print("   Applying Filter Criteria...")
            # Lọc theo User
            self.session.findById("wnd[0]/usr/txtSP$00001-LOW").text = "LEARN-717"

            # Lọc theo Ngày (LOW: Ngày đầu tháng, HIGH: Ngày hiện tại)
            self.session.findById("wnd[0]/usr/ctxtSP$00002-LOW").text = date_start
            self.session.findById("wnd[0]/usr/ctxtSP$00002-HIGH").text = date_end

            self.session.findById("wnd[0]").sendVKey(8)  # F8 Execute
            time.sleep(5)

            # 5. Export dữ liệu
            print("   Step 5: Exporting to Excel...")
            shell = self.session.findById("wnd[0]/usr/cntlCONTAINER/shellcont/shell")
            shell.pressToolbarContextButton("&MB_EXPORT")
            shell.selectContextMenuItem("&XXL")
            time.sleep(2)

            # Chấp nhận format Excel
            self.session.findById("wnd[1]").sendVKey(0)
            time.sleep(3)

            # 6. Lưu file
            print("   Step 6: Saving file...")
            self.session.findById("wnd[1]/usr/ctxtDY_PATH").text = self.save_directory
            self.session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "sap_data.xlsx"

            if os.path.exists(save_path):
                os.remove(save_path)

            self.session.findById("wnd[1]").sendVKey(0)  # Nhấn nút Save/Replace (Enter)
            time.sleep(3)

            print(f"✅ Success! Data saved at: {save_path}")
            return save_path

        except Exception as e:
            print(f"❌ Error: {e}")
            return None


if __name__ == "__main__":
    # Thay đổi đường dẫn lưu file phù hợp với máy bạn
    download_dir = os.path.join(os.path.expanduser("~"), "Downloads")
    collector = SAPDataCollector(user_name="LEARN-717", save_directory=download_dir)
    collector.quick_collect()
