# Fun facts

A few genuinely interesting things about this codebase.

## The whole thing fits in 516 lines

The shipped library is 516 lines of Python across 10 modules, and it beats a much heavier converter on the metrics that matter for academic PDFs (82 headings vs 0, run-together lines down from 928 to 59). The leverage comes from picking two cheap signals: per-character font sizes for headings, and a VLM endpoint for tables. No layout model, no bundled ML, no torch.

## Documentation outweighs the code

There are roughly 1,014 lines of Markdown in `docs/` against 516 lines of source. The reasoning the team wanted to preserve (the research scoreboard, the design decisions, the fixes the tests missed, two roadmap directions) is larger than the program it explains. Most of that lives in `docs/memory/`.

## The first two commits contain no code

The repository opens with `docs: design spec` and `docs: TDD implementation plan`, both before any library code. The spec and plan were written first; the code followed the plan stage by stage. See [Lore](lore.md).

## Zero TODOs, by enforcement

There is not a single `TODO`, `FIXME`, or `HACK` comment in `src/` or `tests/`. This is not luck: ruff's flake8-todos rule (`TD`) requires any such marker to be tracked or linked, so loose tech-debt comments do not survive the linter.

## The numeric-density magic number

Borderless tables are told apart from prose by one threshold: a candidate region must have at least 25% of its cells containing a digit (`numeric / len(cells) >= 0.25` in `src/markitdown_pdf_plus/_tables.py`). Academic data tables are number-dense; prose is not. That single ratio is what took borderless-table pipe rows from 0 to 609 on the test paper without false-positiving paragraphs.

## A coordinate flip that, if wrong, fails silently

pdfminer counts y from the bottom of the page; everything else counts from the top. `TextExtractor` flips it with `top = page_height - y1`. Get this wrong and nothing crashes; the table-text de-duplication just quietly stops working and table content appears twice. It is the kind of bug that only a real document reveals, which is exactly the project's recurring theme.

## Built fast, then documented slow

The repo went from empty to a released, CI-green, fully-tooled PyPI package within its first day of commits (2026-06-06), then waited three weeks before its first pull request, which added the documentation and governance layer (2026-06-27). About 35% of commits record AI co-authorship, a lower bound on how much of it was agent-driven.
