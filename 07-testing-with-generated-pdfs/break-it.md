# Break It: Testing with Generated PDFs

## Challenge 1: Helvetica Instead of Vera

In `fixtures.text_pdf`, change `c.setFont("Vera", 11)` to `c.setFont("Helvetica", 11)` and run
module 07. What happens, and at which stage?

**Hint:** reportlab's built-in fonts only cover a Western encoding, so drawing the Turkish
string fails while the fixture is being *generated* (a `UnicodeEncodeError`), before any
test runs. That's the good outcome. The dangerous version is a font that quietly substitutes
characters: then the PDF builds, and only a fixture check like "the extracted text equals
`fixtures.TURKISH`" tells you the test input no longer means what you think.

## Challenge 2: A Fixture Lie

Edit `scanned_pdf` so the page also draws a line of text. Run module 07. Which check
catches it, and why is that check placed before the real tests?

**Hint:** `check_fixtures` asserts the scanned page has no text. Without it, the later
"scanned pages must be named" check would fail and you'd go hunting for a bug in `read_pdf`
when the bug is in the test input. Verify inputs first so a failure points at the right
layer.

## Challenge 3: Survive a Mutation

Write a third mutation: make `read_pdf` always start at page 2 (for example by dropping the
first selected page). Does `run_checks` catch it? If not, add the check that would.

**Hint:** The unique `zebraN` markers make this one easy: ask for `pages="1"` and assert
`zebra1` is in the output. Checks that read *every* page can miss an off-by-one that drops
or shifts a page; one-page checks with a marker cannot.

## Challenge 4: Make the Performance Test Lie

Change the performance check to read all 300 pages (`max_tokens=10**9`) and keep the 30 s
bound. How long does it take on your machine? What does that tell you about whether the
budget logic is doing real work?

**Hint:** The gap between a budgeted read (about 0.1 s here, since it stops early) and a
full read of 300 dense pages (about 2.4 s here) is the evidence that truncation saves real work, not just
output size. If they take the same time, the code is decoding pages it throws away.
