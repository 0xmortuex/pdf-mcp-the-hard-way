"""Module 06: wrapping it as an MCP server - three tools, tested over real stdio.

Two roles live in this one file:

  python main.py --serve --dir FOLDER
      Runs the MCP server (what Claude Desktop / Claude Code would launch).

  python main.py
      Runs the demo: makes a PDF in a temp folder, starts ITSELF with --serve
      as a subprocess, connects as an MCP client, lists the tools, calls them,
      and checks that errors reach the agent as readable text.
"""

from __future__ import annotations

import argparse
import asyncio
import functools
import os
import re
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from mcp.server.mcpserver import MCPServer  # noqa: E402
from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402
from pypdf import PdfReader, PdfWriter  # noqa: E402

CHARS_PER_TOKEN = 4


class PdfToolError(Exception):
    """Expected, explainable failure: its message goes to the agent."""


# ---- the pieces from modules 02, 04 and 05, condensed ----------------------
ALLOWED: list[Path] = [Path.cwd().resolve()]


def _parts(p: Path) -> tuple[str, ...]:
    return Path(os.path.normcase(str(p))).parts


def inside_allowed(p: Path) -> bool:
    return any(_parts(p)[: len(_parts(root))] == _parts(root) for root in ALLOWED)


def resolve(raw: str, must_exist: bool = True) -> Path:
    p = Path(raw)
    p = (ALLOWED[0] / p) if not p.is_absolute() else p
    p = p.resolve()
    if not inside_allowed(p):
        raise PdfToolError(f"'{raw}' is outside the allowed folders. Start the server with --dir <folder>.")
    if must_exist and not p.exists():
        raise PdfToolError(f"File not found: {p}")
    return p


def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec or not spec.strip():
        return list(range(total))
    out: list[int] = []
    for part in spec.split(","):
        m = re.fullmatch(r"\s*(\d+)\s*(?:(-)\s*(\d*))?\s*", part)
        if not m:
            raise PdfToolError(f"Invalid page range '{part.strip()}'. Use numbers like '1-3,5,7-'.")
        start = int(m.group(1))
        end = (int(m.group(3)) if m.group(3) else total) if m.group(2) else start
        if not (1 <= start <= end <= total):
            raise PdfToolError(f"Page range '{part.strip()}' does not fit this PDF, which has {total} pages.")
        out.extend(range(start - 1, end))
    return out


def open_reader(path: Path, password: str | None) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted and not reader.decrypt(password or ""):
        why = "the password is wrong." if password else "pass the password parameter."
        raise PdfToolError(f"{path.name} is encrypted; {why}")
    return reader


# ---- the MCP layer ----------------------------------------------------------
mcp = MCPServer(
    "mini-pdf",
    instructions="Read PDFs. Start with pdf_info, then read_pdf; extract_pages writes a new file.",
)


def tool(fn: Callable[..., str]) -> Callable[..., str]:
    """Register fn, converting PdfToolError into ToolError.

    MCPServer sends the client ONLY the message of a ToolError. Any other
    exception becomes a bare "Error executing tool X" with no detail, and the
    agent has nothing to act on. So expected failures are re-raised as ToolError.
    """

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        try:
            return fn(*args, **kwargs)
        except PdfToolError as e:
            raise ToolError(str(e)) from e

    # The docstring and type hints become the tool's description and JSON schema.
    mcp.tool()(wrapper)
    return fn


@tool
def pdf_info(path: str, password: str | None = None) -> str:
    """Page count and whether the PDF has a text layer. Call this before read_pdf.

    path: a PDF inside an allowed folder. password: only for encrypted PDFs.
    """
    reader = open_reader(resolve(path), password)
    first = (reader.pages[0].extract_text() or "").strip()
    return f"Pages: {len(reader.pages)}\nText layer: {'yes' if first else 'NO - looks scanned, OCR needed'}"


