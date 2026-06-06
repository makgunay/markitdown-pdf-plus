# markitdown-pdf-plus — Design Spec

- **Date:** 2026-06-06
- **Status:** Approved (brainstorming) → ready for implementation planning
- **Author:** design session (Akgunay Labs)

## 1. Motivation

MarkItDown's built-in PDF converter is a flat text extractor (pdfminer / pdfplumber) with no
layout model. On a representative academic PDF (an 82-page Fed working paper) we measured, on a
weighted rubric (Text 30% · Structure 15% · Tables 30% · Equations 8% · Figures 10% · Refs 5% ·
Noise 2%):

| Tool | Overall | Tables | Structure (headings) | Notes |
|---|---:|---|---|---|
| markitdown 0.1.5 | 58 | flattened to number-streams | 0 headings | pdfminer dump |
| markitdown 0.1.6 | ~55 | messy over-segmented grids | 0 headings | gains tables, **regresses body-text spacing** (788 vs 12 run-together-word lines) |
| Marker (hybrid pipeline) | 87 | real grids | 39 headings | layout model; GPL-3.0 |
| Marker + Nanonets-OCR2 | ~89 | specialist grids | 39 headings | best; not bundleable |

The gap between markitdown (~58) and Marker (87) is almost entirely **structure** (a layout model
classifies regions into `SectionHeader`/`Table`/`Figure`/… and assigns reading order) and **tables**.
Two cheap, MIT-clean levers recover most of it without a layout model or heavy ML:

1. **Structure via font heuristics.** pdfplumber exposes per-character font size/name. A 3-line
   heuristic recovered the paper's full heading hierarchy (body=12pt; 17.2pt→`#`, 14.3pt→`##`) —
   the same hierarchy Marker's layout model produced, at ~zero cost.
2. **Tables via a model-agnostic VLM endpoint.** Sending detected table-region crops to any
   OpenAI-compatible vision model produced structurally faithful Markdown tables (verified with
   Nanonets-OCR2 and Qwen2.5-VL).

`markitdown-pdf-plus` packages both as a single MarkItDown plugin: always-on heuristic structure +
figure extraction, plus opt-in VLM table transcription and figure captioning. It is MIT-clean
(calls an endpoint; bundles no model weights or torch), light (pypdfium2 + pdfplumber + pdfminer),
and cross-platform.

