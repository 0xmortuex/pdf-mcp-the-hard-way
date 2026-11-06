# Break It: The MCP Wrapper

## Challenge 1: Raise a Plain Exception

In the `tool` decorator, delete the `except PdfToolError` clause so the exception
propagates. Run `main.py`. What does the client see for the out-of-range page request, and
which assertion fails?

**Hint:** The client receives `Error executing tool read_pdf` with no explanation, so the
`has 4 pages` assertion fails. The server log (stderr) has the full traceback; the model
sees none of it. This is the difference between an error the agent can act on and one it can
only retry.

## Challenge 2: A Stray Print

Add `print("debug")` as the first line of `pdf_info`. Run `main.py`. What fails, and where?

**Hint:** In stdio transport, stdout *is* the JSON-RPC stream. The client tries to parse
`debug` as a message and the session breaks or logs a parse error. Use
`print(..., file=sys.stderr)` or the `logging` module.

## Challenge 3: Catch Everything

Change the decorator to `except Exception as e: raise ToolError(str(e))`. Now cause a real
bug (misspell an attribute inside `read_pdf`). What does the agent see, and is that good?

**Hint:** The agent now sees an `AttributeError` message presented as if it were advice, and
will try to "fix" its arguments to work around a server bug. Catching broad exceptions
hides which failures are the caller's and which are yours. Keep the decorator narrow.

## Challenge 4: A Vague Docstring

Replace the `read_pdf` docstring with `"""Read a PDF."""`. Ask a model (or yourself, using
only the tool list) how to read pages 3 to the end, and what happens when the output is
long.

**Hint:** Without the range grammar and the truncation behaviour in the description, a
model guesses at `pages` ("3:", "3..end", `[3,4,5]`) and gets errors, or doesn't know to
follow the continuation hint. Tool descriptions are prompts; test them like prompts.
