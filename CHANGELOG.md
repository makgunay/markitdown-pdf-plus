# Changelog

## 0.2.0 — 2026-06-27

Selectable high-quality, low-latency backends + a concurrency overhaul.

### Added

**Backend-selectable architecture** (`pdf_plus_backend`, default `local`):
- `local` — the existing always-on pipeline (pdfminer text + font headings + pdfplumber/VLM tables +
  figures), now refactored behind a `Backend` protocol. No behavior change.
- `mistral_ocr` — routes the whole PDF through the **Mistral OCR 4** cloud document model
  (`/v1/ocr`, pinned `mistral-ocr-4-0`). Returns structured per-page Markdown (Mistral emits HTML
  tables automatically for complex/spanning tables), equations→LaTeX, and multi-column reading order
  in one call. Closes the two gaps the local heuristic path cannot. Zero new runtime deps (stdlib
  `urllib` adapter). Opt-in, never default; documents leave the machine. Set `pdf_plus_mistral_api_key`
  or `MISTRAL_API_KEY`.
- `paddleocr_vl` — routes each page through a **local, OpenAI-compatible document-parsing VLM**
  (PaddleOCR-VL / dots.ocr served via `mlx_vlm.server` on Apple Silicon or vLLM on a GPU).
  Local, free, private SOTA; also closes equations + multi-column. Reuses the `llm_client`/`llm_model`
  hook — no new core dependency. Override the per-page prompt with `pdf_plus_paddleocr_prompt`.

**Concurrency** (`pdf_plus_concurrency`, default 4):
- Table-region VLM transcription, figure captioning, and full-page page-level VLM calls now run in a
  bounded thread pool (I/O-bound network calls overlap), preserving deterministic block ordering and
  per-call fail-soft. Cuts wall-clock roughly N× on endpoint-bound documents.

**Eval harness** (`tests/eval/run_eval.py`):
- Multi-document/folder input, per-document wall-clock timing, a `--backend` selector, richer
  per-dimension metrics (markdown vs HTML tables, equation markers), and optional `--out` markdown
  dump. `PDFPLUS_OPENAI_BASE`/`_MODEL`/`_KEY` env knobs for any OpenAI-compatible endpoint.
- **Table-quality metrics** (new `eval` extra: `apted`):
  - `--teds` — content-aware **TEDS** + structure-only **TEDS-Struct** (`tests/eval/teds.py`) against
    a reference-model pseudo-ground-truth (default reference `mistral_ocr`, or a stored `--teds-ref`
    `.md`). Markdown pipe tables are normalized to HTML so loss of colspan/rowspan is penalized. A
    deterministic regression tracker, not an absolute score.
  - `--judge` — a source-image-grounded vision **LLM-judge** (`tests/eval/judge.py`): each detected
    table region is cropped from the original PDF and scored for fidelity, needing no ground truth and
    correlating with human grading far better than TEDS. Fail-soft, OpenAI-compatible, mock-tested.
  - Both metric modules ship CI-runnable unit tests; the harness also gains a per-document
    `--out`/JSON metrics dump.

### Changed
- `PdfPlusConverter` is now a thin dispatcher; the local pipeline lives in `_backends.LocalBackend`.
- Concurrency helper extracted to `_concurrency.map_ordered`.
- Whole-page transcription (local `full_page` and `paddleocr_vl`) now goes through a shared,
  fence-stripping `VlmService.transcribe_page` (doc-parsing VLMs commonly wrap output in ```` ```markdown ````
  fences) and a shared `render_pages_b64` renderer, removing duplicated render loops and the private
  `_call` reach-in.
- `paddleocr_vl` validates its client lazily in `convert()`, not at construction, so a missing client
  can no longer crash `MarkItDown(...)` setup at plugin-registration time.
- The opt-in `mistral_ocr`/`paddleocr_vl` backends raise on misconfiguration rather than falling back;
  the graceful-degradation guarantee applies to the `local` backend (documented in the README).

### Verified
- 49 offline tests pass; mypy strict + ruff clean; branch coverage 91.7% (88% floor).
- Local backend eval on the 82-page paper unchanged: 82 headings, 609 pipe rows, 11 figures, 59
  run-together lines, now timed (~6.7s no-VLM on M3 Max).

### Notes
- Mistral OCR 4 quality/latency on real documents should be measured with the upgraded harness
  (`--backend mistral_ocr`) before quoting a scoreboard row.
- The `paddleocr_vl` endpoint tier works on Apple Silicon today via `mlx_vlm.server`; an in-process
  `paddleocr` pipeline (PP-DocLayoutV2 + VLM) remains a future optional extra to avoid the
  PaddlePaddle/transformers dependency conflict.

## 0.1.0 — 2026-06-06

Initial release.

A [MarkItDown](https://github.com/microsoft/markitdown) plugin that overrides the built-in PDF
converter with always-on font-heuristic headings and figure extraction, plus opt-in,
model-agnostic VLM table transcription, cross-page table merging, and figure captioning.

### Added

**Always-on (no endpoint required):**
- Clean body-text extraction via **pdfminer** — avoids the word-spacing loss that pdfplumber's
  `extract_words` produces on justified/kerned academic PDFs.
- **Font-heuristic heading detection** (`#`/`##`/`###`) — recovers section structure with no ML.
- **Figure/image extraction.**
- **Borderless-table detection** — pdfplumber `text` strategy + a numeric-density validator
  (academic data tables are number-dense; prose isn't), with a pdfplumber grid fallback.

**Opt-in (any OpenAI-compatible `llm_client`):**
- **VLM table transcription** of detected table regions (tables-only by default).
- **`pdf_plus_full_page`** mode for whole-page vision transcription.
- **Cross-page table merging.**
- **Figure captioning.**

**Design:**
- Registered at priority −1.0 so it overrides the built-in PDF converter when `enable_plugins=True`.
- Graceful degradation — useful output at every capability level; never worse than the built-in.
- Model-agnostic — local (Ollama, LM Studio, mlx-vlm) or cloud (OpenAI, Gemini, …) endpoints.
- MIT-licensed, light dependencies (`pdfminer.six`, `pdfplumber`, `pypdfium2`, `Pillow`); no bundled ML.

### Verified

On an 82-page academic PDF, compared with the markitdown-0.1.6 built-in converter:

| Metric | markitdown 0.1.6 | pdf-plus (no VLM) | pdf-plus (+ Qwen2.5-VL) |
|---|---:|---:|---|
| Section headings | 0 | 82 | 82 |
| Figures extracted | 0 | 11 | 11 (+ captions) |
| Run-together-word lines | 928 | 59 | 59 |
| Borderless tables | scattered | structured grids | clean pipe tables w/ captions |

With a local Qwen2.5-VL endpoint, the paper's borderless summary-statistics and regression tables are
transcribed into clean Markdown pipe tables with captions preserved and no content duplication.

### Known limitations

- Single-column layouts only — multi-column documents need `full_page=True` with a VLM.
- No equation → LaTeX conversion (display equations remain inline text).
- Table detection is heuristic; not perfect on every layout.
- Scanned PDFs (no text layer) require the VLM path.
- The plugin's region-crop method suits general VLMs (e.g. Qwen2.5-VL); full-page OCR specialists
  (e.g. Nanonets-OCR2) are better used via `full_page=True`.
