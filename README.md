# GIU CMS Downloader

Click-to-launch course file downloader for the GIU CMS portal.

The script downloads course files, sorts them into readable folders, and keeps
the workflow fast enough for repeated use during the semester.

## Features

- Interactive mode with `--help`, `--back`, `--restart`, and `--settings`.
- CLI mode for specific courses, all courses, dry runs, week filters, and category filters.
- Course file categorization into folders such as Lectures, Labs, Tutorials, PA, Projects, Exams, Sheets, and Notes.
- Skip-existing behavior for repeated downloads.
- Session-only credentials; username and password are not saved to disk.
- Download manifest and error logging after real runs.
- Lightweight tests for parsing, categorization, filenames, and formatting helpers.

## Installation

1. Install Python 3.10 or newer.
2. Clone this repository.
3. Make sure `curl` is available from the terminal.
4. Run the script from the repository folder.

No Python package installation is required.

## Usage

Interactive mode:

```bash
python cms_downloader.py
```

Download specific courses:

```bash
python cms_downloader.py 2576 2574
```

Download all active courses:

```bash
python cms_downloader.py all
```

Preview without downloading:

```bash
python cms_downloader.py 2576 --dry-run
```

Filter by week or category:

```bash
python cms_downloader.py 2576 --weeks 1-5
python cms_downloader.py 2576 --only lectures,pa
```

List courses:

```bash
python cms_downloader.py --list-courses
```

## Credentials

Credentials are held in memory for the current session only. The settings file
stores workflow preferences, not the CMS password. The repository ignores
`cms_downloader_settings.json` so local preferences do not get committed.

## Quick test

Run the local test script:

```bash
python tests/run_tests.py
```

The tests avoid network calls and do not require GIU CMS credentials.

## Notes

This is a personal academic utility for organizing course material. It assumes
the GIU CMS page structure remains close to the current version; if the portal
HTML changes, the parsing functions may need to be updated.

