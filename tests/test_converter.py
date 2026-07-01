# tests/test_converter.py
import io
import threading

from markitdown import StreamInfo
from tests.test_vlm import MockClient

from markitdown_pdf_plus._concurrency import map_ordered
from markitdown_pdf_plus._converter import PdfPlusConverter
from markitdown_pdf_plus._vlm import VlmService


def _convert(data, vlm=None, config=None):
    conv = PdfPlusConverter(
        vlm, config or {"full_page": False, "image_dir": None, "dpi": 120, "table_fallback": True}
    )
    return conv.convert(io.BytesIO(data), StreamInfo(extension=".pdf", mimetype="application/pdf")).markdown


def test_accepts_pdf():
    conv = PdfPlusConverter(None, {})
    assert conv.accepts(io.BytesIO(b"%PDF"), StreamInfo(extension=".pdf"))
    assert not conv.accepts(io.BytesIO(b""), StreamInfo(extension=".txt"))


def test_headings_present_without_vlm(headings_pdf_bytes):
    md = _convert(headings_pdf_bytes)
    assert "# 1 Introduction" in md
    assert "## 1.1 Background" in md
    assert "This is body text" in md


def test_table_replaced_by_vlm_and_not_duplicated(table_pdf_bytes):
    vlm = VlmService(MockClient("| H1 | H2 |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |"), "m")
    md = _convert(table_pdf_bytes, vlm=vlm)
    assert md.count("| H1 | H2 |") == 1  # table rendered once
    assert "| 1 | 2 |" in md and "| 3 | 4 |" in md  # VLM content present


def _multipage_pdf_bytes(n_pages):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for pi in range(n_pages):
        c.setFont("Helvetica", 12)
        c.drawString(72, 720, f"Page {pi}")
        c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def test_full_page_mode_uses_vlm_per_page():
    n_pages = 3
    vlm = VlmService(MockClient("# Page md"), "m")
    md = _convert(
        _multipage_pdf_bytes(n_pages),
        vlm=vlm,
        config={"full_page": True, "image_dir": None, "dpi": 120, "table_fallback": True},
    )
    assert md.count("# Page md") == n_pages  # one VLM transcription per page


def test_map_ordered_preserves_order_concurrently():
    items = list(range(20))
    assert map_ordered(lambda x: x * x, items, concurrency=8) == [x * x for x in items]


def test_map_ordered_sequential_and_empty():
    assert map_ordered(lambda x: x + 1, [1, 2, 3], concurrency=1) == [2, 3, 4]
    assert map_ordered(lambda x: x, [], concurrency=4) == []


def test_map_ordered_actually_runs_in_parallel():
    # A Barrier of size n only releases when all n calls are in flight at once;
    # if work were serialized, barrier.wait() would time out (BrokenBarrierError).
    n = 4
    barrier = threading.Barrier(n, timeout=5)
    assert map_ordered(lambda i: (barrier.wait(), i)[1], list(range(n)), concurrency=n) == [0, 1, 2, 3]


def test_concurrent_vlm_failure_falls_back_to_grid(table_pdf_bytes):
    class Boom:
        @property
        def chat(self):
            raise RuntimeError("network")

    vlm = VlmService(Boom(), "m")
    md = _convert(
        table_pdf_bytes,
        vlm=vlm,
        config={"full_page": False, "image_dir": None, "dpi": 120, "table_fallback": True, "concurrency": 4},
    )
    # VLM raised -> graceful fallback to the pdfplumber grid for the bordered table
    assert "H1" in md and "H2" in md
