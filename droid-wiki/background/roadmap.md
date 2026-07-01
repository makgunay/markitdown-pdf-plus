# Roadmap

Two forward-looking directions have been measured or assessed but not shipped. Both target the same gap: better tables, and (further out) equations. The detail is in `docs/memory/04-roadmap-v0.2-tatr.md` and `docs/memory/05-mistral-ocr-4-assessment.md`.

## Two tiers, two answers

The reframed v0.2 thinking splits the table problem into a local tier and a cloud tier, and a backend-selectable design could offer both:

| Tier | Backend | For | Trade-off |
| --- | --- | --- | --- |
| Local | pdfminer + font headings + (v0.2) TATR-routed local VLM | offline, private, free | caps around 84, no equations |
| Cloud | Mistral OCR 4 | best quality, fastest, cheap per page | documents leave the machine, paid, proprietary |

## The TATR-routed local hybrid (parked, measured)

The idea is to move from VLM-first to the architecture serious tools use (Docling/Marker/MinerU): structure-model-first, VLM-optional.

1. **gmft/TATR detects all tables** (its decisive strength).
2. **A content router classifies each table by complexity.** A table is complex if it has at least 3 parenthesized standard errors or at least 3 significance stars (a regression table).
3. **Route:** complex tables go to a VLM via a crop; simple tables render deterministically from TATR's dataframe, no endpoint needed.

Measured on the 82-page paper: 30 tables detected, 25 complex → VLM, 5 simple → TATR, 3 prose false-positives dropped. What measuring taught:

- TATR's win is **detection**, not structuring: it caught main-body regression tables the pdfplumber detector missed entirely, but TATR-only structuring collapses to 72/Tables 48 because it scrambles or drops complex tables. The VLM is essential for complex tables.
- Routing buys correctness, not speed, for this regression-heavy paper (25/30 tables went to the VLM anyway).
- The remaining gap to Marker (87-89) is almost entirely equations (55 vs 88); neither the plugin nor TATR does math → LaTeX. That is the next lever after tables.

**Why it must be an optional extra:** gmft pulls torch and torchvision and pins transformers 4.x, which clashes with mlx-vlm's 5.x. It would ship as an optional `[tatr]` extra, never a core dependency, reinforcing the endpoint-based core. See [Design decisions](design-decisions.md).

## Mistral OCR 4 (assessed, not prototyped)

Mistral OCR 4 (released 2026-06-23) is a dedicated document-OCR cloud service (`/v1/ocr`, not chat-completions). The assessment: a strong fit as a new opt-in cloud backend, not a replacement for the local pipeline. It directly fills the two gaps the local path structurally cannot close: equations → LaTeX and multi-column reading order.

- It does **not** drop into the existing `llm_client` path: different API shape (a dedicated endpoint) and granularity (whole-document, not crops). It maps instead to a selectable backend that bypasses the local structure stack, much like full-page mode does today, but returning genuinely structured Markdown.
- Quality benchmarks sit above the scoreboard's ceiling references; pricing is roughly $0.33 per the 82-page paper via the API. Self-hosting is enterprise-and-GPU only, so for a normal user it is effectively a cloud paid API.
- **Roadmap consequence:** demote the TATR-routed hybrid from "the table answer" to "the local/offline table answer," and make a Mistral OCR backend the likely headline of v0.2 (less work, bigger jump).

### Tensions to hold honestly

Mistral is cloud, paid, and single-vendor, which sits against the project's local-first, model-agnostic, MIT-clean premises. It complements, never replaces, the local path; local stays the default. As an optional `[mistral]` extra it can even skip the SDK and hit `/v1/ocr` with a thin httpx adapter. Privacy makes it unacceptable for confidential PDFs, so it must be opt-in and documented, never default.

## Next concrete steps

1. Parameterize the eval harness to accept arbitrary PDF paths and loop a folder (the benchmark scripts currently hardcode the one paper).
2. Generalize the complexity router before trusting cross-domain table numbers (it is tuned to economics regression tables).
3. If validated, wire the routed hybrid in as the `[tatr]` extra, or prototype the Mistral `/v1/ocr` backend against the test paper to produce a real measured scoreboard row.
4. Separately, the equations lever (math → LaTeX) is the biggest remaining gap to Marker.

See [Research and benchmarks](research-and-benchmarks.md) for the measured rows these plans build on.
