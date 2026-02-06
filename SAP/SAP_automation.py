import win32com.client
import os, time, subprocess
from dotenv import load_dotenv

load_dotenv()


class SAPDataCollector:
    def __init__(self, user_name="", save_directory=""):
        # user_name ở đây sẽ đóng vai trò là mã nhân viên (VD: LEARN-717)
        self.user_name = user_name
        self.save_directory = save_directory
        self.sap_logon_path = r"C:\Program Files (x86)\SAP\FrontEnd\SAPgui\saplogon.exe"
        self.session = None
        self.connection = None

    def quick_collect(self):  # Không cần truyền filter_value vào nữa
        try:
            print(f"\n🤖 SAP Data Collection Starting...")
            # Sử dụng self.user_name làm giá trị tìm kiếm
            print(f"   Searching for User ID: {self.user_name}")

            os.makedirs(self.save_directory, exist_ok=True)
            save_path = os.path.join(self.save_directory, "sap_data.xlsx")

            # 1. Mở SAP Logon
            print("   Step 1: Opening SAP Logon...")
            subprocess.Popen(self.sap_logon_path)
            time.sleep(8)

            # 2. Kết nối SAP
            print("   Step 2: Connecting to SAP...")
            sap_gui_auto = None
            for attempt in range(3):
                try:
                    sap_gui_auto = win32com.client.GetObject("SAPGUI")
                    if sap_gui_auto: break
                except:
                    try:
                        sap_gui_auto = win32com.client.Dispatch("Sapgui.Component")
                        if sap_gui_auto: break
                    except:
                        time.sleep(5)

            if not sap_gui_auto:
                print("❌ Lỗi: Không thể kết nối SAP GUI.")
                return None

            application = sap_gui_auto.GetScriptingEngine
            connection_name = "S36 [S36Z]"

            try:
                self.connection = application.OpenConnection(connection_name, True)
            except:
                conn_string = "/H/saprouter.hcc.in.tum.de/S/3298/H/S36Z/S/3200"
                self.connection = application.OpenConnection(conn_string, True)

            start_wait = time.time()
            while self.connection.Children.Count == 0:
                time.sleep(1)
                if time.time() - start_wait > 20: return None

            self.session = self.connection.Children(0)
            self.session.findById("wnd[0]").maximize()

            # 3. Đăng nhập
            print("   Step 3: Logging in...")
            # Lấy thông tin tài khoản SAP từ .env hoặc dùng mặc định
            sap_user = os.getenv("SAP_USER") or "NHIDQ-24411"
            sap_pass = os.getenv("SAP_PASSWORD") or "IPASAP2025"

            try:
                self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = str(sap_user)
                self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = str(sap_pass)
                self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = os.getenv("SAP_CLIENT") or "312"
                self.session.findById("wnd[0]").sendVKey(0)
                time.sleep(3)

                if self.session.Children.Count > 1:
                    try:
                        self.session.findById("wnd[1]/usr/radMULTI_LOGON_OPT2").select()
                        self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                    except:
                        pass
            except:
                print("   ⚠️ Đã đăng nhập sẵn hoặc dùng SSO.")

            # 4. Thực hiện Query SQVI
            print("   Step 4: Running query...")
            self.session.startTransaction("sqvi")
            time.sleep(2)

            self.session.findById("wnd[0]/usr/ctxtRS38R-QNUM").text = "ZSALE_TEST3"
            self.session.findById("wnd[0]").sendVKey(8)
            time.sleep(2)

            # --- SỬ DỤNG self.user_name Ở ĐÂY ---
            print(f"   Entering Filter Criteria: {self.user_name}")

            # Điền mã nhân viên được truyền từ lúc khởi tạo class
            self.session.findById("wnd[0]/usr/txtSP$00001-LOW").text = self.user_name
            self.session.findById("wnd[0]").sendVKey(8)
            time.sleep(5)

            # 5. Export dữ liệu
            print("   Step 5: Exporting to Excel...")
            shell = self.session.findById("wnd[0]/usr/cntlCONTAINER/shellcont/shell")
            shell.pressToolbarContextButton("&MB_EXPORT")
            shell.selectContextMenuItem("&XXL")
            time.sleep(2)

            self.session.findById("wnd[1]").sendVKey(0)
            time.sleep(3)

            # 6. Lưu file
            print("   Step 6: Saving file...")
            self.session.findById("wnd[1]/usr/ctxtDY_PATH").text = self.save_directory
            self.session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "sap_data.xlsx"

            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except:
                    pass
            time.sleep(15)

            self.session.findById("wnd[1]").sendVKey(0)
            print("   ✅ File saved")

            print(f"✅ Thành công! File lưu tại: {save_path}")
            return save_path

        except Exception as e:
            print(f"❌ Lỗi: {e}")
            return None


