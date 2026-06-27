import io

import pdfplumber

from markitdown_pdf_plus._tables import TableDetector


def test_detects_table_region(table_pdf_bytes):
    with pdfplumber.open(io.BytesIO(table_pdf_bytes)) as pdf:
        bboxes = TableDetector().detect(pdf.pages[0])
    assert len(bboxes) >= 1
    x0, top, x1, bottom = bboxes[0]
    assert x1 > x0 and bottom > top


def test_detects_borderless_table(borderless_table_pdf_bytes):
    with pdfplumber.open(io.BytesIO(borderless_table_pdf_bytes)) as pdf:
        bboxes = TableDetector().detect(pdf.pages[0])
    assert len(bboxes) >= 1


def test_no_false_table_on_prose(prose_pdf_bytes):
    with pdfplumber.open(io.BytesIO(prose_pdf_bytes)) as pdf:
        bboxes = TableDetector().detect(pdf.pages[0])
    assert len(bboxes) == 0


def test_grid_fallback_renders_borderless_table(borderless_table_pdf_bytes):
    """No-VLM fallback must render a borderless table as a grid, not empty."""
    with pdfplumber.open(io.BytesIO(borderless_table_pdf_bytes)) as pdf:
        page = pdf.pages[0]
        bboxes = TableDetector().detect(page)
        assert bboxes, "borderless table not detected"
        md = TableDetector().extract_grid_markdown(page, bboxes[0])
    assert "|" in md and md.count("\n") >= 2  # header + separator + >=1 row


def test_real_paper_borderless_table_detected_prose_rejected():
    """Regression on a real academic PDF: the borderless summary-stats table
    (Table 1) must be detected, while a prose page must not false-positive."""
    import os

    pdf = "../markitdown/2025059pap.pdf"
    if not os.path.exists(pdf):
        import pytest

        pytest.skip("real paper fixture not present")
    with pdfplumber.open(pdf) as p:
        table1 = len(TableDetector().detect(p.pages[44]))  # Table 1 page (borderless)
        prose = len(TableDetector().detect(p.pages[3]))  # body-text page
    assert table1 >= 1, "borderless summary table not detected"
    assert prose == 0, "prose page false-positived as a table"
