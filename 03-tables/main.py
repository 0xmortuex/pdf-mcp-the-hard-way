"""Module 03: tables.

    python main.py

A PDF has no "table" object: just text fragments at coordinates and, sometimes,
lines. pdfplumber infers tables from those. This module extracts a ruled table
and a borderless one, then formats them as markdown and CSV for an agent.
"""

from __future__ import annotations

import csv
import io
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pdfplumber  # noqa: E402

import fixtures  # noqa: E402


def extract_tables(path: Path, strategy: str = "lines") -> list[list[list[str | None]]]:
    """strategy 'lines': cells are bounded by drawn rules (reliable).
    strategy 'text' : cells are guessed from how words line up (works with no rules, less exact).
    """
    settings = {"vertical_strategy": strategy, "horizontal_strategy": strategy}
    found = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables(table_settings=settings):
                # The 'text' strategy emits all-blank rows between lines of words: drop them.
                rows = [r for r in table if any(clean(c) for c in r)]
                if rows:
                    found.append(rows)
    return found


def clean(cell: Any) -> str:
    """None (an empty cell) -> '', and newlines inside a cell would break a markdown row."""
    return "" if cell is None else re.sub(r"\s+", " ", str(cell)).strip()


def to_markdown(rows: list[list[Any]]) -> str:
    width = max(len(r) for r in rows)
    grid = [[clean(c).replace("|", "\\|") for c in r] + [""] * (width - len(r)) for r in rows]
    lines = ["| " + " | ".join(grid[0]) + " |", "| " + " | ".join("---" for _ in range(width)) + " |"]
    lines += ["| " + " | ".join(r) + " |" for r in grid[1:]]
    return "\n".join(lines)


def to_csv(rows: list[list[Any]]) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows([[clean(c) for c in r] for r in rows])
    return buf.getvalue()


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)

        ruled = fixtures.table_pdf(tmp / "ruled.pdf")
        tables = extract_tables(ruled)
        assert len(tables) == 1 and len(tables[0]) == 4
        md = to_markdown(tables[0])
        print(md)
        assert "| Item | Qty | Price |" in md
        assert "| Gadget \\| Pro | 10 | 120.00 |" in md  # a literal pipe is escaped
        assert "| Şeker | 2 | 3.75 |" in md

        # CSV round-trips through the csv module, so quoting is handled for us.
        parsed = list(csv.reader(io.StringIO(to_csv(tables[0]))))
        assert parsed[2] == ["Gadget | Pro", "10", "120.00"]

        # The same strategy finds nothing in a borderless table - and that must be
        # reported with advice, not as an empty answer.
        plain = fixtures.borderless_pdf(tmp / "plain.pdf")
        assert extract_tables(plain, "lines") == []
        print("lines strategy on a borderless table: no tables (so the tool suggests strategy='text')")
        rows = extract_tables(plain, "text")[0]
        assert len(rows) == 4  # header + 3 data rows, no blank spacer rows
        print(to_markdown(rows))
        assert [clean(c) for c in rows[0]] == ["Name", "Score", "Grade"]
        assert [clean(c) for c in rows[2]] == ["Linus", "88", "B"]

        # Text pages without any table
        assert extract_tables(fixtures.text_pdf(tmp / "t.pdf", pages=1)) == []

    print("module 03 OK")


if __name__ == "__main__":
    main()
