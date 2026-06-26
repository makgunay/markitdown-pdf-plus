# 03 · Build Findings (hard-won)

The plugin was built TDD-first with reportlab-generated fixtures, and the unit suite went green —
but **simple fixtures hid real-document failure modes**. The findings below were caught only by
running the "tests-green" build end-to-end on the real 82-page academic PDF. This is the
load-bearing lesson of the whole project:

> **Always verify a "tests-green" build end-to-end on a REAL target document. Simple fixtures pass
> while the real document fails — borderless tables, justified text, and table captions are exactly
> the cases a toy reportlab PDF doesn't exercise.**

## The fixes the end-to-end eval forced (post-green)

These landed *after* the 13-task plan finished and the suite was passing. See git log around
commits `d1944d1`, `3f86fde`, `77e3d4d`, `790b516`, `c00beaf`.

### 1. Borderless tables — text strategy + numeric-density validator
`pdfplumber.find_tables()` default `'lines'` strategy finds **zero** borderless academic tables (no
ruling lines). The fix in `_tables.py`:
- Detect with the **`'text'` strategy** (`_TEXT_SETTINGS`) in addition to ruled tables.
- Validate each candidate so the permissive text strategy doesn't turn prose into a "grid":
  `_looks_like_table` requires ≥3 rows, ≥2 cols, ≤30% long (>40-char) cells, **AND a numeric density
  ≥ 0.25** — academic data tables are number-dense; prose isn't. This is the key discriminator.
- Result on the real paper: borderless-table pipe rows went **0 → 609**.

### 2. No-VLM grid fallback must also use the text strategy
`extract_grid_markdown` originally only ran `cropped.extract_tables()` (ruled). For a borderless
table that detection found via text alignment, that returns nothing → the table **collapses back to
flattened text** in no-VLM mode. Fix: `extract_tables() or extract_tables(_TEXT_SETTINGS)`.

### 3. pdfminer for body text (the 0.1.6 spacing regression, avoided)
pdfplumber's `extract_words` **jams words together on justified/kerned text** (~16 run-together
lines/page on this paper). `_extract.py` uses **pdfminer** layout analysis instead (0 jammed). Catch:
pdfminer uses a **bottom-left origin**, so y is converted to a top-left `top`
(`bbox = (x0, page_height - y1, x1, page_height - y0)`) to match the pdfplumber bboxes that table/
figure detection produce. Without this conversion the de-dup logic silently fails.

### 4. Heading heuristic tightened — table rows were becoming false headings
The original `heading_level` promoted short **numbered** lines (`^\d+(\.\d+)*`) as headings. On data
tables, numeric row labels like `2.1` matched and became `##` headings. Fix: **removed the numbered
promotion**; same-size lines are promoted only when **short AND bold** (real section headers are a
larger font anyway). This both cleaned the output and unblocked finding #5.

### 5. Caption preservation — paragraph-only de-dup
The table-region de-dup originally dropped *every* block (incl. headings) inside a table bbox, which
deleted "Table N. ..." captions. Fix in `_converter.py`: de-dup **drops paragraphs only**
(`b.kind == "paragraph"`), keeping headings. Safe *because* finding #4 means a heading inside a table
region is now a genuine caption, not a mis-tagged data row.

### 6. Full-page mode branch
The Task 9 plan body shipped the tables-only path; the `full_page` config flag was read by
`register_converters` but the branch wasn't in `convert()`. The self-review note flagged it and it
was added: render each page → `vlm._call(page_png, table_prompt)` → concatenate. It lives at the top
of `PdfPlusConverter.convert()` and short-circuits the structure pipeline.

## External-tool bugs encountered (reference)

### Marker `--use_llm` + Ollama is broken out of the box
Every LLM call returns `400 Bad Request` from Ollama `/api/generate`. Two distinct bugs in the
installed `marker/services/ollama.py`:
1. **WebP images (the real blocker):** `BaseService.img_to_base64` defaults to `format="WEBP"`;
   Ollama returns `400 "Failed to load image or audio file"`. Fix: encode `format="PNG"` in
   `process_images`. (Verified: WEBP→400, PNG/JPEG→200.)
2. **Dropped `$defs`:** `__call__` copies only `properties`+`required` into the structured-output
   schema, dropping `$defs` → dangling `$ref` → `400 "Error resolving ref"`. Fix: copy `$defs` when
   present. (Latent — `TableSchema` happens to be flat.)

Both are **local edits to the installed package, lost on any `pip install`/reinstall of marker-pdf** —
reapply after reinstall. Marker swallows Ollama's real error (logs only the status), so debugging
requires reproducing the POST directly.

### Specialist-OCR integration walls
- **Nanonets over-segmentation** appears only on *tight crops fed to the wrong format* — when given
  TATR-bounded crops it sits at a sane median 7 cols (corrected an earlier pessimism). It natively
  emits HTML `<table>`; convert with `pandas.read_html(thousands=None)`.
- **DeepSeek-OCR via LM Studio GGUF**: degenerate; custom arch unsupported. Use `mlx-vlm` directly
  for MLX models — `lms get` also can't resolve the case-sensitive MLX repo id.

## Testing posture (what the suite does and doesn't cover)

- **32 test functions** (31 offline + 1 live-VLM integration skipped unless `RUN_VLM_INTEGRATION=1`).
- Pure stages (`HeadingAnnotator`, `CrossPageTableMerger`, `MarkdownAssembler`, VlmService no-op):
  hand-built `Line`/`Block` fixtures, no PDF/network.
- PDF-touching stages: tiny reportlab fixtures (a headings page, a *ruled* table, an embedded image).
- VLM path: deterministic `MockClient` for the end-to-end converter test.
- **CI** (GitHub Actions, py3.10–3.12) runs unit + mock-VLM + fixture only; integration + eval
  excluded.
- **The gap CI does NOT cover** (by design — needs the real paper + a live endpoint): borderless
  detection, justified-text spacing, caption preservation. Those live in `tests/eval/run_eval.py`,
  run manually against `../markitdown/2025059pap.pdf`. **Run the eval before trusting a table/heading
  change.**
