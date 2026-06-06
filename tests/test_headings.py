# tests/test_headings.py
from markitdown_pdf_plus._model import Line
from markitdown_pdf_plus._headings import HeadingAnnotator


def _ln(text, size, page=0, top=0.0, bold=False):
    return Line(page=page, text=text, font_size=size, bold=bold, bbox=(0, top, 100, top + size))


def test_body_is_paragraph_headings_by_font_tier():
    lines = [
        _ln("1 Introduction", 17.2, top=10),
        _ln("This is the body paragraph text that flows.", 12.0, top=40),
        _ln("2.1 Data Sources", 14.3, top=70),
        _ln("More body text at the dominant font size here.", 12.0, top=100),
    ]
    blocks = HeadingAnnotator().annotate(lines)
    kinds = [(b.kind, b.level, b.text) for b in blocks]
    assert kinds[0] == ("heading", 1, "1 Introduction")
    assert kinds[1][0] == "paragraph"
    assert kinds[2] == ("heading", 2, "2.1 Data Sources")
    assert kinds[3][0] == "paragraph"


def test_all_same_font_no_false_headings():
    lines = [_ln(f"line {i}", 12.0, top=i * 15) for i in range(5)]
    blocks = HeadingAnnotator().annotate(lines)
    assert all(b.kind == "paragraph" for b in blocks)


def test_bold_short_line_promoted_when_no_size_signal():
    lines = [
        _ln("Body text at the body size, a full sentence here.", 12.0, top=0),
        _ln("Methods", 12.0, top=30, bold=True),
        _ln("Another full body sentence at the body font size.", 12.0, top=60),
    ]
    blocks = HeadingAnnotator().annotate(lines)
    assert blocks[1].kind == "heading"


def test_numbered_table_row_not_promoted():
    lines = [
        _ln("Body sentence at the dominant font size for context here.", 12.0, top=0),
        _ln("1 (First Lien Senior Secured)", 12.0, top=30),  # table row label, body size
        _ln("Another body sentence at the dominant font size here.", 12.0, top=60),
    ]
    blocks = HeadingAnnotator().annotate(lines)
    assert blocks[1].kind == "paragraph"
