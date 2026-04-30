import csv
import time
import os
import subprocess
import threading
import sys
from playwright.sync_api import sync_playwright

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

# Target URL awal
URL_LOGIN = "https://rb-id.np.accenture.com/RB_ID/Logon.aspx"

# Fungsi untuk animasi loading di terminal
def loading_animation(stop_event, message="Processing"):
    chars = ["|", "/", "-", "\\"]
    idx = 0
    while not stop_event.is_set():
        sys.stdout.write(f"\r[*] {message} {chars[idx % len(chars)]}")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.1)
    sys.stdout.write("\r" + " " * (len(message) + 10) + "\r") # Bersihkan baris loading

def main():
    # 1. HEADER & INPUT (Terminal Only)
    os.system("title Stock Adjustment - by Rizki Firdaus")
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("-" * 65)
    print("           INVENTORY STOCK ADJUSTMENT")
    print("           Created by: Rizki Firdaus")
    print("-" * 65)
    
    print("\n[!] Silakan masukkan kredensial Accenture NewsPage Anda:")
    user_id = input("    User ID  : ")
    password = input("    Password : ")
    
    # 2. PROSES INISIALISASI (Dengan Animasi)
    stop_loading = threading.Event()
    loader = threading.Thread(target=loading_animation, args=(stop_loading, "Menyiapkan sistem dan browser"))
    loader.start()
    
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True, capture_output=True)
    except:
        pass
    
    stop_loading.set() # Matikan animasi
    loader.join()
    print("[+] Membuka browser...")

    # 3. BROWSER MUNCUL DI SINI
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=0, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        page.goto(URL_LOGIN)

        # Proses Login Otomatis
        page.locator("id=txtUserid").fill(user_id)
        page.locator("id=txtPasswd").fill(password)
        page.locator("id=btnLogin").click(force=True)
        
        # Logika Handle Sesi Ganda (Tombol Continue)
        try:
            btn_continue = page.locator("id=SYS_ASCX_btnContinue")
            btn_continue.wait_for(state="visible", timeout=5000)
            print("[!] Sesi aktif terdeteksi. Mengklik Continue...")
            btn_continue.click(force=True)
        except:
            pass
        
        page.wait_for_url("**/Default.aspx", timeout=0, wait_until="domcontentloaded")
        print("[+] Login Detected, Start Automation\n")

        try:
            # =========================================================
            # TAHAP 1: BUKA MENU & BUAT DOKUMEN BARU
            # =========================================================
            # Jalankan animasi lagi saat nunggu menu terbuka
            stop_menu = threading.Event()
            menu_loader = threading.Thread(target=loading_animation, args=(stop_menu, "Mengakses Menu Stock Adjustment"))
            menu_loader.start()

            time.sleep(4)
            page.locator("id=pag_InventoryRoot_tab_Main_itm_StkAdj").dispatch_event("click")
            time.sleep(5) 
            
            tombol_add = page.locator("id=pag_I_StkAdj_btn_Add_Value")
            tombol_add.wait_for(state="attached", timeout=15000)
            tombol_add.click(force=True)
            time.sleep(2)
            page.get_by_role("link", name="GOOD_WHS", exact=True).click(force=True)
            
            stop_menu.set()
            menu_loader.join()
            print("[+] Form Stock Adjustment Siap.")
            
            # =========================================================
            # TAHAP 2: LOOPING INPUT BARANG DARI CSV
            # =========================================================
            print("\n[*] Start Input SKU from CSV to Table...")
            with open('data_inventory.csv', mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    sku = row['sku']
                    qty = row['qty']
                    
                    # Animasi kecil per item
                    sys.stdout.write(f"  -> Processing SKU: {sku}...")
                    sys.stdout.flush()
                    
                    dropdown_reason = page.locator("id=pag_I_StkAdj_NewGeneral_drp_n_REASON_HDR_Value")
                    if dropdown_reason.is_enabled():
                        dropdown_reason.select_option("SA2")
                        time.sleep(0.5)
                    
                    kotak_sku = page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value")
                    kotak_sku.fill(str(sku))
                    kotak_sku.press("Tab")
                    time.sleep(2) 
                    
                    try:
                        qty_input = page.locator("id=pag_I_StkAdj_NewGeneral_txt_QTY1_Value")
                        qty_input.wait_for(state="visible", timeout=15000) 
                        qty_input.fill(str(qty))
                        
                        page.locator("id=pag_I_StkAdj_NewGeneral_btn_Add_Value").click(force=True)
                        page.wait_for_function("document.getElementById('pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value').value === ''", timeout=30000)
                        
                        sys.stdout.write(" [OK]\n")
                    except Exception:
                        sys.stdout.write(" [FAILED]\n")
                        time.sleep(2)
            
            # =========================================================
            # TAHAP 3: SAVE DOKUMEN 
            # =========================================================
            print("\n[*] Preparing Save...")
            page.locator("id=pag_I_StkAdj_NewGeneral_btn_Save_Value").click()
            
            try:
                tombol_yes = page.locator("id=pag_PopUp_YesNo_btn_Yes_Value")
                tombol_yes.wait_for(state="visible", timeout=60000)
                tombol_yes.click()
                print("  -> [!] Popup YES diklik.")
                time.sleep(3) 
            except Exception:
                print("  -> [V] Berhasil simpan tanpa popup.")
            
            print("\n[+] Seluruh data berhasil disimpan.")
            
        except Exception as e:
            print(f"\n[!] Terjadi kesalahan: {e}")
            
        print("\n[!] Task Done! Selesai.")
        input(">>> Hit ENTER to Close ")

if __name__ == "__main__":
    main()
