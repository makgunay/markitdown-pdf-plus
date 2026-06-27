# tests/test_integration.py
import io
import os

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_VLM_INTEGRATION"), reason="set RUN_VLM_INTEGRATION=1 + run Ollama"
)


def test_qwen_transcribes_table(table_pdf_bytes):
    import pdfplumber
    from openai import OpenAI

    from markitdown_pdf_plus._figures import render_bbox_png_b64
    from markitdown_pdf_plus._tables import TableDetector
    from markitdown_pdf_plus._vlm import VlmService

    with pdfplumber.open(io.BytesIO(table_pdf_bytes)) as pdf:
        bbox = TableDetector().detect(pdf.pages[0])[0]
    b64 = render_bbox_png_b64(table_pdf_bytes, 0, bbox, dpi=200)
    svc = VlmService(OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"), "qwen2.5vl:7b")
    md = svc.transcribe_table(b64)
    assert md is not None and "|" in md
