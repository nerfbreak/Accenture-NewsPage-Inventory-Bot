import csv
import time
import os
import subprocess
import threading
import sys
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

# ─── Constants ────────────────────────────────────────────────────────────────
URL_LOGIN   = "https://rb-id.np.accenture.com/RB_ID/Logon.aspx"
CSV_FILE    = "data_inventory.csv"
REASON_CODE = "SA2"
WAREHOUSE   = "GOOD_WHS"
TIMEOUT_MS  = 30_000

GLOBAL_START_TIME = 0.0  # Ditambahkan untuk kalkulasi waktu berjalan

# ─── ANSI — Blue-Dominant Palette ────────────────────────────────────────────
R      = "\033[0m"
B      = "\033[1m"

AZURE  = "\033[38;5;39m"    # Bright azure
SKY    = "\033[38;5;81m"    # Sky blue
DENIM  = "\033[38;5;33m"    # Denim blue
FROST  = "\033[38;5;153m"   # Frost blue
ICE    = "\033[38;5;195m"   # Ice blue
VIOLET = "\033[38;5;147m"   # Soft violet
GHOST  = "\033[38;5;238m"   # Dark charcoal
MIST   = "\033[38;5;246m"   # Mist gray
WHITE  = "\033[38;5;255m"   # White
MINT   = "\033[38;5;120m"   # Mint green
CORAL  = "\033[38;5;203m"   # Coral
GOLD   = "\033[38;5;220m"   # Gold

_WAVE = [AZURE, SKY, FROST, SKY, AZURE, DENIM, FROST, SKY]
ANSI_ESCAPE = re.compile(r'\033\[[0-9;]*[a-zA-Z]')

# ─── Layout Formatting Helpers ────────────────────────────────────────────────
def strip_ansi(text: str) -> str:
    """Menghapus kode ANSI agar hitungan panjang karakter (width) akurat."""
    return ANSI_ESCAPE.sub('', text)

def print_aligned(left_str: str, right_str: str, total_width: int = 75):
    """Mencetak log dengan meratakan ujung akhir right_str ke batas total_width."""
    vis_left = len(strip_ansi(left_str))
    vis_right = len(strip_ansi(right_str))
    pad_len = total_width - (vis_left + vis_right)
    pad = " " * pad_len if pad_len > 0 else " "
    print(f"{left_str}{pad}{right_str}")

# ─── Animation Helpers ────────────────────────────────────────────────────────
def typewriter(text: str, color: str = "", delay: float = 0.022):
    for ch in text:
        sys.stdout.write(f"{color}{ch}{R}")
        sys.stdout.flush()
        time.sleep(delay)

def flash_line(text: str, color: str, flashes: int = 2, interval: float = 0.07):
    for _ in range(flashes):
        sys.stdout.write(f"\r  {color}{B}{text}{R}")
        sys.stdout.flush()
        time.sleep(interval)
        sys.stdout.write(f"\r  {GHOST}{text}{R}")
        sys.stdout.flush()
        time.sleep(interval)
    sys.stdout.write(f"\r  {color}{B}{text}{R}\n")
    sys.stdout.flush()

# ─── Log Primitives ───────────────────────────────────────────────────────────
def _ts_formatted() -> str:
    """Mengembalikan timestamp + waktu berjalan (Elapsed Time) dengan format m/s"""
    current_time = time.strftime('%H:%M:%S')
    if GLOBAL_START_TIME > 0:
        elapsed = int(time.time() - GLOBAL_START_TIME)
        mins, secs = divmod(elapsed, 60)
        if mins > 0:
            return f"{current_time} [{mins}m {secs}s]"
        return f"{current_time} [{secs}s]"
    return f"{current_time} [0s]"

def log(tag: str, color: str, msg: str):
    left_str = f"  {color}{B}{tag:<6}{R}  {msg}"
    right_str = f"{GHOST}{_ts_formatted()}{R}"
    print_aligned(left_str, right_str)

def log_ok(msg: str):      log("Ok",     MINT,  msg)
def log_warn(msg: str):    log("Warn",    GOLD,  msg)
def log_error(msg: str):   log("Error",   CORAL, msg)
def log_run(msg: str):     log("Run",     DENIM, msg)
def log_save(msg: str):    log("Save",    AZURE, msg)
def log_blank():           print()

def log_section(title: str):
    sys.stdout.write(f"\n  {AZURE}{B}◆{R}  ")
    sys.stdout.flush()
    typewriter(title.upper(), SKY, delay=0.03)
    
    # Rata kanan sempurna untuk section divider
    right_str = f"{GHOST}{_ts_formatted()}{R}"
    vis_left = 5 + len(title)  # "  ◆  " + title
    vis_right = len(strip_ansi(right_str))
    pad_len = 75 - (vis_left + vis_right)
    pad = " " * pad_len if pad_len > 0 else " "
    
    sys.stdout.write(f"{pad}{right_str}\n")
    sys.stdout.flush()
    log_blank()

