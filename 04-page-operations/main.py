"""Module 04: merge, split, extract and rotate pages.

    python main.py

pypdf treats a PDF as a list of page objects you can copy between a reader and
a writer. Everything here is "build a new writer, add pages, write it out".
The original file is never touched.
"""

from __future__ import annotations

import io
import os
import re
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pypdf import PdfReader, PdfWriter  # noqa: E402

import fixtures  # noqa: E402


def parse_pages(spec: str, total: int) -> list[int]:
    """Like module 02, but ORDER and REPEATS are kept: '3,1,3' means pages 3, 1, 3.
    (Reading wants sorted-unique; building a new document wants exactly what was asked.)"""
    out: list[int] = []
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)\s*(?:(-)\s*(\d*))?\s*", part)
        if not m:
            raise ValueError(f"Invalid page range '{part.strip()}'")
        start = int(m.group(1))
        end = (int(m.group(3)) if m.group(3) else total) if m.group(2) else start
        if not (1 <= start <= end <= total):
            raise ValueError(f"Page range '{part.strip()}' does not fit a {total}-page PDF")
        out.extend(range(start - 1, end))
    return out


def save(writer: PdfWriter, out: Path) -> None:
    buf = io.BytesIO()
    writer.write(buf)  # build fully in memory first: a failure leaves no half-written file
    out.write_bytes(buf.getvalue())


def merge(paths: list[Path], out: Path) -> int:
    writer = PdfWriter()
    for p in paths:
        writer.append(PdfReader(str(p)))  # append() also carries over bookmarks
    save(writer, out)
    return len(writer.pages)


def extract_pages(src: Path, spec: str, out: Path) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for i in parse_pages(spec, len(reader.pages)):
        writer.add_page(reader.pages[i])
    save(writer, out)


def split(src: Path, spec: str, out_dir: Path) -> list[Path]:
    """Each comma-separated part of the spec becomes its own file."""
    reader = PdfReader(str(src))
    made = []
    for k, part in enumerate(spec.split(","), 1):
        idx = parse_pages(part, len(reader.pages))
        writer = PdfWriter()
        for i in idx:
            writer.add_page(reader.pages[i])
        label = f"{idx[0] + 1}" if len(idx) == 1 else f"{idx[0] + 1}-{idx[-1] + 1}"
        target = out_dir / f"{src.stem}_part{k}_p{label}.pdf"
        save(writer, target)
        made.append(target)
    return made


def rotate(src: Path, degrees: int, pages: set[int], out: Path) -> None:
    """Rotation is a /Rotate flag on the page, not a re-render: text stays text."""
    if degrees % 90 != 0:
        raise ValueError("degrees must be a multiple of 90")
    writer = PdfWriter()
    writer.append(PdfReader(str(src)))
    for i in pages:
        writer.pages[i].rotate(degrees)
    save(writer, out)


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        a = fixtures.text_pdf(tmp / "a.pdf", pages=5)
        b = fixtures.text_pdf(tmp / "b.pdf", pages=2)

        n = merge([a, b], tmp / "merged.pdf")
        merged = PdfReader(str(tmp / "merged.pdf"))
        assert n == 7 and len(merged.pages) == 7
        assert "zebra1" in merged.pages[5].extract_text()  # b's page 1 follows a's page 5
        assert len([o for o in merged.outline if not isinstance(o, list)]) == 7  # bookmarks kept
        print("merge: 5 + 2 pages ->", n, "pages, bookmarks kept")

        parts = split(a, "1-2,4,5-", tmp)
        sizes = [len(PdfReader(str(p)).pages) for p in parts]
        assert [p.name for p in parts] == ["a_part1_p1-2.pdf", "a_part2_p4.pdf", "a_part3_p5.pdf"]
        assert sizes == [2, 1, 1]
        print("split:", [p.name for p in parts])

        extract_pages(a, "4,2,2", tmp / "picked.pdf")
        picked = PdfReader(str(tmp / "picked.pdf"))
        assert [("zebra%d" % z) in picked.pages[i].extract_text() for i, z in enumerate((4, 2, 2))] == [True] * 3
        print("extract: order and repeats kept")

        rotate(a, 90, {1, 2}, tmp / "rot.pdf")
        assert [p.rotation for p in PdfReader(str(tmp / "rot.pdf")).pages] == [0, 90, 90, 0, 0]
        rotate(tmp / "rot.pdf", -90, {1}, tmp / "rot2.pdf")  # rotations accumulate
        assert [p.rotation for p in PdfReader(str(tmp / "rot2.pdf")).pages] == [0, 0, 90, 0, 0]
        print("rotate: ok")

        # The source was never modified.
        assert len(PdfReader(str(a)).pages) == 5 and all(p.rotation == 0 for p in PdfReader(str(a)).pages)

        # Bad input is a clear error. (Module 05 adds the habit of validating ALL parts before writing any.)
        try:
            split(a, "1-9", tmp)
        except ValueError as e:
            print("error ->", e)
        else:
            raise AssertionError("1-9 on a 5-page PDF should fail")

    print("module 04 OK")


if __name__ == "__main__":
    main()
