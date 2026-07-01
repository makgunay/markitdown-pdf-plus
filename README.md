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
| `pdf_plus_backend` | `str` | `local` | Conversion backend: `local`, `mistral_ocr`, or `paddleocr_vl`. |
| `pdf_plus_concurrency` | `int` | `4` | Parallel VLM/OCR calls (table crops, figure captions, full-page passes). |
| `pdf_plus_dpi` | `int` | `200` | DPI for PNG crop rendering (tables and figures). |
| `pdf_plus_image_dir` | `str` or `None` | `None` | Directory to save extracted figure images (referenced by relative path). If `None`, figures are caption-only (no image bytes embedded), keeping the Markdown lean for LLM use. |
| `pdf_plus_table_fallback` | `bool` | `True` | Fall back to pdfplumber grid extraction when VLM transcription is unavailable or fails. |
| `pdf_plus_full_page` | `bool` | `False` | (`local` backend) Render every page as a full PNG and send to VLM instead of per-region crops (requires a VLM client). |
| `pdf_plus_mistral_api_key` | `str` or `None` | env | (`mistral_ocr` backend) Mistral API key (or set `MISTRAL_API_KEY`). |
| `pdf_plus_mistral_model` | `str` | `mistral-ocr-4-0` | (`mistral_ocr` backend) Pinned OCR model version. |
| `pdf_plus_paddleocr_prompt` | `str` or `None` | built-in | (`paddleocr_vl` backend) Override the per-page doc-parsing prompt. |

Example:

```python
result = md.convert(
    "document.pdf",
    pdf_plus_dpi=300,
    pdf_plus_table_fallback=False,
    pdf_plus_full_page=False,
)
```

## Backends

### `local` (default)

The always-on, MIT-clean pipeline: pdfminer text + font-heuristic headings + pdfplumber/VLM tables +
figure extraction + cross-page merge. Works with no endpoint; add an `llm_client` for VLM table
transcription and captions, or `pdf_plus_full_page=True` for whole-page vision transcription.

### `mistral_ocr` (cloud, opt-in)

