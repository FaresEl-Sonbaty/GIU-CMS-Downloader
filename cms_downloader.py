#!/usr/bin/env python3
"""
GIU CMS Course Downloader — Click-to-launch course file downloader.

Downloads all course files from the GIU CMS portal, categorizes them
(Lectures, PA, Labs, Tutorials, etc.), and organizes into a clean
folder structure.

Usage:
    python cms_downloader.py                          Interactive mode
    python cms_downloader.py 2576 2574                Download specific courses
    python cms_downloader.py all                      Download all courses
    python cms_downloader.py --list-courses           List enrolled courses
    python cms_downloader.py 2576 --dry-run           Preview without downloading
    python cms_downloader.py 2576 --weeks 1-5         Weeks 1 through 5 only
    python cms_downloader.py 2576 --only lectures     Lectures category only

First run will ask for credentials. Saving credentials locally is optional
and off by default; enable it from --settings if you want click-to-launch sign-in.
Commands inside interactive mode must be prefixed with "--".
Type --help for a quick command list, or --help-full for the immersive guide.
"""

import os
import sys
import re
import json
import base64
import argparse
import platform
import time
import csv
import traceback
import getpass
from datetime import datetime, date

# Force UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ══════════════════════════════════════════════════════════════════════
#  ANSI COLORS
# ══════════════════════════════════════════════════════════════════════

if platform.system() == "Windows":
    os.system("")  # enables ANSI escape sequences

class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    GRAY    = "\033[90m"

def c(text, color):
    return f"{color}{text}{C.RESET}"

# ══════════════════════════════════════════════════════════════════════
#  COMMAND INFRASTRUCTURE
# ══════════════════════════════════════════════════════════════════════

class CommandAction(Exception):
    def __init__(self, command):
        self.command = command

class DownloadError(Exception):
    """Raised when a download operation fails with details."""
    def __init__(self, message, url="", http_code="", retries_attempted=0):
        super().__init__(message)
        self.url = url
        self.http_code = http_code
        self.retries_attempted = retries_attempted

def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")

def get_input(prompt: str) -> str:
    while True:
        try:
            raw = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            raise CommandAction("exit")
        user_input = raw.strip()
        if user_input.startswith("--"):
            cmd_part = user_input[2:].strip().lower()
            if cmd_part in ("exit", "quit", "q"):
                raise CommandAction("exit")
            elif cmd_part == "clear":
                raise CommandAction("clear")
            elif cmd_part in ("restart", "break"):
                raise CommandAction("restart")
            elif cmd_part in ("back", "undo"):
                raise CommandAction("back")
            elif cmd_part in ("help-full", "helpfull"):
                show_help_full()
                continue
            elif cmd_part in ("help", "h", "?"):
                print_command_list()
                continue
            elif cmd_part in ("settings", "s"):
                show_settings()
                continue
            else:
                print(c(f"  Unknown command: --{cmd_part}. Type --help for a list.", C.RED))
                continue
        else:
            return raw

def prompt_text(base, default_desc):
    if SETTINGS.get("show_defaults", True):
        return f"  {base} ({c(default_desc, C.DIM)}): "
    return f"  {base}: "

# ══════════════════════════════════════════════════════════════════════
#  HELP SYSTEM
# ══════════════════════════════════════════════════════════════════════

def print_command_list():
    print()
    print(c("  Available commands (prefix with '--'):", C.CYAN))
    print("    --exit, --quit, --q     Exit the program")
    print("    --clear                 Clear screen and restart")
    print("    --restart, --break      Jump back to course selection")
    print("    --back, --undo          Go back one step")
    print("    --help, --h, --?        This quick help")
    print("    --help-full             Full immersive help guide")
    print("    --settings, --s         Open settings panel")
    print()

