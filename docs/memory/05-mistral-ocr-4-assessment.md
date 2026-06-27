# 05 · Mistral OCR 4 — fit assessment (2026-06-27)

Assessment of whether [Mistral OCR 4](https://docs.mistral.ai/models/model-cards/ocr-4-0)
(released 2026-06-23) fits the `markitdown-pdf-plus` workflow, and what adopting it would mean.

## Verdict

**Strong fit — but as a new opt-in *cloud backend*, not a replacement for the local pipeline.** It
is the concrete realization of the "selectable backend" idea already parked in the design spec (§11),
and it directly fills the two gaps the local path structurally cannot close: **equations→LaTeX** (our
55 vs Marker's 88) and **multi-column reading order** (an explicit v1 non-goal). It does **not** drop
into the existing `llm_client` path — different API shape and granularity (see below).

## What it is (verified)

- **`mistral-ocr-4-0`**, released 2026-06-23. A *dedicated document-OCR service* —
  `client.ocr.process()` against a **`/v1/ocr`** endpoint, **not** a chat-completions model.
- **Input:** PDF / PPTX / DOCX / image via URL or **base64** (local files work). **Output:** per-page
  **markdown**; a `tables` field with `table_format` = `null` | `markdown` | `html`; an `images`
  list with bounding boxes; and (OCR-4 only) `include_blocks` → paragraph-level bboxes across 12 typed
  blocks including **`equation`**, `table`, `caption`, `references`.
- **Quality:** **OlmOCRBench 85.20**, **OmniDocBench 93.07**, 72% blind-eval win rate, 170 languages —
  above our scoreboard's ceiling references (Marker ~76 olmOCR; MinerU OmniDoc 90.7). Mistral itself
  calls the benchmarks "directional."
- **Pricing:** **$4 / 1,000 pages** API · **$2 / 1,000** batch · **$5 / 1,000** with annotations. The
  82-page test paper ≈ **$0.33** (API) / **$0.16** (batch).
- **Deployment:** cloud (La Plateforme) for everyone. **Self-hosting is enterprise-only**, single GPU
  node via vLLM/TGI — *not* runnable on the M3 Max as a normal user. For us it is effectively a
  **cloud, paid API**.

## Architectural fit

The plugin's VLM path is OpenAI **chat-completions** transcribing **region crops** into table
markdown, plus a `full_page` mode sending whole-page PNGs to that same chat endpoint. Mistral OCR is
a **different API shape** (`/v1/ocr`, not chat-completions) and a **different granularity**
(whole-document, not crops). So it is **not** a swap-in for the VLM table step.

Conceptually it is the same *category* as Marker / Docling / MinerU — a full-document converter —
just cloud, SOTA, fast, and cheap. In our architecture it maps to a **selectable backend** that
bypasses the entire local structure stack (`_extract → _headings → _tables → _figures → _assemble`),
exactly like `full_page` mode does today, but returning genuinely structured markdown (tables,
equations, figures, reading order) instead of a raw page dump. Returned `images` map straight to
`pdf_plus_image_dir`; the `html` table option aligns with our own research finding ([02](02-research-and-benchmarks.md))
that HTML preserves colspan better than pipe tables.

> Related: markitdown's *native* `llm_client`/`llm_model` hook is for **image captioning only** — it
> does not run the PDF body/table extraction through the LLM. That is exactly why a Mistral OCR
> backend must be a **converter/plugin**, not just an `llm_client` swap. (Confirmed against the
> installed markitdown source; this is the same limitation that motivated building the plugin in the
> first place — see [01](01-project-context.md) origin story step 3.)

## Scoreboard impact

With OmniDoc 93 / OlmOCR 85 (both above Marker and MinerU) plus native equations + multi-column,
Mistral OCR 4 would very likely be the **top row (~90+)**, achieved in **seconds-to-minutes for
~$0.33/paper** vs Marker's ~18 min or our routed hybrid's 5–9 min. It raises the ceiling rather than
matching it. **Validate on `2025059pap.pdf` and score on our rubric before quoting a number** —
Mistral's own "directional" caveat plus our TEDS-vs-human finding ([02](02-research-and-benchmarks.md))
mean eyeballing the borderless regression tables + equations on *our* doc matters.

## Strategic impact on the v0.2 TATR work

This is the part that matters most. The **TATR-routed hybrid** ([04](04-roadmap-v0.2-tatr.md)) was the
plan to close the **table** gap *locally*. Mistral OCR 4 closes **tables + equations + multi-column**
in one cheap cloud call at higher quality, for a fraction of the engineering effort (a thin HTTP
adapter vs the torch / transformers-4.x / gmft integration we flagged as a real dependency cost).

They are **complementary, serving two segments** — and the backend-selectable design can offer both:

| Tier | Backend | For | Trade-off |
|---|---|---|---|
| **Local** | pdfminer + font headings + (v0.2) TATR-routed local VLM | offline · private · free | caps ~84, no equations |
| **Cloud** | **Mistral OCR 4** | best quality · fastest · cheap/page | docs leave the machine · paid · proprietary |

**Roadmap consequence:** demote TATR-routed from "*the* table answer" to "the *local/offline* table
answer," and make a **Mistral OCR backend the likely headline of v0.2** (less work, bigger jump). For
the user's stated next step — benchmark a wide range of their own PDFs — Mistral is also the cheaper,
faster harness to run that sweep, **provided those PDFs aren't confidential**.

## Tensions with founding premises (stated honestly)

1. **Local-first / no-API / private / free** — the project's reason for existing. Mistral is cloud +
   paid + documents leave the machine. It complements, never replaces, the local path. Keep local the
   default.
2. **Model-agnostic / OpenAI-compatible** — Mistral OCR is single-vendor proprietary, not the generic
   chat endpoint. Fine as an *optional* backend, but a named exception to the "any endpoint"
   abstraction.
3. **MIT-clean / light deps** — preserved if it is an optional `[mistral]` extra; can even skip the
   `mistralai` SDK and hit `/v1/ocr` with a ~30-line httpx adapter (no heavy dep).

## Integration shape & effort (if pursued)

- New `_mistral.py` (`MistralOcrBackend`) + a `pdf_plus_backend="mistral_ocr"` config selector; in
  that mode short-circuit the local stages, base64 the PDF, call `/v1/ocr` with
  `table_format="markdown"` (or `html` for complex tables), map `images` → `pdf_plus_image_dir`,
  concat per-page markdown.
- **Pin `mistral-ocr-4-0`, never `-latest`** — cloud models drift under aliases; reproducibility
  matters for a benchmarking tool.

## Risks

- **Privacy** — unacceptable for confidential PDFs; opt-in only, documented, never default.
- **Cost at bulk** — cheap per page but non-zero; batch API halves it.
- **Vendor lock-in** for that backend, unlike the generic chat path.
- **Self-host is enterprise+GPU only** — not a "local" option for this user; don't market it as one.

## Status

Assessment only — **not prototyped, not integrated.** Next concrete step if adopted: prototype the
`/v1/ocr` backend against `2025059pap.pdf` (needs a `MISTRAL_API_KEY`) to produce a real measured
scoreboard row, then decide v0.2 framing (Mistral cloud backend vs TATR local hybrid).

Sources: [model card](https://docs.mistral.ai/models/model-cards/ocr-4-0) ·
[announcement](https://mistral.ai/news/ocr-4/) ·
[OCR capabilities](https://docs.mistral.ai/capabilities/OCR/basic_ocr/) ·
[VentureBeat](https://venturebeat.com/data/mistral-launches-ocr-4-turning-document-extraction-into-a-full-enterprise-ai-play) ·
[self-deployment docs](https://docs.mistral.ai/models/deployment/local-deployment)