# ─── Spinner ─────────────────────────────────────────────────────────────────
class Spinner:
    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str):
        self.message = message
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        for i in range(sys.maxsize):
            if self._stop.is_set():
                break
            frame = self._FRAMES[i % len(self._FRAMES)]
            color = _WAVE[i % len(_WAVE)]
            
            left_str = f"  {DENIM}{B}{'Run':<6}{R}  {color}{frame}{R}  {MIST}{self.message}{R}"
            right_str = f"{GHOST}{_ts_formatted()}{R}"
            
            vis_left = len(strip_ansi(left_str))
            vis_right = len(strip_ansi(right_str))
            pad_len = 75 - (vis_left + vis_right)
            pad = " " * pad_len if pad_len > 0 else " "
            
            sys.stdout.write(f"\r{left_str}{pad}{right_str}")
            sys.stdout.flush()
            time.sleep(0.08)
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stop.set()
        self._thread.join()

# ─── Password Input ───────────────────────────────────────────────────────────
def input_password() -> str:
    chars = []
    if os.name == "nt":
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch in ("\r", "\n"): break
            elif ch == "\x03": raise KeyboardInterrupt
            elif ch in ("\x08", "\x7f"):
                if chars:
                    chars.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
            else:
                chars.append(ch)
                sys.stdout.write(f"{AZURE}*{R}")
                sys.stdout.flush()
    else:
        import termios, tty
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while True:
                ch = sys.stdin.read(1)
                if ch in ("\r", "\n"): break
                elif ch == "\x03": raise KeyboardInterrupt
                elif ch in ("\x7f", "\x08"):
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                else:
                    chars.append(ch)
                    sys.stdout.write(f"{AZURE}*{R}")
                    sys.stdout.flush()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return "".join(chars)

# ─── Header ──────────────────────────────────────────────────────────────────
def print_header():
    os.system("title Stock Adjustment - by Rizki Firdaus")
    os.system("cls" if os.name == "nt" else "clear")
    print()
    sys.stdout.write("  ")
    typewriter("INVENTORY STOCK ADJUSTMENT", DENIM, delay=0.025)
    sys.stdout.write(f"  {GHOST}v1.0{R}\n")
    sys.stdout.flush()
    sys.stdout.write(f"  {GHOST}")
    typewriter("Automated Stock Tool  ·  By Kopi Mang Toni", VIOLET, delay=0.012)
    sys.stdout.write(f"{R}\n\n")
    sys.stdout.flush()

# ─── Playwright Setup ─────────────────────────────────────────────────────────
def ensure_playwright():
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True, capture_output=True)
    except: pass

# ─── Browser Actions ──────────────────────────────────────────────────────────
def login(page, user_id: str, password: str):
    log_run("Launching browser session")
    page.goto(URL_LOGIN, wait_until="domcontentloaded")
    page.locator("id=txtUserid").fill(user_id)
    page.locator("id=txtPasswd").fill(password)
    page.locator("id=btnLogin").click(force=True)
    try:
        btn = page.locator("id=SYS_ASCX_btnContinue")
        btn.wait_for(state="visible", timeout=5_000)
        log_warn("Conflict session detected — resuming")
        btn.click(force=True)
    except: pass
    page.wait_for_url("**/Default.aspx", timeout=0, wait_until="domcontentloaded")
    log_ok(f"Authenticated  {MIST}as{R}  {WHITE}{B}{user_id}{R}")

def navigate_to_stock_adjustment(page):
    with Spinner("Opening stock adjustment form"):
        page.locator("id=pag_InventoryRoot_tab_Main_itm_StkAdj").dispatch_event("click")
        add_btn = page.locator("id=pag_I_StkAdj_btn_Add_Value")
        add_btn.wait_for(state="attached", timeout=TIMEOUT_MS)
        add_btn.click(force=True)
        page.get_by_role("link", name=WAREHOUSE, exact=True).wait_for(state="visible", timeout=TIMEOUT_MS)
        page.get_by_role("link", name=WAREHOUSE, exact=True).click(force=True)
        page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value").wait_for(state="visible", timeout=TIMEOUT_MS)
    log_ok(f"Form Ready  {MIST}·{R}  Warehouse  {WHITE}{B}{WAREHOUSE}{R}")

def set_reason_once(page):
    dropdown = page.locator("id=pag_I_StkAdj_NewGeneral_drp_n_REASON_HDR_Value")
    if dropdown.is_enabled():
        dropdown.select_option(REASON_CODE)

