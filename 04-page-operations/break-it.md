# Break It: Page Operations

## Challenge 1: Lose the Bookmarks

In `merge`, replace `writer.append(PdfReader(...))` with a loop that calls
`writer.add_page(page)` for each page. Run the merge check.

**Hint:** The pages are all there but the outline is empty, so `main.py`'s bookmark assertion
fails. Bookmarks are not part of pages; they live in the document catalog, and only
`append()` knows to copy and re-point them.

## Challenge 2: Half a Split

Call `split(a, "1-2,4,9", tmp)` on the 5-page document. What is in the folder afterwards?
Then rewrite `split` to validate all parts (and check that no target exists) before
writing any file.

**Hint:** The first two files are written, then the third part raises. The caller sees an
error but the folder has changed. Compute the whole plan first (list of `(target, pages)`),
check it, then execute it. The finished server's `split_pdf` does exactly this.

## Challenge 3: Rotate Past the Spec

Call `rotate(a, 45, {0}, out)`. Then remove the multiple-of-90 check from `rotate` and
call it again. What happens, and who raises it?

**Hint:** The PDF spec allows only multiples of 90 for `/Rotate`, and pypdf enforces it with
`ValueError: Rotation angle must be a multiple of 90`. That message is accurate but it
mentions neither the parameter name nor the unit, and as a raw `ValueError` an MCP server
would hide it from the agent. Validate at the boundary yourself and say "degrees must be a
non-zero multiple of 90 (90 = clockwise quarter turn)".

## Challenge 4: Rotate In Place

Make `rotate(src, 90, {0}, src)` write to the same path it reads from, by constructing the
`PdfReader` and writing straight to `src` with `open(src, "wb")`. Does it work for a large
file?

**Hint:** Opening the destination for writing truncates it while the reader may still be
pulling pages from it lazily, which can produce a corrupted or empty result. Serialising to
memory first (as `save()` does) avoids this for the write itself; module 05 adds the atomic
temp-file swap that makes in-place replacement safe.
