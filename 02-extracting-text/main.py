"""Module 02: extracting text the way an agent needs it.

    python main.py

Builds, step by step: a page-range parser, text extraction with page headers,
scanned-page detection, a token budget with a "continue at" hint, and search.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pypdf import PdfReader  # noqa: E402

import fixtures  # noqa: E402


class PdfToolError(Exception):
    """An expected failure. Its message is written for the agent, not for a developer."""


# --------------------------------------------------------------------------
# Step 1: page ranges.  "1-3,5,7-" -> [0, 1, 2, 4, 6, 7, ...]
# --------------------------------------------------------------------------
def parse_pages(spec: str | None, total: int) -> list[int]:
    """1-based, inclusive ranges in; sorted unique 0-based indexes out."""
    if not spec or not spec.strip():
        return list(range(total))  # no spec means "everything"
    out: set[int] = set()
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)\s*(?:(-)\s*(\d*))?\s*", part)
        if not m:
            raise PdfToolError(f"Invalid page range '{part.strip()}'. Use numbers like '1-3,5,7-'.")
        start = int(m.group(1))
        end = (int(m.group(3)) if m.group(3) else total) if m.group(2) else start
        if not (1 <= start <= end <= total):
            raise PdfToolError(f"Page range '{part.strip()}' does not fit this PDF, which has {total} pages.")
        out.update(range(start - 1, end))
    return sorted(out)


def format_pages(indexes: list[int]) -> str:
    """The inverse: [4, 5, 6, 9] -> '5-7,10'. Used for hints the agent can paste back."""
    nums = sorted(i + 1 for i in indexes)
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(str(nums[i]) if i == j else f"{nums[i]}-{nums[j]}")
        i = j + 1
    return ",".join(parts)


# --------------------------------------------------------------------------
# Step 2: read, flag scanned pages, respect a token budget
# --------------------------------------------------------------------------
CHARS_PER_TOKEN = 4  # crude but stable; exact tokenizers differ per model anyway
NO_TEXT = "[No extractable text on this page: probably a scanned image. OCR is required.]"


def read_pdf(path: Path, pages: str | None = None, max_tokens: int = 8000) -> str:
    reader = PdfReader(str(path))
    total = len(reader.pages)
    selected = parse_pages(pages, total)
    budget = max_tokens * CHARS_PER_TOKEN

    blocks: list[str] = []
    used = 0
    for n, i in enumerate(selected):
        text = (reader.pages[i].extract_text() or "").strip()
        if not text:
            text = NO_TEXT  # never hand the agent an empty string and let it guess why
        block = f"--- Page {i + 1} of {total} ---\n{text}"
        if used + len(block) > budget and blocks:
            # Out of budget. Say exactly what to ask for next: a value the agent can paste.
            rest = selected[n:]
            blocks.append(f'[Truncated. Continue with pages="{format_pages(rest)}" ({len(rest)} more page(s)).]')
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


# --------------------------------------------------------------------------
# Step 3: search with context
# --------------------------------------------------------------------------
def search_pdf(path: Path, query: str, context: int = 40) -> list[tuple[int, str]]:
    reader = PdfReader(str(path))
    # Whitespace in the query matches any whitespace run, so a phrase that the
    # PDF wrapped across two lines is still found.
    rx = re.compile(r"\s+".join(re.escape(w) for w in query.split()), re.IGNORECASE)
    hits = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        for m in rx.finditer(text):
            snippet = re.sub(r"\s+", " ", text[max(0, m.start() - context) : m.end() + context]).strip()
            hits.append((i + 1, snippet))
    return hits


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        # parse_pages
        assert parse_pages("1-3,5,7-", 9) == [0, 1, 2, 4, 6, 7, 8]
        assert parse_pages("", 4) == [0, 1, 2, 3]
        for bad in ("0", "9", "3-1", "x"):
            try:
                parse_pages(bad, 5)
            except PdfToolError as e:
                print(f"bad range {bad!r} -> {e}")
            else:
                raise AssertionError(f"{bad!r} should have been rejected")
        assert format_pages([0, 1, 2, 4, 6, 7]) == "1-3,5,7-8"

        # Turkish text survives extraction (the PDF stores glyph ids; the font's
        # ToUnicode map is what lets a parser recover real characters).
        doc = fixtures.text_pdf(tmp / "doc.pdf", pages=5)
        out = read_pdf(doc, "2")
        assert "zebra2" in out and fixtures.TURKISH in out
        print(out)

        # Scanned pages are named, not silently empty.
        scan = fixtures.scanned_pdf(tmp / "scan.pdf")
        assert NO_TEXT in read_pdf(scan)

        # Token budget on a 40-page document: tiny budget -> truncation with a usable hint.
        big = fixtures.big_pdf(tmp / "big.pdf", pages=40)
        first = read_pdf(big, max_tokens=1500)
        hint = re.search(r'Continue with pages="([^"]+)"', first)
        assert hint, "expected a continue hint"
        print("hint:", hint.group(0))
        next_start = int(hint.group(1).split("-")[0])
        assert f"--- Page {next_start - 1} of 40 ---" in first
        assert f"--- Page {next_start} of 40 ---" not in first
        # Following the hint picks up exactly where we stopped.
        second = read_pdf(big, hint.group(1), max_tokens=1500)
        assert second.startswith(f"--- Page {next_start} of 40 ---")

        # Search, including a phrase that straddles whitespace differences.
        hits = search_pdf(doc, "MARKER   word zebra4")
        assert [p for p, _ in hits] == [4]
        print("search ->", hits[0])

    print("module 02 OK")


if __name__ == "__main__":
    main()
