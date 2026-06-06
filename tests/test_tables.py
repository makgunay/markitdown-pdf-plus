import io
import pdfplumber
from markitdown_pdf_plus._tables import TableDetector


def test_detects_table_region(table_pdf_bytes):
    with pdfplumber.open(io.BytesIO(table_pdf_bytes)) as pdf:
        bboxes = TableDetector().detect(pdf.pages[0])
    assert len(bboxes) >= 1
    x0, top, x1, bottom = bboxes[0]
    assert x1 > x0 and bottom > top
