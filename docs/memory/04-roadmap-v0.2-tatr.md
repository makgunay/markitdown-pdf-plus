# 04 · Roadmap — v0.2 TATR-routed hybrid (PARKED)

**Status: measured end-to-end, validated, NOT yet integrated into the published plugin. Parked
2026-06-07 at the user's request.** The benchmark scripts live in the sibling scratch dir
`tools/markitdown/` (`routed_detect.py` → `routed_vlm_{qwen,nanonets}.py` → `routed_assemble.py`,
outputs in `tools/markitdown/routed/`) and are re-runnable. **None of this touched the v0.1.0 plugin.**

> **Reframed 2026-06-27 by [05-mistral-ocr-4-assessment.md](05-mistral-ocr-4-assessment.md).** Mistral
> OCR 4 (cloud, SOTA, ~$0.33/paper) closes tables + equations + multi-column in one call, so the
> TATR-routed hybrid is no longer "*the* table answer" — it's the **local/offline/private** table
> answer. Likely v0.2 framing: a Mistral cloud backend as the headline (less work, bigger jump), with
> this TATR work as the local tier. Read doc 05 before resuming here.

## The idea: structure-model-first, VLM-optional

Move the plugin from VLM-first to the architecture the serious tools use (Docling/Marker/MinerU):

1. **gmft/TATR detects ALL tables** (its real, decisive strength — see "why" below).
2. **A content router classifies each table by complexity.** Heuristic: a table is **complex** if it
   has ≥3 parenthesized standard errors **or** ≥3 significance stars (i.e. a regression table).
3. **Route:** complex → render a crop → VLM transcription. Simple (summary-stat) → render
   deterministically from TATR's `df` (no VLM, no endpoint, instant).

## Measured results (on the 82-page paper)

Run composition: **30 tables detected → 25 complex→VLM, 5 simple→TATR, 3 prose false-positives
dropped.** TATR detect + route + 5 simple tables = **14–19 s**.

| Config | Tables | Overall | Time | Notes |
|---|:--:|:--:|---|---|
| **TATR-routed + Qwen2.5-VL** | 87 | **84** | ~9 min | best plugin config; Qwen 504 s (20 s/tbl) |
| **TATR-routed + Nanonets-OCR2** | 85 | **83** | ~5 min | ~99% of the quality, 2× faster; Nanonets 262 s (10 s/tbl) |
| **TATR-only (no VLM)** | 48 | **72** | 19 s | scrambles/drops complex tables — only good for summary-heavy docs |

## What measuring taught us (vs. the earlier projections)

1. **Projection was accurate where it counted** — projected routed+Qwen ≈84/Tables 88; measured
   **84/Tables 87**.
2. **TATR's win is DETECTION, not structuring.** It caught main-body regression Tables on **pp.52–55
   and 61 that the plugin's pdfplumber detector missed entirely** (pdfplumber found 26, dropped
   those). But TATR-only collapsed to **72/Tables 48** — its deterministic structuring scrambles or
   drops complex regression tables (17 survived, 13 dropped). **The VLM is essential for complex
   tables.** The earlier projected "no-VLM ≈75/Tables 68" was too optimistic; the honest floor is
   72/48.
3. **Routing buys correctness, not speed — for THIS paper.** It's regression-heavy, so 25/30 tables
   went to the VLM anyway → wall-clock ≈ full-VLM. On a summary-stat-heavy paper the deterministic
   path would save far more time. The router's payoff here is *correctness + detection completeness*.
4. **Nanonets beat its old reputation** (83 vs the old crop-based ~73). Given clean TATR-bounded
   crops: no 16-column blow-ups (median 7 cols, like Qwen), at ~half Qwen's time. It emits HTML
   `<table>` natively (colspan handles spanning headers better than pipe) → convert with
   `pandas.read_html(thousands=None)`.
5. **The remaining gap to Marker (87–89) is almost entirely equations** (55 vs 88). Neither the
   plugin nor TATR does math→LaTeX. **That's the next lever after tables.**

## Dependency cost (why it must be an optional extra)

gmft pulls **torch + torchvision** and pins **transformers 4.x** — which clashes with mlx-vlm's 5.x
(the recurring conflict from [03](03-build-findings.md)). So:
- It must ship as an **optional `[tatr]` extra**, never a core dependency.
- It's another reason the VLM path stays **endpoint-based** (no in-process transformers/mlx).
- gmft API notes for integration: `bbox` is `[x0, top, x1, bottom]` in **top-left PDF points** —
  directly compatible with the plugin's pdfminer-line frame, so routed tables slot into assembly by
  `(page, top)` with the existing de-dup logic. `ct.image()` → crop PIL, `ct.text()` → region text
  for routing, `df()` → dataframe (clean on summary tables, scrambled on regression tables — confirms
  the routing need). Use **raw cell strings**, not the coerced df, to avoid number mangling
  (`10,197`→`10197`, `7,991,557`→`7.99e6`).

## Next steps when work resumes

The user's stated next intent: **benchmark a wide range of their own PDFs.** To enable that:

1. **Parameterize the harness** — the scripts hardcode `PDF = "2025059pap.pdf"`. Add a PDF-path arg +
   per-doc output dirs, and a small driver to loop the 4 stages (`detect → vlm → assemble`) over a
   folder.
2. **Revisit the complexity router** — it's tuned to econ regression tables (parenthesized SEs +
   significance stars). Other table types (scientific, financial statements) will likely misroute;
   generalize the rule before trusting cross-domain numbers.
3. **Then, if validated, wire it into the plugin** as the `[tatr]` extra: TATR detection always-on
   (when installed), routed structure/VLM, HTML→pipe conversion in the assembler.
4. **Separately, the equations lever** (math→LaTeX) is the biggest remaining gap to Marker — out of
   scope for the table work but the next quality frontier.

## Open decision

At park time the open question was: *wire the routed hybrid into `markitdown-pdf-plus` as a `[tatr]`
extra now, or leave it as the validated benchmark?* Left as the benchmark. Resume here.
