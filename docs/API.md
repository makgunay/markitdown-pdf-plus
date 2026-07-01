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

## `markitdown_pdf_plus._backends`

Selectable conversion backends.

Each backend turns raw PDF bytes into a Markdown string. The default ``LocalBackend``
runs the always-on, MIT-clean local pipeline (pdfminer text + font headings +
pdfplumber/VLM tables + figures). Optional backends route the whole document through
a SOTA full-document model (cloud or local) for higher quality and lower latency.

### class `Backend(*args, **kwargs)`

Base class for protocol classes.

Protocol classes are defined as::

    class Proto(Protocol):
        def meth(self) -> int:
            ...

Such classes are primarily used with static type checkers that recognize
structural subtyping (static duck-typing).

For example::

    class C:
        def meth(self) -> int:
            return 0

    def func(x: Proto) -> int:
        return x.meth()

    func(C())  # Passes static type check

See PEP 544 for details. Protocol classes decorated with
@typing.runtime_checkable act as simple-minded runtime protocols that check
only the presence of given attributes, ignoring their type signatures.
Protocol classes can be generic, they are defined as::

    class GenProto[T](Protocol):
        def meth(self) -> T:
            ...

### class `LocalBackend(vlm: Any, config: dict[str, typing.Any])`

The always-on local pipeline. ``vlm`` is optional (None → grids + uncaptioned figures).

### func `build_backend(vlm: Any, config: dict[str, typing.Any]) -> markitdown_pdf_plus._backends.Backend`

Select a backend by ``config['backend']`` (default ``'local'``).

## `markitdown_pdf_plus._concurrency`

### func `map_ordered(fn: collections.abc.Callable[[~_T], ~_R], items: collections.abc.Sequence[~_T], concurrency: int) -> list[~_R]`

Apply ``fn`` over ``items`` preserving input order.

Runs concurrently in a thread pool when it helps (``concurrency`` > 1 and more
than one item); otherwise sequentially. The VLM/OCR calls are I/O-bound network
requests, so threads overlap their latency. ``fn`` must be fail-soft (the VLM
methods catch their own exceptions and return ``None``).

## `markitdown_pdf_plus._converter`

### class `PdfPlusConverter(vlm: Any, config: dict[str, typing.Any])`

Thin MarkItDown converter: accepts PDFs and delegates to a selectable backend.

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

### func `render_pages_b64(pdf_bytes: bytes, dpi: int = 200) -> list[str]`

Render every page to a base64-encoded PNG, opening the document once.

Sequential on purpose: pypdfium2 is kept single-threaded. Shared by the
whole-page backends (local full_page, paddleocr_vl).

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

## `markitdown_pdf_plus._mistral`

Mistral OCR 4 cloud backend (opt-in).

Routes the whole PDF through Mistral's dedicated ``/v1/ocr`` document model, which
returns structured per-page Markdown (tables as markdown/HTML, equations, figure
bounding boxes) in one call. This closes the two gaps the local heuristic path
cannot: equations->LaTeX and multi-column reading order.

Privacy note: this sends the document to a third-party cloud API. It is opt-in
(``pdf_plus_backend="mistral_ocr"``), never the default.

No new runtime dependency: the HTTP call uses the standard library so the backend
works without installing an SDK. Set ``pdf_plus_mistral_api_key`` or ``MISTRAL_API_KEY``.

### class `MistralOcrBackend(config: dict[str, typing.Any], poster: collections.abc.Callable[[str, dict[str, typing.Any], dict[str, str], float], dict[str, typing.Any]] | None = None)`

Convert a PDF via the Mistral OCR document API. ``poster`` is injectable for tests.

### class `MistralOcrError(...)`

Unspecified run-time error.

## `markitdown_pdf_plus._model`

### class `Block(kind: str, page: int, top: float, x0: float = 0.0, text: str = '', level: int = 0, markdown: str = '', image_path: str | None = None, caption: str | None = None, bbox: tuple[float, float, float, float] | None = None, cols: int = 0) -> None`

Block(kind: str, page: int, top: float, x0: float = 0.0, text: str = '', level: int = 0, markdown: str = '', image_path: str | None = None, caption: str | None = None, bbox: tuple[float, float, float, float] | None = None, cols: int = 0)

### class `Line(page: int, text: str, font_size: float, bold: bool, bbox: tuple[float, float, float, float]) -> None`

Line(page: int, text: str, font_size: float, bold: bool, bbox: tuple[float, float, float, float])

## `markitdown_pdf_plus._paddleocr`

PaddleOCR-VL / dots.ocr local full-document VLM backend (opt-in).

Routes the whole document through a local, OpenAI-compatible document-parsing VLM
(e.g. PaddleOCR-VL served via ``mlx_vlm.server`` on Apple Silicon, or vLLM on a GPU).
Each page is rendered to a PNG and sent to the endpoint, which returns structured
Markdown with tables, equations, and reading order in one pass per page.

This is the local, free, private SOTA tier. Unlike the Mistral cloud backend, no
document leaves the machine. Unlike the ``local`` backend's region-crop table path,
it closes the equations and multi-column gaps a heuristic pipeline cannot.

Requires an ``llm_client``/``llm_model`` pointing at a doc-parsing VLM endpoint.
No new core dependency -- it reuses the existing OpenAI-compatible ``VlmService``.

### class `PaddleOcrBackend(vlm: Any, config: dict[str, typing.Any])`

Whole-document page-by-page VLM transcription using a local doc-parsing endpoint.

## `markitdown_pdf_plus._tables`

### class `TableDetector()`

_Undocumented._

## `markitdown_pdf_plus._vlm`

### class `VlmService(client: Any, model: str, table_prompt: str = 'Convert this table image to a GitHub-flavored Markdown pipe table. Preserve every row label, column header, numeric value, parenthesized standard error, and significance marker exactly. Output only the table.', caption_prompt: str = "Describe this figure for someone who can't see it: chart type, axes, series, and the main trend in 1-3 sentences. If it shows discrete values, add a small Markdown table.", max_tokens: int = 4096)`

_Undocumented._

### func `build_vlm_service(**kwargs: Any) -> markitdown_pdf_plus._vlm.VlmService | None`

_Undocumented._
