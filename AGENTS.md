# AGENTS.md

This repository's agent and contributor guidance lives in **[CLAUDE.md](./CLAUDE.md)**. Read it
first — it covers the architecture, the commands (tests run against the sibling `../markitdown/.venv`),
the non-obvious invariants you must not break, and links to the deeper context in `docs/memory/`.

`AGENTS.md` and `CLAUDE.md` are kept intentionally in sync: this file is the entry point for tools
that look for `AGENTS.md`; `CLAUDE.md` is the single source of truth. If you update one, update the
other (or keep this as the pointer and edit `CLAUDE.md`).

## TL;DR

- **What:** a MarkItDown plugin that overrides the built-in PDF converter — font-heuristic headings +
  figure extraction (always on), opt-in model-agnostic VLM tables/captions + cross-page merge.
- **Test:** `../markitdown/.venv/bin/python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval`
- **Before trusting a table/heading change:** also run the real-document eval —
  `../markitdown/.venv/bin/python tests/eval/run_eval.py` against `../markitdown/2025059pap.pdf`. The
  unit suite's reportlab fixtures do not exercise borderless tables, justified text, or captions.
- **Don't:** swap pdfminer for pdfplumber words, drop the borderless text-strategy/numeric-density
  validator, let table de-dup delete headings, or add in-process ML as a core dependency. See
  CLAUDE.md → "Non-obvious things to know before editing" for why.

→ **[CLAUDE.md](./CLAUDE.md)** · context: **[docs/memory/README.md](./docs/memory/README.md)**
