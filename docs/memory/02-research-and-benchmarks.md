# 02 · Research & Benchmarks

All numbers below are on one document — `2025059pap.pdf`, an **82-page Fed FEDS working paper**
(dense with borderless economics regression tables: parenthesized standard errors, significance
stars, multi-level headers), on an **Apple M3 Max / 128 GB** (MPS; no CUDA). Scored on a weighted
rubric: **Text .30 · Structure .15 · Tables .30 · Equations .08 · Figures .10 · Refs .05 · Noise .02**.

> Caveat on rubric scores: they're a consistent internal yardstick, not a published benchmark.
> "Tables" was eyeballed against rendered pages plus column-count sanity checks, not TEDS (we never
> had ground-truth HTML). Treat them as ordinal, not absolute.

## The full scoreboard

★ = measured end-to-end this round · ~ = measured/estimated earlier.

| Approach | Text | Struct | Tables | Eqns | Figs | Refs | Noise | **Overall** | Time |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---|
| markitdown 0.1.6 | 68 | 45 | 50 | 50 | 10 | 70 | 40 | **~55** | 3.5 s |
| markitdown 0.1.5 | 92 | 45 | 35 | 55 | 10 | 85 | 55 | **58** | 6 s |
| Marker (no-OCR / text layer) | 88 | 90 | 25 | 65 | 70 | 80 | 50 | **~65** | 7 min |
| **pdf-plus (no VLM, pdfplumber)** | 92 | 82 | 50 | 55 | 68 | 88 | 76 | **~70** | ~10 s |
| **pdf-plus (TATR-only, no VLM)** ★ | 92 | 82 | 48 | 55 | 70 | 88 | 72 | **72** | 19 s |
| pdf-plus (+Nanonets, crop — old) | 92 | 82 | 55 | 55 | 70 | 88 | 70 | **~73** | ~8 min |
| pdf-plus (+Qwen, crop — old) | 92 | 82 | 84 | 55 | 70 | 88 | 78 | **~82** | ~10 min |
| **pdf-plus (TATR-routed + Nanonets)** ★ | 92 | 82 | 85 | 55 | 70 | 88 | 76 | **83** | ~5 min |
| **pdf-plus (TATR-routed + Qwen)** ★ | 92 | 82 | 87 | 55 | 70 | 88 | 78 | **84** | ~9 min |
| Marker (base hybrid) | 93 | 90 | 85 | 88 | 70 | 90 | 75 | **87** | ~18 min |
| Marker + Qwen refine | 93 | 90 | 88 | 88 | 70 | 90 | 75 | **~88** | ~18 min |
| Marker + Nanonets hybrid | 93 | 90 | 90 | 88 | 70 | 90 | 75 | **~89** | ~29 min |

**Shipped in v0.1.0:** the `pdf-plus (no VLM)` and `pdf-plus (+Qwen/+Nanonets, crop)` rows. The
TATR-routed rows are a **measured-but-unshipped** v0.2 prototype — see
[04-roadmap-v0.2-tatr.md](04-roadmap-v0.2-tatr.md).

## What each experiment proved

**markitdown 0.1.5 → 0.1.6 is a wash (58 → ~55).** 0.1.6 rewired `convert()` to per-page pdfplumber
extraction, so it now emits pipe tables (646 rows vs 0) — but they're messy (over-segmented columns,
detached significance stars, jammed cell words) AND body text regressed badly: **788 run-together
lines vs 12** in 0.1.5 (word-spacing lost on ~⅓ of lines; even the title page becomes a fake table).
Still 0 headings, 0 figures. This regression is *why* the plugin uses pdfminer for text, not
pdfplumber words.

**Marker is the quality ceiling (87) but heavy.** Pipeline of Surya (layout/OCR/reading-order) +
texify (math→LaTeX). Real grids, LaTeX equations, 10 figures, full heading hierarchy. ~18 min
inference (MPS-bound) + a one-time model download. GPL-3.0 → not bundleable. `--use_llm` with a local
Qwen via Ollama nudges tables ~0.82→0.91 TEDS (+~58 s/table) — a *real but modest* polish, because
base Marker is already strong.

**Marker with OCR disabled craters tables (~65).** `disable_ocr:true` is 2.5× faster (~7 min) and
keeps headings/figures/equations — but Marker fills table *cells* through its OCR pipeline, so
without it tables become per-character `<br>` soup even on a born-digital PDF. Lesson: "it has a text
layer, skip OCR" doesn't hold for Marker's tables.

