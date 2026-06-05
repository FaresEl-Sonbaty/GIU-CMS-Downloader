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
- Lightweight non-network tests for parsing, categorization, filename cleaning, and size formatting.

## Installation

  1. Ensure Python 3.10+ is installed.
  2. Ensure `curl` is available from the terminal.
  3. Download `cms_downloader.py` (or clone the repository).
  4. Place it anywhere you like.

No Python package installation is required.

## Quick test

Run the lightweight test script from the repository root:

    python tests/run_tests.py

The tests do not contact GIU CMS and do not require credentials.

## Usage

### Interactive mode
Double-click the script, or run:
```bash
python cms_downloader.py
```
Follow the prompts. At any prompt you can type a command, for example `--help`.

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

## Notes

This is a personal academic utility for organizing GIU course material. It assumes the GIU CMS page structure remains close to the current version; if the portal HTML changes, the parsing functions may need updates.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Fares El-Sonbaty
---

**Enjoy!**
