"""Module 05: safety - folder allow-list, no silent overwrites, passwords.

    python main.py

An agent chooses the paths. Three rules keep that safe:
  1. Every path must resolve inside an allowed folder.
  2. Never replace an existing file unless the caller said so.
  3. Passwords go to the PDF library and nowhere else.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to a legacy codec
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from pypdf import PdfReader  # noqa: E402

import fixtures  # noqa: E402


class PdfToolError(Exception):
    pass


# --------------------------------------------------------------------------
# Rule 1: the allow-list
# --------------------------------------------------------------------------
class Sandbox:
    def __init__(self, dirs: list[Path]) -> None:
        # resolve() makes each root absolute and follows symlinks, once, up front.
        self.dirs = [Path(d).resolve() for d in dirs]

    def resolve(self, raw: str) -> Path:
        p = Path(raw)
        if not p.is_absolute():
            p = self.dirs[0] / p  # relative paths start at the first allowed folder
        # resolve() collapses ".." and follows symlinks, so a path that LOOKS
        # inside but points outside is judged by where it really leads.
        p = p.resolve()
        if not any(self._inside(p, d) for d in self.dirs):
            raise PdfToolError(
                f"'{raw}' is outside the allowed folders ({', '.join(map(str, self.dirs))}). "
                "Start the server with --dir <folder> to allow more."
            )
        return p

    @staticmethod
    def _inside(p: Path, root: Path) -> bool:
        # Compare path COMPONENTS, never string prefixes: "/data/in-evil" starts with
        # the string "/data/in" but is a different folder. normcase folds Windows case.
        pp = Path(os.path.normcase(str(p))).parts
        rp = Path(os.path.normcase(str(root))).parts
        return pp[: len(rp)] == rp


# --------------------------------------------------------------------------
# Rule 2: no silent overwrites
# --------------------------------------------------------------------------
def write_bytes(out: Path, data: bytes, overwrite: bool) -> None:
    if not overwrite:
        try:
            # Mode "x" = create exclusively. The check and the creation are ONE
            # operation, so there is no gap in which another process can slip a
            # file in between "does it exist?" and "write it".
            with open(out, "xb") as f:
                f.write(data)
        except FileExistsError:
            raise PdfToolError(
                f"Refusing to overwrite existing file {out}. "
                "Pass overwrite=true to replace it, or choose a different output path."
            ) from None
        return
    # Overwrite was requested: write a temp file, then swap it in atomically. A crash
    # mid-write leaves the old file intact instead of a truncated PDF.
    tmp = out.with_name(out.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, out)


# --------------------------------------------------------------------------
# Rule 3: passwords
# --------------------------------------------------------------------------
def open_reader(path: Path, password: str | None) -> PdfReader:
    reader = PdfReader(str(path))
    if reader.is_encrypted:
        # Many PDFs are "encrypted" with an EMPTY user password just to restrict
        # printing/copying. Try that first so those open without bothering the agent.
        if not reader.decrypt(password or ""):
            if password:
                # Note what is NOT in this message: the password that was tried.
                raise PdfToolError(f"The password for {path.name} is wrong.")
            raise PdfToolError(f"{path.name} is encrypted. Retry with the password parameter.")
    return reader


def main() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d).resolve()
        inside = root / "inside"
        inside.mkdir()
        (root / "inside-evil").mkdir()
        outside = root / "outside"
        outside.mkdir()
        doc = fixtures.text_pdf(inside / "doc.pdf", pages=2)
        fixtures.text_pdf(outside / "secret.pdf", pages=1)
        fixtures.text_pdf(root / "inside-evil" / "x.pdf", pages=1)

        sb = Sandbox([inside])
        assert sb.resolve("doc.pdf") == doc.resolve()
        assert sb.resolve(str(doc)) == doc.resolve()
        for bad in (str(outside / "secret.pdf"), "../outside/secret.pdf",
                    str(inside / ".." / "outside" / "secret.pdf"), str(root / "inside-evil" / "x.pdf")):
            try:
                sb.resolve(bad)
            except PdfToolError as e:
                print("blocked:", bad.replace(str(root), "<root>"))
                assert "outside the allowed folders" in str(e)
            else:
                raise AssertionError(f"{bad} should have been blocked")

        # A symlink inside the folder pointing outside is judged by its target.
        try:
            (inside / "link.pdf").symlink_to(outside / "secret.pdf")
        except OSError:
            print("(symlinks need privileges on this Windows account: skipping that check)")
        else:
            try:
                sb.resolve("link.pdf")
            except PdfToolError:
                print("blocked: symlink that leads outside")
            else:
                raise AssertionError("symlink escape")

        # Overwrite rules
        out = inside / "out.pdf"
        write_bytes(out, b"first", overwrite=False)
        try:
            write_bytes(out, b"second", overwrite=False)
        except PdfToolError as e:
            print("refused:", str(e).split(".")[0])
        assert out.read_bytes() == b"first"
        write_bytes(out, b"second", overwrite=True)
        assert out.read_bytes() == b"second" and not list(inside.glob("*.tmp"))

        # Passwords
        locked = fixtures.encrypted_pdf(inside / "locked.pdf", doc, password="s3cret-pw")
        for pw, expect in ((None, "is encrypted"), ("wrong-guess-123", "is wrong")):
            try:
                open_reader(locked, pw)
            except PdfToolError as e:
                assert expect in str(e), str(e)
                assert (pw or "\0") not in str(e)  # the password never appears in the message
            else:
                raise AssertionError("should not open")
        assert len(open_reader(locked, "s3cret-pw").pages) == 2
        print("passwords: missing -> asks, wrong -> says wrong (without echoing it), right -> opens")

    print("module 05 OK")


if __name__ == "__main__":
    main()
