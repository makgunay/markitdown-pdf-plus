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
| `pdf_plus_image_dir` | `str` or `None` | `None` | Directory to save extracted figure images. If `None`, figures are base64-encoded inline. |
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

- **Single-column PDFs only** — multi-column layouts are not yet supported; text extraction follows the order pdfplumber returns words, which may interleave columns.
- **Scanned PDFs** — rasterized pages with no text layer produce no headings or pdfplumber tables. Use `full_page=True` with a capable VLM to transcribe them.
- **No OCR fallback** — the plugin does not bundle Tesseract or any OCR engine; scanned-PDF support depends entirely on the VLM path.
- **Table heuristic** — pdfplumber's `find_tables` requires explicit lines/borders; borderless tables are not detected in fallback mode (but a VLM may still transcribe them via the full-page path).

## Eval results

Evaluated against the markitdown-0.1.6 built-in PDF converter on a representative academic PDF:

| Metric | markitdown-0.1.6 | markitdown-pdf-plus (no VLM) |
|---|---|---|
| Heading recall | baseline | improved (font-heuristic) |
| Table Markdown | pdfplumber fallback | pdfplumber fallback + optional VLM |
| Figure captions | none | optional VLM captions |

Run the evaluation harness yourself:

```bash
python tests/eval/run_eval.py
```

## License

MIT
