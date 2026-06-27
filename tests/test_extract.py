# tests/test_extract.py
import io
import os

import pytest

from markitdown_pdf_plus._extract import TextExtractor


def test_extracts_lines_with_font_and_clean_spacing(headings_pdf_bytes):
    lines = TextExtractor().extract(io.BytesIO(headings_pdf_bytes))
    texts = [ln.text for ln in lines]
    assert "1 Introduction" in texts
    body = next(ln for ln in lines if ln.text.startswith("This is body"))
    # spacing preserved: no run-together words of 18+ letters
    assert not any(len(w) >= 18 for w in body.text.split())
    # font sizes distinguish heading from body
    heading = next(ln for ln in lines if ln.text == "1 Introduction")
    assert heading.font_size > body.font_size


def test_real_paper_body_spacing_is_clean():
    pdf = "../markitdown/2025059pap.pdf"
    if not os.path.exists(pdf):
        pytest.skip("real paper fixture not present")
    with open(pdf, "rb") as fh:
        lines = TextExtractor().extract(fh)
    prose = [ln for ln in lines if ln.page == 3]  # a body-text page
    jammed = sum(1 for ln in prose for w in ln.text.split() if len(w) >= 18)
    assert jammed == 0, f"{jammed} run-together words on a real prose page"
