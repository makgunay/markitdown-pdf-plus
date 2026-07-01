"""Selectable conversion backends.

Each backend turns raw PDF bytes into a Markdown string. The default ``LocalBackend``
runs the always-on, MIT-clean local pipeline (pdfminer text + font headings +
pdfplumber/VLM tables + figures). Optional backends route the whole document through
a SOTA full-document model (cloud or local) for higher quality and lower latency.
"""

import io
from typing import Any, Protocol, runtime_checkable

import pdfplumber

from ._assemble import MarkdownAssembler
from ._concurrency import map_ordered
from ._extract import TextExtractor
from ._figures import FigureExtractor, render_bbox_png_b64, render_pages_b64
from ._headings import HeadingAnnotator
from ._merge import CrossPageTableMerger
from ._model import BBox, Block, Line
from ._tables import TableDetector


@runtime_checkable
class Backend(Protocol):
    def convert(self, data: bytes) -> str:
        """Convert raw PDF bytes to a Markdown string."""
        ...


def _inside(line_bbox: BBox, region_bbox: BBox) -> bool:
    lx0, ltop, lx1, lbottom = line_bbox
    rx0, rtop, rx1, rbottom = region_bbox
    cx, cy = (lx0 + lx1) / 2, (ltop + lbottom) / 2
    return rx0 <= cx <= rx1 and rtop <= cy <= rbottom


class LocalBackend:
    """The always-on local pipeline. ``vlm`` is optional (None → grids + uncaptioned figures)."""

    def __init__(self, vlm: Any, config: dict[str, Any]):
        self.vlm = vlm
        self.config = config or {}
        self.concurrency = int(self.config.get("concurrency", 4))

    def convert(self, data: bytes) -> str:
        dpi = self.config.get("dpi", 200)
        image_dir = self.config.get("image_dir")
        fallback = self.config.get("table_fallback", True)
        if self.config.get("full_page") and self.vlm is not None:
            return self._convert_full_page(data, dpi)
        return self._convert_local(data, dpi, image_dir, fallback)

    def _convert_full_page(self, data: bytes, dpi: int) -> str:
        """Render each page to a PNG and let the VLM transcribe it whole.

        Pages are rendered sequentially (pypdfium2 is kept single-threaded), then
        the page-level VLM calls run concurrently since they are network-bound.
        """
        page_b64 = render_pages_b64(data, dpi)
        pages_md = map_ordered(self.vlm.transcribe_page, page_b64, self.concurrency)
        return "\n\n".join(pages_md).strip()

    def _convert_local(self, data: bytes, dpi: int, image_dir: str | None, fallback: bool) -> str:
        lines = TextExtractor().extract(io.BytesIO(data))
        blocks: list[Block] = HeadingAnnotator().annotate(lines)

        # Sequential render pass: detect tables/figures and render their crops
        # (pdfplumber/pypdfium2 stay on one thread). Defer only the VLM calls.
        table_specs: list[tuple[int, BBox, str | None, str | None]] = []
        figure_specs: list[tuple[Block, str | None]] = []
        td = TableDetector()
        fx = FigureExtractor(image_dir=image_dir, dpi=dpi)
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pi, page in enumerate(pdf.pages):
                for bbox in td.detect(page):
                    crop = render_bbox_png_b64(data, pi, bbox, dpi) if self.vlm is not None else None
                    fb = td.extract_grid_markdown(page, bbox) if fallback else None
                    table_specs.append((pi, bbox, crop, fb))
                for fig in fx.extract(page, pi, data):
                    crop = (
                        render_bbox_png_b64(data, pi, fig.bbox, dpi)
                        if self.vlm is not None and fig.bbox is not None
                        else None
                    )
                    figure_specs.append((fig, crop))

        # Concurrent VLM pass (I/O-bound), then assemble deterministically.
        table_results = self._transcribe_tables(table_specs)
        self._caption_figures(figure_specs)

        table_regions: list[tuple[int, BBox]] = []
        for (pi, bbox, _crop, fb), vlm_md in zip(table_specs, table_results, strict=True):
            md = vlm_md or fb
            if not md:
                continue
            blocks.append(
                Block(
                    kind="table",
                    page=pi,
                    top=bbox[1],
                    x0=bbox[0],
                    markdown=md,
                    bbox=bbox,
                    cols=self._col_count(md),
                )
            )
            table_regions.append((pi, bbox))

        # Drop paragraph lines inside any accepted table region so their content
        # isn't duplicated. Headings (e.g. a "Table N. ..." caption) are kept --
        # the heading heuristic no longer mis-tags table rows, so any heading
        # inside a region is a real one.
        blocks = [b for b in blocks if not self._is_dup_paragraph(b, table_regions, lines)]
        blocks.extend(fig for fig, _crop in figure_specs)

        blocks = CrossPageTableMerger().merge(blocks)
        return MarkdownAssembler().assemble(blocks)

    def _transcribe_tables(self, specs: list[tuple[int, BBox, str | None, str | None]]) -> list[str | None]:
        if self.vlm is None:
            return [None] * len(specs)
        return map_ordered(
            lambda s: self.vlm.transcribe_table(s[2]) if s[2] is not None else None,
            specs,
            self.concurrency,
        )

    def _caption_figures(self, specs: list[tuple[Block, str | None]]) -> None:
        if self.vlm is None:
            return
        captions = map_ordered(
            lambda s: self.vlm.caption_figure(s[1]) if s[1] is not None else None,
            specs,
            self.concurrency,
        )
        for (fig, _crop), cap in zip(specs, captions, strict=True):
            if cap is not None:
                fig.caption = cap

    def _is_dup_paragraph(
        self, block: Block, table_regions: list[tuple[int, BBox]], lines: list[Line]
    ) -> bool:
        if block.kind != "paragraph":
            return False
        return any(block.page == pi and self._line_inside(block, bbox, lines) for pi, bbox in table_regions)

    @staticmethod
    def _col_count(md: str) -> int:
        for row in md.splitlines():
            if row.strip().startswith("|"):
                return row.count("|") - 1
        return 0

    @staticmethod
    def _line_inside(block: Block, bbox: BBox, lines: list[Line]) -> bool:
        # block has no bbox; match by position against original lines on same page/top
        for ln in lines:
            if ln.page == block.page and abs(ln.bbox[1] - block.top) < 0.5 and ln.text == block.text:
                return _inside(ln.bbox, bbox)
        return False


def build_backend(vlm: Any, config: dict[str, Any]) -> Backend:
    """Select a backend by ``config['backend']`` (default ``'local'``)."""
    name = (config or {}).get("backend", "local")
    if name == "local":
        return LocalBackend(vlm, config)
    if name == "mistral_ocr":
        from ._mistral import MistralOcrBackend

        return MistralOcrBackend(config)
    if name == "paddleocr_vl":
        from ._paddleocr import PaddleOcrBackend

        return PaddleOcrBackend(vlm, config)
    raise ValueError(
        f"unknown pdf_plus_backend: {name!r} (expected 'local', 'mistral_ocr', or 'paddleocr_vl')"
    )
