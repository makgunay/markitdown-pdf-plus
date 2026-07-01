from markitdown_pdf_plus._merge import CrossPageTableMerger
from markitdown_pdf_plus._model import Block

T1 = "| a | b |\n| - | - |\n| 1 | 2 |"
T2 = "| a | b |\n| - | - |\n| 3 | 4 |"


def _tbl(page, top, md, cols=2):
    return Block(kind="table", page=page, top=top, markdown=md, cols=cols)


def test_merges_consecutive_page_tables_same_cols():
    blocks = [_tbl(0, 700, T1), _tbl(1, 50, T2)]
    out = CrossPageTableMerger().merge(blocks)
    assert len(out) == 1
    assert out[0].markdown == "| a | b |\n| - | - |\n| 1 | 2 |\n| 3 | 4 |"


def test_does_not_merge_when_col_count_differs():
    blocks = [_tbl(0, 700, T1, cols=2), _tbl(1, 50, "| x |\n| - |\n| 9 |", cols=1)]
    out = CrossPageTableMerger().merge(blocks)
    assert len(out) == 2


def test_does_not_merge_when_heading_between():
    blocks = [_tbl(0, 700, T1), Block(kind="heading", page=1, top=20, level=1, text="X"), _tbl(1, 50, T2)]
    out = CrossPageTableMerger().merge(blocks)
    assert sum(1 for b in out if b.kind == "table") == 2


def test_html_table_is_not_merged_with_adjacent_pipe_table():
    # An HTML-emitting backend sets cols=0 (no pipe row); it must never be merged,
    # so HTML tables from the Mistral/PaddleOCR backends can't corrupt pipe-table merges.
    html = "<table><tr><td>1</td></tr></table>"
    blocks = [_tbl(0, 700, T1, cols=2), _tbl(1, 50, html, cols=0)]
    out = CrossPageTableMerger().merge(blocks)
    assert len(out) == 2
    assert out[1].markdown == html
