# Glossary

Project-specific terms and domain vocabulary used across this wiki and the codebase.

**Block** — A positioned unit of output produced by the pipeline: a heading, paragraph, table, or figure. Defined as a dataclass in `src/markitdown_pdf_plus/_model.py`. Blocks carry their page, vertical position (`top`), and left edge (`x0`) so the assembler can sort them into reading order.

**Borderless table** — A table with no ruling lines whose columns are defined only by text alignment, common in academic papers. pdfplumber's default line strategy finds none of these; the plugin detects them with the text strategy plus a numeric-density validator. See [Table handling](../systems/table-handling.md).

**BBox / bounding box** — A `tuple[float, float, float, float]` of `(x0, top, x1, bottom)` in PDF points, top-left origin. The `BBox` type alias lives in `src/markitdown_pdf_plus/_model.py`.

**Body font size** — The modal (most common) font size among text lines on a page, computed in `body_font_size` (`src/markitdown_pdf_plus/_headings.py`). Heading detection compares each line's size against this baseline.

**Cross-page merge** — Joining two consecutive table blocks that continue across a page break, when they have the same column count and no heading appears between them. Implemented in `src/markitdown_pdf_plus/_merge.py`.

**Full-page mode** — An opt-in mode (`pdf_plus_full_page=True`) that bypasses the structure pipeline and sends each whole page as a PNG to the VLM. The escape hatch for multi-column, scanned, and equation-heavy documents.

**Font heuristic** — Recovering heading structure from per-character font sizes (and the bold flag) rather than from a trained layout model. The plugin's always-on, no-ML structure lever.

**Graceful degradation** — The core design principle: useful output at every capability tier, never worse than the built-in converter. No client yields headings plus pdfplumber grids; a client adds VLM tables and captions.

**Grid fallback** — The no-VLM path for rendering a detected table region, using pdfplumber's own cell extraction (`extract_grid_markdown` in `src/markitdown_pdf_plus/_tables.py`). Messy but structured, never a flattened text dump.

**Line** — One extracted text line with its font metadata, produced by `TextExtractor` (`src/markitdown_pdf_plus/_extract.py`). The input to heading annotation.

**MarkItDown** — Microsoft's document-to-Markdown library that this project plugs into. The plugin overrides MarkItDown's built-in PDF converter. See [github.com/microsoft/markitdown](https://github.com/microsoft/markitdown).

**Numeric density** — The fraction of a candidate table's cells that contain a digit. A region must reach ≥0.25 to be accepted as a borderless table; this discriminator catches number-dense academic data tables while rejecting prose.

**pdfminer** — The text-extraction library (`pdfminer.six`) used for body text, chosen over pdfplumber's `extract_words` because it preserves word spacing on justified and kerned text.

**pdfplumber** — The library used for table and figure geometry (region detection, cell extraction, page cropping).

**pypdfium2** — The PDFium binding used to rasterize page and region crops to PNG for the VLM and for saved figures.

**Priority −1.0** — The registration priority of `PdfPlusConverter`. Lower priority means MarkItDown tries it first, so it overrides the built-in PDF converter when plugins are enabled.

**Run-together line** — A line of body text where word spacing was lost and words are jammed together. A failure mode of pdfplumber word extraction on justified text; the metric the eval harness tracks to validate the pdfminer text path.

**Stage** — One single-purpose step of the pipeline (extract, annotate, detect, merge, assemble). Each lives in its own `_*.py` module and is independently testable.

**TATR (Table Transformer)** — Microsoft's MIT-licensed, DETR-based table-structure model trained on scientific papers. A measured-but-unshipped v0.2 prototype for structure-model-first detection. See [Roadmap](../background/roadmap.md).

**VLM (vision-language model)** — A vision model reached through an OpenAI-compatible chat-completions endpoint. The opt-in backend for table transcription and figure captioning. The plugin is model-agnostic: any compatible endpoint works.
