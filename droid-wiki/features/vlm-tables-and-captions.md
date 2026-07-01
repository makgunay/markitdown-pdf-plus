# VLM tables and captions

Active contributors: Mehmet Akgunay

The VLM tier turns on when you pass an OpenAI-compatible `llm_client` and an `llm_model`. It transcribes each detected table region into a clean Markdown pipe table, captions figures, and merges tables that span page breaks. The plugin is model-agnostic: the same code works with a local Ollama model or a cloud OpenAI model.

## What you get

- **Clean table transcription.** Each detected table region is rendered to a PNG crop and sent to the vision model, which returns a Markdown pipe table preserving row labels, headers, numeric values, parenthesized standard errors, and significance markers.
- **Figure captions.** Each figure crop is described in 1-3 sentences (chart type, axes, series, main trend), with a small Markdown table for discrete values.
- **Cross-page table merging.** Consecutive table blocks with the same column count and no heading between them are joined into one table.

## How to use it

Local Ollama:

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
md = MarkItDown(enable_plugins=True, llm_client=client, llm_model="qwen2.5vl:7b")
result = md.convert("document.pdf")
```

Cloud OpenAI:

```python
import openai
from markitdown import MarkItDown

client = openai.OpenAI()  # uses OPENAI_API_KEY
md = MarkItDown(enable_plugins=True, llm_client=client, llm_model="gpt-4o")
result = md.convert("document.pdf")
```

## Tuning

| Option | Default | Effect |
| --- | --- | --- |
| `pdf_plus_dpi` | `200` | resolution of the table/figure PNG crops sent to the model |
| `pdf_plus_table_fallback` | `True` | fall back to a pdfplumber grid when the VLM is absent or a call fails |
| `pdf_plus_table_prompt` | built-in | override the table transcription prompt |
| `pdf_plus_caption_prompt` | built-in | override the figure caption prompt |
| `pdf_plus_max_tokens` | `4096` | response token budget per call |

See [Configuration](../reference/configuration.md) for the full list.

## Fail-soft behavior

A single bad crop or model call never aborts the document. If a call raises, or the model returns a refusal or non-table answer, the VLM service returns `None` and the converter falls back to the pdfplumber grid (when `pdf_plus_table_fallback` is on). Captions that fail are simply omitted. This contract is implemented in the [VLM service](../systems/vlm-service.md).

## Quality, measured

On the 82-page test paper, the VLM tier with a local Qwen2.5-VL endpoint transcribes the borderless summary-statistics and regression tables into clean Markdown pipe tables with captions preserved and no content duplication, matching dedicated tools' table quality while staying inside MarkItDown's interface. The full scoreboard, including which models worked and which did not, is in [Research and benchmarks](../background/research-and-benchmarks.md).

## Choosing a model

General vision models (Qwen2.5-VL) do well on tight, correctly-bounded region crops, which is exactly the plugin's per-region mode. Full-page OCR specialists are better used through [full-page mode](full-page-mode.md). The implementation that drives this choice is in [VLM service](../systems/vlm-service.md).
