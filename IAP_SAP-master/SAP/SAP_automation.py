import win32com.client
import os, time, subprocess
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

            # 1. Mở SAP Logon
            print("   Step 1: Opening SAP Logon...")
            subprocess.Popen(self.sap_logon_path)
            time.sleep(8)

            # 2. Kết nối SAP (Cơ chế Retry 3 lần)
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
                        print(f"      Attempt {attempt + 1}: Waiting for SAP...")
                        time.sleep(5)

            if not sap_gui_auto:
                print("❌ Lỗi: Không thể kết nối SAP GUI. Hãy đảm bảo Scripting đã bật!")
                return None

            application = sap_gui_auto.GetScriptingEngine
            # Tên kết nối từ ảnh của bạn
            connection_name = "SAP Vista : Pre-configured S/4HANA"

            try:
                self.connection = application.OpenConnection(connection_name, True)
            except:
                print("      ⚠️ Không tìm thấy tên, thử dùng Connection String...")
                conn_string = "/H/saprouter.hcc.in.tum.de/S/3298/H/S36Z/S/3200"
                self.connection = application.OpenConnection(conn_string, True)

            # Đợi Session xuất hiện
            start_wait = time.time()
            while self.connection.Children.Count == 0:
                time.sleep(1)
                if time.time() - start_wait > 20:
                    print("❌ Timeout: Không lấy được Session")
                    return None

            self.session = self.connection.Children(0)
            self.session.findById("wnd[0]").maximize()

            # 3. Đăng nhập
            print("   Step 3: Logging in...")
            sap_user = os.getenv("SAP_USER")
            sap_pass = os.getenv("SAP_PASSWORD")

            try:
                # Thử tìm ô Username, nếu thấy thì nhập liệu
                self.session.findById("wnd[0]/usr/txtRSYST-BNAME").text = str(sap_user)
                self.session.findById("wnd[0]/usr/pwdRSYST-BCODE").text = str(sap_pass)
                self.session.findById("wnd[0]/usr/txtRSYST-MANDT").text = os.getenv("SAP_CLIENT")
                self.session.findById("wnd[0]").sendVKey(0)  # Enter
                time.sleep(3)

                # Xử lý popup Multi-logon (nếu có)
                if self.session.Children.Count > 1:
                    try:
                        self.session.findById("wnd[1]/usr/radMULTI_LOGON_OPT2").select()
                        self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
                    except:
                        pass
            except:
                print("   ⚠️ Đã đăng nhập sẵn hoặc dùng SSO.")

            # --- QUAN TRỌNG: BƯỚC 4, 5, 6 PHẢI NẰM NGOÀI KHỐI EXCEPT TRÊN ---

            # 4. Thực hiện Query SQVI
            print("   Step 4: Running query...")
            self.session.startTransaction("sqvi")
            time.sleep(2)

            self.session.findById("wnd[0]/usr/ctxtRS38R-QNUM").text = "ZSALE_TEST3"
            self.session.findById("wnd[0]").sendVKey(8)  # F8 Execute
            time.sleep(2)

            # Nhập tham số Filter
            print("   Entering Filter Criteria...")
            try:
                self.session.findById("wnd[0]/usr/txtSP$00001-LOW").text = "LEARN-717"
                self.session.findById("wnd[0]").sendVKey(8)  # F8 chạy tiếp
            except:
                self.session.findById("wnd[0]").sendVKey(8)

            time.sleep(5)  # Đợi kết quả

            # 5. Export dữ liệu
            print("   Step 5: Exporting to Excel...")
            # Sử dụng VKey hoặc Shell để Export
            shell = self.session.findById("wnd[0]/usr/cntlCONTAINER/shellcont/shell")
            shell.pressToolbarContextButton("&MB_EXPORT")
            shell.selectContextMenuItem("&XXL")
            time.sleep(2)

            # Xác nhận Format (nhấn Enter ở cửa sổ wnd[1])
            self.session.findById("wnd[1]").sendVKey(0)
            time.sleep(3)

            # 6. Lưu file
            print("   Step 6: Saving file...")
            # Nhập đường dẫn và tên file
            self.session.findById("wnd[1]/usr/ctxtDY_PATH").text = self.save_directory
            self.session.findById("wnd[1]/usr/ctxtDY_FILENAME").text = "sap_data.xlsx"
            self.session.findById("wnd[1]").sendVKey(0)  # Nhấn Save (Enter)
            time.sleep(2)

            # Xóa file cũ nếu tồn tại
            if os.path.exists(save_path):
                print("   ⚠️ File exists, deleting...")
                os.remove(save_path)
                time.sleep(1)

            # Nhấn Save
            self.session.findById("wnd[1]/tbar[0]/btn[0]").press()
            print("   ✅ File saved")

            print(f"✅ Thành công! File lưu tại: {save_path}")
            return save_path

        except Exception as e:
            print(f"❌ Lỗi: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    collector = SAPDataCollector(user_name="TEST", save_directory=os.path.join(os.path.expanduser("~"), "Downloads"))
    collector.quick_collect()