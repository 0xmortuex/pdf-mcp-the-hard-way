# Module 07: Testing with Generated PDFs

## The Concept

You can't test a PDF tool with "a PDF I had lying around": it may be copyrighted, it
won't be in the repo, and you don't know what's inside it. Generate the inputs. With
reportlab you can produce a PDF with *exactly* the properties a test needs: a known marker
word on page 3, a table with a pipe character in a cell, a page that is only an image.

reportlab is a **test-only** dependency. The server itself only needs pypdf and
pdfplumber, so users never install it.

## `fixtures.py`

| Function | What it makes | What it tests |
|----------|---------------|---------------|
| `text_pdf` | N pages, a unique `zebraN` per page, Turkish text, one bookmark per page | extraction, ranges, search, Unicode, outline |
| `table_pdf` | a ruled 4x3 table (includes `Gadget \| Pro`) | `lines` strategy, markdown escaping |
| `borderless_pdf` | aligned words with no rules | `text` strategy, "no tables" advice |
| `scanned_pdf` | pages holding only an image | the no-text-layer path |
| `encrypted_pdf` | any PDF re-saved with AES-256 | password handling |
| `big_pdf` | dense pages (default 300) | performance |

Two details are worth stealing:

**A unique marker per page** (`zebra3`) turns "did we read the right page?" into a substring
check. Pages that all say "Lorem ipsum" can't tell you if page 3 and page 4 were swapped.

**A font that can draw Turkish.** reportlab's built-in Helvetica has no `ş`, `ğ` or `İ`.
The fixtures register `Vera.ttf`, which ships inside reportlab, so the test needs no
font installed and passes identically on Windows, macOS and Linux CI.

## Test the Fixtures First

`main.py` begins by asserting each fixture is what it claims: the text fixture really
yields the Turkish string, the "scanned" fixture really has one image and no text, the
"encrypted" fixture really rejects a wrong password. A scanned-PDF test built on a fixture
that accidentally has text would pass for the wrong reason forever.

## Assert Against Literals

```python
assert "probably a scanned image" in output      # good
assert m.NO_TEXT in output                       # blind spot
```

The second form passes if someone sets `NO_TEXT = ""`, because an empty string is a
substring of everything. `main.py`'s second mutation proves it: it empties the constant and
the literal-based check catches it.

## Performance Tests Without Flakiness

A 300-page document checks two things: the budgeted `read_pdf` stops early (it must not
decode 300 pages to return 8000 tokens), and `search_pdf` over every page finishes. The
time bounds are deliberately generous (30 s, 120 s); on a normal machine the read takes
well under a second and the search a couple of seconds. The test exists to catch an
accidental quadratic loop, not to benchmark. A timing test that fails on a slow CI runner
gets disabled, and then it protects nothing.

## Mutation Check: Do the Tests Test Anything?

`mutation_check` deliberately breaks the code (a token is "a billion characters", so
truncation can never trigger; scanned pages return nothing) and requires the checks to
**fail**. If a mutation survives, the corresponding test is decoration. You can do this
by hand on any project: break the code on purpose and see which test notices.

## Beyond This Course

The finished project adds what a CI needs: a real MCP stdio handshake test against the
installed package, tests of the allow-list with symlinks, and a matrix over operating
systems. See the `tests/` folder of pdf-toolkit-mcp, which follows this module's pattern.

## Run It

```bash
python main.py       # this module
python ../verify.py  # the whole course
```

## Key Takeaways

- Generate PDFs; give each page a unique, searchable marker.
- Test the fixtures before the code.
- Assert against literal expected text, never the code's own constants.
- Keep performance bounds generous; check the *shape* (stops early), not the stopwatch.
- Break your code on purpose to prove the tests can fail.
