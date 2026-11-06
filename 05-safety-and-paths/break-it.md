# Break It: Safety and Paths

## Challenge 1: Use a String Prefix

Replace `Sandbox._inside` with `str(p).startswith(str(root))`. Does the `inside-evil` check
still pass? Then try the Windows-only variant: allow `C:\Users\You\Docs` and ask for
`c:\users\you\docs\a.pdf`.

**Hint:** `inside-evil` is now allowed, because its path starts with the characters of
`inside`. On Windows the lower-case spelling fails the prefix check even though it's the
same folder, so a naive fix tempts people to lower-case everything, which is wrong on
case-sensitive file systems. Path components plus `os.path.normcase` is right on both.

## Challenge 2: Check Before Resolving

Move `p = p.resolve()` to *after* the containment check. Rerun. Which of the blocked cases
now get through?

**Hint:** `inside/../outside/secret.pdf` and the symlink both pass, because the string looks
inside. Anything that checks a path and later opens it must check the *resolved* path.

## Challenge 3: The Race

Rewrite `write_bytes` as `if out.exists(): raise ...` followed by `out.write_bytes(data)`.
Write a script with two threads that both call it for the same new file. Can both succeed?

**Hint:** With enough tries, yes: both see "doesn't exist", both write, the second silently
replaces the first. `open(out, "xb")` fails for the second thread with `FileExistsError`.
MCP clients can issue calls concurrently, so this isn't hypothetical.

## Challenge 4: Echo the Password

Change the wrong-password message to include the password that was tried ("password 'xyz'
is wrong"). Why might that be a problem even though the agent supplied it?

**Hint:** Error text is returned to the model, often logged by the client, and may be
copied into a chat transcript or bug report. The agent already knows what it sent; echoing
it back adds nothing but another place the secret can leak. Also test it: the assertion in
`main.py` that the password is not in the message is exactly this regression test.