@tool
def read_pdf(path: str, pages: str | None = None, max_tokens: int = 8000, password: str | None = None) -> str:
    """Text of the selected pages ('1-3,5,7-', 1-based; empty = all), capped near max_tokens.
    If cut off, the last line says which pages= value continues.
    """
    reader = open_reader(resolve(path), password)
    total = len(reader.pages)
    selected = parse_pages(pages, total)
    blocks: list[str] = []
    used = 0
    for n, i in enumerate(selected):
        text = (reader.pages[i].extract_text() or "").strip() or "[No text layer: scanned image]"
        block = f"--- Page {i + 1} of {total} ---\n{text}"
        if used + len(block) > max_tokens * CHARS_PER_TOKEN and blocks:
            blocks.append(f'[Truncated. Continue with pages="{selected[n] + 1}-{selected[-1] + 1}"]')
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


@tool
def extract_pages(path: str, pages: str, output_path: str, overwrite: bool = False, password: str | None = None) -> str:
    """Copy the chosen pages into a NEW pdf at output_path. Never overwrites unless overwrite=true."""
    reader = open_reader(resolve(path), password)
    out = resolve(output_path, must_exist=False)  # same allow-list check as inputs
    if out.exists() and not overwrite:
        raise PdfToolError(f"Refusing to overwrite {out}. Pass overwrite=true or choose another output_path.")
    writer = PdfWriter()
    for i in parse_pages(pages, len(reader.pages)):
        writer.add_page(reader.pages[i])
    with open(out, "wb") as f:
        writer.write(f)
    return f"Wrote {len(writer.pages)} page(s) to {out}"


# ---- the demo client ---------------------------------------------------------
async def demo() -> None:
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    import fixtures

    with tempfile.TemporaryDirectory() as d:
        folder = Path(d).resolve()
        fixtures.text_pdf(folder / "doc.pdf", pages=4)
        fixtures.scanned_pdf(folder / "scan.pdf")

        params = StdioServerParameters(command=sys.executable, args=[__file__, "--serve", "--dir", str(folder)])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
            await s.initialize()
            names = {t.name for t in (await s.list_tools()).tools}
            assert names == {"pdf_info", "read_pdf", "extract_pages"}, names
            print("tools:", sorted(names))

            res = await s.call_tool("pdf_info", {"path": "doc.pdf"})
            assert not res.is_error and "Pages: 4" in res.content[0].text
            res = await s.call_tool("pdf_info", {"path": "scan.pdf"})
            assert "NO - looks scanned" in res.content[0].text
            res = await s.call_tool("read_pdf", {"path": "doc.pdf", "pages": "3"})
            assert "zebra3" in res.content[0].text and fixtures.TURKISH in res.content[0].text
            res = await s.call_tool("extract_pages", {"path": "doc.pdf", "pages": "2-3", "output_path": "mid.pdf"})
            assert not res.is_error and len(PdfReader(str(folder / "mid.pdf")).pages) == 2

            # Errors: an agent must be able to read them and recover.
            res = await s.call_tool("extract_pages", {"path": "doc.pdf", "pages": "1", "output_path": "mid.pdf"})
            assert res.is_error and "overwrite=true" in res.content[0].text
            print("error the agent sees:", res.content[0].text.replace(str(folder), "<dir>"))
            res = await s.call_tool("read_pdf", {"path": "doc.pdf", "pages": "99"})
            assert res.is_error and "has 4 pages" in res.content[0].text
            res = await s.call_tool("pdf_info", {"path": str(folder.parent / "elsewhere.pdf")})
            assert res.is_error and "outside the allowed folders" in res.content[0].text

    print("module 06 OK")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--dir", action="append", default=[])
    args = ap.parse_args()
    if args.serve:
        if args.dir:
            ALLOWED[:] = [Path(x).resolve() for x in args.dir]
        mcp.run()  # speaks JSON-RPC on stdin/stdout until the client disconnects
    else:
        asyncio.run(demo())


if __name__ == "__main__":
    main()
