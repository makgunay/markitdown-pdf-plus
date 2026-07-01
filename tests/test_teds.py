import pytest

pytest.importorskip("apted")

from tests.eval.teds import (  # noqa: E402
    doc_teds,
    extract_tables,
    md_table_to_html,
    teds,
)

_T = "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td><td>2</td></tr></table>"


def test_identical_tables_score_one():
    assert teds(_T, _T) == pytest.approx(1.0)


def test_dropped_cell_scores_below_one():
    missing = "<table><tr><th>a</th><th>b</th></tr><tr><td>1</td></tr></table>"
    assert 0.0 < teds(missing, _T) < 1.0


def test_struct_only_ignores_cell_text():
    other_text = "<table><tr><th>x</th><th>y</th></tr><tr><td>9</td><td>8</td></tr></table>"
    assert teds(other_text, _T, struct_only=True) == pytest.approx(1.0)
    assert teds(other_text, _T, struct_only=False) < 1.0


def test_colspan_mismatch_is_penalized():
    spanning = '<table><tr><th colspan="2">a</th></tr><tr><td>1</td><td>2</td></tr></table>'
    assert teds(_T, spanning) < 1.0


def test_unparseable_table_scores_zero():
    assert teds("not a table", _T) == 0.0


def test_md_table_to_html_header_and_separator():
    html = md_table_to_html("| a | b |\n| --- | --- |\n| 1 | 2 |")
    assert html.count("<th>") == 2
    assert html.count("<td>") == 2
    assert "---" not in html


def test_pipe_table_matches_equivalent_html():
    pipe = md_table_to_html("| a | b |\n| --- | --- |\n| 1 | 2 |")
    assert teds(pipe, _T) == pytest.approx(1.0)


def test_extract_tables_finds_html_and_pipe():
    md = f"intro\n\n{_T}\n\ntext\n\n| a | b |\n| - | - |\n| 1 | 2 |\n\nend"
    assert len(extract_tables(md)) == 2


def test_doc_teds_best_match_mean():
    result = doc_teds(f"junk\n\n{_T}", _T)
    assert result["teds"] == pytest.approx(1.0)
    assert result["teds_struct"] == pytest.approx(1.0)
    assert result["n_reference_tables"] == 1
    assert result["n_predicted_tables"] == 1


def test_doc_teds_no_reference_tables():
    result = doc_teds(_T, "no tables here")
    assert result["teds"] is None
    assert result["teds_struct"] is None
    assert result["n_reference_tables"] == 0
