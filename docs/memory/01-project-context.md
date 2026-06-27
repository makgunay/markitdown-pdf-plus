# 01 · Project Context

## What this is

`markitdown-pdf-plus` is a [MarkItDown](https://github.com/microsoft/markitdown) plugin that
**overrides the built-in PDF converter** (registered at priority −1.0, so it wins whenever
`enable_plugins=True`). It exists because MarkItDown's built-in PDF path is a flat text extractor
with no layout model: on academic PDFs it produces 0 headings, loses figures, and flattens tables
into number-streams.

The plugin recovers most of that gap with two cheap, MIT-clean levers instead of a heavy layout
model:

1. **Structure via font heuristics** (always on, no ML) — per-character font sizes recover the
   heading hierarchy a layout model would produce, at ~zero cost.
2. **Tables via a model-agnostic VLM endpoint** (opt-in) — detected table-region crops are sent to
   any OpenAI-compatible vision model for clean Markdown transcription.

Plus always-on figure extraction, opt-in cross-page table merging, and opt-in figure captioning.
**Graceful degradation is a core principle:** useful output at every capability level, never worse
than the built-in converter.

- **Published:** https://github.com/Akgunay-Labs/markitdown-pdf-plus — `main`, **v0.1.0** released (CI green).
- **License:** MIT · **Python:** ≥3.10 · no bundled ML weights.

## Origin story (how we arrived at "build a plugin")

The project was not "let's build a plugin" from day one. It was a research arc that *concluded* a
plugin was the right move:

1. **Baseline.** Converted a test PDF — `2025059pap.pdf`, an 82-page Fed FEDS working paper, dense
   with borderless regression tables — with stock markitdown and rated it **58/100** on a weighted
   rubric. Tables flattened, 0 headings, figures lost.
2. **Tried the obvious upgrades.** markitdown 0.1.6 was a *wash* (gained messy tables, regressed
   body-text spacing). [Marker](https://github.com/datalab-to/marker) scored **87** but takes ~18 min
   on the M3 Max and is GPL-3.0 (not bundleable).
3. **Tried OCR specialists locally.** Qwen2.5-VL (Ollama), Nanonets-OCR2 (MLX), DeepSeek-OCR
   (LM Studio). Finding: the SOTA specialists are either CUDA-only or break under generic Mac serving
   stacks; the working ones (Qwen, Nanonets) are good at *region* table transcription.
4. **Identified the real gap.** The distance from markitdown (58) to Marker (87) is almost entirely
   **structure** (headings) and **tables** — both recoverable cheaply (font heuristics + a VLM
   endpoint) without a layout model.
5. **Saw open community demand.** microsoft/markitdown issues #41, #131 ("open for contribution"),
   #1419; no existing plugin does region/full-page VLM conversion on *born-digital* PDFs
   (`markitdown-ocr` only OCRs embedded images and scanned pages).
6. **Built it** via the superpowers workflow: brainstorming → design spec → writing-plans →
   subagent-driven TDD execution → release.

See [02-research-and-benchmarks.md](02-research-and-benchmarks.md) for the measured scoreboard
behind each step.

## Key decisions (with rationale)

| Decision | Why |
|---|---|
| **Combined "best-of-both" plugin** (structure always-on + opt-in VLM), enhance pattern | One plugin, useful at every capability tier — not two separate tools. |
| **Publishable from the start** — standalone MIT package, own repo | Open community demand; keeps users inside markitdown's interface and multi-format breadth. |
| **Tables-only VLM by default**, `pdf_plus_full_page` flag as escape hatch | Keeps the common case cheap; full-page mode handles multi-column/scanned/equation-heavy docs. |
| **v1 includes both extras** (cross-page merge + figure captioning) | They're small and complete the "academic paper" story. |
| **Approach 1: composable single-purpose stages** (not subclassing the built-in, not a monolith) | Sidesteps the 0.1.6 spacing regression; each stage is independently testable/reviewable. |
| **pdfminer for text, pdfplumber for geometry** | pdfplumber's `extract_words` jams words on justified text (~16/page); pdfminer keeps spacing (0 jammed). See [03](03-build-findings.md). |
| **Model-agnostic via OpenAI-compatible `llm_client`; no bundled ML** | Stays MIT-clean and light (no torch); works with Ollama / LM Studio / OpenAI / Gemini alike. |
| **Priority −1.0** | Lower priority = tried first, so it overrides the built-in PDF converter. |

## Architecture at a glance

A pipeline of small stages orchestrated by a thin `PdfPlusConverter`. (Full detail in the
[design spec](../superpowers/specs/2026-06-06-markitdown-pdf-plus-design.md) §5–6.)

```
convert(stream)
  → TextExtractor (pdfminer)      → list[Line]  (text + font size + bold + top-left bbox)
  → HeadingAnnotator (font tiers) → Blocks (heading / paragraph)
  → per page:
      TableDetector.detect        → bboxes (ruled + borderless via text strategy)
        → VlmService.transcribe_table(crop)         [VLM path]
          └ else TableDetector.extract_grid_markdown [pdfplumber fallback]
        → Table block; DROP paragraph lines inside the bbox (de-dup — critical)
      FigureExtractor             → Figure blocks (+ VLM caption if client present)
  → CrossPageTableMerger          → merged Blocks
  → MarkdownAssembler             → markdown (sorted by (page, top, x0))
```

| File | Responsibility |
|---|---|
| `_model.py` | `Line`, `Block` dataclasses |
| `_extract.py` | `TextExtractor` — pdfminer lines, bottom-left→top-left y conversion |
| `_headings.py` | `HeadingAnnotator` — body = modal font size; tiers + short-bold promotion |
| `_tables.py` | `TableDetector` — ruled + borderless (text strategy + numeric-density validator); grid fallback |
| `_figures.py` | `FigureExtractor` + `render_bbox_png_b64` (pypdfium2 crop) |
| `_vlm.py` | `VlmService` (fence-strip, validation, fail-soft) + `build_vlm_service` (None when no client) |
| `_merge.py` | `CrossPageTableMerger` — consecutive pages, equal cols, no heading between |
| `_assemble.py` | `MarkdownAssembler` — reading-order sort + per-block rendering |
| `_converter.py` | `PdfPlusConverter` — orchestration, table-text de-dup, full-page branch |
| `__init__.py` | `__plugin_interface_version__ = 1`, `register_converters()` |

## Configuration surface

Passed through `MarkItDown(...)` constructor kwargs (CLI users set `pdf_plus_*` via env vars).

| Setting | Default | Purpose |
|---|---|---|
| `llm_client` / `llm_model` / `llm_prompt` | none | the VLM endpoint; **absent → no-op** (structure + pdfplumber tables only) |
| `pdf_plus_full_page` | `False` | render every page → VLM transcribe whole (multi-column/scanned escape hatch) |
| `pdf_plus_image_dir` | `None` | save figure PNGs here; else caption-only |
| `pdf_plus_dpi` | `200` | crop render resolution |
| `pdf_plus_table_fallback` | `True` | use pdfplumber grid when VLM absent/fails |
| `pdf_plus_table_prompt` / `pdf_plus_caption_prompt` | built-ins | override prompts |

## Dev & test environment

- **Test interpreter:** the sibling `../markitdown/.venv/bin/python` (has markitdown 0.1.6,
  pdfplumber, pypdfium2). Install editable once: `../markitdown/.venv/bin/pip install -e ".[test]"`.
- **Test fixtures:** `tests/conftest.py` builds tiny PDFs with reportlab (headings page, bordered
  table, embedded image). Pure stages use hand-built `Line`/`Block` fixtures; the VLM path uses a
  deterministic `MockClient`.
- **Real-document eval:** `tests/eval/run_eval.py` scores against `../markitdown/2025059pap.pdf` vs
  the markitdown-0.1.6 baseline. `PDFPLUS_OLLAMA=1` adds the live Qwen pass.
- **Local endpoints used during the build:** Ollama (`qwen2.5vl:7b` at `localhost:11434/v1`),
  mlx-vlm (`Nanonets-OCR2-3B-8bit`). The plugin itself bundles none of this — it only needs an
  OpenAI-compatible client.

## Verified result (v0.1.0, on the 82-page paper vs markitdown-0.1.6)

| Metric | markitdown 0.1.6 | pdf-plus (no VLM) | pdf-plus (+ Qwen2.5-VL) |
|---|---:|---:|---|
| Section headings | 0 | 82 | 82 |
| Figures extracted | 0 | 11 | 11 (+ captions) |
| Run-together-word lines | 928 | 59 | 59 |
| Borderless tables | scattered | structured grids | clean pipe tables w/ captions |
