# PDF MCP Server — The Hard Way

Build an MCP server that lets an AI agent work with PDFs: read them in budget-sized
pieces, search them, pull out tables, and merge, split and rotate pages. Start from the
raw bytes of a PDF file and end with a tested server that refuses to leave its folder.

At the end you'll have built a minimal version of
[pdf-toolkit-mcp](https://github.com/0xmortuex/pdf-toolkit-mcp) yourself, and you'll
understand the parts most "PDF tool" tutorials skip: **what a PDF actually is**, why
**scanned PDFs return nothing**, and how to **keep an agent that chooses file paths safe**.

## Why This Exists

Most PDF libraries return an empty string when a page is a scan, silently overwrite
output files, and dump 300 pages into a context window. Those are fine for a script you
watch. They are bad for an agent that can't see what went wrong. A good PDF tool for an
agent:

- tells the agent *why* there is no text ("scanned image, OCR needed") instead of returning an empty string
- hands back a bounded amount of text plus the exact `pages=` value to continue
- refuses to write outside its folder or over an existing file
- turns every expected failure into a message the agent can act on

And it does this with **pure-Python wheels only** (pypdf, pdfplumber), so it installs
everywhere with `uvx`, with no Java, Ghostscript or Poppler.

## Who This Is For

- Developers who've built a "hello world" MCP server and want a real one
- Anyone who wants to know how PDF text extraction and table detection actually work
- Anyone designing tools that let an AI touch the file system

**Prerequisites:** Python and basic file I/O. No PDF knowledge needed. Setup:

```bash
uv venv && uv pip install -r requirements.txt     # or: pip install -r requirements.txt
python verify.py                                  # runs all seven modules
```

## Modules

| # | Module | What You'll Build |
|---|--------|-------------------|
| 01 | [PDF Structure](01-pdf-structure/) | A PDF written byte by byte, the xref table, and the difference between a text page and a scanned page |
| 02 | [Extracting Text](02-extracting-text/) | A page-range parser, text with page headers, scanned-page detection, token budgets with a "continue at" hint, search |
| 03 | [Tables](03-tables/) | Ruled and borderless table detection with pdfplumber, markdown and CSV output |
| 04 | [Page Operations](04-page-operations/) | Merge, split, extract and rotate pages without touching the original |
| 05 | [Safety and Paths](05-safety-and-paths/) | A folder allow-list, symlink and `..` escapes, no-overwrite writes, passwords |
| 06 | [The MCP Wrapper](06-the-mcp-wrapper/) | Three tools served over real stdio, and errors that reach the agent |
| 07 | [Testing with Generated PDFs](07-testing-with-generated-pdfs/) | reportlab fixtures (Turkish text, tables, encryption, scans), a 300-page performance test, and a mutation check |

Each module contains:
- **`README.md`**: the concepts and design decisions
- **`main.py`**: a working, commented implementation that checks its own claims with `assert`
- **`break-it.md`**: challenges that break your own code, with hints

`fixtures.py` at the top level generates the test PDFs. Treat it as a given until Module 07
explains it.

## How To Use This Course

**Option A: Build along.** Read the modules in order, run each `main.py`, then do the
break-it challenges.

**Option B: Reference.** Jump to the module you need. Each `main.py` stands alone.

`python verify.py` runs every `main.py` for real and exits non-zero if any claim in a
module no longer holds. Output on Windows: the scripts switch stdout to UTF-8 so Turkish
letters print correctly.

## Key Design Principles

**1. Empty is never an answer.** "No text" has causes (scanned, wrong page, locked file).
Name the cause.

**2. Bound the output.** Every read has a budget, and a cut-off result ends with the
exact argument that continues it.

**3. Errors are instructions.** "Refusing to overwrite X. Pass overwrite=true or choose
another output_path" beats a stack trace.

**4. The agent picks the paths, so the server enforces the boundary.** Allow-list folders,
resolve before checking, never trust string prefixes.

## Tech Stack

- **Language:** Python 3.10+
- **Libraries:** `mcp`, `pypdf`, `pdfplumber`; `reportlab` for test fixtures only
- **Protocol:** MCP over stdio. No system packages.

## License

MIT. Use it, modify it, ship it.

---

Built by [0xmortuex](https://github.com/0xmortuex)
