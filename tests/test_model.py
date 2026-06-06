# tests/test_model.py
from markitdown_pdf_plus._model import Line, Block


def test_line_fields():
    ln = Line(page=0, text="Hello", font_size=12.0, bold=False, bbox=(0, 0, 50, 12))
    assert ln.page == 0 and ln.text == "Hello" and ln.font_size == 12.0


def test_block_defaults():
    b = Block(kind="paragraph", page=1, top=100.0, text="body")
    assert b.kind == "paragraph" and b.level == 0 and b.markdown == ""
    assert b.image_path is None and b.cols == 0