Routes the whole PDF through [Mistral OCR 4](https://mistral.ai/news/ocr-4/) in one call, returning
structured Markdown with tables (Mistral emits HTML automatically for complex/spanning tables),
equations→LaTeX, and multi-column reading order. Best quality and lowest latency for documents that
may leave the machine (~$2–4 / 1,000 pages).

```python
md = MarkItDown(
    enable_plugins=True,
    pdf_plus_backend="mistral_ocr",
    pdf_plus_mistral_api_key=os.environ["MISTRAL_API_KEY"],
)
```

Privacy: documents are sent to a third-party cloud API. Opt-in, never the default.

### `paddleocr_vl` (local, opt-in)

Routes each page through a local, OpenAI-compatible document-parsing VLM — e.g.
[PaddleOCR-VL](https://github.com/PaddlePaddle/PaddleOCR) served via `mlx_vlm.server` on Apple
Silicon, or vLLM on a GPU. Local, free, private; closes equations + multi-column like the cloud
backend but nothing leaves the machine. Reuses the `llm_client`/`llm_model` hook (no new core dep).

```python
client = OpenAI(base_url="http://localhost:8111/v1", api_key="x")
md = MarkItDown(
    enable_plugins=True,
    pdf_plus_backend="paddleocr_vl",
    llm_client=client,
    llm_model="PaddleOCR-VL-0.9B",
)
```

> **Note on the failure contract.** The graceful-degradation guarantee (never worse than the
> built-in converter) applies to the **`local`** backend. The opt-in `mistral_ocr` and `paddleocr_vl`
> backends raise on a missing client/key or a transport error rather than silently falling back, so a
> misconfiguration surfaces instead of producing degraded output. Per-page transcription itself stays
> fail-soft (a single bad page yields an empty section, not an aborted document).

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

All four columns are live runs against the same paper (`--backend` / `PDFPLUS_OLLAMA=1`):

| Metric | markitdown-0.1.6 | pdf-plus (no VLM) | pdf-plus (+ Qwen2.5-VL) | pdf-plus (Mistral OCR 4) |
|---|---:|---:|---:|---:|
| Section headings (`#`) | 0 | **82** | **82** | 35 |
| Figures extracted | 0 | **11** | **11** (+ captions) | 9 |
| Table pipe-rows | 646 (scattered) | 609 (26 grids) | 473 (**37** grids) | 406 (30 grids) |
| Equation markers (`$$`/`\(`) | 0 | 0 | **25** | **26** |
| Run-together-word lines | 928 | **59** | 74 | 69 |
| Wall-clock (82 pp) | ~3s | 9.2s | ~1505s ² | **2.9s** ¹ |

¹ A single `/v1/ocr` call. Requesting page-image base64 (which our backend does when `pdf_plus_image_dir`
is set, to save figure files) balloons this to ~180s on this document, so leave image extraction off
unless you need the figure files.
² Local `+VLM` via Ollama `qwen2.5vl:7b`. Ollama serializes vision calls, so `pdf_plus_concurrency`
does not help: one 7B model grinds through ~37 table-region transcriptions + 11 captions at ~17 tok/s.
A smaller doc-parsing model (`paddleocr_vl`, see the note below) decodes far faster per token
(~237 vs ~17 tok/s here), though its whole-page verbosity offsets much of that end-to-end.

The paper's summary-statistics and regression tables (borderless) are transcribed into clean Markdown
pipe tables with captions preserved and no content duplication. The takeaways:

- **Equations need a VLM, not heuristics.** Both VLM paths recover ~25–26 equation markers (→LaTeX);
  the no-VLM heuristic path gets 0. This is the clearest capability gap.
- **Quality is comparable across the VLM paths.** `+Qwen2.5-VL` and **Mistral OCR 4** land within a few
  points on every structural metric (Qwen finds the most tables, 37; Mistral the fastest at ~3s).
- **Latency is the real differentiator.** Mistral does the whole 82-page doc in ~3s; the local 7B VLM
  path takes ~25min on this machine because Ollama serializes. The no-VLM local path (~9s) is the
  middle ground when you don't need equations.
- **Mistral's lower heading count (35 vs 82)** reflects semantic heading detection rather than the local
  font-size heuristic's more aggressive promotion. Trade-off: the document leaves the machine (opt-in).

#### `paddleocr_vl` (experimental — deliberately *not* in the table above)

The `paddleocr_vl` backend sends each whole page to the **PaddleOCR-VL-1.5** doc-parser (0.9B,
Apache-2.0) served locally. Measured on the same paper via `mlx_vlm` 0.6.3 serving the 4-bit MLX
weights (`mlx-community/PaddleOCR-VL-1.5-4bit`, ~715 MB) at concurrency 1: **~894 s (~11 s/page)**,
with **strong body-text OCR**. It is kept out of the comparison table because it emits a different
Markdown dialect, so its structural counts are **not apples-to-apples**:

- **No headings.** 0 `#`/bold headings — it transcribes prose, not document structure.
- **Inline math, not display equations.** All math is inline `\(...\)` (629 markers: every superscript,
  footnote ref, R², significance star), with 0 `$$` blocks — not comparable to Mistral's 26.
- **"Run-together" is LaTeX.** 97% of its 1118 flagged lines are LaTeX/variable tokens
  (`\operatorname{...}`, `BankLoanExpense`), not OCR errors.
- **Occasional table blow-ups.** 2 pages rendered as giant empty `| | |` mega-rows (~4% of the output);
  the real regression tables transcribe correctly.
- **Verbose.** ~2x the character count of the other backends.

Net: a capable, fast-per-token local doc-OCR model that needs **output normalization** before its
Markdown matches the conventions the metrics (and the other backends) assume. Reproduce with
`mlx-vlm>=0.6.3` (the 0.6.2 processor loader is broken for this model):

```bash
python -m mlx_vlm.server --model mlx-community/PaddleOCR-VL-1.5-4bit \
  --port 8111 --trust-remote-code --max-tokens 4096 &
PDFPLUS_OPENAI_BASE=http://localhost:8111/v1 \
  PDFPLUS_OPENAI_MODEL=mlx-community/PaddleOCR-VL-1.5-4bit \
  PDFPLUS_OPENAI_KEY=x PDFPLUS_CONCURRENCY=1 \
  python tests/eval/run_eval.py --backend paddleocr_vl --no-baseline
```

Run the evaluation harness yourself (set `PDFPLUS_OLLAMA=1` to include the VLM path):

```bash
python tests/eval/run_eval.py
```

### Table-quality metrics (TEDS + LLM-judge)

Beyond the structural counts above, the harness can score table fidelity two complementary ways
(install the extra: `pip install -e ".[eval]"`):

- **`--teds`** — Tree-Edit-Distance Similarity (content-aware **TEDS** and structure-only
  **TEDS-Struct**) against a reference-model pseudo-ground-truth. By default a reference backend
  (`mistral_ocr`) is run live as "truth"; point `--teds-ref` at a stored `.md` instead. It is a
  deterministic *regression tracker*, not an absolute score.
- **`--judge`** — a source-image-grounded LLM-judge: each detected table region is cropped from the
  original PDF and a vision model scores how faithfully the predicted table reproduces it (no ground
  truth needed). This correlates with human grading far better than TEDS, so it is the quality gate.

```bash
# deterministic regression vs a Mistral reference
MISTRAL_API_KEY=... python tests/eval/run_eval.py --teds

# human-correlated quality via a vision judge, with a machine-readable dump
PDFPLUS_JUDGE_BASE=https://api.openai.com/v1 PDFPLUS_JUDGE_KEY=sk-... \
  python tests/eval/run_eval.py --judge --judge-model gpt-4o --out tests/_tmp/eval
```

## License

MIT
