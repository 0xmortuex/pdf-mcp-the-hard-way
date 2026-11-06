# Module 02: Extracting Text

## The Concept

`PdfReader(path).pages[0].extract_text()` is one line. Turning it into something an agent
can use takes four design decisions, each of which fixes a real failure.

## 1. Page Ranges the Agent Can Type

Agents say "pages 12 to 15", "the first three and page 9", "everything from 7 on". One small
grammar covers all of it: `1-3,5,7-`, 1-based, inclusive, `N-` meaning "to the end".

```
parse_pages("1-3,5,7-", 9)  ->  [0, 1, 2, 4, 6, 7, 8]      # 0-based indexes into reader.pages
```

Two details matter:

- **1-based in, 0-based inside.** Humans and PDF viewers count from 1; Python lists from 0.
  Convert at exactly one place (the parser) and the formatter (`format_pages`) converts back.
- **Fail loudly with the number.** `"Page range '9' does not fit this PDF, which has 5
  pages."` lets the agent fix its own request. Silently clamping to the last page would
  hand back the wrong text with no signal.

## 2. Say Which Page You Are On

Each page is emitted under `--- Page N of M ---`. The agent can then cite pages, and a
truncated result tells it where it stopped.

## 3. Never Return an Empty String

A scanned page makes `extract_text()` return `""`. If you pass that through, the agent sees
an empty page and guesses: maybe it's a blank page, maybe an error, maybe the tool is
broken. Instead:

```
[No extractable text on this page: probably a scanned image. OCR is required.]
```

The agent now knows what to tell the user and not to retry.

## 4. A Token Budget with a Handle

A 300-page PDF is ~150,000 tokens. Returning it all fills the context and costs money. So
`read_pdf` takes `max_tokens` (default 8000, estimated at 4 characters per token) and stops
at a **page boundary** once the next page would not fit. The last line is not prose, it's an
argument:

```
[Truncated. Continue with pages="7-40" (34 more page(s)).]
```

The agent pastes `7-40` back into `pages=` and gets exactly the next chunk. If the user
asked for `pages="1,3,5"`, the hint lists only what remains of *that* selection
(`format_pages` handles non-contiguous sets).

A single page bigger than the whole budget is the edge case: you must still return
*something*, otherwise a small `max_tokens` loops forever. The finished server returns the
start of that page and says it was cut.

Stopping early also keeps a long document fast: pages after the budget are never decoded.

## 5. Search

`search_pdf` finds a phrase and returns `(page, snippet)` pairs so the agent can locate
the right pages and then read only those. Turning the query `"marker word zebra4"` into the
regex `marker\s+word\s+zebra4` means a phrase the PDF wrapped across two lines is still
found: PDF text comes out as lines, not as the sentences the reader sees.

## Unicode

The fixture contains `Çalışma: İstanbul'da öğrenci şarkısı`. PDFs store glyph numbers, not
letters; a font's `ToUnicode` map is what lets a parser recover real characters. reportlab
writes that map for TrueType fonts, so extraction round-trips exactly. (PDFs produced
without a ToUnicode map give garbage no matter which library you use; that's a property of
the file, not a bug in your code.) Also remember to print as UTF-8: the scripts call
`sys.stdout.reconfigure(encoding="utf-8")` because a Windows console defaults to a legacy
code page and would turn `ş` into `?`.

## Run It

```bash
python main.py
```

## Key Takeaways

- Parse a tiny grammar once; convert 1-based to 0-based in one place.
- Name the cause of "no text" instead of returning an empty string.
- Truncate at a page boundary and end with an argument the agent can paste back.
- Whitespace-tolerant search finds phrases that wrap lines.
