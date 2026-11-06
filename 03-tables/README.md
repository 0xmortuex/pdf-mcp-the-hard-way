# Module 03: Tables

## The Concept

There is no "table" in a PDF. A page is a list of drawing instructions: glyphs at x/y
coordinates, and sometimes straight lines. What looks like a table to a human is words that
happen to line up, perhaps with lines around them. Table extraction is **inference**:
decide which lines and words form a grid.

pdfplumber does that inference with two strategies per axis:

| strategy | A cell boundary is... | Good for | Fails on |
|----------|----------------------|----------|----------|
| `lines` (default) | a drawn rule (line or rectangle edge) | invoices, statements, anything with a grid | tables with no rules |
| `text` | an alignment of words' edges | borderless tables | prose with accidental alignment, ragged columns |

`main.py` runs both on generated PDFs: a ruled table (reportlab `GRID` style) where `lines`
finds all 4x3 cells, and a table made only of aligned words where `lines` finds nothing and
`text` succeeds.

## "Found nothing" Needs Advice

The `lines` strategy returning `[]` on a borderless table is not an error, but if the tool
replies "no tables" the agent gives up. The finished server says *"No tables found. Try
strategy='text' for tables without ruling lines."* The failure mode of the tool is part of
its interface.

## Cleaning What Comes Back

pdfplumber hands you `list[list[str | None]]`. Three details make it usable as text:

- **`None` cells** (merged or empty) become `""`, so every row has the same width.
- **Newlines inside a cell** break a markdown row, so whitespace runs collapse to one space.
- **A literal `|` inside a cell** corrupts the markdown grid; escape it as `\|`. The fixture
  deliberately contains `Gadget | Pro`.
- **Blank spacer rows**: the `text` strategy emits an all-empty row between each pair of
  lines. `main.py` filters rows with no content; without it the Name/Score/Grade table comes
  back as 7 rows instead of 4.

CSV goes through the `csv` module rather than `",".join`, so commas and quotes inside cells
are quoted correctly. The test parses the CSV back and compares cell-for-cell.

## Cost

Table detection is much slower than plain text extraction because pdfplumber analyses every
character and line on the page. That's why the tool takes a `pages` argument and why the
agent should use `search_pdf` to find the right pages first.

## Run It

```bash
python main.py
```

## Key Takeaways

- Tables are inferred from lines (`lines`) or word alignment (`text`).
- An empty result should come with the next thing to try.
- Normalise cells (None, newlines, pipes) and drop blank rows before formatting.
- Use `csv.writer`, never string joins, for CSV.
