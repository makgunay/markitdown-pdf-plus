# markitdown-pdf-plus

`markitdown-pdf-plus` is a [MarkItDown](https://github.com/microsoft/markitdown) plugin that overrides MarkItDown's built-in PDF converter. It recovers the document structure that a flat text extractor loses, adding font-heuristic headings and figure extraction (always on, no machine learning), plus opt-in vision-language model (VLM) table transcription, cross-page table merging, and figure captioning.

## What problem it solves

MarkItDown's built-in PDF path is a flat text extractor with no layout model. On academic PDFs it produces zero headings, drops figures, and flattens tables into streams of numbers. This plugin closes most of that gap with two cheap, MIT-clean levers instead of a heavy layout model:

1. **Structure via font heuristics** (always on, no ML) — per-character font sizes recover the heading hierarchy a layout model would produce, at near-zero cost.
2. **Tables via a model-agnostic VLM endpoint** (opt-in) — detected table-region crops are sent to any OpenAI-compatible vision model for clean Markdown transcription.

It registers at plugin priority `-1.0`, so it takes precedence over the built-in PDF converter whenever `enable_plugins=True`.

## Core principle: graceful degradation

The plugin produces useful output at every capability tier, and is never worse than the built-in converter:

| Tier | What you provide | What you get |
| --- | --- | --- |
| Baseline | nothing (no `llm_client`) | font-heuristic headings + pdfplumber table grids + uncaptioned figures |
| VLM | an OpenAI-compatible `llm_client` + `llm_model` | clean VLM-transcribed tables + figure captions + cross-page merge |
| Full page | `pdf_plus_full_page=True` + a client | every page rendered to PNG and transcribed whole (multi-column / scanned escape hatch) |

## Who uses it

Anyone converting born-digital PDFs (especially dense academic papers) to Markdown for LLM ingestion, RAG pipelines, or archival, while staying inside MarkItDown's interface and multi-format breadth. The plugin is published on [GitHub](https://github.com/Akgunay-Labs/markitdown-pdf-plus) and PyPI as `markitdown-pdf-plus`, MIT-licensed, Python ≥3.10, with no bundled ML weights.

## How the pieces fit

The plugin is a pipeline of small, single-purpose stages orchestrated by a thin `PdfPlusConverter`. Text and font metadata come from pdfminer; table and figure geometry come from pdfplumber and pypdfium2; the optional VLM path is a thin HTTP adapter over any chat-completions endpoint. See [Architecture](architecture.md) for the full data flow.

## Quick links

- [Architecture](architecture.md) — the conversion pipeline and data flow
- [Getting started](getting-started.md) — install, configure, run
- [Glossary](glossary.md) — project-specific terms
- [The conversion pipeline](../systems/index.md) — stage-by-stage implementation
- [Capabilities and modes](../features/index.md) — what each tier does and when to use it
- [Background and history](../background/index.md) — the research arc and design rationale

## Verified result

On an 82-page academic PDF (a Federal Reserve working paper), compared with the markitdown-0.1.6 built-in converter:

| Metric | markitdown 0.1.6 | pdf-plus (no VLM) | pdf-plus (+ Qwen2.5-VL) |
| --- | ---: | ---: | --- |
| Section headings | 0 | 82 | 82 |
| Figures extracted | 0 | 11 | 11 (+ captions) |
| Run-together-word lines | 928 | 59 | 59 |
| Borderless tables | scattered | structured grids | clean pipe tables with captions |

See [Research and benchmarks](../background/research-and-benchmarks.md) for the full measured scoreboard.
