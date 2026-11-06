"""Real PDFs for the course, generated with reportlab.

Module 07 explains this file. Until then, treat it as a supplier of test inputs:
every function writes one PDF to the path you give it and returns that path.
"""

from __future__ import annotations

import os
from pathlib import Path

import reportlab
from PIL import Image
from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

# reportlab's built-in fonts (Helvetica...) cannot draw Turkish letters like
# s-cedilla or g-breve. Vera.ttf ships inside reportlab itself and can, so the
# fixtures work on any machine with no font installed.
pdfmetrics.registerFont(TTFont("Vera", os.path.join(os.path.dirname(reportlab.__file__), "fonts", "Vera.ttf")))

TURKISH = "Çalışma: İstanbul'da öğrenci şarkısı, ğüşıöç ĞÜŞİÖÇ"


def text_pdf(path: Path, pages: int = 5) -> Path:
    """`pages` pages, each with a unique marker word zebraN, Turkish text and a bookmark."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setTitle("Test Document")
    for n in range(1, pages + 1):
        c.setFont("Vera", 14)
        c.drawString(72, 720, f"Chapter {n} heading")
        c.setFont("Vera", 11)
        c.drawString(72, 690, f"This page contains the marker word zebra{n} and some text.")
        c.drawString(72, 670, TURKISH)
        c.bookmarkPage(f"p{n}")
        c.addOutlineEntry(f"Chapter {n}", f"p{n}", level=0)
        c.showPage()
    c.save()
    return path


def table_pdf(path: Path) -> Path:
    """One page holding a ruled 4x3 table."""
    data = [["Item", "Qty", "Price"], ["Widget", "4", "9.50"], ["Gadget | Pro", "10", "120.00"], ["Şeker", "2", "3.75"]]
    table = Table(data)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black), ("FONTNAME", (0, 0), (-1, -1), "Vera")]))
    SimpleDocTemplate(str(path), pagesize=letter).build([table])
    return path


def borderless_pdf(path: Path) -> Path:
    """A table made only of aligned words: no ruling lines at all."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Vera", 11)
    rows = [("Name", "Score", "Grade"), ("Ada", "95", "A"), ("Linus", "88", "B"), ("Grace", "91", "A")]
    for r, row in enumerate(rows):
        for col, cell in enumerate(row):
            c.drawString(72 + col * 120, 700 - r * 20, cell)
    c.save()
    return path


def scanned_pdf(path: Path, pages: int = 2) -> Path:
    """Image-only pages, like a scanner makes: pixels, no text layer."""
    img = path.with_suffix(".png")
    Image.effect_noise((200, 100), 60).convert("RGB").save(img)
    c = canvas.Canvas(str(path), pagesize=letter)
    for _ in range(pages):
        c.drawImage(str(img), 72, 500, width=400, height=200)
        c.showPage()
    c.save()
    img.unlink()
    return path


def encrypted_pdf(path: Path, source: Path, password: str = "s3cret-pw") -> Path:
    writer = PdfWriter(clone_from=PdfReader(str(source)))
    writer.encrypt(password, algorithm="AES-256")
    with open(path, "wb") as f:
        writer.write(f)
    return path


def big_pdf(path: Path, pages: int = 300) -> Path:
    """Dense pages (55 lines each) for performance checks."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Vera", 9)
    for n in range(1, pages + 1):
        for line in range(55):
            c.drawString(50, 760 - line * 13, f"Page {n} line {line}: the quick brown fox jumps over the lazy dog 0123456789")
        c.showPage()
    c.save()
    return path
