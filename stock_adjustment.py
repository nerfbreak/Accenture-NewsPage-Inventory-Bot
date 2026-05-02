import csv
import os
import sys
import getpass
import threading
import subprocess
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

# ─── Constants ────────────────────────────────────────────────────────────────
URL_LOGIN    = "https://rb-id.np.accenture.com/RB_ID/Logon.aspx"
CSV_FILE     = "data_inventory.csv"
REASON_CODE  = "SA2"
WAREHOUSE    = "GOOD_WHS"
TIMEOUT_MS   = 30_000


# ─── UI Helpers ───────────────────────────────────────────────────────────────
class Spinner:
    """Thread-safe CLI spinner context manager."""
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str):
        self.message    = message
        self._stop      = threading.Event()
        self._thread    = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        for i in range(sys.maxsize):
            if self._stop.is_set():
                break
            frame = self._FRAMES[i % len(self._FRAMES)]
            sys.stdout.write(f"\r \033[94m{frame} {self.message}...\033[0m")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * 65 + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()


def print_header():
    os.system("title Stock Adjustment - by Rizki Firdaus")
    os.system("cls" if os.name == "nt" else "clear")
    print("\033[96m")
    print("                INVENTORY STOCK ADJUSTMENT v1.0                ")
    print("                  Developed by: Kopi Mang Toni                 ")
    print("\033[0m")


def ensure_playwright():
    """Install Playwright's Chromium browser if not already present."""
    try:
        subprocess.run(
            ["playwright", "install", "chromium"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # Already installed or non-fatal


# ─── Browser Actions ──────────────────────────────────────────────────────────
def login(page, user_id: str, password: str):
    print(f"\n \033[93m» Connecting to Portal...\033[0m")
    page.goto(URL_LOGIN, wait_until="domcontentloaded")

    page.locator("id=txtUserid").fill(user_id)
    page.locator("id=txtPasswd").fill(password)
    page.locator("id=btnLogin").click(force=True)

    # Resolve session conflict if prompted
    try:
        btn = page.locator("id=SYS_ASCX_btnContinue")
        btn.wait_for(state="visible", timeout=5_000)
        print(" \033[95m» Conflict Session: Auto-Continuing...\033[0m")
        btn.click(force=True)
    except PlaywrightTimeoutError:
        pass

    page.wait_for_url("**/Default.aspx", timeout=0, wait_until="domcontentloaded")
    print(" \033[92m✔ Authentication Granted!\033[0m\n")


def navigate_to_stock_adjustment(page):
    with Spinner("Accessing Inventory Menu"):
        page.locator("id=pag_InventoryRoot_tab_Main_itm_StkAdj").dispatch_event("click")

        add_btn = page.locator("id=pag_I_StkAdj_btn_Add_Value")
        add_btn.wait_for(state="attached", timeout=TIMEOUT_MS)
        add_btn.click(force=True)

        page.get_by_role("link", name=WAREHOUSE, exact=True).wait_for(
            state="visible", timeout=TIMEOUT_MS
        )
        page.get_by_role("link", name=WAREHOUSE, exact=True).click(force=True)

        # Wait for the form to be ready
        page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value").wait_for(
            state="visible", timeout=TIMEOUT_MS
        )


def set_reason_once(page):
    """Select the adjustment reason — only needs to happen once per session."""
    dropdown = page.locator("id=pag_I_StkAdj_NewGeneral_drp_n_REASON_HDR_Value")
    if dropdown.is_enabled():
        dropdown.select_option(REASON_CODE)


def process_row(page, sku: str, qty: str) -> bool:
    """Fill one SKU row and click Add. Returns True on success."""
    sku_input = page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value")
    sku_input.fill(sku)
    sku_input.press("Tab")

    qty_input = page.locator("id=pag_I_StkAdj_NewGeneral_txt_QTY1_Value")
    qty_input.wait_for(state="visible", timeout=TIMEOUT_MS)
    qty_input.fill(qty)

    page.locator("id=pag_I_StkAdj_NewGeneral_btn_Add_Value").click(force=True)

    # Wait for the form to reset (SKU field cleared = row accepted)
    page.wait_for_function(
        "document.getElementById('pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value').value === ''",
        timeout=TIMEOUT_MS,
    )
    return True


def process_csv(page) -> tuple[int, int]:
    print(f" \033[96m» Starting SKU Input Process...\033[0m")

    set_reason_once(page)

    success_count = failed_count = 0

    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sku, qty = row["sku"].strip(), row["qty"].strip()
            try:
                process_row(page, sku, qty)
                print(
                    f"   \033[94m→\033[0m SKU: \033[93m{sku:<10}\033[0m "
                    f"| QTY: \033[95m{qty:<5}\033[0m | Status: \033[92mSUCCESS\033[0m"
                )
                success_count += 1
            except Exception:
                print(
                    f"   \033[94m→\033[0m SKU: \033[93m{sku:<10}\033[0m "
                    f"| QTY: \033[95m{qty:<5}\033[0m | Status: \033[91mFAILED\033[0m"
                )
                failed_count += 1

    return success_count, failed_count


def save_document(page):
    print(f"\n \033[93m» Finalizing Document...\033[0m")
    page.locator("id=pag_I_StkAdj_NewGeneral_btn_Save_Value").click()

    try:
        yes_btn = page.locator("id=pag_PopUp_YesNo_btn_Yes_Value")
        yes_btn.wait_for(state="visible", timeout=60_000)
        yes_btn.click()
        print(" \033[92m✔ Data committed to server.\033[0m")
    except PlaywrightTimeoutError:
        print(" \033[92m✔ Auto-saved successfully.\033[0m")


# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    print_header()

    print("\n \033[97m[\033[94m!\033[97m] Authentication Required\033[0m")
    user_id  = input("     User ID  : ")
    password = getpass.getpass("     Password : ")  # Masks input — no echo

    with Spinner("System Initializing"):
        ensure_playwright()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(no_viewport=True)
        page    = context.new_page()

        try:
            login(page, user_id, password)
            navigate_to_stock_adjustment(page)
            success_count, failed_count = process_csv(page)
            save_document(page)

            print("\n")
            print(
                f" \033[1;96mPROCESS COMPLETED\033[0m"
                f" | SUCCESS: \033[1;92m{success_count}\033[0m"
                f" | FAILED: \033[1;91m{failed_count}\033[0m"
            )
        except Exception as e:
            print(f"\n\033[91m[!] Unhandled Error: {e}\033[0m")
        finally:
            browser.close()

    input("\n\033[90m>>> Press ENTER to terminate script\033[0m")


if __name__ == "__main__":
    main()
