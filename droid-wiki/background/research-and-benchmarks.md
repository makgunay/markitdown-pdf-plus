# Research and benchmarks

All numbers below come from one document: `2025059pap.pdf`, an 82-page Federal Reserve FEDS working paper dense with borderless economics regression tables (parenthesized standard errors, significance stars, multi-level headers), measured on an Apple M3 Max with 128 GB (MPS, no CUDA). Scores use a weighted rubric (Text .30, Structure .15, Tables .30, Equations .08, Figures .10, References .05, Noise .02). The full notes are in `docs/memory/02-research-and-benchmarks.md`.

> The rubric scores are a consistent internal yardstick, not a published benchmark. Treat them as ordinal, not absolute. Tables were eyeballed against rendered pages plus column-count sanity checks, not TEDS.

## The scoreboard

| Approach | Tables | Overall | Time |
| --- | ---: | ---: | --- |
| markitdown 0.1.6 | 50 | ~55 | 3.5 s |
| markitdown 0.1.5 | 35 | 58 | 6 s |
| Marker (no-OCR / text layer) | 25 | ~65 | 7 min |
| **pdf-plus (no VLM, pdfplumber)** | 50 | ~70 | ~10 s |
| pdf-plus (TATR-only, no VLM) | 48 | 72 | 19 s |
| pdf-plus (+Nanonets, crop — old) | 55 | ~73 | ~8 min |
| **pdf-plus (+Qwen, crop)** | 84 | ~82 | ~10 min |
| pdf-plus (TATR-routed + Nanonets) | 85 | 83 | ~5 min |
| pdf-plus (TATR-routed + Qwen) | 87 | 84 | ~9 min |
| Marker (base hybrid) | 85 | 87 | ~18 min |
| Marker + Nanonets hybrid | 90 | ~89 | ~29 min |

The rows shipped in v0.1.0 are **pdf-plus (no VLM)** and **pdf-plus (+Qwen/+Nanonets, crop)**. The TATR-routed rows are a measured-but-unshipped prototype, covered in [Roadmap](roadmap.md).

## What each experiment proved

**markitdown 0.1.5 → 0.1.6 is a wash.** 0.1.6 rewired conversion to per-page pdfplumber extraction, so it emits pipe tables (646 rows vs 0) but they are messy, and body text regressed badly: 788 run-together lines vs 12 in 0.1.5. Still 0 headings, 0 figures. This regression is exactly why the plugin uses pdfminer for text rather than pdfplumber words. See [Build findings](build-findings.md).

**Marker is the quality ceiling (87) but heavy.** A pipeline of Surya plus texify produces real grids, LaTeX equations, figures, and a full heading hierarchy, but takes about 18 minutes on the M3 Max and is GPL-3.0, so it cannot be bundled. With OCR disabled it is faster but its tables crater, because Marker fills table cells through its OCR pipeline even on born-digital PDFs.

**Local OCR specialists — the decisive table finding.** Tested directly on a dense table page:

- **Nanonets-OCR2-3B** (MLX): the best specialist, correct row structure, natively emits HTML `<table>` (colspan handles spanning headers better than pipe tables), occasionally drops a few standard errors.
- **Qwen2.5-VL** (Ollama): numbers mostly right but scrambles dense-table row structure when doing free-form full-page OCR; does well on tight, correctly-bounded region crops, which is the plugin's mode.
- **DeepSeek-OCR** (LM Studio GGUF): broken, degenerate output.

The takeaway: the working local specialists are the Qwen2.5-VL family via MLX/Ollama; the SOTA leaderboard winners are CUDA/vLLM-bound and will not serve on Apple Silicon. Three local-specialist integration attempts hit three walls. That is the finding: a model-agnostic-endpoint design beats trying to bundle a specialist.

**Hybrid wins, and the reason is the structure model.** The highest-fidelity result tested (~89-90) was Marker for the whole document plus Nanonets re-transcribing the table pages. A dedicated layout/table-structure model preserves the grid; a general VLM doing free-form OCR mangles it. This drove the v0.2 direction toward structure-model-first, VLM-optional.

## Table-measurement research

- Every serious tool (Marker/Surya, Docling/TableFormer, MinerU) uses a dedicated table-structure model, then matches PDF text back. The plugin's heuristic-detect → crop → VLM is the weak link by comparison.
- **Microsoft Table Transformer (TATR)** is MIT, trained on PubTables-1M (scientific papers), runs on CPU, and is wrapped by the lightweight `gmft`. It became the parked v0.2 prototype.
- **Emit HTML for complex tables, Markdown for simple ones.** Markdown loses colspan/rowspan; HTML preserves them and embeds fine in a Markdown document.
- **Counting pipe-rows is not measuring tables.** The standard metric is TEDS (tree-edit-distance on the HTML tree), but research suggests an LLM-judge correlates far better with humans than TEDS does. The intended posture: an LLM-judge as the quality gate, TEDS for regression tracking.

## Environment conflicts that shaped the design

The transformers 4.x vs 5.x split is a recurring wall: Marker/Surya and gmft/TATR need 4.x, while mlx-vlm (Nanonets) needs 5.x, and they cannot share one environment. This is a direct reason the plugin's VLM path stays endpoint-based and why any future TATR backend must be an isolated optional extra. See [Roadmap](roadmap.md) and [Design decisions](design-decisions.md).
