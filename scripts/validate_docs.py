#!/usr/bin/env python3
"""Validate that AGENTS.md / CLAUDE.md stay consistent with the repository.

Two checks, both genuine freshness guards:

1. **Link/path integrity** — every Markdown link target that looks like a local
   file or directory (``[x](./docs/memory/README.md)``) must resolve relative to
   the repo root. Catches docs that drift when files move.

2. **Documented tools still installed** — the commands the docs tell agents to
   run (``ruff``, ``mypy``, ``pytest``, ``pre-commit``, ``markitdown``) must
   actually be invokable. Catches docs that reference tools the env no longer has.

Exit codes:
    0  all references valid
    1  one or more broken references / missing tools
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = [REPO / "AGENTS.md", REPO / "CLAUDE.md"]

LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
# Tools the docs instruct agents to run; each must be on PATH or runnable as
# `python -m <module>`. The map covers tools whose CLI name differs from the
# importable module name.
TOOLS = {
    "ruff": "ruff",
    "mypy": "mypy",
    "pytest": "pytest",
    "pre-commit": "pre_commit",
    "markitdown": "markitdown",
}


def _is_local(target: str) -> bool:
    # Strip an optional anchor (#...) from local paths.
    return not target.startswith(("http://", "https://", "mailto:", "#"))


def check_links() -> list[str]:
    errors: list[str] = []
    for doc in DOCS:
        if not doc.exists():
            errors.append(f"{doc.relative_to(REPO)}: file missing")
            continue
        for i, line in enumerate(doc.read_text().splitlines(), 1):
            for target in LINK_RE.findall(line):
                if not _is_local(target):
                    continue
                path_part = target.split("#", 1)[0]
                if not path_part:
                    continue
                resolved = (REPO / path_part).resolve()
                if not resolved.exists():
                    errors.append(f"{doc.relative_to(REPO)}:{i}: broken link '{target}'")
    return errors


def check_tools() -> list[str]:
    errors: list[str] = []
    for cli, module in TOOLS.items():
        if shutil.which(cli) is not None:
            continue
        probe = subprocess.run(
            [sys.executable, "-m", module, "--version"],
            capture_output=True,
        )
        if probe.returncode != 0:
            errors.append(f"documented tool '{cli}' not found on PATH or as `python -m {module}`")
    return errors


def main() -> int:
    errors = check_links() + check_tools()
    if errors:
        print("AGENTS.md / CLAUDE.md validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"AGENTS.md / CLAUDE.md valid: {len(DOCS)} docs, {len(TOOLS)} tools checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