**Why a plugin (vs. just using Marker/Docling):** there is open, maintainer-invited demand for this
(microsoft/markitdown issues #41, #131 "open for contribution", #1419), no existing plugin does
full-page-or-region VLM conversion on *born-digital* PDFs (`markitdown-ocr` only OCRs embedded
images and *scanned* pages), and the plugin keeps users inside markitdown's interface and multi-format
breadth.

## 2. Goals / Non-goals

**Goals (v1):**
- Override the built-in PDF converter (priority −1.0) when plugins are enabled.
- Always-on: clean body text, **font-heuristic headings**, **figure/image extraction**.
- Opt-in (when an `llm_client` is configured): **VLM table transcription** (tables-only by default),
  **cross-page table merging**, **figure captioning**.
- Optional **full-page VLM mode** as an escape hatch for hard documents.
- **Graceful degradation:** produces useful output at every capability level; never worse than the
  built-in converter.
- Publishable: standalone MIT package, own git repo, pyproject entry point, tests, README, CI.
- Model-agnostic: any OpenAI-compatible endpoint (cloud or local Ollama/LM Studio/vLLM).

**Non-goals (v1, deferred to v2):**
- Multi-column reading-order reconstruction (needs a layout model; full-page mode is the workaround).
- Equations → LaTeX (only feasible in full-page mode, which handles it implicitly).
- Scanned PDFs with no text layer (`markitdown-ocr` covers these; full-page mode also handles them).
- Office formats (DOCX/PPTX/XLSX) — PDF only.
- A Docling-backend variant (possible future selectable backend).

## 3. Key decisions (from the design session)

- **Combined "best-of-both" plugin**, enhance pattern (one plugin, structure always-on + opt-in VLM).
- **Publishable from the start** — standalone package, own repo.
- **Tables-only default**, `pdf_plus_full_page` flag for full-page mode.
- **v1 includes both extras**: cross-page table merging AND figure captioning.
- **Approach 1**: pipeline of composable single-purpose stages (vs. subclassing the built-in converter
  or a monolith) — sidesteps the 0.1.6 spacing regression and stays testable/reviewable.
- **Unify text on pdfplumber `extract_words`** (clean spacing proven in POC; one source for
  text+font+bbox) rather than correlating pdfminer-text with pdfplumber-geometry; pdfminer kept as a
  per-line text fallback, guarded by a spacing-quality test.
- **Location:** sibling repo `tools/markitdown-pdf-plus` (separate from the scratch/test env); develop
  and test against the existing `tools/markitdown/.venv`, `2025059pap.pdf`, and the local endpoints.

## 4. Package layout

- Dist name `markitdown-pdf-plus`; import package `markitdown_pdf_plus`. License **MIT**. Python **≥3.10**.
- Runtime deps: `markitdown` (peer), `pypdfium2` (BSD), `pdfplumber`, `pdfminer.six`, `Pillow`
  (transitive). VLM: **no** bundled ML; the user supplies any OpenAI-compatible `llm_client`.

```
markitdown-pdf-plus/
├── pyproject.toml                # entry point, deps, MIT, py>=3.10
├── README.md  LICENSE
├── src/markitdown_pdf_plus/
│   ├── __init__.py               # __plugin_interface_version__ = 1, register_converters()
│   ├── _converter.py             # PdfPlusConverter (thin orchestrator)
│   ├── _extract.py               # TextExtractor (pdfplumber extract_words → Lines)
│   ├── _headings.py              # HeadingAnnotator (font heuristic)
│   ├── _figures.py               # FigureExtractor (page.images → crops)
│   ├── _tables.py                # TableDetector (pdfplumber find_tables → bboxes)
│   ├── _vlm.py                   # VlmService.transcribe_table()/caption_figure() (no-op safe)
│   ├── _merge.py                 # CrossPageTableMerger
│   ├── _assemble.py              # MarkdownAssembler (blocks → markdown, reading order)
│   └── _model.py                 # Line / Block dataclasses
└── tests/                        # one module per stage + fixtures + eval
```

Entry point:
```toml
[project.entry-points."markitdown.plugin"]
pdf_plus = "markitdown_pdf_plus"
```
`register_converters(markitdown, **kwargs)` reads config, builds a `VlmService` (or `None`),
constructs `PdfPlusConverter`, and registers it at priority **−1.0**.

## 5. Component architecture

**Data model (`_model.py`):**
- `Line` = `{page:int, text:str, font_size:float, bold:bool, bbox:(x0,top,x1,bottom)}`
- `Block` = a positioned semantic unit; one of `Heading(level)`, `Paragraph`, `Table(markdown,bbox,page)`,
  `Figure(image_path|None, caption|None, bbox, page)`.
- `PdfPlusDoc` = ordered `list[Block]`.

**Stages (each: one job; clear inputs/outputs; independently testable):**

| Stage | Input → Output | Does | Depends on |
|---|---|---|---|
| `TextExtractor` | bytes → `list[Line]` | pdfplumber `extract_words(+size,fontname)` joined with spaces → clean text + font + bbox | pdfplumber |
| `HeadingAnnotator` | `Lines` → `Blocks` | body=mode font size; line ≥ body+tier / bold / `N.N` pattern → `Heading(level)`, else `Paragraph` | pure |
| `TableDetector` | page → `list[bbox]` | pdfplumber `find_tables()` geometry | pdfplumber |
| `FigureExtractor` | page → `list[Figure]` | `page.images` bboxes → pypdfium2 crop → PNG + bbox | pypdfium2 |
| `VlmService` | image → markdown / caption | `transcribe_table`, `caption_figure`; **None when no client** | OpenAI-compat client (optional) |
| `CrossPageTableMerger` | `Blocks` → `Blocks` | bottom-of-page + top-of-next, equal col count, no heading between → merge grids | pure |
| `MarkdownAssembler` | `Blocks` → `str` | sort `(page, top, x0)`; render each block type | pure |
| `PdfPlusConverter` | stream → `DocumentConverterResult` | orchestrates; reads kwargs | all |

Pure stages (`HeadingAnnotator`, `CrossPageTableMerger`, `MarkdownAssembler`, VlmService no-op path)
are tested with hand-built fixtures; pdf-touching stages with tiny real-PDF fixtures; the converter
end-to-end with a mock VLM.

## 6. Data flow

```
convert(file_stream, stream_info, **kwargs)
  1. read config: llm_client/llm_model/llm_prompt + pdf_plus_* flags
  2. TextExtractor.extract(bytes)            → Lines[]
  3. HeadingAnnotator.annotate(Lines)        → Heading/Paragraph blocks
  4. per page: TableDetector.detect → bboxes ; FigureExtractor.extract → Figure blocks
  5. per table bbox:
       crop = pypdfium2 render(bbox)
       md = VlmService.transcribe_table(crop)         # VLM path
            └─ if no client/failure → pdfplumber table.extract() → markdown grid   # fallback
       → Table block ; DROP Lines inside bbox from the paragraph stream   # de-dup (critical)
  6. per figure: caption = VlmService.caption_figure(crop)   (None if no client)
  7. CrossPageTableMerger.merge(blocks)
  8. MarkdownAssembler.assemble(blocks)      → markdown
  9. return DocumentConverterResult(markdown, title)
```

Full-page mode (`pdf_plus_full_page=True` + client): steps 4–6 replaced by render-each-page → VLM →
concatenate (structure layer bypassed for those pages).

**Correctness guarantees in the flow:**
- **Table-text de-duplication:** text lines inside a transcribed table bbox are removed from the
  paragraph stream so table content never appears twice. Same for figure regions.
- **Degradation cascade:** VLM table → pdfplumber grid → leave lines as paragraphs; VLM caption →
  none. Useful output at every level (~70 no endpoint; ~80 with endpoint); never worse than built-in.
- **Reading order:** positional sort `(page, top, x0)` — correct for single-column; multi-column is
  out of v1.

## 7. VLM integration, config & prompts

**Client call** (markitdown's existing `llm_client` pattern, already validated with Nanonets/Qwen):
```python
client.chat.completions.create(
    model=llm_model,
    messages=[{"role":"user","content":[
        {"type":"image_url","image_url":{"url":"data:image/png;base64,<crop>"}},
        {"type":"text","text":prompt}]}],
    max_tokens=..., temperature=0)
```
Works with any OpenAI-compatible endpoint (cloud or local, e.g.
`OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")`, model `qwen2.5vl:7b`).

**Config** — `register_converters` pulls these from `MarkItDown(...)` constructor kwargs (forwarded by
markitdown). CLI users set `pdf_plus_*` via env vars (CLI can't pass arbitrary kwargs).

| Setting | Default | Purpose |
|---|---|---|
| `llm_client` / `llm_model` / `llm_prompt` | none | the VLM endpoint; **absent → no-op** |
| `pdf_plus_full_page` | `False` | full-page mode |
| `pdf_plus_image_dir` | `None` | save figure PNGs here; else caption-only |
| `pdf_plus_table_prompt` / `pdf_plus_caption_prompt` | built-ins | override prompts |
| `pdf_plus_dpi` | 200 | crop render resolution |
| `pdf_plus_table_fallback` | `True` | use pdfplumber grid when VLM absent/fails |

**Figure output:** renders `![{caption}]({ref})`; `ref` = relative path if `pdf_plus_image_dir` set,
else a base64 data URI if markitdown's `keep_data_uris` is on, else omitted (caption-only). Default =
caption-primary — keeps markdown lean for LLM use.

**Default prompts (overridable):**
- *Table:* "Convert this table image to a GitHub-flavored Markdown pipe table. Preserve every row
  label, column header, numeric value, parenthesized standard error, and significance marker exactly.
  Output only the table."
- *Caption:* "Describe this figure for someone who can't see it: chart type, axes, series, and the
  main trend in 1–3 sentences. If it shows discrete values, add a small Markdown table."

## 8. Error handling (fail soft — never abort the document)

| Situation | Behavior |
|---|---|
| No `llm_client` | VlmService no-ops → pdfplumber grid + uncaptioned figures |
| VLM call fails (network/400/timeout) | catch per-call, warn, fall back to grid / no caption |
| VLM returns junk / code-fenced | strip ` ```markdown ` fences; require pipe rows; else fall back |
| Scanned PDF (no text layer) | out of v1: if `full_page`+client → VLM full-page; else raise so markitdown defers |
| Malformed/encrypted PDF | catch open failure, raise clear conversion error (optional pypdfium2 retry) |
| Per-crop render failure | skip that crop with a warning; doc proceeds |
| Large-PDF memory | process page-by-page; release pdfplumber page caches (5–10 MiB/page issue) |

## 9. Testing strategy

- **Pure-stage unit tests** (no PDF/network): `HeadingAnnotator` (font tiers, all-same-font,
  bold-only, `N.N`), `CrossPageTableMerger` (continuation vs col-mismatch), `MarkdownAssembler`
  (ordering + rendering), VlmService no-op. Tiny `Line`/`Block` fixtures.
- **`MockVlmClient`**: deterministic fake `llm_client` returning canned tables/captions → end-to-end
  converter test, CI-friendly (mirrors markitdown-ocr's MockOCRService).
- **Tiny real-PDF fixtures** (1–2 pages, checked-in or reportlab-generated): `TextExtractor`
  (incl. a **spacing-quality assertion** guarding the 0.1.6 regression), `TableDetector`,
  `FigureExtractor`.
- **Opt-in integration smoke test**: live Ollama Qwen2.5-VL on one table page; skipped unless
  `RUN_VLM_INTEGRATION=1`.
- **Eval harness** (`tests/eval/`, a script): run on `2025059pap.pdf`, score headings / pipe-rows /
  figures / spacing vs the markitdown-0.1.6 baseline + Marker/Nanonets references → *verifies* the
  ~80 claim rather than asserting it.
- **CI** (GitHub Actions, py3.10–3.12): unit + mock-VLM + PDF-fixture only; integration + eval excluded.
- **TDD throughout**: failing test → implement, per the superpowers workflow.

## 10. Success criteria

- No endpoint: headings present (`#`/`##` hierarchy), figures extracted, clean text (spacing-quality
  guard passes), basic tables — eval ≈ **70** on `2025059pap.pdf` vs the **58** baseline.
- With endpoint: + specialist tables + captions — eval ≈ **80**.
- All stages unit-tested; converter passes the mock-VLM end-to-end test; plugin loads via
  `markitdown --use-plugins` and overrides the built-in PDF converter.
- Never produces output worse than the built-in converter at any capability level.

## 11. Future (v2 candidates)

Multi-column reading order (layout model), equations → LaTeX, scanned-PDF handling, Office formats,
a selectable Docling backend, cross-page figure handling, per-call kwargs overrides.
