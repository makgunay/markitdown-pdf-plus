# Data models

The pipeline exchanges two dataclasses and one type alias, all defined in `src/markitdown_pdf_plus/_model.py`. Keeping the model small is what lets the pure stages be tested with hand-built fixtures.

## `BBox`

```python
BBox = tuple[float, float, float, float]  # (x0, top, x1, bottom), PDF points
```

A bounding box in PDF points with a **top-left origin**. Every stage after [text extraction](../systems/text-extraction.md) uses this frame; the extractor converts pdfminer's bottom-left coordinates into it.

## `Line`

One extracted text line, produced by `TextExtractor`.

| Field | Type | Description |
| --- | --- | --- |
| `page` | `int` | zero-based page index |
| `text` | `str` | the line's text |
| `font_size` | `float` | median glyph size, rounded to 0.1 |
| `bold` | `bool` | majority of glyphs have "Bold" in the font name |
| `bbox` | `BBox` | top-left bounding box |

Consumed by `HeadingAnnotator` (font size + bold) and by the converter's de-dup (page + `top` + text + bbox).

## `Block`

A positioned unit of output. The `kind` field selects which other fields are meaningful.

| Field | Type | Default | Used by kind |
| --- | --- | --- | --- |
| `kind` | `str` | — | `"heading"` / `"paragraph"` / `"table"` / `"figure"` |
| `page` | `int` | — | all |
| `top` | `float` | — | all (reading-order sort) |
| `x0` | `float` | `0.0` | all (reading-order sort) |
| `text` | `str` | `""` | heading, paragraph |
| `level` | `int` | `0` | heading (1-3) |
| `markdown` | `str` | `""` | table |
| `image_path` | `str \| None` | `None` | figure |
| `caption` | `str \| None` | `None` | figure |
| `bbox` | `BBox \| None` | `None` | table, figure |
| `cols` | `int` | `0` | table (drives cross-page merge) |

How each kind is created and rendered:

- **heading / paragraph** — created by `HeadingAnnotator` from a `Line`; rendered as `#`-prefixed text or plain text.
- **table** — created by the converter after detection; `markdown` holds the VLM or grid output, `cols` is derived from the first pipe row, `bbox` is the detected region. Rendered as its Markdown.
- **figure** — created by `FigureExtractor`; `image_path` is set only when `pdf_plus_image_dir` is configured, `caption` only when the VLM captions it. Rendered as `![caption](image_path)`.

All blocks are sorted by `(page, top, x0)` before rendering. See [Orchestration](../systems/orchestration.md) and [Assembly](../systems/orchestration.md#assembly).
