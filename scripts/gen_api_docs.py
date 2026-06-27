#!/usr/bin/env python3
"""Auto-generate docs/API.md from the package's public surface.

Introspects every module in ``markitdown_pdf_plus`` and emits one section per
module listing its public classes/functions with their signatures and docstrings.
Run with the project installed (``pip install -e .``) so the package imports.

Usage:
    python scripts/gen_api_docs.py            # write docs/API.md
    python scripts/gen_api_docs.py --check    # exit 1 if the file would change

Exit codes:
    0  success (or no drift with --check)
    1  drift detected with --check
"""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

import markitdown_pdf_plus  # noqa: F401  ensures the package is importable

PKG = "markitdown_pdf_plus"
OUT = Path(__file__).resolve().parent.parent / "docs" / "API.md"


def _public_members(module) -> list:
    members = []
    for name, obj in inspect.getmembers(module):
        if name.startswith("_"):
            continue
        if inspect.ismodule(obj):
            continue
        if inspect.isclass(obj) and obj.__module__ != module.__name__:
            continue
        if inspect.isfunction(obj) and obj.__module__ != module.__name__:
            continue
        if not (inspect.isclass(obj) or inspect.isfunction(obj)):
            continue
        members.append((name, obj))
    members.sort(key=lambda pair: pair[0])
    return members


def _sig(obj) -> str:
    try:
        return str(inspect.signature(obj))
    except (TypeError, ValueError):
        return "(...)"


def _render_module(modname: str, module) -> str:
    lines = [f"## `{modname}`", ""]
    doc = inspect.getdoc(module)
    if doc:
        lines += [doc, ""]
    members = _public_members(module)
    if not members:
        lines += ["_No public members._", ""]
        return "\n".join(lines)
    for name, obj in members:
        kind = "class" if inspect.isclass(obj) else "func"
        lines.append(f"### {kind} `{name}{_sig(obj)}`")
        lines.append("")
        doc = inspect.getdoc(obj)
        if doc:
            lines += [doc, ""]
        else:
            lines += ["_Undocumented._", ""]
    return "\n".join(lines)


def generate() -> str:
    import importlib
    import pkgutil

    pkg = importlib.import_module(PKG)
    # The package's stages live in single-underscore modules (e.g. _extract);
    # they are the documented architecture surface, so include them. Skip only
    # dunder-named modules if any ever appear.
    submodules = sorted(
        m.name for m in pkgutil.iter_modules(pkg.__path__) if m.name and not m.name.startswith("__")
    )
    parts = [
        "# API reference (auto-generated)",
        "",
        f"Generated from `{PKG}` by `scripts/gen_api_docs.py`. Do not edit by hand;",
        "the CI `docs` job regenerates this and fails if the committed copy is stale.",
        "",
        _render_module(PKG, pkg),
    ]
    for sub in submodules:
        full = f"{PKG}.{sub}"
        parts.append(_render_module(full, importlib.import_module(full)))
    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the file would change")
    args = ap.parse_args()

    rendered = generate()
    if args.check:
        if not OUT.exists():
            print(f"docs/API.md missing; regenerate with {__file__}", file=sys.stderr)
            return 1
        current = OUT.read_text()
        if current != rendered:
            print("docs/API.md is stale; regenerate with: python scripts/gen_api_docs.py", file=sys.stderr)
            return 1
        print("docs/API.md up to date.")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(rendered)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
