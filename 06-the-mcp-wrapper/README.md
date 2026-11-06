# Module 06: The MCP Wrapper

## The Concept

The previous modules built functions. An MCP server is those functions plus three things:
**names and descriptions** the model reads, **a schema** for the arguments, and **errors
the model can read**. This module wraps a condensed version of modules 02, 04 and 05 as
three tools and tests it the way a real client uses it.

## What the Model Sees

`MCPServer` turns a typed Python function into a tool:

```python
@tool
def read_pdf(path: str, pages: str | None = None, max_tokens: int = 8000, password: str | None = None) -> str:
    """Text of the selected pages ('1-3,5,7-', 1-based; empty = all), capped near max_tokens.
    If cut off, the last line says which pages= value continues."""
```

- the function name is the tool name
- the type hints become the JSON Schema (`pages` is optional, `max_tokens` is an integer)
- the docstring becomes the description: **this is the only documentation the model
  has**. State the range grammar, the default, and what the output looks like when it's cut.

The `instructions=` string passed to `MCPServer(...)` is sent once at the handshake: a
short manual for how the tools fit together ("start with `pdf_info`, then `read_pdf`").

## The Error Trap

This is the part most tutorials get wrong. In `mcp` 2.x, if a tool raises an ordinary
exception, the client receives only `Error executing tool X` with **no detail**. The agent
can't tell "page out of range" from "server crashed", so it can't fix its call.

Only a `ToolError`'s message is forwarded. So the `tool` decorator catches the
expected failure type (`PdfToolError`) and re-raises it as `ToolError(str(e))`:

```python
try:
    return fn(*args, **kwargs)
except PdfToolError as e:
    raise ToolError(str(e)) from e
```

Two design points:

- **Catch a specific type, not `Exception`.** `PdfToolError` is raised only where we wrote
  the message for the agent. A genuine bug (an `AttributeError`) should stay hidden from
  the client and visible in the server's stderr, not be presented as advice.
- **Every expected failure has an actionable message**: what's wrong, and what to do.
  `Refusing to overwrite X. Pass overwrite=true or choose another output_path.`

## Three Tools Are Enough to Start

`pdf_info` first (is it encrypted? scanned? how long?), `read_pdf` to read it, `extract_pages`
to produce a file. The finished server has nine, but each follows this shape. Notice that
`pdf_info` reports `Text layer: NO - looks scanned, OCR needed`: the module 01 insight,
delivered to the agent *before* it wastes a `read_pdf` call.

## Testing Over Real stdio

`main.py` plays both roles. With `--serve --dir FOLDER` it is the server. Without flags it
is a client that launches *itself* as `python main.py --serve ...` and talks MCP over the
child's stdin/stdout, which is exactly what Claude Desktop does:

```
client (demo) --- JSON-RPC over pipes ---> server (subprocess)
  initialize / tools/list / tools/call
```

It checks that the tool list is exactly the three expected names, that real PDFs produce the
right text (including Turkish letters, which also proves the UTF-8 path end to end), and
that the *error text* survives the trip: `overwrite=true`, `has 4 pages`, `outside the allowed
folders`. A unit test of the function alone cannot catch the `ToolError` problem, because
the failure is in how the framework relays the exception.

A stdio server has one hard rule: **stdout belongs to the protocol**. A stray `print()` in
a tool corrupts the JSON stream. Diagnostics go to stderr.

## Run It

```bash
python main.py
```

To use it from Claude Code:

```bash
claude mcp add minipdf -- python /full/path/to/06-the-mcp-wrapper/main.py --serve --dir ~/Documents
```

## Key Takeaways

- Name, type hints and docstring are the model's entire manual: write them as one.
- Re-raise expected errors as `ToolError`; leave bugs as bugs.
- Test through the real transport, including the error path.
- Never print to stdout from a stdio server.
