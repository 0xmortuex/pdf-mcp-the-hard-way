# Module 04: Page Operations

## The Concept

Merge, split, extract and rotate all follow one pattern:

```
reader = PdfReader(source)        # pages you can read
writer = PdfWriter()              # a new, empty document
writer.add_page(reader.pages[i])  # copy the pages you want, in the order you want
writer.write(buffer)              # serialise
```

The source file is never opened for writing, so there's nothing to corrupt. Every "edit" is
really "build a new document".

## The Four Operations

**Merge** uses `writer.append(reader)`, which copies all pages *and* carries the
bookmarks/outline across (adding pages one by one would drop them). `main.py` checks the
merged file has 7 bookmarks: 5 from one PDF and 2 from the other.

**Split** treats each comma-separated part of the range string as its own output file:
`1-2,4,5-` makes three files. The file name records what's inside
(`a_part1_p1-2.pdf`, `a_part2_p4.pdf`), so an agent can find "the file with page 4"
without opening anything. The `partK` prefix keeps names unique when two parts overlap.

**Extract** is the one place where order and repetition *matter*: `4,2,2` means "page 4,
then page 2, then page 2 again". So this module's `parse_pages` deliberately does not sort
or de-duplicate, unlike reading, where `3,1,3` should just mean "pages 1 and 3". Same
grammar, different semantics, decided by what the result is used for.

**Rotate** sets a `/Rotate` entry on the page. It is a viewing hint, not a re-render:
text stays selectable and searchable. Rotations accumulate (`+90` then `-90` returns to 0),
which `main.py` checks, and negative angles mean counter-clockwise. Reject anything that's
not a multiple of 90, because the PDF spec only allows quarter turns.

## Write Fully, Then Save

`save()` serialises into a `BytesIO` first, then writes the bytes in one go. If pypdf fails
halfway (a damaged page, an unsupported feature), no half-written file is left on disk.
Module 05 goes further: it also decides *whether* the target may be written at all.

## Check Everything Before Writing Anything

For `split`, a bad range in the *third* part would leave two finished files and an error.
The finished server therefore parses all parts and checks all output names before writing
the first byte, so a failure leaves the folder exactly as it was. (In `main.py` the bad
range is the first part, which is simply the easiest case to demonstrate. Break-it
challenge 2 asks you to fix the general case.)

## Run It

```bash
python main.py
```

## Key Takeaways

- Every operation is "copy pages into a new writer". Originals are never modified.
- `append()` preserves bookmarks; `add_page()` does not.
- Reading wants sorted-unique pages; building wants the order and repeats as written.
- Serialise in memory, then write. Validate everything before the first write.
