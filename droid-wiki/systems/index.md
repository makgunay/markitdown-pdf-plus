# The conversion pipeline

Active contributors: Mehmet Akgunay

This section documents the implementation of each pipeline stage: the code, the algorithms, and the invariants. For the user-facing capabilities and when to use each mode, see [Capabilities and modes](../features/index.md).

## Purpose

`markitdown-pdf-plus` converts a PDF stream to Markdown through a sequence of single-purpose stages. Each stage lives in its own `_*.py` module under `src/markitdown_pdf_plus/`, takes a simple input, and returns a simple output, so each is testable on its own. A thin orchestrator, `PdfPlusConverter`, wires them together.

## Stage order

```mermaid
graph LR
    A[TextExtractor] --> B[HeadingAnnotator]
    B --> C[TableDetector]
    C --> D[VlmService / grid fallback]
    D --> E[FigureExtractor]
    E --> F[CrossPageTableMerger]
    F --> G[MarkdownAssembler]
```

## Stage pages

| Stage | Module | Page |
| --- | --- | --- |
| Text extraction | `_extract.py` | [Text extraction](text-extraction.md) |
| Heading detection | `_headings.py` | [Heading detection](heading-detection.md) |
| Table detection, fallback, merge | `_tables.py`, `_merge.py` | [Table handling](table-handling.md) |
| Figure extraction and crop rendering | `_figures.py` | [Figures](figures.md) |
| VLM transcription and captioning | `_vlm.py` | [VLM service](vlm-service.md) |
| Orchestration, de-dup, assembly, registration | `_converter.py`, `_assemble.py`, `__init__.py` | [Orchestration](orchestration.md) |

## Shared data model

All stages exchange the two dataclasses defined in `src/markitdown_pdf_plus/_model.py`:

| Type | Fields | Produced by | Consumed by |
| --- | --- | --- | --- |
| `Line` | `page`, `text`, `font_size`, `bold`, `bbox` | `TextExtractor` | `HeadingAnnotator`, de-dup |
| `Block` | `kind`, `page`, `top`, `x0`, `text`, `level`, `markdown`, `image_path`, `caption`, `bbox`, `cols` | every stage | `CrossPageTableMerger`, `MarkdownAssembler` |

`BBox` is `tuple[float, float, float, float]` — `(x0, top, x1, bottom)` in PDF points, top-left origin. Keeping the data model this small is what lets the pure stages be tested with hand-built fixtures and no PDF or network.

## Key abstractions

| Type | File | Description |
| --- | --- | --- |
| `PdfPlusConverter` | `src/markitdown_pdf_plus/_converter.py` | Orchestrates all stages; the only `DocumentConverter` |
| `TextExtractor` | `src/markitdown_pdf_plus/_extract.py` | pdfminer lines with font metadata |
| `HeadingAnnotator` | `src/markitdown_pdf_plus/_headings.py` | font-tier heading classification |
| `TableDetector` | `src/markitdown_pdf_plus/_tables.py` | ruled + borderless detection, grid fallback |
| `FigureExtractor` | `src/markitdown_pdf_plus/_figures.py` | image-region extraction + PNG crops |
| `VlmService` | `src/markitdown_pdf_plus/_vlm.py` | endpoint adapter, fence-strip, fail-soft |
| `CrossPageTableMerger` | `src/markitdown_pdf_plus/_merge.py` | join tables across page breaks |
| `MarkdownAssembler` | `src/markitdown_pdf_plus/_assemble.py` | reading-order sort + rendering |

## Entry points for modification

To add a new block kind or change how a stage behaves, edit that stage's module and its targeted test. To change how stages are wired (ordering, a new branch, de-dup rules), edit `PdfPlusConverter.convert` (`src/markitdown_pdf_plus/_converter.py`). Start at [Orchestration](orchestration.md) to see how the pieces connect.
