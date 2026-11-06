# Break It: PDF Structure

## Challenge 1: Off By One Byte

After `build_minimal_pdf` returns, shift every xref offset by +1 (rewrite each
`NNNNNNNNNN 00000 n` entry) and open the result from memory with `PdfReader(io.BytesIO(...))`.
Does it still open? What does pypdf print while it does?

**Hint:** It opens and reads the text: pypdf notices that the offsets don't land on
`N 0 obj` and rebuilds the table by scanning ("Object 4 0 found" in the log). Strict
readers and print pipelines are less forgiving, which is why writers compute each offset
from `len(out)` at the moment the object is appended instead of by hand.

## Challenge 2: Truncate the Download

Write the first 90% of the bytes of `hand.pdf` and open them with `PdfReader`. What exception
do you get? Make a `pdf_info` that catches it and tells the agent something it can act on.

**Hint:** The trailer and `startxref` are at the end, so a truncated file has no index.
pypdf raises `PdfStreamError: Stream has ended unexpectedly` (a `PyPdfError`). The agent
message should say the file looks incomplete or damaged, not show a traceback; the finished
server wraps `PyPdfError` into "`name.pdf` could not be read as a PDF: ...".

## Challenge 3: Why Not Count With a Regex?

Part 2 counts `/Type /Page` with a regex and gets the right answer. Find or make a PDF where
it gives the wrong one (try saving a few real-world PDFs from different producers, or a
PDF/A export from a word processor) and compare with `len(reader.pages)`.

**Hint:** Some producers pack objects into compressed object streams, where `/Type /Page` is
not visible in the raw bytes at all. The regex also over-counts if you drop the word boundary after `Page`
(it then matches `/Type /Pages`). The page tree walk is the only version that is always right.

## Challenge 4: Is This Page Scanned?

Write `is_scanned(page)` that returns True when a page has an image but no `Tj`/`TJ`.
Then build a page that has *both* a full-page scan image **and** an invisible text layer
(what OCR software produces). What should your function say, and what does `extract_text()`
return?

**Hint:** Searchable scans have a real text layer on top of the image, so text extraction
works and the page is not "scanned" for our purposes. That is why the decision should rest
on "can I extract text?", not on "is there an image?".
