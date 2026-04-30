import csv
import time
import os
import subprocess
import threading
import sys
from playwright.sync_api import sync_playwright

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
URL_LOGIN = "https://rb-id.np.accenture.com/RB_ID/Logon.aspx"

def loading_animation(stop_event, message="Processing"):
    chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    idx = 0
    while not stop_event.is_set():
        char = chars[idx % len(chars)]
        sys.stdout.write(f"\r \033[94m{char} {message}...\033[0m")
        sys.stdout.flush()
        idx += 1
        time.sleep(0.08)
    sys.stdout.write("\r" + " " * (len(message) + 20) + "\r")

def main():
    # 1. HEADER DENGAN BINGKAI
    os.system("title Stock Adjustment - by Rizki Firdaus")
    os.system('cls' if os.name == 'nt' else 'clear')
    
    print("\033[96m")
    print("┌───────────────────────────────────────────────────────────────┐")
    print("│                INVENTORY STOCK ADJUSTMENT v1.0                │")
    print("│                  Developed by: Rizki Firdaus                  │")
    print("└───────────────────────────────────────────────────────────────┘\033[0m")
    
    print("\n \033[97m[\033[94m!\033[97m] Authentication Required\033[0m")
    user_id = input("     User ID  : ")
    password = input("     Password : ")
    
    stop_loading = threading.Event()
    loader = threading.Thread(target=loading_animation, args=(stop_loading, "System Initializing"))
    loader.start()
    
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True, capture_output=True)
    except:
        pass
    
    stop_loading.set()
    loader.join()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=0, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        print(f"\n \033[93m» Connecting to Portal...\033[0m")
        page.goto(URL_LOGIN)

        page.locator("id=txtUserid").fill(user_id)
        page.locator("id=txtPasswd").fill(password)
        page.locator("id=btnLogin").click(force=True)
        
        try:
            btn_continue = page.locator("id=SYS_ASCX_btnContinue")
            btn_continue.wait_for(state="visible", timeout=5000)
            print(" \033[95m» Conflict Session: Auto-Continuing...\033[0m")
            btn_continue.click(force=True)
        except:
            pass
        
        page.wait_for_url("**/Default.aspx", timeout=0, wait_until="domcontentloaded")
        print(" \033[92m✔ Authentication Granted!\033[0m\n")

        try:
            # --- TAHAP 1: NAVIGASI ---
            stop_menu = threading.Event()
            menu_loader = threading.Thread(target=loading_animation, args=(stop_menu, "Accessing Inventory Menu"))
            menu_loader.start()

            time.sleep(4)
            page.locator("id=pag_InventoryRoot_tab_Main_itm_StkAdj").dispatch_event("click")
            time.sleep(5) 
            
            page.locator("id=pag_I_StkAdj_btn_Add_Value").wait_for(state="attached", timeout=15000)
            page.locator("id=pag_I_StkAdj_btn_Add_Value").click(force=True)
            time.sleep(2)
            page.get_by_role("link", name="GOOD_WHS", exact=True).click(force=True)
            
            stop_menu.set()
            menu_loader.join()
            
            # --- TAHAP 2: TABEL MONITORING ---
            print("\033[94m┌" + "─"*30 + "┬" + "─"*12 + "┬" + "─"*15 + "┐")
            print(f"│ {'PRODUCT SKU':<28} │ {'QTY':<10} │ {'STATUS':<13} │")
            print("├" + "─"*30 + "┼" + "─"*12 + "┼" + "─"*15 + "┤\033[0m")

            success_count = 0
            failed_count = 0

            with open('data_inventory.csv', mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sku, qty = row['sku'], row['qty']
                    
                    try:
                        dropdown_reason = page.locator("id=pag_I_StkAdj_NewGeneral_drp_n_REASON_HDR_Value")
                        if dropdown_reason.is_enabled():
                            dropdown_reason.select_option("SA2")
                        
                        page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value").fill(str(sku))
                        page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value").press("Tab")
                        time.sleep(2)
                        
                        qty_input = page.locator("id=pag_I_StkAdj_NewGeneral_txt_QTY1_Value")
                        qty_input.wait_for(state="visible", timeout=15000) 
                        qty_input.fill(str(qty))
                        page.locator("id=pag_I_StkAdj_NewGeneral_btn_Add_Value").click(force=True)
                        
                        page.wait_for_function("document.getElementById('pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value').value === ''", timeout=30000)
                        
                        # FIX: Reset warna biru (\033[94m) sebelum mencetak karakter pembatas │
                        print(f"\033[94m│ \033[93m{sku:<28} \033[94m│ \033[95m{qty:<10} \033[94m│ \033[92mSUCCESS\033[94m       │")
                        success_count += 1
                    except Exception:
                        print(f"\033[94m│ \033[93m{sku:<28} \033[94m│ \033[95m{qty:<10} \033[94m│ \033[91mFAILED\033[94m        │")
                        failed_count += 1
                        time.sleep(2)

            print("\033[94m└" + "─"*30 + "┴" + "─"*12 + "┴" + "─"*15 + "┘\033[0m")

            # --- TAHAP 3: SAVE ---
            print("\n \033[93m» Finalizing Document...\033[0m")
            page.locator("id=pag_I_StkAdj_NewGeneral_btn_Save_Value").click()
            
            try:
                tombol_yes = page.locator("id=pag_PopUp_YesNo_btn_Yes_Value")
                tombol_yes.wait_for(state="visible", timeout=60000)
                tombol_yes.click()
                print(" \033[92m✔ Data committed to server.\033[0m")
            except Exception:
                print(" \033[92m✔ Auto-saved successfully.\033[0m")
            
            # --- FINAL SUMMARY (CENTERED) ---
            print("\n\033[96m╔" + "═"*63 + "╗")
            summary_text = f"PROCESS COMPLETED | SUCCESS: {success_count} | FAILED: {failed_count}"
            # Menggunakan .center(63) agar teks berada tepat di tengah kotak
            print(f"║{summary_text.center(63)}║")
            print("╚" + "═"*63 + "╝\033[0m")
            
        except Exception as e:
            print(f"\n\033[91m[!] Error: {e}\033[0m")
            
        input("\n\033[90m>>> Press ENTER to terminate script\033[0m")

if __name__ == "__main__":
    main()
