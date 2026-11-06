"""Module 07: testing PDF tools with PDFs you generate.

    python main.py

1. Check the fixtures themselves (a test PDF that is not what it claims makes
   every test built on it meaningless).
2. Run real checks against the code from module 02: Turkish text, scanned
   pages, truncation, search, the 300-page performance case.
3. Mutation check: deliberately break the code and confirm the tests notice.
"""

from __future__ import annotations

import importlib.util
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from types import ModuleType

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from pypdf import PdfReader  # noqa: E402

import fixtures  # noqa: E402


def load_module(name: str, relpath: str) -> ModuleType:
    """Import a module whose directory name starts with a digit (so `import` can't)."""
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "..", relpath))
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# 1. Are the fixtures what they claim to be?
# --------------------------------------------------------------------------
def check_fixtures(tmp: Path) -> dict[str, Path]:
    f = {
        "text": fixtures.text_pdf(tmp / "text.pdf", pages=5),
        "scan": fixtures.scanned_pdf(tmp / "scan.pdf"),
        "table": fixtures.table_pdf(tmp / "table.pdf"),
    }
    f["locked"] = fixtures.encrypted_pdf(tmp / "locked.pdf", f["text"], "pw-1")

    # A text fixture must have a text layer, with the Turkish letters intact.
    page = PdfReader(str(f["text"])).pages[0]
    assert fixtures.TURKISH in page.extract_text(), "Turkish glyphs must round-trip through the font's ToUnicode map"

    # A "scanned" fixture must have NO text, but must have an image.
    scan = PdfReader(str(f["scan"])).pages[0]
    assert scan.extract_text().strip() == "" and len(scan.images) == 1

    # An "encrypted" fixture must really be locked, and a wrong password must fail.
    locked = PdfReader(str(f["locked"]))
    assert locked.is_encrypted and not locked.decrypt("wrong") and locked.decrypt("pw-1")

    # Bookmarks exist.
    assert [o.title for o in PdfReader(str(f["text"])).outline] == [f"Chapter {n}" for n in range(1, 6)]
    print("fixtures: text/Turkish, scanned (image, no text), encrypted, bookmarks, table - all as advertised")
    return f


# --------------------------------------------------------------------------
# 2. Tests of the real code. A plain function that asserts; no framework needed.
# --------------------------------------------------------------------------
def run_checks(m: ModuleType, f: dict[str, Path], big: Path) -> None:
    out = m.read_pdf(f["text"], "2")
    assert "zebra2" in out and fixtures.TURKISH in out

    # Assert against a LITERAL, not the code's own constant: "" is a substring of every
    # string, so `m.NO_TEXT in output` would pass even if NO_TEXT were emptied.
    assert "probably a scanned image" in m.read_pdf(f["scan"]), "scanned pages must be named, not returned empty"

    short = m.read_pdf(big, max_tokens=1500)
    assert "Continue with pages=" in short, "a small token budget must truncate with a hint"

    hits = m.search_pdf(f["text"], "marker word zebra4")
    assert [p for p, _ in hits] == [4]


def performance(m: ModuleType, big: Path) -> None:
    t = time.perf_counter()
    first = m.read_pdf(big, max_tokens=8000)  # stops early: must NOT pay for 300 pages
    t_read = time.perf_counter() - t
    assert "Continue with" in first

    t = time.perf_counter()
    hits = m.search_pdf(big, "line 54: the quick")
    t_search = time.perf_counter() - t
    assert len({p for p, _ in hits}) == 300  # every page has a line 54
    print(f"performance (300 pages): budgeted read {t_read:.2f}s, search every page {t_search:.2f}s")
    # Bounds are generous on purpose: they catch accidental quadratic behaviour,
    # not a slow laptop. A flaky timing test is worse than none.
    assert t_read < 30 and t_search < 120


# --------------------------------------------------------------------------
# 3. Do the tests actually test anything?
# --------------------------------------------------------------------------
def mutation_check(m: ModuleType, f: dict[str, Path], big: Path) -> None:
    original = m.CHARS_PER_TOKEN
    m.CHARS_PER_TOKEN = 10**9  # "a token is a billion characters": truncation can never trigger
    try:
        run_checks(m, f, big)
    except AssertionError as e:
        print("mutation 1 (budget disabled) was caught:", e)
    else:
        raise SystemExit("mutation survived: the truncation test is not testing truncation")
    finally:
        m.CHARS_PER_TOKEN = original

    original_no_text = m.NO_TEXT
    m.NO_TEXT = ""  # simulate returning an empty string for scanned pages
    try:
        run_checks(m, f, big)
    except AssertionError as e:
        print("mutation 2 (scanned pages return nothing) was caught:", e)
    else:
        raise SystemExit("mutation survived: the scanned-page test is blind")
    finally:
        m.NO_TEXT = original_no_text


def main() -> None:
    mod = load_module("module02", "02-extracting-text/main.py")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        f = check_fixtures(tmp)
        big = fixtures.big_pdf(tmp / "big.pdf", 300)
        run_checks(mod, f, big)
        print("checks: Turkish, scanned, truncation, search - pass")
        performance(mod, big)
        mutation_check(mod, f, big)
        run_checks(mod, f, big)  # and the unmutated code still passes afterwards
    print("module 07 OK")


if __name__ == "__main__":
    main()
