import csv
import time
import os
import subprocess
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
from playwright.sync_api import sync_playwright

# Target URL awal
URL_LOGIN = "https://rb-id.np.accenture.com/RB_ID/Logon.aspx"

def main():
    try:
    # Memaksa install chromium jika tidak ditemukan
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except:
        pass
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=0)
        context = browser.new_context()
        page = context.new_page()

        # =========================================================
        # HEADER MINIMALIS - CREATED BY RIZKI FIRDAUS
        # =========================================================
        os.system("title Stock Adjustment - by Rizki Firdaus")
    
        os.system('cls' if os.name == 'nt' else 'clear')
        print("-" * 65)
        print("           INVENTORY STOCK ADJUSTMENT")
        print("           Created by: Rizki Firdaus")
        print("-" * 65)
        print("\n[*] Membuka browser... Silakan login secara manual.")
        page.goto(URL_LOGIN)
        page.wait_for_url("**/Default.aspx", timeout=0, wait_until="domcontentloaded")
        print("[+] Login Detected, Start Automation\n")

        try:
            # =========================================================
            # TAHAP 1: BUKA MENU & BUAT DOKUMEN BARU (Hanya 1 kali)
            # =========================================================
            print("[*] Create Stock Adjustment")
            
            # Jeda sebentar agar server ASP.NET siap menerima perintah
            time.sleep(4)
            
            # A. Tembak event klik langsung tanpa peduli menu terlihat atau tidak
            print("  -> Call Menu Stock Adjustment...")
            page.locator("id=pag_InventoryRoot_tab_Main_itm_StkAdj").dispatch_event("click")
            
            # Tunggu 5 detik karena server sedang memproses perpindahan halaman (loading)
            time.sleep(5) 
            
            # B. Klik tombol New/Add Dokumen 
            # (Gunakan wait_for agar script sabar menunggu jika loading servernya agak lama)
            tombol_add = page.locator("id=pag_I_StkAdj_btn_Add_Value")
            tombol_add.wait_for(state="attached", timeout=15000)
            tombol_add.click(force=True)
            time.sleep(2)
            
            # C. Pilih Warehouse "GOOD_WHS"
            page.get_by_role("link", name="GOOD_WHS", exact=True).click(force=True)
            time.sleep(2)
            
            
            # =========================================================
            # TAHAP 2: LOOPING INPUT BARANG CEPAT (Dari data_inventory.csv)
            # =========================================================
            print("\n[*] Start Input SKU from CSV to Table...")
            with open('data_inventory.csv', mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    sku = row['sku']
                    qty = row['qty']
                    print(f"  -> Input SKU: {sku} | QTY: {qty}")
                    
                    # 1. Pilih Alasan / Reason
                    dropdown_reason = page.locator("id=pag_I_StkAdj_NewGeneral_drp_n_REASON_HDR_Value")
                    if dropdown_reason.is_enabled():
                        dropdown_reason.select_option("SA2")
                        time.sleep(0.5)
                    
                    # 2. Masukkan Kode Produk dan Tab
                    kotak_sku = page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value")
                    kotak_sku.fill(str(sku))
                    kotak_sku.press("Tab")
                    time.sleep(2) # Waktu untuk server menarik nama barang
                    
                    # Menggunakan Try-Except untuk berjaga-jaga jika SKU tidak valid
                    try:
                        # 3. Tunggu form QTY siap, lalu masukkan angkanya
                        qty_input = page.locator("id=pag_I_StkAdj_NewGeneral_txt_QTY1_Value")
                        qty_input.wait_for(state="visible", timeout=15000) 
                        qty_input.fill(str(qty))
                        
                        # 4. Klik Add untuk menurunkan barang ke Grid
                        page.locator("id=pag_I_StkAdj_NewGeneral_btn_Add_Value").click(force=True)
                        
                        # 5. SMART WAIT (Jeda Pintar) - Menunggu loading ASP.NET selesai
                        # Robot akan menunggu sampai kotak SKU kembali menjadi KOSONG
                        page.wait_for_function("document.getElementById('pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value').value === ''", timeout=30000)
                        
                        time.sleep(0.5) # Jeda napas milidetik sebelum looping ke barang selanjutnya
                        
                    except Exception:
                        print(f"  -> [!] GAGAL memproses SKU {sku}. Mungkin SKU tidak terdaftar atau server sangat lambat.")
                        # Robot akan membiarkannya dan lanjut ke SKU berikutnya di dalam CSV
                        time.sleep(2)
            

            # =========================================================
            # TAHAP 3: SAVE DOKUMEN 
            # =========================================================
            print("\n[*] Preparing Save...")
            
            # 1. Klik tombol Save
            page.locator("id=pag_I_StkAdj_NewGeneral_btn_Save_Value").click()
            print("  -> Click Save Executed, Waiting Server Response...")
            
            # 2. Logika "JIKA" muncul popup
            try:
                # Targetkan ID tombol Yes yang Anda temukan
                tombol_yes = page.locator("id=pag_PopUp_YesNo_btn_Yes_Value")
                
                # Tunggu maksimal 60 detik. Jika elemen ini muncul, lanjut ke baris bawahnya
                tombol_yes.wait_for(state="visible", timeout=60000)
                
                # Eksekusi klik
                tombol_yes.click()
                print("  -> [!] Popup muncul. Tombol YES berhasil diklik.")
                time.sleep(3) # Tunggu database selesai menyimpan
                
            except Exception:
                # Jika dalam 3 detik popup tidak muncul, anggap aman dan biarkan lewat
                print("  -> [V] Tidak ada popup peringatan.")
                time.sleep(2)
            
            print("\n[+] Seluruh data berhasil disimpan.")
            
        except Exception as e:
            print(f"\n[!] Terjadi kesalahan: {e}")
            
        # =========================================================
        # TAHAP 4: TAHAN BROWSER AGAR TIDAK AUTO-CLOSE
        # =========================================================
        print("\n[!] Task Done! Holding Browser Try to not close Automatically")
        input(">>> Hit ENTER if Done ")
        
        # Perintah ini diabaikan sampai tombol Enter ditekan
        # browser.close() 

if __name__ == "__main__":
    main()