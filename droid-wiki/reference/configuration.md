# Configuration

All configuration is passed as keyword arguments to `MarkItDown(...)` (or to `md.convert(...)`). `register_converters` in `src/markitdown_pdf_plus/__init__.py` reads them. CLI users set the `pdf_plus_*` values via environment variables where MarkItDown forwards them.

## VLM client

| Kwarg | Type | Default | Purpose |
| --- | --- | --- | --- |
| `llm_client` | OpenAI-compatible client | none | the vision endpoint; absent means the VLM tier is off |
| `llm_model` | `str` | none | model name; required alongside `llm_client` to enable the VLM |

If either is missing, `build_vlm_service` returns `None` and the plugin runs the always-on structure path only (font headings + pdfplumber grids + figure regions). See [VLM service](../systems/vlm-service.md).

## Plugin options

| Kwarg | Type | Default | Purpose |
| --- | --- | --- | --- |
| `pdf_plus_full_page` | `bool` | `False` | render every page to a PNG and send the whole page to the VLM, bypassing the structure pipeline (requires a client) |
| `pdf_plus_image_dir` | `str` or `None` | `None` | directory to save extracted figure PNGs (referenced by relative path); `None` keeps figures caption-only and the Markdown lean |
| `pdf_plus_dpi` | `int` | `200` | DPI for PNG crop rendering of tables and figures (and full pages) |
| `pdf_plus_table_fallback` | `bool` | `True` | fall back to pdfplumber grid extraction when VLM transcription is unavailable or fails |
| `pdf_plus_table_prompt` | `str` | built-in | override the table transcription prompt |
| `pdf_plus_caption_prompt` | `str` | built-in | override the figure caption prompt |
| `pdf_plus_max_tokens` | `int` | `4096` | response token budget per VLM call |

The default prompts (`DEFAULT_TABLE_PROMPT`, `DEFAULT_CAPTION_PROMPT`) are defined in `src/markitdown_pdf_plus/_vlm.py`.

## How the config maps internally

`register_converters` builds a config dict with four keys (`full_page`, `image_dir`, `dpi`, `table_fallback`) and passes it, plus the optional `VlmService`, to `PdfPlusConverter`. The prompt and token overrides are consumed by `build_vlm_service` when constructing the service. See [Orchestration](../systems/orchestration.md).

## Example

```python
result = md.convert(
    "document.pdf",
    pdf_plus_dpi=300,
    pdf_plus_table_fallback=False,
    pdf_plus_full_page=False,
)
```

## Credentials

The plugin itself takes no secrets. You construct the `llm_client` (for example `openai.OpenAI()`), and that client reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` from the environment. `.env.example` documents the variables used by the eval and integration helpers (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, and the opt-in flags `PDFPLUS_OLLAMA`, `RUN_VLM_INTEGRATION`). Copy it to a gitignored `.env`; never commit secrets.
