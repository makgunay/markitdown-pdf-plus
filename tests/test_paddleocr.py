import io

import pytest
from markitdown import StreamInfo
from tests.test_vlm import MockClient

from markitdown_pdf_plus._backends import build_backend
from markitdown_pdf_plus._converter import PdfPlusConverter
from markitdown_pdf_plus._paddleocr import PaddleOcrBackend
from markitdown_pdf_plus._vlm import VlmService


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


def test_construction_without_vlm_does_not_raise():
    # Constructed at plugin-registration time, so a missing client must NOT crash
    # MarkItDown construction -- only an actual conversion should raise.
    PaddleOcrBackend(None, {})
    PdfPlusConverter(None, {"backend": "paddleocr_vl"})


def test_convert_without_vlm_raises():
    backend = PaddleOcrBackend(None, {})
    with pytest.raises(ValueError, match="llm_client"):
        backend.convert(b"%PDF")


def test_custom_prompt_is_used():
    captured = {}

    class CapturingVlm:
        def transcribe_page(self, b64, prompt=None):
            captured["prompt"] = prompt
            return "x"

    backend = PaddleOcrBackend(CapturingVlm(), {"dpi": 120, "paddleocr_prompt": "MY PROMPT"})
    backend.convert(_multipage_pdf_bytes(1))
    assert captured["prompt"] == "MY PROMPT"


def test_none_prompt_falls_back_to_default():
    # __init__.py sets paddleocr_prompt=None when the kwarg is absent; must not
    # pass None through as the prompt.
    from markitdown_pdf_plus._paddleocr import DOC_PARSE_PROMPT

    backend = PaddleOcrBackend(VlmService(MockClient("x"), "m"), {"paddleocr_prompt": None})
    assert backend.prompt == DOC_PARSE_PROMPT


def test_transcribes_each_page_concurrently():
    n = 3
    vlm = VlmService(MockClient("# Page md"), "m")
    backend = PaddleOcrBackend(vlm, {"dpi": 120, "concurrency": 4})
    md = backend.convert(_multipage_pdf_bytes(n))
    assert md.count("# Page md") == n


def test_end_to_end_via_converter():
    n = 2
    vlm = VlmService(MockClient("# Parsed"), "m")
    conv = PdfPlusConverter(
        vlm,
        {"backend": "paddleocr_vl", "dpi": 120, "image_dir": None, "table_fallback": True, "concurrency": 2},
    )
    md = conv.convert(io.BytesIO(_multipage_pdf_bytes(n)), StreamInfo(extension=".pdf")).markdown
    assert md.count("# Parsed") == n


def test_build_backend_selects_paddleocr():
    vlm = VlmService(MockClient("x"), "m")
    assert isinstance(build_backend(vlm, {"backend": "paddleocr_vl"}), PaddleOcrBackend)