def show_help_full():
    clear_screen()
    hdr = c("COMMANDS:", C.YELLOW)
    wf = c("WORKFLOW:", C.YELLOW)
    cats = c("CATEGORIES:", C.YELLOW)
    creds = c("CREDENTIALS:", C.YELLOW)
    cli = c("CLI MODE:", C.YELLOW)
    filt = c("FILTERS:", C.YELLOW)
    print("=" * 60)
    print(c("  GIU CMS DOWNLOADER — FULL HELP", C.BOLD + C.CYAN))
    print("=" * 60)
    print(f"""
  {hdr}
    --exit, --quit, --q     Exit the program completely
    --clear                 Clear screen & start fresh
    --restart, --break      Jump to course selection
    --back, --undo          Undo the last prompt
    --help, --h, --?        Quick command list
    --help-full             This screen
    --settings, --s         Change program settings

  {wf}
    1. Select courses to download
    2. Choose download location
    3. Set filters (weeks, categories)
    4. Confirm options (skip existing, dry run)
    5. Downloads run automatically
    6. Summary report — then back to step 1

  {cats}
    Files are auto-sorted into: Lectures, Labs, Tutorials,
    PA, PA_Solutions, Lab_Solutions, Projects, Exams,
    Sheets, Notes, Other

  {filt}
    Week range: only download from week 3 to 8
    Category:   only download Lectures and PA

  {creds}
    Stored in cms_downloader_settings.json next to script.
    Change via --settings > Manage credential storage.

  {cli}
    python cms_downloader.py all
    python cms_downloader.py 2576 2574
    python cms_downloader.py INCS409 MATH403
    python cms_downloader.py --list-courses
    python cms_downloader.py --list-courses --all
    python cms_downloader.py all --dry-run
    python cms_downloader.py 2576 --weeks 1-5
    python cms_downloader.py 2576 --only lectures,pa
""")
    print("-" * 60)
    while True:
        try:
            raw = input("--▶ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise CommandAction("exit")
        if not raw.startswith("--"):
            print("  Commands must start with '--'. Type --back to return.")
            continue
        cmd = raw[2:].strip().lower()
        if cmd in ("back", "undo"):
            clear_screen(); return
        elif cmd in ("exit", "quit", "q"):
            raise CommandAction("exit")
        elif cmd in ("settings", "s"):
            show_settings(); clear_screen(); return
        else:
            print("  Unknown. Use --back to return.")

# ══════════════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════════════

FACTORY_SETTINGS = {
    "show_defaults": True,
    "show_tips": True,
    "default_download_path": "D:\\Downloads\\GIU_CMS_Downloads",
    "default_skip_existing": True,
    "default_courses": "all",
    "default_show_all_courses": False,
    "auto": {
        "course_select": False,
        "download_path": False,
        "filters": False,
        "options": False
    },
    "categories": {
        "lecture": "Lectures", "tutorial": "Tutorials",
        "assignment_solution": "PA_Solutions", "assignment": "PA",
        "lab_solution": "Lab_Solutions", "lab": "Labs",
        "project": "Projects", "exam": "Exams",
        "sheet": "Sheets", "notes": "Notes", "other": "Other"
    },
    "preset": "factory_default",
    "last_run": None,
    "credential_storage": {
        "save_credentials": False,
        "username": "",
        "password_b64": ""
    }
}

# Session credentials are always loaded into memory first. Saving them to disk
# is opt-in from settings and disabled by default.
SESSION_CREDS = {"username": "", "password": ""}

PRESETS = {
    "ask_all": {
        "auto": {"course_select": False, "download_path": False,
                 "filters": False, "options": False}
    },
    "skip_all": {
        "auto": {"course_select": True, "download_path": True,
                 "filters": True, "options": True}
    },
    "factory_default": {
        "auto": {"course_select": False, "download_path": False,
                 "filters": False, "options": False}
    }
}

SETTINGS = {}
settings_file = None

def _deep_copy(d):
    if isinstance(d, dict): return {k: _deep_copy(v) for k, v in d.items()}
    if isinstance(d, list): return [_deep_copy(i) for i in d]
    return d

def load_settings():
    global SETTINGS, settings_file
    script_dir = os.path.dirname(os.path.realpath(sys.argv[0])) if sys.argv[0] else os.getcwd()
    settings_file = os.path.join(script_dir, "cms_downloader_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                SETTINGS.update(json.load(f))
        except Exception:
            pass
    for key, val in FACTORY_SETTINGS.items():
        if key not in SETTINGS:
            SETTINGS[key] = _deep_copy(val)
        elif isinstance(val, dict):
            for k2, v2 in val.items():
                if k2 not in SETTINGS[key]:
                    SETTINGS[key][k2] = _deep_copy(v2)
    save_settings()

def save_settings():
    try:
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(SETTINGS, f, indent=2)
    except Exception:
        pass

def _encode_saved_password(password):
    if not password:
        return ""
    return base64.b64encode(password.encode("utf-8")).decode("ascii")

def _decode_saved_password(encoded):
    if not encoded:
        return ""
    try:
        return base64.b64decode(encoded.encode("ascii")).decode("utf-8")
    except Exception:
        return ""

def _mask_password(password):
    if not password:
        return "(none)"
    return "*" * min(12, max(6, len(password)))

def saved_credentials_enabled():
    return bool(SETTINGS.get("credential_storage", {}).get("save_credentials"))

def load_saved_credentials():
    storage = SETTINGS.get("credential_storage", {})
    if not storage.get("save_credentials"):
        return False
    username = storage.get("username", "")
    password = _decode_saved_password(storage.get("password_b64", ""))
    if not username or not password:
        return False
    SESSION_CREDS["username"] = username
    SESSION_CREDS["password"] = password
    return True

def save_current_credentials():
    storage = SETTINGS.setdefault("credential_storage", _deep_copy(FACTORY_SETTINGS["credential_storage"]))
    if not storage.get("save_credentials"):
        return
    storage["username"] = SESSION_CREDS["username"]
    storage["password_b64"] = _encode_saved_password(SESSION_CREDS["password"])
    save_settings()

def clear_saved_credentials(settings_target=None):
    target = settings_target if settings_target is not None else SETTINGS
    storage = target.setdefault("credential_storage", _deep_copy(FACTORY_SETTINGS["credential_storage"]))
    storage["username"] = ""
    storage["password_b64"] = ""

def get_password():
    return SESSION_CREDS["password"]

def get_username():
    return SESSION_CREDS["username"]

def has_credentials():
    return bool(SESSION_CREDS["username"]) and bool(SESSION_CREDS["password"])

def prompt_password(prompt="  Password: "):
    """Read a password with masked feedback in a Windows console."""
    if os.name == "nt" and sys.stdin.isatty():
        import msvcrt
        print(prompt, end="", flush=True)
        characters = []
        while True:
            char = msvcrt.getwch()
            if char in ("\r", "\n"):
                print()
                return "".join(characters)
            if char == "\x03":
                print()
                raise KeyboardInterrupt
            if char == "\x1a":
                print()
                raise EOFError
            if char in ("\x00", "\xe0"):
                msvcrt.getwch()  # Consume the second part of special keys.
                continue
            if char in ("\b", "\x7f"):
                if characters:
                    characters.pop()
                    print("\b \b", end="", flush=True)
            elif char.isprintable():
                characters.append(char)
                print("*", end="", flush=True)
    else:
        print("  Password input is hidden; type your password and press Enter.")
        return getpass.getpass(prompt)


def sign_in(username=None, password=None, source="prompt"):
    """Prompt for credentials or use supplied/saved credentials.
    Saving credentials is opt-in and disabled by default."""
    if username and password:
        SESSION_CREDS["username"] = username
        SESSION_CREDS["password"] = password
    else:
        print(c("\n  Sign in to GIU CMS", C.BOLD + C.CYAN))
        if saved_credentials_enabled():
            print(c("  (saved credentials are enabled in settings)\n", C.DIM))
        else:
            print(c("  (credentials are used for this session only)\n", C.DIM))
        u = input("  Username: ").strip()
        if not u:
            print(c("  Username is required.", C.RED))
            return False
        p = prompt_password("  Password: ")
        if not p:
            print(c("  Password is required.", C.RED))
            return False
        SESSION_CREDS["username"] = u
        SESSION_CREDS["password"] = p

    print(f"\n  {c('Connecting...', C.CYAN)}", end="", flush=True)
    ok, msg = test_connection()
    if ok:
        print(c(f" {msg}", C.GREEN))
        save_current_credentials()
        if source == "saved":
            print(c("  Signed in using saved credentials.", C.DIM))
        return True
    else:
        print(c(f" {msg}", C.RED))
        SESSION_CREDS["username"] = ""
        SESSION_CREDS["password"] = ""
        return False

# ══════════════════════════════════════════════════════════════════════
#  SETTINGS PANEL
# ══════════════════════════════════════════════════════════════════════

def show_settings():
    import copy
    temp = copy.deepcopy(SETTINGS)

    def changes_exist(): return temp != SETTINGS
    def save_temp():
        SETTINGS.clear(); SETTINGS.update(temp); save_settings()

    def manage_credentials():
        storage = temp.setdefault("credential_storage", _deep_copy(FACTORY_SETTINGS["credential_storage"]))
        show_password = False
        while True:
            clear_screen()
            print(c("  Credential Storage\n", C.CYAN))
            enabled = c("ON", C.GREEN) if storage.get("save_credentials") else c("OFF", C.YELLOW)
            username = storage.get("username") or "(none)"
            saved_password = _decode_saved_password(storage.get("password_b64", ""))
            password_label = saved_password if show_password else _mask_password(saved_password)
            saved = c("yes", C.GREEN) if storage.get("username") and saved_password else c("no", C.YELLOW)
            print(f"  1) Save credentials locally : {enabled}")
            visibility = "visible" if show_password else "hidden"
            print(f"  2) Update username          : {c(username, C.YELLOW)}")
            print(f"  3) Saved password ({visibility}) : {c(password_label, C.YELLOW)}")
            print(f"  4) Password saved           : {saved}")
            print("  5) Update password")
            print("  6) Update both")
            print("  7) Show/hide password")
            print("  8) Clear saved credentials")
            print("  9) Back")
            print(c("\n  Note: saved credentials are base64-obfuscated, not encrypted.", C.DIM))
            ch = input("\n  >> ").strip()
            if ch == "1":
                storage["save_credentials"] = not storage.get("save_credentials", False)
                if not storage["save_credentials"]:
                    clear_saved_credentials(temp)
            elif ch == "2":
                u = input("  Username (Enter to keep): ").strip()
                if u: storage["username"] = u
            elif ch == "5":
                if not storage.get("username"):
                    u = input("  Username required first: ").strip()
                    if not u:
                        print(c("  Username is required before saving a password.", C.RED)); time.sleep(1); continue
                    storage["username"] = u
                p = prompt_password("  Password: ")
                if not p:
                    print(c("  Password is required.", C.RED)); time.sleep(1); continue
                storage["save_credentials"] = True
                storage["password_b64"] = _encode_saved_password(p)
            elif ch == "6":
                current_user = storage.get("username", "")
                prompt = f"  Username (Enter to keep '{current_user}'): " if current_user else "  Username: "
                u = input(prompt).strip()
                if u:
                    storage["username"] = u
                elif not current_user:
                    print(c("  Username is required.", C.RED)); time.sleep(1); continue
                p = prompt_password("  Password (Enter to keep current): ")
                if p:
                    storage["password_b64"] = _encode_saved_password(p)
                elif not storage.get("password_b64"):
                    print(c("  Password is required.", C.RED)); time.sleep(1); continue
                storage["save_credentials"] = True
            elif ch == "7":
                show_password = not show_password
            elif ch == "8":
                clear_saved_credentials(temp)
            elif ch == "9":
                return

    def modify_defaults():
        while True:
            clear_screen()
            print(c("  Modify Defaults\n", C.CYAN))
            dp = temp["default_download_path"]
            se = c("yes", C.GREEN) if temp["default_skip_existing"] else c("no", C.RED)
            ac = c("yes", C.GREEN) if temp.get("default_show_all_courses") else c("no", C.YELLOW)
            print(f"  1) Download path        : {c(dp, C.YELLOW)}")
            print(f"  2) Skip existing        : {se}")
            print(f"  3) Default courses      : {c(temp['default_courses'], C.YELLOW)}")
            print(f"  4) Show all courses     : {ac}")
            tips = c("yes", C.GREEN) if temp.get("show_tips", True) else c("no", C.YELLOW)
            print(f"  5) Show tips            : {tips}")
            print(f"  6) Back")
            ch = input("\n  >> ").strip()
            if ch == "1":
                p = input("  Enter path (Enter to keep): ").strip()
                if p: temp["default_download_path"] = p
            elif ch == "2": temp["default_skip_existing"] = not temp["default_skip_existing"]
            elif ch == "3":
                nc = input("  Course IDs (comma-sep) or 'all': ").strip()
                if nc: temp["default_courses"] = nc
            elif ch == "4": temp["default_show_all_courses"] = not temp.get("default_show_all_courses", False)
            elif ch == "5": temp["show_tips"] = not temp.get("show_tips", True)
            elif ch == "6": return

    def change_automation():
        steps = ("course_select", "download_path", "filters", "options")
        while True:
            clear_screen()
            print(c("  Step Automation\n", C.CYAN))
            auto = temp["auto"]
            for idx, step in enumerate(steps, 1):
                status = c("AUTO", C.GREEN) if auto.get(step) else c("ASK", C.YELLOW)
                print(f"  {idx}) {step:<20} : {status}")
            print(f"  {len(steps)+1}) Back")
            ch = input("\n  Toggle: ").strip()
            if ch.isdigit():
                i = int(ch)
                if 1 <= i <= len(steps): temp["auto"][steps[i-1]] = not temp["auto"].get(steps[i-1], False)
                elif i == len(steps)+1: return

    def customize_categories():
        cats = temp["categories"]; keys = list(cats.keys())
        while True:
            clear_screen()
            print(c("  Category Folder Names\n", C.CYAN))
            for idx, key in enumerate(keys, 1):
                print(f"  {idx:2}) {key:<22} -> {c(cats[key], C.YELLOW)}")
            print(f"  {len(keys)+1}) Back")
            ch = input("\n  >> ").strip()
            if ch.isdigit():
                i = int(ch)
                if 1 <= i <= len(keys):
                    key = keys[i-1]
                    nn = input(f"  New name for '{key}' (Enter to keep): ").strip()
                    if nn: cats[key] = nn
                elif i == len(keys)+1: return

    def switch_preset():
        clear_screen()
        print(c("  Choose Preset\n", C.CYAN))
        print("  1) Ask all"); print("  2) Skip all (click to launch)")
        print("  3) Factory default"); print("  4) Back")
        ch = input("\n  >> ").strip()
        if ch == "1": temp["auto"] = _deep_copy(PRESETS["ask_all"]["auto"]); temp["preset"] = "ask_all"
        elif ch == "2": temp["auto"] = _deep_copy(PRESETS["skip_all"]["auto"]); temp["preset"] = "skip_all"
        elif ch == "3": temp["auto"] = _deep_copy(PRESETS["factory_default"]["auto"]); temp["preset"] = "factory_default"

    clear_screen()
    while True:
        print("=" * 60)
        print(c("  SETTINGS", C.BOLD + C.CYAN))
        print("=" * 60)
        se = "yes" if temp["default_skip_existing"] else "no"
        ac = "yes" if temp.get("default_show_all_courses") else "no"
        cred_storage = temp.setdefault("credential_storage", _deep_copy(FACTORY_SETTINGS["credential_storage"]))
        cred_status = "saved" if cred_storage.get("save_credentials") and cred_storage.get("username") and cred_storage.get("password_b64") else "session-only"
        print(f"\n  {c('Defaults:', C.YELLOW)}")
        print(f"    Download path    : {temp['default_download_path']}")
        print(f"    Skip existing    : {se}")
        print(f"    Courses          : {temp['default_courses']}")
        print(f"    Show all courses : {ac}")
        print(f"    Show tips        : {'yes' if temp.get('show_tips', True) else 'no'}")
        print(f"\n  {c('Step automation:', C.YELLOW)}")
        for step in ("course_select", "download_path", "filters", "options"):
            status = c("AUTO", C.GREEN) if temp["auto"].get(step) else "ASK"
            print(f"    {step:<20} : {status}")
        print(f"\n  Active preset: {c(temp.get('preset', 'custom'), C.MAGENTA)}")
        print(f"\n  Credentials: {c(cred_status, C.DIM)}")
        print(f"\n  {c('Options:', C.YELLOW)}")
        print("    1) Modify defaults")
        print("    2) Change step automation"); print("    3) Customize category folder names")
        print("    4) Switch preset"); print("    5) Manage credential storage")
        print("    6) Restore factory defaults"); print("    7) Save and exit"); print()
        try: choice = input("  >> ").strip()
        except (EOFError, KeyboardInterrupt): raise CommandAction("exit")
        if choice.startswith("--"):
            cmd = choice[2:].strip().lower()
            if cmd in ("back", "undo"):
                if changes_exist():
                    a = input("  Unsaved changes. Save? (y/n): ").strip().lower()
                    if a == "y": save_temp()
                clear_screen(); return
            elif cmd in ("exit", "quit", "q"):
                if changes_exist():
                    a = input("  Unsaved changes. Save? (y/n): ").strip().lower()
                    if a == "y": save_temp()
                raise CommandAction("exit")
            continue
        try:
            if choice == "1": modify_defaults()
            elif choice == "2": change_automation()
            elif choice == "3": customize_categories()
            elif choice == "4": switch_preset()
            elif choice == "5": manage_credentials()
            elif choice == "6":
                a = input("  Restore factory defaults? (y/n): ").strip().lower()
                if a == "y": temp.clear(); temp.update(_deep_copy(FACTORY_SETTINGS))
            elif choice == "7": save_temp(); clear_screen(); return
        except CommandAction: raise
        except Exception as e:
            print(c(f"  Error in settings: {e}", C.RED))
        clear_screen()

# (first_run_setup removed — credentials are handled through sign_in/settings)

# ══════════════════════════════════════════════════════════════════════
#  CMS ENGINE
# ══════════════════════════════════════════════════════════════════════

BASE_URL = "https://cms.giu-uni.de"
ERROR_LOG = []  # Collects errors for the final report

def log_error(context, message, detail=""):
    ERROR_LOG.append({
        "time": datetime.now().strftime("%H:%M:%S"),
        "context": context, "message": message, "detail": detail
    })

def _request(url, output_file=None, timeout=60, retries=3):
    """Fetch CMS content using Python NTLM support, independently of curl."""
    username, password = get_username(), get_password()
    if not username or not password:
        return ("NO_CREDS", "")
    try:
        import requests
        from requests_ntlm import HttpNtlmAuth
    except ImportError:
        return ("ERROR", "Missing login library. Install it with: "
                f'"{sys.executable}" -m pip install requests requests-ntlm')

    for attempt in range(retries):
        try:
            with requests.Session() as session:
                session.auth = HttpNtlmAuth(username, password)
                # Do not forward authentication to a redirected host.
                with session.get(url, timeout=timeout, stream=bool(output_file),
                                 allow_redirects=False) as response:
                    code = str(response.status_code)
                    if output_file:
                        if code != "200":
                            return (code, "")
                        # Publish only complete downloads; preserve an existing file on failure.
                        partial = os.fspath(output_file) + ".part"
                        try:
                            with open(partial, "wb") as target:
                                for chunk in response.iter_content(chunk_size=65536):
                                    if chunk:
                                        target.write(chunk)
                            if os.path.getsize(partial) == 0:
                                raise OSError("Server returned an empty file")
                            os.replace(partial, output_file)
                        finally:
                            if os.path.exists(partial):
                                os.remove(partial)
                        return (code, output_file)
                    return (code, response.text)
        except requests.exceptions.SSLError:
            return ("ERROR", "CMS certificate verification failed. Check the server certificate and your computer's date.")
        except requests.exceptions.Timeout:
            error_code, message = "TIMEOUT", f"Timeout after {timeout}s"
        except requests.exceptions.RequestException as exc:
            error_code, message = "CONN_ERROR", str(exc).replace(password, "[redacted]")
        except Exception as exc:
            error_code, message = "ERROR", str(exc).replace(password, "[redacted]")
        if attempt < retries - 1:
            time.sleep(1 + attempt)
        else:
            log_error("request", message, f"URL: {url}")
            return (error_code, message)
    return ("CONN_ERROR", "No request attempts configured.")


def test_connection():
    code, detail = _request(f"{BASE_URL}/apps/student/HomePageStn.aspx")
    if code == "NO_CREDS": return (False, "No credentials configured. Run --settings.")
    if code in ("TIMEOUT", "CONN_ERROR", "ERROR"):
        return (False, f"Connection failed: {detail}")
    if code == "200": return (True, "Connected successfully!")
    if code in ("401", "403"): return (False, "Authentication failed. Check --settings.")
    return (False, f"Unexpected HTTP {code}.")

def fetch_courses(show_all=False):
    """Fetch courses. show_all=True uses ViewAllCourseStn, else HomePageStn (active only)."""
    if show_all:
        page = f"{BASE_URL}/apps/student/ViewAllCourseStn.aspx"
    else:
        page = f"{BASE_URL}/apps/student/HomePageStn.aspx"

    code, html = _request(page)
    if code != "200":
        log_error("fetch_courses", f"Failed to fetch course list (HTTP {code})")
        return None, f"Failed (HTTP {code})"

    courses = []

    if show_all:
        # ViewAllCourseStn: columns are Name | Active | ID | SeasonId
        pattern = (r'\(\|([A-Z]+\d+)\|\)\s*(.*?)\s*\((\d+)\)</td>'
                   r'<td>(Active|Inactive)</td><td>(\d+)</td><td>(-?\d+)</td>')
        for m in re.finditer(pattern, html):
            course_code = m.group(1)
            name = m.group(2).strip()
            cid = m.group(3)
            active = m.group(4)
            # group(5) = ID column (same as cid), group(6) = SeasonId
            sid = m.group(6)
            name = name.replace("&amp;", "&").replace("&#160;", " ").replace("&nbsp;", " ").strip()

            safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
            safe_name = re.sub(r'\s+', '_', safe_name)
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')

            courses.append({
                "id": cid, "sid": sid, "code": course_code,
                "name": name, "active": active, "season": f"sid:{sid}",
                "folder": f"{course_code}_{safe_name}"
            })
    else:
        # HomePageStn: columns are Name | Active | Season
        pattern = (r'\(\|([A-Z]+\d+)\|\)\s*(.*?)\s*\((\d+)\)</td>'
                   r'<td>(Active|Inactive)</td><td>(.*?)</td>')
        for m in re.finditer(pattern, html):
            course_code = m.group(1)
            name = m.group(2).strip()
            cid = m.group(3)
            active = m.group(4)
            season = m.group(5)
            name = name.replace("&amp;", "&").replace("&#160;", " ").replace("&nbsp;", " ").strip()

            sid_match = re.search(rf'id={cid}&amp;sid=(\d+)', html)
            if not sid_match:
                sid_match = re.search(rf'id={cid}&sid=(\d+)', html)
            sid = sid_match.group(1) if sid_match else "68"

            safe_name = re.sub(r'[\\/:*?"<>|]', '_', name)
            safe_name = re.sub(r'\s+', '_', safe_name)
            safe_name = re.sub(r'_+', '_', safe_name).strip('_')

            courses.append({
                "id": cid, "sid": sid, "code": course_code,
                "name": name, "active": active, "season": season,
                "folder": f"{course_code}_{safe_name}"
            })

    return courses, "OK"

def parse_course_page(html):
    """Parse course HTML -> list of content items with week numbers."""
    items = []
    week_re = (r'(?s)<div class="card mb-5 weeksdata".*?'
               r'(?=<div class="card mb-5 weeksdata"|<div class="app-main__outer"|$)')

    all_week_dates = []
    week_blocks = list(re.finditer(week_re, html))

    # First pass: collect all week dates to assign week numbers
    for wm in week_blocks:
        dm = re.search(r'<h2 class="text-big">Week:\s*([\d-]+)</h2>', wm.group())
        if dm:
            all_week_dates.append(dm.group(1))

    # Sort chronologically (oldest first) for week numbering
    def parse_date(ds):
        parts = ds.split("-")
        try:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            return date(2000, 1, 1)

    sorted_dates = sorted(set(all_week_dates), key=parse_date)
    date_to_week = {d: i for i, d in enumerate(sorted_dates)}

    for wm in week_blocks:
        whtml = wm.group()
        dm = re.search(r'<h2 class="text-big">Week:\s*([\d-]+)</h2>', whtml)
        week_date = dm.group(1) if dm else "Unknown"
        week_num = date_to_week.get(week_date, -1)

        content_re = (r'(?s)<div id="content\d+">(.*?)</div>\s*<div></div>'
                      r'\s*.*?<a href=\'([^\']+)\' id="download"')
        for cm in re.finditer(content_re, whtml):
            desc_html = cm.group(1)
            dl_path = cm.group(2)

            tm = re.search(r'<strong>(.*?)</strong>\s*\((.*?)\)', desc_html)
            if tm:
                raw_title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
                type_text = re.sub(r'<[^>]+>', '', tm.group(2)).strip()
            else:
                tm2 = re.search(r'<strong>(.*?)</strong>(.*)', desc_html)
                if tm2:
                    raw_title = re.sub(r'<[^>]+>', '', tm2.group(1)).strip()
                    type_text = re.sub(r'<[^>]+>', '', tm2.group(2)).strip('() ')
                else:
                    raw_title = re.sub(r'<[^>]+>', '', desc_html).strip()
                    type_text = ""

            clean_title = re.sub(r'^\d+\s*[-\u2013\u2014]\s*', '', raw_title)
            ext = os.path.splitext(dl_path)[1] or ".pdf"

            items.append({
                "week": week_date, "week_num": week_num,
                "title": clean_title, "type": type_text,
                "download_path": dl_path, "extension": ext
            })
    return items, len(sorted_dates)

def categorize(title, type_text, cats):
    t = title.lower(); tt = type_text.lower()
    if re.search(r'\blec(?:ture)?\b', t):                     return cats.get("lecture", "Lectures")
    if re.search(r'\blab\b', t) and re.search(r'\bsolution\b', t): return cats.get("lab_solution", "Lab_Solutions")
    if re.search(r'\blab\b', t):                               return cats.get("lab", "Labs")
    if re.search(r'\bquiz\b|\bmidterm\b|\bexam\b|\bfinal\b', t): return cats.get("exam", "Exams")
    if re.search(r'\bsolution\b|\bmodel[\s_]*answer\b', t):   return cats.get("assignment_solution", "PA_Solutions")
    if re.search(r'\btut(?:orial)?\b|\bworksheet\b', t):      return cats.get("tutorial", "Tutorials")
    if re.search(r'\bproject\b|\bmilestone\b', t):             return cats.get("project", "Projects")
    if re.search(r'\bassignment\b|\bpa[\s_]*\d|\bpractice[\s_]*assignment\b', t): return cats.get("assignment", "PA")
    if re.search(r'\bformula\b|\bsheet\b|\btable\b', t) and not re.search(r'\bworksheet\b', t): return cats.get("sheet", "Sheets")
    if re.search(r'\bnotes?\b', t):                            return cats.get("notes", "Notes")
    # Fallback to CMS type
    if re.search(r'lecture', tt):              return cats.get("lecture", "Lectures")
    if re.search(r'tutorial', tt):             return cats.get("tutorial", "Tutorials")
    if re.search(r'assignment\s*solution', tt):return cats.get("assignment_solution", "PA_Solutions")
    if re.search(r'assignment', tt):           return cats.get("assignment", "PA")
    if re.search(r'lab', tt):                  return cats.get("lab", "Labs")
    if re.search(r'project', tt):              return cats.get("project", "Projects")
    if re.search(r'quiz|exam', tt):            return cats.get("exam", "Exams")
    if re.search(r'exercise|sheet|supplementary', tt): return cats.get("sheet", "Sheets")
    if re.search(r'note', tt):                 return cats.get("notes", "Notes")
    return cats.get("other", "Other")

def safe_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'_+', '_', name).strip('_')
    return name[:150] if len(name) > 150 else name

# ══════════════════════════════════════════════════════════════════════
#  DOWNLOAD ENGINE
# ══════════════════════════════════════════════════════════════════════

def download_course(course, download_root, skip_existing, cats,
                    dry_run=False, week_range=None, category_filter=None):
    """Download all files for one course with optional filters.
    week_range: (min_week, max_week) or None for all.
    category_filter: set of lowercase category names to include, or None for all."""
    course_folder = os.path.join(download_root, course["folder"])
    os.makedirs(course_folder, exist_ok=True)

    url = f"{BASE_URL}/apps/student/CourseViewStn.aspx?id={course['id']}&sid={course['sid']}"
    code, html = _request(url)
    if code != "200":
        msg = f"Could not fetch course page (HTTP {code})"
        log_error(course["code"], msg, url)
        print(c(f"  ✗ {msg}", C.RED))
        return {"downloaded": 0, "skipped": 0, "failed": 0, "filtered": 0,
                "total": 0, "size_bytes": 0, "categories": {}, "files": [],
                "total_weeks": 0, "errors": [msg]}

    try:
        items, total_weeks = parse_course_page(html)
    except Exception as e:
        msg = f"Failed to parse course page: {e}"
        log_error(course["code"], msg, traceback.format_exc())
        print(c(f"  ✗ {msg}", C.RED))
        return {"downloaded": 0, "skipped": 0, "failed": 0, "filtered": 0,
                "total": 0, "size_bytes": 0, "categories": {}, "files": [],
                "total_weeks": 0, "errors": [msg]}

    total = len(items)
    downloaded = skipped = failed = filtered = total_bytes = 0
    cat_counts = {}
    file_manifest = []
    errors = []

    for i, item in enumerate(items, 1):
        cat = categorize(item["title"], item["type"], cats)

        # Week filter
        if week_range:
            wn = item["week_num"]
            if wn < week_range[0] or wn > week_range[1]:
                filtered += 1
                continue

        # Category filter
        if category_filter:
            if cat.lower() not in category_filter:
                filtered += 1
                continue

        cat_folder = os.path.join(course_folder, cat)
        os.makedirs(cat_folder, exist_ok=True)
        fname = safe_filename(item["title"]) + item["extension"]
        fpath = os.path.join(cat_folder, fname)

        ctr = 1
        while os.path.exists(fpath) and not skip_existing:
            fname = safe_filename(item["title"]) + f"_({ctr})" + item["extension"]
            fpath = os.path.join(cat_folder, fname)
            ctr += 1

        cat_counts[cat] = cat_counts.get(cat, 0) + 1

        # Skip existing
        if skip_existing and os.path.exists(fpath) and os.path.getsize(fpath) > 0:
            sz = os.path.getsize(fpath)
            total_bytes += sz
            wk = item["week_num"]
            print(f"  {c('[' + str(i) + '/' + str(total) + ']', C.DIM)} "
                  f"{c('[SKIP]', C.YELLOW)} W{wk} {item['title']} -> {cat}/{fname}")
            skipped += 1
            file_manifest.append({"course": course["code"], "week": item["week"],
                "week_num": item["week_num"], "title": item["title"], "type": item["type"],
                "category": cat, "filename": fname, "status": "skipped", "size": sz})
            continue

        # Dry run
        if dry_run:
            wk = item["week_num"]
            print(f"  {c('[' + str(i) + '/' + str(total) + ']', C.DIM)} "
                  f"{c('[DRY]', C.MAGENTA)} W{wk} {item['title']} -> {cat}/{fname}")
            downloaded += 1
            file_manifest.append({"course": course["code"], "week": item["week"],
                "week_num": item["week_num"], "title": item["title"], "type": item["type"],
                "category": cat, "filename": fname, "status": "dry_run", "size": 0})
            continue

        # Real download with per-file retry
        full_url = f"{BASE_URL}{item['download_path']}"
        wk = item["week_num"]
        print(f"  {c('[' + str(i) + '/' + str(total) + ']', C.CYAN)} "
              f"W{wk} {item['title']} -> {cat}/{fname}", end="", flush=True)

        dl_ok = False
        dl_retries = 3
        for attempt in range(dl_retries):
            try:
                code, detail = _request(full_url, output_file=fpath, timeout=120, retries=1)
                if code == "200" and os.path.exists(fpath) and os.path.getsize(fpath) > 0:
                    dl_ok = True
                    break
                if attempt < dl_retries - 1:
                    time.sleep(1)
                else:
                    reason = detail if code in ("ERROR", "CONN_ERROR", "TIMEOUT") else f"HTTP {code} or empty file"
                    err_msg = f"Download failed: {reason}"
                    errors.append(err_msg)
                    log_error(course["code"], err_msg, f"File: {item['title']}, URL: {full_url}")
            except Exception as e:
                err_msg = f"Download error: {e}"
                errors.append(err_msg)
                log_error(course["code"], err_msg, traceback.format_exc())
                break

        if dl_ok:
            sz = os.path.getsize(fpath)
            total_bytes += sz
            sz_str = f"{sz/1024:.0f} KB" if sz < 1048576 else f"{sz/1048576:.1f} MB"
            print(c(f"  OK {sz_str}", C.GREEN))
            downloaded += 1
            file_manifest.append({"course": course["code"], "week": item["week"],
                "week_num": item["week_num"], "title": item["title"], "type": item["type"],
                "category": cat, "filename": fname, "status": "downloaded", "size": sz})
        else:
            print(c("  FAILED", C.RED))
            failed += 1
            file_manifest.append({"course": course["code"], "week": item["week"],
                "week_num": item["week_num"], "title": item["title"], "type": item["type"],
                "category": cat, "filename": fname, "status": "failed", "size": 0})

    return {
        "downloaded": downloaded, "skipped": skipped, "failed": failed,
        "filtered": filtered, "total": total, "size_bytes": total_bytes,
        "categories": cat_counts, "files": file_manifest,
        "total_weeks": total_weeks, "errors": errors
    }

# ══════════════════════════════════════════════════════════════════════
#  REPORTING
# ══════════════════════════════════════════════════════════════════════

def fmt_size(b):
    if b < 1024: return f"{b} B"
    if b < 1048576: return f"{b/1024:.1f} KB"
    return f"{b/1048576:.1f} MB"

def print_course_report(course, stats):
    w = 52
    print()
    print(c("+" + "="*w + "+", C.CYAN))
    title = f"  {course['code']} - {course.get('name', '')}"
    if len(title) > w - 1: title = title[:w-4] + "..."
    print(c("|", C.CYAN) + c(title.ljust(w), C.BOLD) + c("|", C.CYAN))
    print(c("+" + "-"*w + "+", C.CYAN))

    n_dl = stats["downloaded"]; n_sk = stats["skipped"]
    n_fl = stats["failed"]; n_ft = stats.get("filtered", 0)
    sz = fmt_size(stats["size_bytes"])
    dl_c = C.GREEN if n_dl > 0 else C.DIM
    sk_c = C.YELLOW if n_sk > 0 else C.DIM
    fl_c = C.RED if n_fl > 0 else C.DIM
    ft_c = C.MAGENTA if n_ft > 0 else C.DIM
    summary = ("  " + c("dl:" + str(n_dl), dl_c) + "  "
               + c("skip:" + str(n_sk), sk_c) + "  "
               + c("fail:" + str(n_fl), fl_c))
    if n_ft > 0:
        summary += "  " + c("filt:" + str(n_ft), ft_c)
    summary += "  " + c(sz, C.DIM)
    raw_len = len(re.sub(r'\033\[[^m]*m', '', summary))
    pad = w - raw_len
    print(c("|", C.CYAN) + summary + " "*max(0, pad) + c("|", C.CYAN))

    print(c("+" + "-"*w + "+", C.CYAN))
    for cat, count in sorted(stats["categories"].items()):
        unit = "file" if count == 1 else "files"
        line = f"  {cat:<22} {count:>3} {unit}"
        print(c("|", C.CYAN) + line.ljust(w) + c("|", C.CYAN))

    # Show errors inline
    if stats.get("errors"):
        print(c("+" + "-"*w + "+", C.CYAN))
        for err in stats["errors"][:5]:
            eline = "  " + c("! ", C.RED) + err[:w-4]
            raw_l = len(re.sub(r'\033\[[^m]*m', '', eline))
            print(c("|", C.CYAN) + eline + " "*max(0, w - raw_l) + c("|", C.CYAN))
        if len(stats["errors"]) > 5:
            more = f"  ...and {len(stats['errors'])-5} more errors"
            print(c("|", C.CYAN) + more.ljust(w) + c("|", C.CYAN))

    print(c("+" + "="*w + "+", C.CYAN))

def save_manifest(download_root, all_stats):
    manifest_path = os.path.join(download_root, "download_manifest.csv")
    all_files = []
    for _, stats in all_stats:
        all_files.extend(stats.get("files", []))
    if not all_files: return
    try:
        with open(manifest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "course", "week", "week_num", "title", "type", "category",
                "filename", "status", "size"])
            writer.writeheader()
            writer.writerows(all_files)
        print(c(f"  Manifest: {manifest_path}", C.DIM))
    except Exception as e:
        print(c(f"  Could not save manifest: {e}", C.RED))

