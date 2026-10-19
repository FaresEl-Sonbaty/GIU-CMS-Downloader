# GIU CMS Downloader

A cross-platform terminal tool that downloads course files from the GIU CMS portal and organizes them into a clean course folder structure.  
It supports interactive prompts, course selection, active/all course listing, week filters, category filters, dry runs, skip-existing downloads, optional saved credentials, manifests, error logs, and command-line one-shot mode.

## Features

- Click-to-launch interactive mode for downloading course material.
- Command-line one-shot mode for specific courses, all courses, dry runs, and filtering.
- Course discovery from the GIU CMS portal.
- Optional active-course or all-course listing.
- Auto-sorts files into readable folders:
  - Lectures
  - Tutorials
  - PA
  - PA_Solutions
  - Labs
  - Lab_Solutions
  - Projects
  - Exams
  - Sheets
  - Notes
  - Other
- Week filters such as `1-5`, `3+`, or a single week number.
- Category filters such as `lectures`, `pa`, `labs`, or comma-separated combinations.
- Skip-existing mode for repeated semester downloads.
- Dry-run mode to preview what would be downloaded.
- **Commands** (prefixed with `--`) at interactive prompts:
  - `--exit` `--clear` `--restart` `--back` `--help` `--help-full` `--settings`
- Undo (`--back`) returns to the previous step.
- Immersive full-screen help (`--help-full`) and a settings panel (`--settings`).
- **Persistent settings** saved in `cms_downloader_settings.json`:
  - Default download path.
  - Default course selection.
  - Skip-existing preference.
  - Active/all course listing preference.
  - Tip visibility.
  - Per-step automation.
  - Category folder names.
  - Optional saved credentials, disabled by default.
- Session-only credentials by default.
- Optional local credential saving from `--settings` for click-to-launch sign-in.
- Saved passwords are base64-obfuscated in the local settings file, not encrypted.
- Download manifest and error log output after real runs.
- Offline regression tests for parsing, credential prompts, authentication errors, and interrupted downloads.
- Visible `*` feedback for password typing in Windows consoles, including backspace.
- Downloads are staged in `.part` files and published only after a complete, nonempty HTTP 200 response.

## Installation

1. Install Python 3.10 or newer (verified with Python 3.11 and 3.14 on Windows).
2. Clone this repository or download and extract its ZIP.
3. Open a terminal in the repository folder and install the dependencies:

```bash
python -m pip install -r requirements.txt
python cms_downloader.py
```

The downloader uses `requests` and `requests-ntlm` for CMS authentication and downloads. **curl is no longer required.** Keep `requirements.txt` with the script when sharing the project.

If you download only the script, install its dependencies with:

```bash
python -m pip install requests requests-ntlm
```

