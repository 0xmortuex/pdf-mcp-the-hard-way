# Module 01: PDF Structure

## The Concept

An agent asks "what's in this PDF?" Before you can answer, you need a picture of what a
PDF file is, because three of the behaviours that surprise people come straight from its
layout:

- why a half-downloaded PDF won't open at all
- why page count is cheap but text is not
- why a *scanned* PDF is full of content and yet has **no text**

## A PDF Is a Numbered Pile of Objects

```
%PDF-1.4                      header
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj      object 1: the document root
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj   object 2: the page list
3 0 obj << /Type /Page ... /Contents 4 0 R >> endobj      object 3: one page
4 0 obj << /Length 48 >> stream BT ... Tj ET endstream endobj   object 4: its drawing instructions
xref                          byte offset of every object
0 5
0000000000 65535 f
0000000009 00000 n
...
trailer << /Size 5 /Root 1 0 R >>
startxref
312                           where the xref table starts
%%EOF
```

Objects point at each other with `N 0 R` ("object N, generation 0"). A reader works
**backwards**: read the last bytes to find `startxref`, jump to the xref table, which says
where each object starts, then follow `/Root` to the catalog, `/Pages` to the page tree,
and each page's `/Contents` to its instructions. That is why a truncated file is
unreadable (the end is the index) and why the page *count* is cheap (one number in the
page tree) while *text* is expensive (every page's instructions must be decoded).

## Pages Don't Contain Text, They Contain Drawing Instructions

A page's content stream is a small program: `BT ... (Hello) Tj ... ET` means "begin text,
show this string, end text". A **scanned** page's program is just `/Im0 Do`: "paint
image Im0". Pixels, no glyphs. There is no text to extract and no library can conjure it
without OCR.

This is the single most important fact for an agent-facing PDF tool: *an empty result from
`extract_text()` does not mean an error and does not mean an empty page*. It usually
means "this is a picture of text". Your tool has to say so.

One trap shows up in `main.py`: reportlab emits an empty `BT ... ET` block on every page,
so looking for `BT` "proves" every page has text. Only `Tj`/`TJ` draw glyphs.

## What `main.py` Does

1. **Writes a PDF by hand**: five objects, an xref table with real byte offsets, a trailer.
   pypdf opens it and reads "Hello from raw bytes". Then it corrupts `startxref`; pypdf
   prints a warning and recovers by scanning for `obj` markers, which is why real-world,
   slightly broken PDFs still open.
2. **Reads a real file's structure**: the `%PDF-` header, `startxref`, the catalog's keys
   (`/Outlines` is where bookmarks live), and a page count by walking the tree, compared
   with a naive regex count. The regex works here but fails on PDFs that pack objects into
   compressed object streams; walking the tree always works.
3. **Compares a text page with a scanned page** at the operator level.

## Run It

```bash
python main.py
```

You will see a pypdf warning (`incorrect startxref pointer`) in the middle: that's the
deliberately corrupted file being repaired.

## Key Takeaways

- A PDF is an index (xref, at the end) plus numbered objects. Read the end first.
- Page count is a metadata lookup; text needs decoding per page. Budget accordingly.
- No `Tj`/`TJ` operators means no text layer: say "scanned", don't return an empty string.
