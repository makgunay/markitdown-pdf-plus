import io
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


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
