import io
from typing import Any, BinaryIO, List, Optional
import pdfplumber
from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

from ._model import Block, Line
from ._extract import TextExtractor
from ._headings import HeadingAnnotator
from ._tables import TableDetector
from ._figures import FigureExtractor, render_bbox_png_b64
from ._merge import CrossPageTableMerger
from ._assemble import MarkdownAssembler


def _inside(line_bbox, region_bbox) -> bool:
    lx0, ltop, lx1, lbottom = line_bbox
    rx0, rtop, rx1, rbottom = region_bbox
    cx, cy = (lx0 + lx1) / 2, (ltop + lbottom) / 2
    return rx0 <= cx <= rx1 and rtop <= cy <= rbottom


class PdfPlusConverter(DocumentConverter):
    def __init__(self, vlm, config: dict):
        self.vlm = vlm
        self.config = config or {}

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext == ".pdf" or mime.startswith("application/pdf") or mime.startswith("application/x-pdf")

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> DocumentConverterResult:
        data = file_stream.read()
        dpi = self.config.get("dpi", 200)
        image_dir = self.config.get("image_dir")
        fallback = self.config.get("table_fallback", True)

        # full-page mode: render each page as a PNG and let the VLM transcribe it whole
        if self.config.get("full_page") and self.vlm is not None:
            import base64
            from ._figures import _render_page_pil
            pages_md = []
            with pdfplumber.open(io.BytesIO(data)) as pdf:
                n = len(pdf.pages)
            for pi in range(n):
                pil, _, _ = _render_page_pil(data, pi, dpi)
                buf = io.BytesIO(); pil.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                page_md = self.vlm._call(b64, self.vlm.table_prompt) or ""
                pages_md.append(page_md)
            return DocumentConverterResult(markdown="\n\n".join(pages_md).strip())

        lines = TextExtractor().extract(io.BytesIO(data))
        blocks: List[Block] = HeadingAnnotator().annotate(lines)

        td = TableDetector()
        fx = FigureExtractor(image_dir=image_dir, dpi=dpi)
        line_by_id = {id(b): b for b in blocks}

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pi, page in enumerate(pdf.pages):
                # tables
                for bbox in td.detect(page):
                    md = None
                    if self.vlm is not None:
                        crop = render_bbox_png_b64(data, pi, bbox, dpi)
                        md = self.vlm.transcribe_table(crop)
                    if md is None and fallback:
                        md = td.extract_grid_markdown(page, bbox)
                    if not md:
                        continue
                    cols = self._col_count(md)
                    blocks.append(Block(kind="table", page=pi, top=bbox[1], x0=bbox[0],
                                        markdown=md, bbox=bbox, cols=cols))
                    # drop paragraph lines inside this table region
                    blocks = [b for b in blocks
                              if not (b.kind == "paragraph" and b.page == pi
                                      and self._line_inside(b, bbox, lines))]
                # figures
                figs = fx.extract(page, pi, data)
                for fig in figs:
                    if self.vlm is not None:
                        crop = render_bbox_png_b64(data, pi, fig.bbox, dpi)
                        fig.caption = self.vlm.caption_figure(crop)
                blocks.extend(figs)

        blocks = CrossPageTableMerger().merge(blocks)
        markdown = MarkdownAssembler().assemble(blocks)
        return DocumentConverterResult(markdown=markdown)

    @staticmethod
    def _col_count(md: str) -> int:
        for row in md.splitlines():
            if row.strip().startswith("|"):
                return row.count("|") - 1
        return 0

    @staticmethod
    def _line_inside(block: Block, bbox, lines: List[Line]) -> bool:
        # block has no bbox; match by position against original lines on same page/top
        for ln in lines:
            if ln.page == block.page and abs(ln.bbox[1] - block.top) < 0.5 and ln.text == block.text:
                return _inside(ln.bbox, bbox)
        return False
