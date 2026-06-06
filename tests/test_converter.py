# tests/test_converter.py
import io
from markitdown import StreamInfo
from markitdown_pdf_plus._converter import PdfPlusConverter
from markitdown_pdf_plus._vlm import VlmService
from tests.test_vlm import MockClient


def _convert(data, vlm=None, config=None):
    conv = PdfPlusConverter(vlm, config or {"full_page": False, "image_dir": None,
                                            "dpi": 120, "table_fallback": True})
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
    assert md.count("| H1 | H2 |") == 1            # table rendered once
    assert "| 1 | 2 |" in md and "| 3 | 4 |" in md  # VLM content present
