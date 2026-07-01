"""TEDS (Tree-Edit-Distance Similarity) for table-quality eval.

Compares a predicted table to a reference table as HTML trees:

    TEDS = 1 - TreeEditDistance(pred, ref) / max(|pred|, |ref|)

We use it for *regression tracking* against a reference-model pseudo-ground-truth
(Mistral OCR output treated as truth), not as an absolute quality score. The
"Beyond String Matching" finding (docs/memory/02) is that TEDS compresses real
parsers into a narrow band while an LLM-judge correlates far better with humans, so
TEDS is the deterministic drift detector and `judge.py` is the quality gate.

Two variants:
  - TEDS         : content-aware (cell text contributes via normalized edit distance)
  - TEDS-Struct  : structure only (tags + colspan/rowspan), ignores cell text

Markdown pipe tables are normalized to HTML so that their inability to express
colspan/rowspan is correctly penalized against spanning-header reference tables.

Dependency: `apted` (eval-only extra). HTML is parsed with the stdlib.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

from apted import APTED, Config

_CELL_TAGS = ("td", "th")
_KEEP_TAGS = ("table", "tr", "td", "th")  # thead/tbody are treated as transparent
_HTML_TABLE_RE = re.compile(r"<table\b.*?</table>", re.DOTALL | re.IGNORECASE)


class TableNode:
    """A node in a table tree: a `<table>`, `<tr>`, or `<td>`/`<th>` cell."""

    __slots__ = ("tag", "colspan", "rowspan", "content", "children")

    def __init__(
        self,
        tag: str,
        colspan: int = 1,
        rowspan: int = 1,
        content: str = "",
        children: list[TableNode] | None = None,
    ):
        self.tag = tag
        self.colspan = colspan
        self.rowspan = rowspan
        self.content = content
        self.children = children if children is not None else []


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def _norm_dist(a: str, b: str) -> float:
    m = max(len(a), len(b))
    return _levenshtein(a, b) / m if m else 0.0


class _TedsConfig(Config):
    """APTED cost model: unit insert/delete, content-aware cell substitution."""

    def __init__(self, struct_only: bool = False):
        self.struct_only = struct_only

    def children(self, node: TableNode) -> list[TableNode]:
        return node.children

    def rename(self, n1: TableNode, n2: TableNode) -> float:
        if n1.tag != n2.tag or n1.colspan != n2.colspan or n1.rowspan != n2.rowspan:
            return 1.0
        if not self.struct_only and n1.tag in _CELL_TAGS and (n1.content or n2.content):
            return _norm_dist(n1.content, n2.content)
        return 0.0


class _TableHTMLParser(HTMLParser):
    """Parse a single `<table>` into a TableNode tree (thead/tbody flattened)."""

    def __init__(self) -> None:
        super().__init__()
        self.root: TableNode | None = None
        self._stack: list[TableNode] = []
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in _KEEP_TAGS:
            return
        a = dict(attrs)
        node = TableNode(tag, _to_int(a.get("colspan")), _to_int(a.get("rowspan")))
        if self.root is None and tag == "table":
            self.root = node
        elif self._stack:
            self._stack[-1].children.append(node)
        self._stack.append(node)
        self._text = []

    def handle_data(self, data: str) -> None:
        self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag not in _KEEP_TAGS or not self._stack:
            return
        node = self._stack.pop()
        if node.tag in _CELL_TAGS:
            node.content = "".join(self._text).strip()
        self._text = []


def _to_int(value: str | None) -> int:
    try:
        return max(int(value), 1) if value else 1
    except (TypeError, ValueError):
        return 1


def parse_table(html: str) -> TableNode | None:
    parser = _TableHTMLParser()
    parser.feed(html)
    return parser.root


def md_table_to_html(md_table: str) -> str:
    """Convert a Markdown pipe table to flat HTML (header row -> th, rest -> td)."""
    cell_rows: list[list[str]] = []
    for raw in md_table.splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if set(line) <= set("|-: "):  # separator row
            continue
        cell_rows.append([c.strip() for c in line.strip("|").split("|")])
    if not cell_rows:
        return ""
    parts = ["<table>"]
    for i, cells in enumerate(cell_rows):
        tag = "th" if i == 0 else "td"
        parts.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
    parts.append("</table>")
    return "".join(parts)


def extract_tables(markdown: str) -> list[str]:
    """Pull every table out of a Markdown blob as HTML (HTML tables + pipe runs)."""
    tables = list(_HTML_TABLE_RE.findall(markdown))
    run: list[str] = []
    for line in markdown.splitlines():
        if line.strip().startswith("|"):
            run.append(line)
            continue
        if run:
            html = md_table_to_html("\n".join(run))
            if html:
                tables.append(html)
            run = []
    if run:
        html = md_table_to_html("\n".join(run))
        if html:
            tables.append(html)
    return tables


def _count(node: TableNode) -> int:
    return 1 + sum(_count(c) for c in node.children)


def teds(pred_html: str, ref_html: str, struct_only: bool = False) -> float:
    """TEDS between two single tables given as HTML strings."""
    t_pred = parse_table(pred_html)
    t_ref = parse_table(ref_html)
    if t_pred is None or t_ref is None:
        return 0.0
    denom = max(_count(t_pred), _count(t_ref))
    if denom == 0:
        return 0.0
    distance = APTED(t_pred, t_ref, _TedsConfig(struct_only)).compute_edit_distance()
    return 1.0 - distance / denom


def doc_teds(pred_md: str, ref_md: str) -> dict:
    """Document-level TEDS: best-match each reference table to a predicted table.

    Reference tables come from the pseudo-ground-truth backend. Each is scored
    against its best-matching predicted table (0.0 if none) for both content-aware
    TEDS and structure-only TEDS-Struct; the means are reported with table counts.
    """
    ref_tables = extract_tables(ref_md)
    pred_tables = extract_tables(pred_md)
    if not ref_tables:
        return {
            "teds": None,
            "teds_struct": None,
            "n_reference_tables": 0,
            "n_predicted_tables": len(pred_tables),
        }

    def _best(rt: str, struct_only: bool) -> float:
        return max((teds(pt, rt, struct_only) for pt in pred_tables), default=0.0)

    content = [_best(rt, False) for rt in ref_tables]
    struct = [_best(rt, True) for rt in ref_tables]
    return {
        "teds": sum(content) / len(content),
        "teds_struct": sum(struct) / len(struct),
        "n_reference_tables": len(ref_tables),
        "n_predicted_tables": len(pred_tables),
    }
