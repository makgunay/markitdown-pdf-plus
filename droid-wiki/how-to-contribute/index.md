# How to contribute

This section is the entry point for working in the codebase: the development loop, how to test, how to debug, the conventions you must not break, and the tooling stack.

## Start here

Read [Patterns and conventions](patterns-and-conventions.md) first. Most of its rules encode invariants that cost real debugging time to discover (the coordinate conversion, the paragraph-only de-dup, the numeric-density gate). Then skim the [Architecture](../overview/architecture.md) so you know which stage owns the behavior you want to change.

## The loop in brief

1. **Set up** the sibling venv or the dev container (see [Getting started](../overview/getting-started.md)).
2. **Work in the right stage.** Each pipeline step lives in its own `_*.py` module with a targeted test. Keep new logic in the stage it belongs to, not in `PdfPlusConverter`.
3. **Test-first, frequent commits**, matching the existing history (one focused change per commit).
4. **Run the offline suite** plus lint, format, and type-check before pushing.
5. **For table or heading changes, run the real-document eval.** Green unit tests are necessary, not sufficient.
6. **Open a PR.** CI runs lint, duplication, docs-freshness, the test matrix (Python 3.10-3.12), and a flaky re-run job. The PR template and CODEOWNERS (`@makgunay`) apply.

## Definition of done

- The offline test suite passes with the coverage gate (branch coverage, ~90% baseline, 88% floor).
- `ruff check`, `ruff format --check`, and `mypy` are clean.
- `vulture`, `deptry`, and the jscpd duplication check pass.
- `docs/API.md` is regenerated if the public surface changed (`scripts/gen_api_docs.py`), and `scripts/validate_docs.py` passes.
- For table/heading work, the real-document eval was run and the metrics did not regress.

## Pages

| Page | Purpose |
| --- | --- |
| [Development workflow](development-workflow.md) | branch, code, test, commit, release, dependency policy |
| [Testing](testing.md) | the unit suite, the eval harness, the live-VLM integration test, coverage and flakiness tooling |
| [Debugging](debugging.md) | the real failure modes, the eval as a debugger, common errors |
| [Patterns and conventions](patterns-and-conventions.md) | the invariants and code style |
| [Tooling](tooling.md) | ruff, mypy, vulture, deptry, jscpd, pre-commit, the docs generators, CI, the dev container |