**Local OCR specialists — the decisive table finding.** Tested directly on the Table 3 page
(image → markdown, the proper role for a specialist):
- **Nanonets-OCR2-3B (MLX `mlx-community/Nanonets-OCR2-3B-8bit` via `mlx-vlm`):** *best specialist.*
  Correct row structure, all coefficients/R²/N, ~32 s/page, peak 5.6 GB. Natively emits **HTML
  `<table>`** (colspan handles spanning super-headers better than pipe tables can). Only blemish:
  occasionally drops a few standard errors.
- **Qwen2.5-VL (Ollama):** numbers mostly right but **scrambles dense-table row structure**, ~105
  s/page. General VLMs mangle dense tables when doing free-form full-page OCR — but do well on
  *tight, correctly-bounded region crops* (the plugin's mode).
- **DeepSeek-OCR (LM Studio GGUF):** **broken** — degenerate output (emits `<|det|>` boxes,
  text="1"). LM Studio's vision pipeline doesn't replicate its custom arch.
- **Takeaway:** the working local specialists are the Qwen2.5-VL family via MLX/Ollama. The SOTA
  leaderboard winners (dots.ocr, PaddleOCR-VL, MinerU 2.5, olmOCR-2) are **CUDA/vLLM-bound** and
  won't serve on Apple Silicon. Three local-specialist integration attempts, three walls — *that is
  the finding*: model-agnostic-endpoint design beats trying to bundle a specialist.

**Hybrid wins, and the reason is the structure model.** The highest-fidelity result tested (~89–90)
was Marker for the whole doc + Nanonets re-transcribing the table pages. A dedicated layout/
table-structure model is what preserves the grid; a general VLM doing free-form OCR mangles it. This
insight drove the v0.2 direction (structure-model-first, VLM-optional).

## Table-improvement research (the v0.2 lever)

Deep research (Exa) on how the serious tools do tables surfaced these threads:

- **Every serious tool uses a dedicated table-structure model**, then matches PDF text back: Marker
  (Surya), Docling (DocLayNet + **TableFormer**), MinerU (PDF-Extract-Kit). The plugin's
  heuristic-detect → crop → VLM is the weak link by comparison.
- **Microsoft Table Transformer (TATR)** — **MIT**, DETR-based, trained on **PubTables-1M
  (scientific papers — our exact domain)**. Detection AP50 0.995, structure GriTS 0.985. Runs on
  **CPU**. Wrapped by **`gmft`** (lightweight, uses pypdfium2). This became the v0.2 prototype.
- **The architectural shift it implies:** move from *VLM-first* to **structure-model-first,
  VLM-optional** — exactly what Docling/Marker/MinerU do.
- **Emit HTML for complex tables, markdown for simple ones.** Markdown loses colspan/rowspan; HTML
  preserves them and embeds fine in a markdown doc. **OTSL** (IBM: 5 tokens vs HTML's 28, ~50%
  shorter, on-the-fly validity, used by MinerU 2.5 / Docling Granite-Vision) is the better target if
  you go model-based.
- **Cross-page merge is a known hard problem** (PubTables-v2 is the first multi-page TSR benchmark).
  The plugin's heuristic (same col count, consecutive pages) is the right idea but crude; a small
  continuation classifier lifts GriTS 0.577→0.684. Cheap intermediate win: require same col count
  **AND** table-1 ends near page bottom **AND** table-2 starts near top **AND** no heading/caption
  between **AND** the continuation lacks a repeated header.
- **We're not really measuring tables.** Counting pipe-rows is meaningless; the standard metric is
  **TEDS** (tree-edit-distance on the HTML tree). Caveat from "Beyond String Matching" (2026): TEDS
  compresses parsers into a narrow 0.66–0.88 band, and an **LLM-judge correlates far better with
  humans (r=0.93 vs TEDS 0.65)**. So: LLM-judge ("could a reader unambiguously reconstruct every
  cell→header mapping?") as the *quality* gate, TEDS for regression tracking.

## Environment conflicts that shaped the design

- **transformers 4.x vs 5.x is a recurring wall.** Marker/Surya and gmft/TATR need transformers
  **4.x**; mlx-vlm (Nanonets) needs **5.x** (removes `transformers.onnx`, which breaks Marker). They
  **cannot share one venv** — pin per-tool, or run sequentially. This is a direct reason the plugin's
  VLM path stays **endpoint-based** (no in-process transformers) and any future TATR backend must be
  an isolated optional extra.
- **Marker `--use_llm` + Ollama is broken out of the box** (two bugs). Details in
  [03-build-findings.md](03-build-findings.md).
