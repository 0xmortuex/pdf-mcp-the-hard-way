# Break It: Tables

## Challenge 1: Forget the Pipe

Remove `.replace("|", "\\|")` (the escape is a backslash before the pipe) from `to_markdown` and print the ruled table. Count the
columns in the `Gadget | Pro` row against the header.

**Hint:** The row now has four cells where the header has three, so any markdown renderer
(and any LLM reading it) misaligns the data. Escaping in the output format is part of
extraction, not decoration.

## Challenge 2: Trust the Spacer Rows

Delete the blank-row filter in `extract_tables` and run the borderless example with
`strategy="text"`. How many rows come back, and how would a downstream agent summing the
Score column fare?

**Hint:** Seven rows instead of four; every other row is empty. A sum would still work, but
a "count the rows" or "show the third row" question gets wrong answers. When a library
returns structural noise, filter it where you can prove it is noise (all cells empty).

## Challenge 3: Wrong Strategy on Prose

Run `strategy="text"` on the five-page `fixtures.text_pdf`. What does it report?

**Hint:** Lines of prose have accidental alignment (left margins, repeated indentation), so
the `text` strategy can invent "tables" from ordinary text. That is why `lines` is the
default and `text` is opt-in: false positives cost more tokens and trust than a "no tables
found" message that suggests the fallback.

## Challenge 4: Time It

Time `extract_tables` on all 300 pages of `fixtures.big_pdf` versus `PdfReader` text
extraction on the same file. Then time `extract_tables` on page 250 only.

**Hint:** Table detection was roughly 8x slower per page than plain text when measured on 60 dense
pages (about 5 s versus 0.65 s), which is
why the real tool exposes `pages` and the README tells the agent to locate pages with
search first. Performance limits belong in the tool description, where the agent reads them.
