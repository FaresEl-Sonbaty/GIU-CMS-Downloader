from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "cms_downloader.py"

spec = importlib.util.spec_from_file_location("cms_downloader", MODULE_PATH)
cms_downloader = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(cms_downloader)


def test_safe_filename_removes_windows_reserved_characters() -> None:
    cleaned = cms_downloader.safe_filename('Lecture 1: Intro/Setup? <draft>')
    assert cleaned == "Lecture_1_Intro_Setup_draft"


def test_week_range_parser_matches_current_behavior() -> None:
    assert cms_downloader.parse_week_range("1-5", 12) == (1, 5)
    assert cms_downloader.parse_week_range("3+", 12) == (3, 11)
    assert cms_downloader.parse_week_range("all", 12) is None


def test_category_filter_accepts_partial_names() -> None:
    cats = {"lecture": "Lectures", "assignment": "PA", "lab": "Labs"}
    assert cms_downloader.parse_category_filter("lect,pa", cats) == {"lectures", "pa"}


def test_categorize_uses_title_before_type_fallback() -> None:
    cats = cms_downloader.FACTORY_SETTINGS["categories"]
    assert cms_downloader.categorize("Lecture 3 - Sorting", "", cats) == "Lectures"
    assert cms_downloader.categorize("Lab solution week 2", "", cats) == "Lab_Solutions"
    assert cms_downloader.categorize("Midterm practice", "", cats) == "Exams"


def test_format_size_outputs_readable_units() -> None:
    assert cms_downloader.fmt_size(900) == "900 B"
    assert cms_downloader.fmt_size(2048) == "2.0 KB"
    assert cms_downloader.fmt_size(2 * 1024 * 1024) == "2.0 MB"


if __name__ == "__main__":
    test_safe_filename_removes_windows_reserved_characters()
    test_week_range_parser_matches_current_behavior()
    test_category_filter_accepts_partial_names()
    test_categorize_uses_title_before_type_fallback()
    test_format_size_outputs_readable_units()
    print("5 tests passed")