def save_error_log(download_root):
    if not ERROR_LOG: return
    err_path = os.path.join(download_root, "error_log.json")
    try:
        with open(err_path, "w", encoding="utf-8") as f:
            json.dump(ERROR_LOG, f, indent=2)
        print(c(f"  Error log: {err_path}", C.DIM))
    except Exception:
        pass

def print_error_summary():
    if not ERROR_LOG: return
    print(c(f"\n  Errors encountered ({len(ERROR_LOG)}):", C.RED + C.BOLD))
    for err in ERROR_LOG[:10]:
        print(f"    [{err['time']}] {c(err['context'], C.YELLOW)}: {err['message']}")
    if len(ERROR_LOG) > 10:
        print(c(f"    ...and {len(ERROR_LOG)-10} more (see error_log.json)", C.DIM))

# ══════════════════════════════════════════════════════════════════════
#  FILTER PARSING
# ══════════════════════════════════════════════════════════════════════

def parse_week_range(text, total_weeks):
    """Parse week range string. Returns (min, max) tuple (0-indexed).
    Formats: '1-5', '3+', '1,3,5', 'all'."""
    text = text.strip().lower()
    if not text or text == "all":
        return None

    # Range: "1-5"
    m = re.match(r'(\d+)\s*-\s*(\d+)', text)
    if m:
        lo = max(0, int(m.group(1)))
        hi = min(total_weeks - 1, int(m.group(2)))
        return (lo, hi)

    # From N onwards: "3+"
    m = re.match(r'(\d+)\s*\+', text)
    if m:
        lo = max(0, int(m.group(1)))
        return (lo, total_weeks - 1)

    # Single number
    if text.isdigit():
        n = int(text)
        return (n, n)

    return None

