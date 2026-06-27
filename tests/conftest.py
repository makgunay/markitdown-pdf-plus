import io

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


@pytest.fixture
def headings_pdf_bytes():
    """One page: a 17pt heading, body text, and a 14pt subheading."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(72, 720, "1 Introduction")
    c.setFont("Helvetica", 12)
    c.drawString(72, 690, "This is body text that should remain a paragraph with spaces.")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 660, "1.1 Background")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def table_pdf_bytes():
    """One page with a bordered 2x3 table."""
    from reportlab.platypus import SimpleDocTemplate, Table

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [["H1", "H2"], ["1", "2"], ["3", "4"]]
    t = Table(data, style=[("GRID", (0, 0), (-1, -1), 1, (0, 0, 0))])
    doc.build([t])
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def borderless_table_pdf_bytes():
    """A table with NO ruling lines (text-aligned columns), like academic tables."""
    from reportlab.platypus import SimpleDocTemplate, Table

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [
        ["Variable", "Mean", "SD"],
        ["Loan", "87.2", "108.0"],
        ["Rate", "4.32", "2.13"],
        ["Maturity", "5.71", "2.53"],
    ]
    doc.build([Table(data)])  # no GRID style -> borderless
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def prose_pdf_bytes():
    """A page of flowing prose (no table) -- must NOT be detected as a table."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 12)
    y = 720
    for line in [
        "This is a paragraph of ordinary prose text that flows naturally across",
        "the page without any tabular structure whatsoever, describing the study",
        "and its motivation in complete sentences as a normal document would.",
    ]:
        c.drawString(72, y, line)
        y -= 18
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.fixture
def image_pdf_bytes(tmp_path):
    """One page containing a small embedded raster image."""
    from PIL import Image

    img_path = tmp_path / "blue.png"
    Image.new("RGB", (120, 80), (0, 0, 255)).save(img_path)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawImage(str(img_path), 100, 500, width=120, height=80)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
