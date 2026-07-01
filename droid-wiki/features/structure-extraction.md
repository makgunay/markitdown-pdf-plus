# Structure extraction (baseline tier)

Active contributors: Mehmet Akgunay

The baseline tier runs with no VLM client and is always on. It recovers the document structure that MarkItDown's built-in PDF converter loses: headings, clean body text, figures, and detected tables rendered as grids. This is the floor of the graceful-degradation contract, and it is already a measurable improvement over the built-in converter.

## What you get

- **Headings** (`#`/`##`/`###`) promoted from larger or bold fonts. On the 82-page test paper this recovers 82 section headings where the built-in converter produces 0.
- **Clean body text** with word spacing preserved, via pdfminer rather than pdfplumber word extraction. Run-together-word lines drop from 928 (built-in) to 59.
- **Figure extraction** of embedded image regions. With `pdf_plus_image_dir` set, PNG crops are saved and referenced by relative path; without it, figures are caption-only placeholders.
- **Table grids** for both ruled and borderless tables, rendered with pdfplumber's cell extraction. Messy but structured, never a flat number stream.

## How to use it

No client, just enable plugins:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("document.pdf")
print(result.text_content)
```

To save figure images alongside the Markdown:

```python
result = md.convert("document.pdf", pdf_plus_image_dir="figs")
```

## The borderless-table catch

Academic data tables usually have no ruling lines. pdfplumber's default detection finds none of them. The baseline tier detects them with a text-alignment strategy plus a numeric-density filter (data tables are number-dense; prose is not), then renders them as pipe-table grids. This is what takes borderless-table pipe rows from 0 to 609 on the test paper. The mechanism is described in [Table handling](../systems/table-handling.md).

## Implementation

The capabilities here map directly to pipeline stages: [text extraction](../systems/text-extraction.md), [heading detection](../systems/heading-detection.md), [table handling](../systems/table-handling.md) (the grid fallback), and [figures](../systems/figures.md). The reason body text uses pdfminer is documented in [Build findings](../background/build-findings.md).

## When to add a VLM

The grid fallback preserves structure but not always clean cell boundaries on dense regression tables. If you need publication-quality tables and figure captions, add an `llm_client`. See [VLM tables and captions](vlm-tables-and-captions.md).
