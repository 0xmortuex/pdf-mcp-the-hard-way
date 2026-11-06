# Break It: Extracting Text

## Challenge 1: Clamp Instead of Fail

Change `parse_pages` so that a range past the end is clamped (`"2-99"` on a 5-page PDF
becomes `2-5`) instead of raising. Ask for `pages="9"`. What does the agent get?

**Hint:** For a range, clamping looks friendly. For a single page that doesn't exist it
produces an empty selection or the wrong page, with no signal. An agent that asked for page
9 of a 5-page document needs to be told it only has 5, because that usually means it is
looking at the wrong file.

## Challenge 2: Truncate Mid-Page

Make `read_pdf` cut the text at exactly `max_tokens * 4` characters instead of stopping at
a page boundary. What does the "Continue with" hint become, and how does the agent resume?

**Hint:** There is no `pages=` value that means "the second half of page 3", so the hint
cannot be an argument anymore; the agent has to re-read the whole page. Page-boundary
truncation is what makes the hint pasteable.

## Challenge 3: The Infinite Loop

Set `max_tokens=10` on the 40-page PDF. Remove the `and blocks` condition from the budget
check in `read_pdf`. What happens, and why does the original code avoid it?

**Hint:** Without `and blocks`, the first page doesn't fit the budget, so nothing is
returned and the hint says "continue at page 1". The agent follows it forever. Every
paginated API needs a rule that guarantees progress.

## Challenge 4: Break the Search

Replace the whitespace-tolerant regex in `search_pdf` with a plain `query.lower() in
text.lower()`. Search for `"split across two lines"` in a PDF whose text wraps that phrase
(draw it with two `drawString` calls at different heights). Then search for the Turkish
`"İSTANBUL"`. What do you find?

**Hint:** Plain substring search misses phrases that wrap, since the PDF text contains a
newline where the query has a space. And Turkish case folding is a trap: `"İSTANBUL".lower()`
is `"i̇stanbul"` (an `i` plus a combining dot, two characters), which does not equal
`"istanbul"`, so a `lower()`-based search misses it. The original code uses
`re.IGNORECASE`, which does match `İ` with `i` and `ı` with `I`. Test the behaviour you
actually promise callers, with the real letters.
