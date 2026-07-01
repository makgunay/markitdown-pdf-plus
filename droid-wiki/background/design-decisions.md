# Design decisions

This page records the key decisions behind the plugin and the reasoning for each. The full detail is in `docs/memory/01-project-context.md`.

## Why a plugin at all

MarkItDown's built-in PDF path is a flat text extractor with no layout model: on academic PDFs it yields 0 headings, drops figures, and flattens tables. A research arc (see [Research and benchmarks](research-and-benchmarks.md)) showed the distance from the built-in converter to the quality ceiling was almost entirely structure and tables, both recoverable cheaply. There was also open community demand: MarkItDown issues asked for exactly this, and no existing plugin did region or full-page VLM conversion on born-digital PDFs. Building a standalone, publishable plugin kept users inside MarkItDown's interface and multi-format breadth.

## The decisions

| Decision | Rationale |
| --- | --- |
| **One "best-of-both" plugin** (always-on structure + opt-in VLM), the enhance pattern | One tool useful at every capability tier, not two separate tools |
| **Publishable from day one** — standalone MIT package, own repo | Open community demand; stays inside MarkItDown's ecosystem |
| **Tables-only VLM by default**, with `pdf_plus_full_page` as the escape hatch | Keeps the common case cheap; full-page handles multi-column / scanned / equations |
| **Ship both extras in v1** (cross-page merge + figure captioning) | Small additions that complete the academic-paper story |
| **Composable single-purpose stages** (not subclassing the built-in, not a monolith) | Sidesteps the 0.1.6 spacing regression; each stage is independently testable |
| **pdfminer for text, pdfplumber for geometry** | pdfplumber word extraction jams words on justified text; pdfminer preserves spacing |
| **Model-agnostic via OpenAI-compatible `llm_client`, no bundled ML** | Stays MIT-clean and light (no torch); works with Ollama / LM Studio / OpenAI / Gemini |
| **Priority −1.0** | Lower priority is tried first, so the plugin overrides the built-in PDF converter |

## Graceful degradation as a principle

The plugin guarantees useful output at every capability tier and is never worse than the built-in converter. With no client it produces font headings, pdfplumber grids, and figure regions; with a client it adds VLM tables and captions. This shaped the API: the VLM service is built only when both `llm_client` and `llm_model` are present, and every external call falls back rather than failing. See [Capabilities and modes](../features/index.md).

## Why endpoint-based VLM, not in-process

Bundling a vision or structure model would pull heavy dependencies (torch, transformers) and a license cost, and would tie the plugin to one model. The recurring transformers 4.x vs 5.x conflict (different tools demand different majors and cannot share one environment) made this concrete. The endpoint-based design keeps the core MIT-clean and light, and any future structure model must be an optional extra with pinned dependencies. This constraint also frames the [Roadmap](roadmap.md).

## Where the decisions are exercised

- The enhance pattern and priority live in [Orchestration](../systems/orchestration.md).
- The pdfminer choice lives in [Text extraction](../systems/text-extraction.md) and is justified in [Build findings](build-findings.md).
- The model-agnostic VLM lives in [VLM service](../systems/vlm-service.md).
