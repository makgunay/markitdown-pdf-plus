# markitdown-pdf-plus

A [MarkItDown](https://github.com/microsoft/markitdown) plugin that overrides the built-in PDF converter with always-on font-heuristic heading detection and figure extraction, plus opt-in model-agnostic VLM table transcription, cross-page table merging, and figure captioning.

## Features

- **Font-heuristic headings** — promotes lines with larger or bolder fonts to `#`/`##`/`###` headings automatically, with no ML required.
- **Figure extraction** — detects image regions and, when a VLM client is provided, captions them.
- **VLM table transcription** — renders each detected table region as a PNG crop and sends it to any OpenAI-compatible vision model (Ollama, OpenAI, etc.) to produce clean Markdown tables.
- **Cross-page table merging** — consecutive table blocks with the same column count and no heading in between are merged into a single table.
- **Full-page VLM mode** — renders every page as a full-resolution PNG for fully vision-driven transcription (opt-in via `full_page=True`).
- **Graceful no-op** — works without a VLM client: font-heuristic headings and pdfplumber table fallback are always active.
- **Plugin priority −1.0** — registered at a lower priority than the built-in PDF converter so it takes precedence whenever `enable_plugins=True`.

## Install

```bash
pip install markitdown-pdf-plus
```

Or from source:

```bash
pip install -e ".[test]"
```

## Usage

### Without a VLM (headings + pdfplumber tables, always on)

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("document.pdf")
print(result.text_content)
```

### With a local Ollama model

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="qwen2.5vl:7b",
)
result = md.convert("document.pdf")
print(result.text_content)
```

### With OpenAI

```python
from markitdown import MarkItDown
import openai

client = openai.OpenAI()  # uses OPENAI_API_KEY env var

md = MarkItDown(enable_plugins=True, llm_client=client, llm_model="gpt-4o")
result = md.convert("document.pdf")
print(result.text_content)
```

## Configuration options (`pdf_plus_*` kwargs)

Pass extra keyword arguments to `md.convert()` to tune the plugin:

| Option | Type | Default | Description |
|---|---|---|---|
| `pdf_plus_dpi` | `int` | `200` | DPI for PNG crop rendering (tables and figures). |
| `pdf_plus_image_dir` | `str` or `None` | `None` | Directory to save extracted figure images (referenced by relative path). If `None`, figures are caption-only (no image bytes embedded), keeping the Markdown lean for LLM use. |
| `pdf_plus_table_fallback` | `bool` | `True` | Fall back to pdfplumber grid extraction when VLM transcription is unavailable or fails. |
| `pdf_plus_full_page` | `bool` | `False` | Render every page as a full PNG and send to VLM instead of per-region crops (requires a VLM client). |

Example:

```python
result = md.convert(
    "document.pdf",
    pdf_plus_dpi=300,
    pdf_plus_table_fallback=False,
    pdf_plus_full_page=False,
)
```

## CLI usage

MarkItDown does not forward arbitrary env vars to plugins via the CLI, but you can set `OPENAI_API_KEY` or configure Ollama before running:

```bash
OPENAI_API_KEY=sk-... markitdown document.pdf --use-plugins
```

## Known limitations

- **Single-column PDFs only** — multi-column layouts are not yet supported; reading order is a positional sort that may interleave columns. Use `full_page=True` with a VLM for multi-column documents.
- **Scanned PDFs** — rasterized pages with no text layer produce no headings or fallback tables. Use `full_page=True` with a capable VLM to transcribe them.
- **No bundled OCR** — the plugin ships no Tesseract/ML; scanned-PDF support depends entirely on the VLM path.
- **Table detection is heuristic** — borderless tables are found via text-alignment plus a numeric-density filter (catches academic data tables, rejects prose), but it isn't perfect on every layout. Detected tables are transcribed by the VLM when configured, or rendered as a pdfplumber grid (messy but structured) in no-VLM mode.

## Eval results

Measured on a representative 82-page academic PDF (a Federal Reserve working paper) against the markitdown-0.1.6 built-in PDF converter:

| Metric | markitdown-0.1.6 | pdf-plus (no VLM) | pdf-plus (+ Qwen2.5-VL) |
|---|---:|---:|---|
| Section headings (`#`) | 0 | **82** | **82** |
| Figures extracted | 0 | **11** | **11** (+ captions) |
| Table pipe-rows | 646 (scattered) | **609** (structured grids) | clean specialist tables |
| Run-together-word lines | 928 | **59** | **59** |

End-to-end verification with a local Qwen2.5-VL endpoint: the paper's summary-statistics and regression tables (which are borderless) are transcribed into clean Markdown pipe tables with captions preserved and no content duplication — matching dedicated tools' table quality while keeping the rest of MarkItDown's interface.

Run the evaluation harness yourself (set `PDFPLUS_OLLAMA=1` to include the VLM path):

```bash
python tests/eval/run_eval.py
```

## License

MIT