def parse_category_filter(text, cats):
    """Parse category filter string. Returns set of lowercase category names or None.
    Matches partial names case-insensitively."""
    text = text.strip().lower()
    if not text or text == "all":
        return None

    parts = re.split(r'[,\s]+', text)
    result = set()
    all_cats = {v.lower(): v.lower() for v in cats.values()}

    for part in parts:
        part = part.strip()
        if not part: continue
        if part in all_cats:
            result.add(all_cats[part])
            continue
        matches = [v for k, v in all_cats.items() if part in k]
        if matches:
            result.update(matches)
        else:
            print(c(f"  Unknown category: '{part}'", C.YELLOW))

    return result if result else None

# ══════════════════════════════════════════════════════════════════════
#  STAGES
# ══════════════════════════════════════════════════════════════════════

STAGE_COURSE_SELECT = 0
STAGE_DOWNLOAD_PATH = 1
STAGE_FILTERS       = 2
STAGE_OPTIONS       = 3
STAGE_DOWNLOAD      = 4
STAGE_REPORT        = 5
STAGE_DONE          = 6

BACK_MAP = {
    STAGE_COURSE_SELECT: STAGE_COURSE_SELECT,
    STAGE_DOWNLOAD_PATH: STAGE_COURSE_SELECT,
    STAGE_FILTERS:       STAGE_DOWNLOAD_PATH,
    STAGE_OPTIONS:       STAGE_FILTERS,
}

