# Patterns and conventions

The conventions below are not style preferences. Most encode invariants that cost real debugging time to discover. The fuller rationale lives in [Build findings](../background/build-findings.md) and [Design decisions](../background/design-decisions.md).

## Single-purpose stages

Each pipeline step lives in its own `_*.py` module and does one thing: extract, annotate, detect, merge, or assemble. Stages take simple inputs (`list[Line]`, a pdfplumber `page`, `list[Block]`) and return simple outputs. Keep new logic in the stage it belongs to rather than thickening `PdfPlusConverter` (`src/markitdown_pdf_plus/_converter.py`). This keeps every stage independently testable: pure stages with hand-built `Line`/`Block` fixtures, PDF-touching stages with tiny reportlab fixtures, and the VLM path with a `MockClient`.

## Fail soft, never abort a document

A single bad crop or VLM call must never abort a whole document. `VlmService._call` (`src/markitdown_pdf_plus/_vlm.py`) catches every exception, logs a warning, and returns `None`; the converter then falls back to the pdfplumber grid. Preserve this contract: new external calls should degrade to the next-best output, not raise.

## Text comes from pdfminer, not pdfplumber words

`TextExtractor` (`src/markitdown_pdf_plus/_extract.py`) uses pdfminer's layout analysis, not pdfplumber's `extract_words`, because pdfplumber jams words together on justified and kerned academic text. pdfminer uses a **bottom-left origin**, so y-coordinates are converted to a top-left `top` (`page_height - y1`) to match the pdfplumber geometry used by table and figure detection. Break that conversion and the table-text de-duplication silently fails. Do not swap pdfminer for pdfplumber words.

## Borderless detection needs the text strategy and the numeric-density gate

pdfplumber's default `lines` strategy finds zero borderless tables. `TableDetector` (`src/markitdown_pdf_plus/_tables.py`) also runs the `text` strategy and gates each candidate on numeric density ≥ 0.25 so prose is not mistaken for a grid. The no-VLM grid fallback (`extract_grid_markdown`) must also try the text strategy, or borderless tables collapse back to flattened text. Do not drop either half of this.

## Table-text de-dup drops paragraphs only, never headings

When a table region is rendered, the converter drops the paragraph lines inside that bounding box to avoid duplication, but keeps headings, because a heading inside a table region is a real caption ("Table N. ..."). This is safe only because the heading heuristic was tightened to not promote numbered or data rows: `heading_level` (`src/markitdown_pdf_plus/_headings.py`) promotes same-size lines only when they are short and bold. Do not reintroduce numbered-line promotion without re-checking caption handling.

## No in-process machine learning as a core dependency

The VLM path is endpoint-based on purpose: model-agnostic, MIT-clean, and light. Any future structure model (for example the parked TATR work) must be an optional extra with pinned dependencies, never a core dependency. The recurring transformers 4.x / 5.x conflict is the practical reason. See [Roadmap](../background/roadmap.md).

## Unit tests are necessary, not sufficient

The reportlab fixtures in `tests/conftest.py` do not exercise the real failure modes: borderless detection, justified-text spacing, and caption preservation only surface on a real academic PDF. Run the real-document eval (`tests/eval/run_eval.py`) before trusting any table or heading change. See [Testing](testing.md).

## Code style and quality gates

- **Formatting and linting:** ruff (line length 110, double quotes, space indent). The lint rule set includes pyflakes, isort, pyupgrade, bugbear, simplify, comprehensions, pep8-naming, mccabe complexity (max 10), and flake8-todos (tech-debt markers must be tracked or linked).
- **Typing:** mypy in strict mode over `src/` only; third-party imports without stubs are treated as `Any`.
- **Comments:** the codebase is sparse with comments by design. The comments that exist explain non-obvious invariants (the coordinate conversion, the de-dup rule, the numeric-density discriminator), not what the code does. Match that posture.
- **Dead code:** vulture runs with a whitelist (`vulture_whitelist.py`) for names called through MarkItDown's plugin contract that static analysis cannot see.

See [Tooling](tooling.md) for how to run each of these.
