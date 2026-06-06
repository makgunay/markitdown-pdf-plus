# Changelog

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