# ══════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════

def main():
    global ERROR_LOG
    load_settings()

    parser = argparse.ArgumentParser(description="GIU CMS Course Downloader")
    parser.add_argument("courses", nargs="*", help="Course IDs/codes or 'all'")
    parser.add_argument("-u", "--user", help="CMS username")
    parser.add_argument("-p", "--password", help="CMS password")
    parser.add_argument("-o", "--output", help="Download directory")
    parser.add_argument("--overwrite", action="store_true", help="Re-download all files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--no-pause", action="store_true", help="No pause on exit")
    parser.add_argument("--list-courses", action="store_true", help="List courses and exit")
    parser.add_argument("--all", action="store_true", help="Include all courses (not just active)")
    parser.add_argument("--weeks", help="Week range filter (e.g. '1-5', '3+', '7')")
    parser.add_argument("--only", help="Category filter (e.g. 'lectures,pa')")
    args = parser.parse_args()

    # Check the actual running interpreter before asking for credentials.
    try:
        import requests
        from requests_ntlm import HttpNtlmAuth
    except ImportError:
        print(c("  Missing login libraries for this Python installation.", C.RED))
        print(f"  Python: {sys.executable}")
        print("  In PowerShell, run:")
        print(f'  & "{sys.executable}" -m pip install requests requests-ntlm')
        if not args.no_pause:
            try: input("\n  Press Enter to exit...")
            except (EOFError, KeyboardInterrupt): pass
        return

    # ── Sign in ─────────────────────────────────────────────────
    if args.user and args.password:
        # CLI mode with credentials provided
        if not sign_in(args.user, args.password, source="cli"):
            if not args.no_pause:
                try: input("\n  Press Enter to exit...")
                except: pass
            sys.exit(1)
    elif load_saved_credentials():
        if not sign_in(get_username(), get_password(), source="saved"):
            print(c("  Saved credentials failed. Please sign in again.", C.YELLOW))
            clear_saved_credentials()
            save_settings()
            max_attempts = 3
            for attempt in range(max_attempts):
                if sign_in():
                    break
                remaining = max_attempts - attempt - 1
                if remaining > 0:
                    print(c(f"  {remaining} attempt(s) remaining.\n", C.YELLOW))
                else:
                    print(c("  Max attempts reached.", C.RED))
                    if not args.no_pause:
                        try: input("\n  Press Enter to exit...")
                        except: pass
                    sys.exit(1)
    else:
        # Interactive sign-in
        max_attempts = 3
        for attempt in range(max_attempts):
            if sign_in():
                break
            remaining = max_attempts - attempt - 1
            if remaining > 0:
                print(c(f"  {remaining} attempt(s) remaining.\n", C.YELLOW))
            else:
                print(c("  Max attempts reached.", C.RED))
                if not args.no_pause:
                    try: input("\n  Press Enter to exit...")
                    except: pass
                sys.exit(1)

    # ── CLI MODE ─────────────────────────────────────────────────
    if args.courses or args.list_courses:
        show_all = args.all
        result = fetch_courses(show_all=show_all)
        if result[0] is None:
            print(c(f"  {result[1]}", C.RED)); sys.exit(1)
        enrolled = result[0]

        if args.list_courses:
            label = "All" if show_all else "Active"
            print(f"\n  {c(label + ' courses:', C.BOLD)} ({len(enrolled)})\n")
            print(f"  {'ID':<8} {'Code':<12} {'Name':<40} {'Season'}")
            print("  " + "-"*70)
            for co in enrolled:
                act = " " if co["active"] == "Active" else c("*", C.DIM)
                print(f"  {co['id']:<8} {co['code']:<12} {co.get('name','?'):<40} {co.get('season','?')}{act}")
            if not show_all:
                print(c(f"\n  Use --all to see all {28} courses (including past semesters).", C.DIM))
            sys.exit(0)

        if "all" in [x.lower() for x in args.courses]:
            selected = enrolled
        else:
            selected = []
            for arg in args.courses:
                found = next((co for co in enrolled
                              if co["id"] == arg or co["code"].lower() == arg.lower()), None)
                if found: selected.append(found)
                else: print(c(f"  '{arg}' not found.", C.YELLOW))
        if not selected: print(c("  No courses selected.", C.RED)); sys.exit(1)

        dl_path = args.output or SETTINGS["default_download_path"]
        skip = not args.overwrite
        cats = SETTINGS.get("categories", FACTORY_SETTINGS["categories"])
        os.makedirs(dl_path, exist_ok=True)

        # Parse CLI filters
        week_range_cli = None
        cat_filter_cli = None
        if args.weeks:
            week_range_cli = parse_week_range(args.weeks, 20)
        if args.only:
            cat_filter_cli = parse_category_filter(args.only, cats)

        print(f"\n  Downloading {c(str(len(selected)), C.BOLD)} course(s) to: {dl_path}\n")
        all_stats = []
        for co in selected:
            print(f"\n{'='*60}")
            print(c(f"  {co['code']} - {co.get('name', '')}", C.BOLD))
            print(f"{'='*60}")
            stats = download_course(co, dl_path, skip, cats, args.dry_run,
                                    week_range_cli, cat_filter_cli)
            all_stats.append((co, stats))
            print_course_report(co, stats)

        if not args.dry_run:
            save_manifest(dl_path, all_stats)
            save_error_log(dl_path)
        print_error_summary()
        SETTINGS["last_run"] = datetime.now().isoformat()
        save_settings()
        if not args.no_pause:
            try: input("\n  Press Enter to exit...")
            except: pass
        sys.exit(0)

    # ══════════════════════════════════════════════════════════════
    #  INTERACTIVE MODE
    # ══════════════════════════════════════════════════════════════
    clear_screen()
    print(c("""
 +==================================================+
 |        GIU CMS Course Downloader                  |
 +==================================================+
 |  --help for commands, --settings to configure     |
 +==================================================+
""", C.CYAN))

    last_run = SETTINGS.get("last_run")
    if last_run:
        try:
            lr = datetime.fromisoformat(last_run)
            print(c(f"  Last run: {lr.strftime('%Y-%m-%d %H:%M')}", C.DIM))
        except: pass
    print(f"  Logged in as: {c(get_username(), C.GREEN)}\n")

    stage = STAGE_COURSE_SELECT
    enrolled = []
    selected = []
    download_path = skip_existing = dry_run = None
    week_range = None
    category_filter = None
    all_stats = []
    back_override = False
    show_all_courses = SETTINGS.get("default_show_all_courses", False)

    # Pre-fetch courses
    print(f"  {c('Fetching courses...', C.CYAN)}", end="", flush=True)
    result = fetch_courses(show_all=show_all_courses)
    if result[0] is None:
        print(c(f" {result[1]}", C.RED))
        input("\n  Press Enter to exit..."); return
    enrolled = result[0]
    label = "all" if show_all_courses else "active"
    print(c(f" {len(enrolled)} {label} courses found.", C.GREEN))

    while True:
        try:
            # ── Course Selection ──────────────────────────────
            if stage == STAGE_COURSE_SELECT:
                default_c = SETTINGS.get("default_courses", "all")

                if SETTINGS["auto"].get("course_select") and not back_override:
                    if default_c.lower() == "all":
                        selected = enrolled[:]
                    else:
                        ids = [x.strip() for x in default_c.split(",")]
                        selected = [co for co in enrolled
                                    if co["id"] in ids or co["code"] in ids]
                    codes = ", ".join(co["code"] for co in selected)
                    print(f"\n  {c('Auto-selected:', C.DIM)} {codes}")
                    stage = STAGE_DOWNLOAD_PATH; continue

                back_override = False

                print(f"\n  {c('Enrolled courses:', C.BOLD)} ({label})")
                print(f"  {'#':<4} {'Code':<12} {'Name':<40} {'Season'}")
                print("  " + "-"*65)
                for idx, co in enumerate(enrolled, 1):
                    idx_s = c(str(idx), C.CYAN)
                    act = "" if co["active"] == "Active" else c(" (inactive)", C.DIM)
                    print(f"  {idx_s:<16} {co['code']:<12} {co.get('name','?'):<40} "
                          f"{co.get('season','?')}{act}")
                if SETTINGS.get("show_tips", True):
                    toggle_label = "all" if not show_all_courses else "active only"
                    tip = c('Tip: type "toggle" to switch to ' + toggle_label + ' courses', C.DIM)
                    print(f"\n  {tip}")
                print()

                while True:
                    try:
                        sel = get_input(prompt_text(
                            "Select courses (#s, IDs, codes, 'all', or 'toggle')",
                            f"default: {default_c}")).strip()
                    except CommandAction as e:
                        if e.command == "back":
                            print(c("  Already at the first step.", C.YELLOW)); continue
                        raise
                    if not sel: sel = default_c

                    # Toggle all/active courses
                    if sel.lower() == "toggle":
                        show_all_courses = not show_all_courses
                        print(f"  {c('Fetching...', C.CYAN)}", end="", flush=True)
                        result = fetch_courses(show_all=show_all_courses)
                        if result[0] is None:
                            print(c(f" Failed: {result[1]}", C.RED))
                            show_all_courses = not show_all_courses
                            continue
                        enrolled = result[0]
                        label = "all" if show_all_courses else "active"
                        print(c(f" {len(enrolled)} {label} courses.", C.GREEN))
                        # Re-display
                        print(f"\n  {c('Enrolled courses:', C.BOLD)} ({label})")
                        print(f"  {'#':<4} {'Code':<12} {'Name':<40} {'Season'}")
                        print("  " + "-"*65)
                        for idx, co in enumerate(enrolled, 1):
                            idx_s = c(str(idx), C.CYAN)
                            act = "" if co["active"] == "Active" else c(" (inactive)", C.DIM)
                            print(f"  {idx_s:<16} {co['code']:<12} {co.get('name','?'):<40} "
                                  f"{co.get('season','?')}{act}")
                        if SETTINGS.get("show_tips", True):
                            toggle_label = "all" if not show_all_courses else "active only"
                            tip = c('Tip: type "toggle" for ' + toggle_label, C.DIM)
                            print(f"\n  {tip}\n")
                        else:
                            print()
                        continue

                    if sel.lower() == "all":
                        selected = enrolled[:]; break

                    parts = re.split(r'[,\s]+', sel)
                    selected = []; ok_sel = True
                    for part in parts:
                        part = part.strip()
                        if not part: continue
                        found = None
                        if part.isdigit() and 1 <= int(part) <= len(enrolled):
                            found = enrolled[int(part)-1]
                        if not found:
                            found = next((co for co in enrolled
                                          if co["id"] == part or co["code"].lower() == part.lower()), None)
                        if found:
                            if found not in selected: selected.append(found)
                        else:
                            print(c(f"  '{part}' not recognized.", C.RED)); ok_sel = False; break
                    if ok_sel and selected: break
                    if not selected: print(c("  No courses selected.", C.RED))

                codes = ", ".join(co["code"] for co in selected)
                print(f"  {c('Selected:', C.GREEN)} {codes}\n")
                stage = STAGE_DOWNLOAD_PATH

            # ── Download Path ─────────────────────────────────
            elif stage == STAGE_DOWNLOAD_PATH:
                default_p = SETTINGS["default_download_path"]
                if SETTINGS["auto"].get("download_path") and not back_override:
                    download_path = default_p
                    print(f"  {c('Path:', C.DIM)} {download_path}")
                    stage = STAGE_FILTERS; continue
                back_override = False
                while True:
                    try:
                        p = get_input(prompt_text("Download path", f"default: {default_p}")).strip()
                    except CommandAction as e:
                        if e.command == "back": stage = BACK_MAP[stage]; back_override = True; break
                        raise
                    download_path = p if p else default_p; break
                if stage != STAGE_DOWNLOAD_PATH: continue
                stage = STAGE_FILTERS

            # ── Filters ───────────────────────────────────────
            elif stage == STAGE_FILTERS:
                if SETTINGS["auto"].get("filters") and not back_override:
                    week_range = None; category_filter = None
                    stage = STAGE_OPTIONS; continue
                back_override = False

                cats = SETTINGS.get("categories", FACTORY_SETTINGS["categories"])

                # Week filter
                while True:
                    try:
                        wf = get_input(prompt_text(
                            "Week filter (e.g. '1-5', '3+', '7', or Enter for all)",
                            "default: all")).strip()
                    except CommandAction as e:
                        if e.command == "back": stage = BACK_MAP[stage]; back_override = True; break
                        raise
                    if not wf or wf.lower() == "all":
                        week_range = None; break
                    wr = parse_week_range(wf, 20)
                    if wr:
                        week_range = wr
                        print(f"  {c('Weeks:', C.GREEN)} {wr[0]} to {wr[1]}")
                        break
                    print(c("  Invalid format. Use: 1-5, 3+, 7, or all", C.RED))
                if stage != STAGE_FILTERS: continue

                # Category filter
                cat_names = ", ".join(sorted(cats.values()))
                while True:
                    try:
                        cf = get_input(prompt_text(
                            f"Category filter (e.g. 'lectures,pa' or Enter for all)",
                            "default: all")).strip()
                    except CommandAction as e:
                        if e.command == "back": stage = BACK_MAP[stage]; back_override = True; break
                        raise
                    if not cf or cf.lower() == "all":
                        category_filter = None; break
                    cf_parsed = parse_category_filter(cf, cats)
                    if cf_parsed:
                        category_filter = cf_parsed
                        names = ", ".join(sorted(category_filter))
                        print(f"  {c('Categories:', C.GREEN)} {names}")
                        break
                    print(c(f"  Available: {cat_names}", C.DIM))
                if stage != STAGE_FILTERS: continue
                stage = STAGE_OPTIONS

            # ── Options ───────────────────────────────────────
            elif stage == STAGE_OPTIONS:
                if SETTINGS["auto"].get("options") and not back_override:
                    skip_existing = SETTINGS["default_skip_existing"]
                    dry_run = False; stage = STAGE_DOWNLOAD; continue
                back_override = False

                while True:
                    se_def = "y" if SETTINGS["default_skip_existing"] else "n"
                    try:
                        ans = get_input(prompt_text("Skip existing? (y/n)", f"default: {se_def}")).strip().lower()
                    except CommandAction as e:
                        if e.command == "back": stage = BACK_MAP[stage]; back_override = True; break
                        raise
                    if ans in ("y", "yes", ""): skip_existing = True; break
                    elif ans in ("n", "no"): skip_existing = False; break
                    print(c("  y or n.", C.RED))
                if stage != STAGE_OPTIONS: continue

                while True:
                    try:
                        ans = get_input(prompt_text("Dry run? (y/n)", "default: n")).strip().lower()
                    except CommandAction as e:
                        if e.command == "back": break
                        raise
                    if ans in ("n", "no", ""): dry_run = False; break
                    elif ans in ("y", "yes"): dry_run = True; break
                    print(c("  y or n.", C.RED))
                stage = STAGE_DOWNLOAD

            # ── Download ──────────────────────────────────────
            elif stage == STAGE_DOWNLOAD:
                ERROR_LOG = []  # Reset errors for this run
                os.makedirs(download_path, exist_ok=True)
                cats = SETTINGS.get("categories", FACTORY_SETTINGS["categories"])
                all_stats = []

                mode = c(" [DRY RUN]", C.MAGENTA) if dry_run else ""
                print(f"\n  {c('Starting download', C.BOLD)}{mode}")
                print(f"  {c('Destination:', C.DIM)} {download_path}")
                print(f"  {c('Courses:', C.DIM)} {len(selected)}")
                if week_range:
                    print(f"  {c('Weeks:', C.DIM)} {week_range[0]} to {week_range[1]}")
                if category_filter:
                    print(f"  {c('Categories:', C.DIM)} {', '.join(sorted(category_filter))}")
                t0 = time.time()

                for co in selected:
                    print(f"\n{'='*60}")
                    print(c(f"  {co['code']} - {co.get('name', '')}", C.BOLD))
                    print(f"{'='*60}")
                    try:
                        stats = download_course(co, download_path, skip_existing, cats,
                                                dry_run, week_range, category_filter)
                    except Exception as e:
                        msg = f"Unexpected error downloading {co['code']}: {e}"
                        log_error(co["code"], msg, traceback.format_exc())
                        print(c(f"  {msg}", C.RED))
                        stats = {"downloaded": 0, "skipped": 0, "failed": 0, "filtered": 0,
                                 "total": 0, "size_bytes": 0, "categories": {}, "files": [],
                                 "total_weeks": 0, "errors": [msg]}
                    all_stats.append((co, stats))

                elapsed = time.time() - t0
                stage = STAGE_REPORT

            # ── Report ────────────────────────────────────────
            elif stage == STAGE_REPORT:
                print(f"\n{'='*60}")
                print(c("  FINAL REPORT", C.BOLD + C.CYAN))
                print(f"{'='*60}")

                tot_dl = sum(s["downloaded"] for _, s in all_stats)
                tot_sk = sum(s["skipped"] for _, s in all_stats)
                tot_fl = sum(s["failed"] for _, s in all_stats)
                tot_ft = sum(s.get("filtered", 0) for _, s in all_stats)
                tot_sz = sum(s["size_bytes"] for _, s in all_stats)

                for co, stats in all_stats:
                    print_course_report(co, stats)

                elapsed_str = f"({elapsed:.1f}s)"
                print("\n  " + c("Grand total:", C.BOLD) + " "
                      + c("dl:" + str(tot_dl), C.GREEN) + "  "
                      + c("skip:" + str(tot_sk), C.YELLOW) + "  "
                      + c("fail:" + str(tot_fl), C.RED) + "  "
                      + (c("filt:" + str(tot_ft), C.MAGENTA) + "  " if tot_ft else "")
                      + c(fmt_size(tot_sz), C.DIM) + "  "
                      + c(elapsed_str, C.DIM))

                if not dry_run:
                    save_manifest(download_path, all_stats)
                    save_error_log(download_path)
                    SETTINGS["last_run"] = datetime.now().isoformat()
                    save_settings()

                print_error_summary()

                # ── Cycle back instead of exiting ─────────────
                stage = STAGE_DONE

            # ── Done (loop back) ──────────────────────────────
            elif stage == STAGE_DONE:
                print(c("\n  --- Cycle complete. Starting new selection. ---", C.CYAN))
                print(c("  (Type --exit to quit)\n", C.DIM))
                selected = []
                all_stats = []
                week_range = None
                category_filter = None
                ERROR_LOG = []
                stage = STAGE_COURSE_SELECT

        except CommandAction as e:
            if e.command == "exit":
                print(c("\n  Goodbye!", C.CYAN)); break
            elif e.command == "clear":
                clear_screen(); stage = STAGE_COURSE_SELECT
                selected = []; all_stats = []; back_override = False; continue
            elif e.command == "restart":
                stage = STAGE_COURSE_SELECT
                selected = []; all_stats = []; back_override = False; continue
            elif e.command == "back":
                if stage in BACK_MAP:
                    stage = BACK_MAP[stage]; back_override = True
                else:
                    print(c("  Already at the first step.", C.YELLOW))
                continue
        except Exception as e:
            # Catch-all for truly unexpected errors
            print(c(f"\n  Unexpected error: {e}", C.RED))
            log_error("main", str(e), traceback.format_exc())
            print(c("  The script will continue. Type --exit to quit.", C.YELLOW))
            stage = STAGE_COURSE_SELECT
            selected = []; all_stats = []
            continue

    try: input("\n  Press Enter to exit...")
    except: pass

if __name__ == "__main__":
    main()
