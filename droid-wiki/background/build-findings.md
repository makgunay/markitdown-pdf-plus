# Build findings

The plugin was built test-first with reportlab-generated fixtures, and the unit suite went green. But simple fixtures hid real-document failure modes. The findings below were caught only by running the tests-green build end-to-end on the real 82-page academic PDF. This is the load-bearing lesson of the project. The full notes are in `docs/memory/03-build-findings.md`.

> Always verify a tests-green build end-to-end on a real target document. Simple fixtures pass while the real document fails. Borderless tables, justified text, and table captions are exactly the cases a toy reportlab PDF does not exercise.

## The fixes the end-to-end eval forced

These landed after the implementation plan finished and the suite was passing.

### 1. Borderless tables — text strategy plus a numeric-density validator

pdfplumber's default `lines` strategy finds zero borderless academic tables. The fix in `src/markitdown_pdf_plus/_tables.py`: also detect with the `text` strategy, and validate each candidate so prose is not turned into a "grid". `_looks_like_table` requires at least 3 rows, at least 2 columns, at most 30% long cells, and a numeric density of at least 0.25. Academic data tables are number-dense; prose is not. On the real paper, borderless-table pipe rows went from 0 to 609. See [Table handling](../systems/table-handling.md).

### 2. The no-VLM grid fallback must also use the text strategy

`extract_grid_markdown` originally ran only `cropped.extract_tables()` (ruled). For a borderless table found via text alignment, that returns nothing, so the table collapsed back to flattened text in no-VLM mode. The fix: `extract_tables() or extract_tables(_TEXT_SETTINGS)`.

### 3. pdfminer for body text (avoiding the 0.1.6 spacing regression)

pdfplumber's `extract_words` jams words together on justified and kerned text (about 16 run-together lines per page on this paper). `src/markitdown_pdf_plus/_extract.py` uses pdfminer layout analysis instead (zero jammed). The catch: pdfminer uses a bottom-left origin, so y is converted to a top-left `top` (`page_height - y1`) to match the pdfplumber bboxes table and figure detection produce. Without this conversion the de-dup logic silently fails. See [Text extraction](../systems/text-extraction.md).

### 4. Heading heuristic tightened — table rows were becoming false headings

The original `heading_level` promoted short numbered lines as headings. On data tables, numeric row labels like `2.1` matched and became `##` headings. The fix removed numbered promotion: same-size lines are promoted only when short and bold. This cleaned the output and unblocked finding 5. See [Heading detection](../systems/heading-detection.md).

### 5. Caption preservation — paragraph-only de-dup

The table-region de-dup originally dropped every block inside a table bbox, including headings, which deleted "Table N. ..." captions. The fix in `src/markitdown_pdf_plus/_converter.py`: de-dup drops paragraphs only, keeping headings. This is safe only because finding 4 means a heading inside a table region is now a genuine caption, not a mis-tagged data row. See [Orchestration](../systems/orchestration.md).

### 6. Full-page mode branch

The implementation plan shipped the tables-only path; the `full_page` flag was read by `register_converters` but the branch was missing in `convert()`. A self-review caught it and the branch was added: render each page, send to the VLM, concatenate. See [Full-page mode](../features/full-page-mode.md).

## External-tool bugs encountered

Two were notable during the research phase:

- **Marker `--use_llm` plus Ollama is broken out of the box.** WebP images cause a 400 from Ollama (fix: encode PNG), and the structured-output schema drops `$defs` causing a dangling `$ref`. Both are local edits to the installed package, lost on reinstall.
- **DeepSeek-OCR via LM Studio GGUF** produces degenerate output; its custom architecture is unsupported there. Use mlx-vlm directly for MLX models.

## What the test suite does and does not cover

The unit suite (pure stages with hand-built fixtures, PDF stages with tiny reportlab fixtures, the VLM path with a `MockClient`) runs in CI across Python 3.10-3.12. By design it does not cover borderless detection, justified-text spacing, or caption preservation, because those need the real paper and a live endpoint. Those live in `tests/eval/run_eval.py`. Run the eval before trusting a table or heading change. See [Testing](../how-to-contribute/testing.md).