Use the **same Python installation** to install packages and run the downloader. Bare `pip` can point to a different installation. For Windows users who double-click `.py` files, see [Troubleshooting](#troubleshooting) if the file association uses a different Python version.

See [CHANGELOG.md](CHANGELOG.md) for the login and download reliability update.

## Quick test

Run the lightweight test script from the repository root:

    python tests/run_tests.py
    python -m unittest discover -s tests -p "test_*.py"

The tests do not contact GIU CMS and do not require credentials.

## Usage

### Interactive mode
Double-click the script, or run:
```bash
python cms_downloader.py
```
Follow the prompts. At workflow prompts you can type a command, for example `--help`. Password prompts treat input as a password. Windows consoles display `*` while you type; other terminals normally hide password input. Press Enter to submit.

### Selecting courses interactively

Use the numbers in the displayed course list, with inclusive ranges and comma or space separators:

- `1-6` selects courses 1 through 6.
- `1-3, 5, 7-9` selects courses 1, 2, 3, 5, 7, 8, and 9.
- Individual numbers, course IDs, and course codes still work and can be mixed with ranges.

Ranges refer to displayed list positions. Overlapping selections are included once. Reversed or out-of-bounds ranges are rejected so you can correct the selection.

### Command-line one-shot mode
Download specific courses:
```bash
python cms_downloader.py 2576 2574
```

Download all active courses:
```bash
python cms_downloader.py all
```

List enrolled courses:
```bash
python cms_downloader.py --list-courses
```

Preview without downloading:
```bash
python cms_downloader.py 2576 --dry-run
```

Filter by week:
```bash
python cms_downloader.py 2576 --weeks 1-5
python cms_downloader.py 2576 --weeks 3+
```

Filter by category:
```bash
python cms_downloader.py 2576 --only lectures
python cms_downloader.py 2576 --only lectures,pa
```

Available flags:
- `--list-courses` : list courses without downloading
- `--all` with `--list-courses` : include inactive/all visible courses where supported
- `--dry-run` : preview the download plan
- `--weeks RANGE` : restrict files by week range
- `--only CATEGORIES` : restrict files by category
- `--no-pause` : do not pause on exit, useful in scripts

## Settings

Type `--settings` at any prompt to open the settings panel. Changes are saved automatically and persist across runs. You can:
- Change the default download path.
- Change the default course selection.
- Toggle skip-existing behavior.
- Toggle active-course vs all-course listing.
- Show or hide interactive tips.
- Toggle auto-apply for each step individually.
- Rename category folders.
- Enable, update, show/hide, or clear locally saved credentials.
- Update the saved password without retyping the username.
- Switch between presets such as **Ask all**, **Skip all**, and **Factory default**.

The settings file is created next to the script as `cms_downloader_settings.json`. Deleting it restores defaults.

Credential saving is off by default. If enabled, the settings file stores your username and a base64-obfuscated password so the script can sign in automatically next time. This is convenient, but it is not encryption; only enable it on a personal machine you trust.

## Examples

**Interactive semester download**
```
python cms_downloader.py
```
Then choose courses, download path, week/category filters, and skip-existing behavior from the prompts.

**Download two courses**
```bash
python cms_downloader.py 2576 2574
```

**Preview lectures from weeks 1 to 5**
```bash
python cms_downloader.py 2576 --weeks 1-5 --only lectures --dry-run
```

**Download all active courses and skip the ending pause**
```bash
python cms_downloader.py all --no-pause
```

**List all visible courses**
```bash
python cms_downloader.py --list-courses --all
```

## Troubleshooting

### Missing login library even after installing it

There may be multiple Python installations. The downloader checks dependencies before asking for credentials and prints the path of the interpreter that needs the packages. In PowerShell, use that exact path with the `&` call operator:

```powershell
& "C:\path\to\python.exe" -m pip install requests requests-ntlm
& "C:\path\to\python.exe" "C:\path\to\cms_downloader.py"
```

Replace both example paths with the actual paths on your computer. Installing packages into Python 3.11 does not install them into Python 3.14. Close and reopen the downloader after installing dependencies.

### Password changed or saved credentials fail

Enter the new username and password when prompted. Successful sign-in updates the saved credentials if local credential saving is enabled. You can also use `--settings` > Manage credential storage to update them. Passwords retain leading and trailing spaces exactly as typed.

### Old curl/NTLM error or blank “Unexpected HTTP” message

These messages came from the previous curl transport. Replace the old script with the latest version and install the dependencies above. Both login and downloads now use Python NTLM authentication and read HTTP status codes directly.

### Authentication, connection, or certificate errors

HTTP 401/403 indicates that authentication or access was rejected. Check that the same credentials work in the university portal. Timeouts and connection errors are reported separately. Certificate verification is enabled; for certificate errors, check your computer's date and the CMS certificate. Redirects are not followed automatically; an HTTP 3xx response is reported rather than treated as a successful login.

## Development checks

The tests use synthetic credentials and mocked HTTP responses; they do not access GIU CMS or read your settings file.

```bash
python tests/run_tests.py
python -m unittest discover -s tests -p "test_*.py"
python cms_downloader.py --help
```

## Notes

This is a personal academic utility for organizing GIU course material. It assumes the GIU CMS page structure remains close to the current version; if the portal HTML changes, the parsing functions may need updates.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Fares El-Sonbaty
---

**Enjoy!**
