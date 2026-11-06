"""Module 01: what is inside a PDF - built by hand, then checked against pypdf.

    python main.py

Part 1 writes a complete one-page PDF byte by byte (objects, cross-reference
table, trailer) and proves a real parser can read it.
Part 2 looks at a reportlab-made PDF the way a parser must: find startxref,
read the trailer, follow /Root -> /Pages -> page objects.
Part 3 shows the difference between a text page and a scanned page at the level
of the page's drawing instructions.
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


# --------------------------------------------------------------------------
# Part 1: write a PDF by hand
# --------------------------------------------------------------------------
def build_minimal_pdf(text: str) -> bytes:
    """A PDF is: header, numbered objects, an xref table of their byte offsets, a trailer.

    The xref table is why PDFs can be opened without reading the whole file: the
    trailer (at the END of the file) says where the xref is, and the xref says
    where every object starts. That is also why a truncated download is
    unreadable - the end is the part that is missing.
    """
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))  # byte position where "N 0 obj" begins
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"  # object 0 is always the head of the free list
    for off in offsets:
        out += b"%010d 00000 n \n" % off  # every entry is exactly 20 bytes
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    out += b"startxref\n%d\n%%%%EOF\n" % xref_pos
    return bytes(out)


def part1(tmp: Path) -> None:
    data = build_minimal_pdf("Hello from raw bytes")
    path = tmp / "hand.pdf"
    path.write_bytes(data)
    reader = PdfReader(str(path))
    assert len(reader.pages) == 1
    assert reader.pages[0].extract_text().strip() == "Hello from raw bytes"
    print("part 1: a hand-written PDF opens in pypdf and says:", reader.pages[0].extract_text().strip())

    # Break the xref offset by one byte: strict readers complain, pypdf rebuilds the table by scanning.
    damaged = data.replace(b"startxref\n", b"startxref\n9", 1)
    (tmp / "damaged.pdf").write_bytes(damaged)
    recovered = PdfReader(str(tmp / "damaged.pdf"))
    assert len(recovered.pages) == 1
    print("part 1: with a corrupt startxref pypdf still recovers the page by scanning for objects")


# --------------------------------------------------------------------------
# Part 2: read the structure of a real file
# --------------------------------------------------------------------------
def part2(tmp: Path) -> None:
    path = fixtures.text_pdf(tmp / "doc.pdf", pages=3)
    raw = path.read_bytes()

    assert raw.startswith(b"%PDF-")
    print("part 2: header ->", raw[:8])

    startxref = int(re.search(rb"startxref\s+(\d+)\s+%%EOF\s*$", raw).group(1))  # type: ignore[union-attr]
    print(f"part 2: startxref says the xref starts at byte {startxref}: {raw[startxref:startxref + 4]!r}")

    # Counting "/Type /Page" objects by regex works for this file but is NOT how
    # to do it: modern PDFs pack objects into compressed object streams where a
    # regex cannot see them. The reliable way is to walk /Root -> /Pages -> /Kids.
    naive = len(re.findall(rb"/Type\s*/Page\b", raw))
    reader = PdfReader(str(path))
    walked = len(reader.pages)
    assert walked == 3
    print(f"part 2: regex counted {naive} page objects, the page tree has {walked}")

    root = reader.trailer["/Root"]
    assert root["/Type"] == "/Catalog"
    assert "/Outlines" in root  # bookmarks hang off the catalog
    print("part 2: catalog keys:", sorted(root.keys()))
    print("part 2: metadata:", reader.metadata.title)


# --------------------------------------------------------------------------
# Part 3: a "text" page versus a "scanned" page
# --------------------------------------------------------------------------
def operators(page) -> set[str]:  # type: ignore[no-untyped-def]
    content = page.get_contents().get_data().decode("latin-1")
    return set(re.findall(r"\b(Tj|TJ|Do|BT)\b", content))


def part3(tmp: Path) -> None:
    text_page = PdfReader(str(fixtures.text_pdf(tmp / "t.pdf", pages=1))).pages[0]
    scan_page = PdfReader(str(fixtures.scanned_pdf(tmp / "s.pdf", pages=1))).pages[0]

    t_ops, s_ops = operators(text_page), operators(scan_page)
    print("part 3: text page operators   :", sorted(t_ops))
    print("part 3: scanned page operators:", sorted(s_ops))
    # Careful: reportlab opens an empty BT..ET block on every page, so the mere
    # presence of BT proves nothing. What draws glyphs is Tj / TJ.
    assert t_ops & {"Tj", "TJ"}
    assert "Do" in s_ops and not (s_ops & {"Tj", "TJ"})  # "Do" paints an image XObject

    assert text_page.extract_text().strip() != ""
    assert scan_page.extract_text().strip() == ""
    print("part 3: no Tj/TJ operators -> extract_text() returns '' -> the server must say 'scanned', not return nothing")


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        part1(tmp)
        part2(tmp)
        part3(tmp)
    print("module 01 OK")


if __name__ == "__main__":
    main()