def process_row(page, sku: str, qty: str) -> bool:
    sku_input = page.locator("id=pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value")
    sku_input.fill(sku)
    sku_input.press("Tab")
    qty_input = page.locator("id=pag_I_StkAdj_NewGeneral_txt_QTY1_Value")
    qty_input.wait_for(state="visible", timeout=TIMEOUT_MS)
    qty_input.fill(qty)
    page.locator("id=pag_I_StkAdj_NewGeneral_btn_Add_Value").click(force=True)
    page.wait_for_function("document.getElementById('pag_I_StkAdj_NewGeneral_sel_PRD_CD_Value').value === ''", timeout=TIMEOUT_MS)
    return True

def process_csv(page) -> tuple[int, int]:
    set_reason_once(page)
    success_count = failed_count = 0

    with open(CSV_FILE, mode="r", encoding="utf-8") as f:
        for idx, row in enumerate(csv.DictReader(f), start=1):
            sku, qty = row["sku"].strip(), row["qty"].strip()
            try:
                process_row(page, sku, qty)
                ok = True
                success_count += 1
            except Exception:
                ok = False
                failed_count += 1

            s_color = MINT  if ok else CORAL
            s_text  = "ok"  if ok else "failed"
            num_raw = f"{idx:>2}."

            left_str = (
                f"  {GHOST}{num_raw:<6}{R}"
                f"{ICE}{B}{sku:<20}{R}"
                f"{VIOLET}{qty:<10}{R}"
                f"{s_color}{B}{s_text:<15}{R}"
            )
            right_str = f"{GHOST}{_ts_formatted()}{R}"
            print_aligned(left_str, right_str)

    log_blank()
    return success_count, failed_count

def save_document(page):
    log_save("Committing document to server...")
    page.locator("id=pag_I_StkAdj_NewGeneral_btn_Save_Value").click()
    try:
        yes_btn = page.locator("id=pag_PopUp_YesNo_btn_Yes_Value")
        yes_btn.wait_for(state="visible", timeout=60_000)
        yes_btn.click()
        log_ok("Document saved successfully")
    except:
        log_ok("Auto-saved")

def print_summary(success_count: int, failed_count: int):
    total = success_count + failed_count
    elapsed = int(time.time() - GLOBAL_START_TIME)
    mins, secs = divmod(elapsed, 60)
    time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"

    log_blank()
    sys.stdout.write(f"  {AZURE}{B}◆{R}  ")
    sys.stdout.flush()
    typewriter("PROCESS COMPLETE", SKY, delay=0.03)
    
    right_str = f"{GHOST}{_ts_formatted()}{R}"
    vis_left = 5 + 16 # "  ◆  " + "PROCESS COMPLETE"
    vis_right = len(strip_ansi(right_str))
    pad_len = 75 - (vis_left + vis_right)
    pad = " " * pad_len if pad_len > 0 else " "
    sys.stdout.write(f"{pad}{right_str}\n")
    sys.stdout.flush()

    log_blank()
    f_color = CORAL if failed_count else GHOST
    
    left_str = (
        f"  {GHOST}{'':>2}{R}  "
        f"{MIST}total {WHITE}{B}{total:<4}{R}   "
        f"{MIST}success {MINT}{B}{success_count:<4}{R}   "
        f"{MIST}failed {f_color}{B}{failed_count:<4}{R}"
    )
    right_str = f"{MIST}time {WHITE}{B}{time_str}{R}"
    print_aligned(left_str, right_str)
    log_blank()

# ─── Entry Point ──────────────────────────────────────────────────────────────
def main():
    global GLOBAL_START_TIME
    
    print_header()
    PREFIX = 12
    sys.stdout.write(f"  {MIST}User ID  :   {R}\n  {MIST}Password :   {R}\n")
    sys.stdout.flush()
    sys.stdout.write(f"\033[2A\033[{PREFIX}C")
    sys.stdout.flush()
    user_id  = input()
    sys.stdout.write(f"\033[{PREFIX}C")
    sys.stdout.flush()
    password = input_password()
    log_blank()

    # Mulai timer tepat setelah input password selesai
    GLOBAL_START_TIME = time.time()

    with Spinner("System initializing"):
        ensure_playwright()

    log_blank()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(no_viewport=True)
        page    = context.new_page()
        try:
            log_section("authentication")
            login(page, user_id, password)
            log_section("navigation")
            navigate_to_stock_adjustment(page)
            log_section("sku stream")
            success_count, failed_count = process_csv(page)
            save_document(page)
            print_summary(success_count, failed_count)
        except Exception as e:
            log_blank()
            log_error(str(e))
            log_blank()
        finally:
            browser.close()
    input(f"  {GHOST}press enter to exit{R}\n")

if __name__ == "__main__":
    main()
