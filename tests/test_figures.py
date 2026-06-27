# tests/test_figures.py
import io

import pdfplumber

from markitdown_pdf_plus._figures import FigureExtractor, render_bbox_png_b64


def test_extracts_figure_block(image_pdf_bytes, tmp_path):
    data = image_pdf_bytes
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        figs = FigureExtractor(image_dir=str(tmp_path), dpi=150).extract(
            pdf.pages[0], page_index=0, pdf_bytes=data
        )
    assert len(figs) == 1
    f = figs[0]
    assert f.kind == "figure" and f.image_path is not None
    assert (tmp_path / f.image_path.split("/")[-1]).exists()


def test_render_bbox_returns_base64_png(image_pdf_bytes):
    b64 = render_bbox_png_b64(image_pdf_bytes, page_index=0, bbox=(100, 500, 220, 580), dpi=100)
    import base64

    raw = base64.b64decode(b64)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
