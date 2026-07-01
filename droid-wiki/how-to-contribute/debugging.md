# Debugging

A troubleshooting runbook for the failure modes this plugin actually hits. The recurring theme: the real document fails where the fixtures pass, so the eval harness is your primary debugger.

## The eval is your debugger

When output looks wrong on a real PDF, run `tests/eval/run_eval.py` against `../markitdown/2025059pap.pdf` and compare the five metrics (headings, pipe rows, figures, run-together lines, characters) to the baseline. A regression in one metric points at one stage:

| Symptom (metric) | Likely stage | Where to look |
| --- | --- | --- |
| `runtogether_lines` jumps | text extraction | `src/markitdown_pdf_plus/_extract.py` — pdfminer vs word extraction |
| `headings` drops to 0 or explodes | heading detection | `src/markitdown_pdf_plus/_headings.py` — body-size baseline, thresholds |
| `pipe_rows` collapses on borderless tables | table detection / fallback | `src/markitdown_pdf_plus/_tables.py` — text strategy + numeric-density gate |
| table text duplicated outside the table | de-dup | `src/markitdown_pdf_plus/_converter.py` — coordinate alignment |
| "Table N." captions disappear | de-dup + heading rule | paragraph-only de-dup depends on the tightened heading heuristic |

## Common issues

**Table text appears twice.** The de-dup matches paragraph lines to a table bbox positionally. It depends on the [text extractor's](../systems/text-extraction.md) bottom-left → top-left coordinate conversion lining up with the pdfplumber geometry. If you changed the coordinate frame, the centers no longer fall inside the bbox and de-dup stops removing anything. Confirm `Line.bbox` uses `top = page_height - y1`.

**Borderless tables come out as flattened text (no VLM).** The grid fallback must try the text strategy: `extract_tables() or extract_tables(_TEXT_SETTINGS)`. If only the ruled strategy runs, a text-aligned table returns nothing. See [Build findings](../background/build-findings.md).

**Numeric row labels became `##` headings.** The heading heuristic must not promote numbered lines; same-size promotion is gated on short and bold. If you reintroduced numbered promotion, data rows like `2.1` get mis-tagged, and the paragraph-only de-dup will then incorrectly preserve them as "captions".

**Prose page detected as a table.** The numeric-density gate (≥0.25) in `_looks_like_table` is what rejects prose. If you loosened it, the permissive text strategy will cluster paragraphs into grids.

**VLM returns nothing useful.** `transcribe_table` returns `None` unless the (fence-stripped) output contains a pipe, so refusals and prose answers fall back to the grid. Check the model and prompt; raise `pdf_plus_max_tokens` for very large tables. Any exception in the call is caught, logged as a warning, and turned into a fallback, so check logs for `VLM call failed`.

## Logging

`VlmService` (`src/markitdown_pdf_plus/_vlm.py`) logs failed VLM calls via the standard `logging` module at WARNING level (`logger = logging.getLogger(__name__)`). Enable logging to see them:

```python
import logging
logging.basicConfig(level=logging.WARNING)
```

## Reproducing a randomized-order failure

The suite randomizes test order (pytest-randomly). If a test only fails sometimes, copy the seed printed at the top of the run and re-run with it to reproduce, then look for shared state between tests.

## External-tool gotchas (research phase)

If you revisit the benchmark tooling: Marker's `--use_llm` plus Ollama needs local patches (PNG instead of WebP encoding, and copying `$defs` into the structured-output schema), and these are lost on any reinstall. DeepSeek-OCR via LM Studio GGUF is broken; use mlx-vlm for MLX models. Details in [Build findings](../background/build-findings.md).
