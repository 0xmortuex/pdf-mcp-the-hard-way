"""Run every module's main.py, the way CI does.

Each main.py builds its own PDFs in a temporary folder, runs real checks with
assert, and exits 0 only if every claim its README makes holds. Module 06 also
starts a real MCP server over stdio.

Usage: python verify.py            # all modules
       python verify.py 02 05      # just these
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    wanted = sys.argv[1:]
    modules = sorted(
        d
        for d in os.listdir(ROOT)
        if os.path.isfile(os.path.join(ROOT, d, "main.py")) and (not wanted or any(d.startswith(w) for w in wanted))
    )
    if not modules:
        print("no modules matched")
        return 1
    failed = []
    for m in modules:
        start = time.monotonic()
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(ROOT, m, "main.py")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=300,
                cwd=os.path.join(ROOT, m),
                env=env,
            )
            ok, output = proc.returncode == 0, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            ok, output = False, "timed out after 300s"
        print(f"{'PASS' if ok else 'FAIL'}  {m}  ({time.monotonic() - start:.1f}s)")
        if not ok:
            failed.append(m)
            print("    " + output.strip().replace("\n", "\n    "))
    print(f"\n{len(modules) - len(failed)}/{len(modules)} modules verified")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
