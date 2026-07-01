# Full-page mode

Active contributors: Mehmet Akgunay

Full-page mode is the escape hatch for documents the positional structure pipeline cannot handle: multi-column layouts, scanned pages with no text layer, and equation-heavy papers. When enabled, it bypasses every structure stage and sends each whole page as a PNG to the VLM, concatenating the per-page Markdown.

## When to use it

| Document type | Default pipeline | Full-page mode |
| --- | --- | --- |
| Single-column born-digital | best choice | unnecessary |
| Multi-column | columns can interleave | recommended |
| Scanned (no text layer) | no headings or tables | required |
| Equation-heavy | equations stay inline text | better, with a capable VLM |

The default per-region pipeline is the common case and stays cheap. Full-page mode trades that for whole-page vision transcription, which costs one model call per page.

## How to use it

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="qwen2.5vl:7b",
    pdf_plus_full_page=True,
)
result = md.convert("document.pdf")
```

Full-page mode requires a VLM client. With `pdf_plus_full_page=True` but no client, the plugin falls through to the normal structure pipeline.

## How it works

The branch sits at the top of `PdfPlusConverter.convert` (`src/markitdown_pdf_plus/_converter.py`). It counts pages with pdfplumber, renders each page to a PNG at `pdf_plus_dpi` via `_render_page_pil`, sends each to `VlmService._call` with the table prompt, and joins the results. None of the structure stages (text extraction, heading detection, table or figure detection, merge, assembly) run. See [Orchestration](../systems/orchestration.md).

## Model choice matters

Full-page transcription is the right role for full-page OCR specialists. General vision models can scramble dense-table row structure when given a whole page, but do well on the tight region crops the default pipeline uses. Pick the model to match the mode. The measured comparison is in [Research and benchmarks](../background/research-and-benchmarks.md).

## Trade-offs

- **Cost and latency** scale with page count (one call per page) rather than with the number of tables.
- **Structure quality** depends entirely on the model; the plugin contributes no font-heuristic headings or de-dup in this mode.
- **Reproducibility** depends on the endpoint; pin the model version where it matters.

For a cloud full-document alternative under evaluation (Mistral OCR 4), see [Roadmap](../background/roadmap.md).
