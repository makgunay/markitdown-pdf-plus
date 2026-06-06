# tests/test_assemble.py
from markitdown_pdf_plus._model import Block
from markitdown_pdf_plus._assemble import MarkdownAssembler


def test_orders_by_position_and_renders_each_kind():
    blocks = [
        Block(kind="paragraph", page=0, top=200, text="second para"),
        Block(kind="heading", page=0, top=10, level=1, text="Title"),
        Block(kind="table", page=0, top=120, markdown="| a | b |\n| - | - |\n| 1 | 2 |"),
        Block(kind="figure", page=0, top=160, image_path="fig1.png", caption="A chart"),
    ]
    md = MarkdownAssembler().assemble(blocks)
    lines = md.split("\n\n")
    assert lines[0] == "# Title"
    assert lines[1].startswith("| a | b |")
    assert lines[2] == "![A chart](fig1.png)"
    assert lines[3] == "second para"


def test_figure_caption_only_when_no_image():
    blocks = [Block(kind="figure", page=0, top=0, caption="desc only")]
    md = MarkdownAssembler().assemble(blocks)
    assert md == "![desc only]()"


def test_skips_empty_blocks():
    blocks = [Block(kind="paragraph", page=0, top=0, text="  ")]
    assert MarkdownAssembler().assemble(blocks) == ""
