# API reference (auto-generated)

Generated from `markitdown_pdf_plus` by `scripts/gen_api_docs.py`. Do not edit by hand;
the CI `docs` job regenerates this and fails if the committed copy is stale.

## `markitdown_pdf_plus`

markitdown-pdf-plus: enhanced PDF converter plugin for MarkItDown.

### func `register_converters(markitdown: Any, **kwargs: Any) -> None`

Entry point called by MarkItDown when plugins are enabled.

## `markitdown_pdf_plus._assemble`

### class `MarkdownAssembler()`

_Undocumented._

## `markitdown_pdf_plus._converter`

### class `PdfPlusConverter(vlm: Any, config: dict[str, typing.Any])`

Abstract superclass of all DocumentConverters.

## `markitdown_pdf_plus._extract`

### class `TextExtractor()`

Per-line text + font size + bbox via pdfminer (clean word spacing).

pdfminer (not pdfplumber.extract_words) because on justified/kerned PDFs
pdfplumber merges words and loses spaces; pdfminer's layout analysis keeps
spacing. pdfminer uses a bottom-left origin, so y is converted to a top-left
'top' to match the pdfplumber bboxes used by table/figure detection.

## `markitdown_pdf_plus._figures`

### class `FigureExtractor(image_dir: str | None, dpi: int = 200)`

_Undocumented._

### func `render_bbox_png_b64(pdf_bytes: bytes, page_index: int, bbox: tuple[float, float, float, float], dpi: int = 200) -> str`

_Undocumented._

## `markitdown_pdf_plus._headings`

### class `HeadingAnnotator()`

_Undocumented._

### func `body_font_size(lines: list[markitdown_pdf_plus._model.Line]) -> float`

_Undocumented._

### func `heading_level(line: markitdown_pdf_plus._model.Line, body: float) -> int`

Return heading level 1-3, or 0 if not a heading.

## `markitdown_pdf_plus._merge`

### class `CrossPageTableMerger()`

_Undocumented._

## `markitdown_pdf_plus._model`

### class `Block(kind: str, page: int, top: float, x0: float = 0.0, text: str = '', level: int = 0, markdown: str = '', image_path: str | None = None, caption: str | None = None, bbox: tuple[float, float, float, float] | None = None, cols: int = 0) -> None`

Block(kind: str, page: int, top: float, x0: float = 0.0, text: str = '', level: int = 0, markdown: str = '', image_path: str | None = None, caption: str | None = None, bbox: tuple[float, float, float, float] | None = None, cols: int = 0)

### class `Line(page: int, text: str, font_size: float, bold: bool, bbox: tuple[float, float, float, float]) -> None`

Line(page: int, text: str, font_size: float, bold: bool, bbox: tuple[float, float, float, float])

## `markitdown_pdf_plus._tables`

### class `TableDetector()`

_Undocumented._

## `markitdown_pdf_plus._vlm`

### class `VlmService(client: Any, model: str, table_prompt: str = 'Convert this table image to a GitHub-flavored Markdown pipe table. Preserve every row label, column header, numeric value, parenthesized standard error, and significance marker exactly. Output only the table.', caption_prompt: str = "Describe this figure for someone who can't see it: chart type, axes, series, and the main trend in 1-3 sentences. If it shows discrete values, add a small Markdown table.", max_tokens: int = 4096)`

_Undocumented._

### func `build_vlm_service(**kwargs: Any) -> markitdown_pdf_plus._vlm.VlmService | None`

_Undocumented._
