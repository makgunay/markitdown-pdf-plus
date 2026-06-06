# markitdown-pdf-plus Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a publishable MarkItDown plugin that overrides the built-in PDF converter with always-on font-heuristic headings + figure extraction and opt-in model-agnostic VLM table transcription, cross-page table merging, and figure captioning.

**Architecture:** A pipeline of small, single-purpose stages (`_model`, `_extract`, `_headings`, `_tables`, `_figures`, `_vlm`, `_merge`, `_assemble`) orchestrated by a thin `PdfPlusConverter`, registered as a `markitdown.plugin` entry point at priority −1.0. Pure stages are unit-tested with hand-built fixtures; PDF stages with reportlab-generated fixtures; the VLM path with a deterministic mock client.

**Tech Stack:** Python ≥3.10, pdfplumber + pdfminer.six (text/geometry), pypdfium2 (crop rendering), Pillow, markitdown (peer); pytest + reportlab (test-only). VLM via any OpenAI-compatible `llm_client` (no bundled ML).

**Working dir:** `/Users/akgunay/Documents/CodingProjects/AkgunayLab/tools/markitdown-pdf-plus` (its own git repo). Develop/test against the sibling `tools/markitdown/.venv` (has markitdown 0.1.6, pdfplumber, pypdfium2) and the live Ollama/Nanonets endpoints. The eval references `../markitdown/2025059pap.pdf` and `../markitdown/marker_out`, `../markitdown/nanonets_tables`.

> **Setup note (all tasks):** the test interpreter is `../markitdown/.venv/bin/python`. Install the package editable into it once in Task 0 (`../markitdown/.venv/bin/pip install -e .`). Run pytest as `../markitdown/.venv/bin/python -m pytest`.

---

## File Structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | package metadata, deps, `markitdown.plugin` entry point |
| `src/markitdown_pdf_plus/__init__.py` | `__plugin_interface_version__`, `register_converters()` |
| `src/markitdown_pdf_plus/_model.py` | `Line`, `Block` dataclasses |
| `src/markitdown_pdf_plus/_headings.py` | `HeadingAnnotator` (font heuristic) |
| `src/markitdown_pdf_plus/_assemble.py` | `MarkdownAssembler` |
| `src/markitdown_pdf_plus/_merge.py` | `CrossPageTableMerger` |
| `src/markitdown_pdf_plus/_extract.py` | `TextExtractor` (pdfplumber words → Lines) |
| `src/markitdown_pdf_plus/_tables.py` | `TableDetector` (pdfplumber find_tables) |
| `src/markitdown_pdf_plus/_figures.py` | `FigureExtractor` + `render_bbox_png_b64()` |
| `src/markitdown_pdf_plus/_vlm.py` | `VlmService` (no-op safe) |
| `src/markitdown_pdf_plus/_converter.py` | `PdfPlusConverter` (orchestrator) |
| `tests/conftest.py` | reportlab fixture builders |
| `tests/test_*.py` | one module per stage + converter |
| `tests/eval/run_eval.py` | score vs markitdown-0.1.6 baseline + references |
| `.github/workflows/ci.yml` | CI (unit + mock + fixture) |

---

## Task 0: Scaffold package

**Files:**
- Create: `pyproject.toml`, `src/markitdown_pdf_plus/__init__.py`, `LICENSE`, `README.md`, `.gitignore`

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
*.egg-info/
.pytest_cache/
build/
dist/
.venv/
tests/_tmp/
```

- [ ] **Step 2: Create `LICENSE`** (MIT, year 2026, holder "Akgunay Labs"). Use the standard MIT text.

- [ ] **Step 3: Create `pyproject.toml`**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "markitdown-pdf-plus"
version = "0.1.0"
description = "MarkItDown plugin: font-heuristic structure + opt-in VLM tables/figures for PDFs"
readme = "README.md"
license = "MIT"
requires-python = ">=3.10"
dependencies = [
  "markitdown>=0.1.5",
  "pdfplumber>=0.11",
  "pypdfium2>=4",
  "Pillow>=10",
]

[project.optional-dependencies]
test = ["pytest>=8", "reportlab>=4"]

[project.entry-points."markitdown.plugin"]
pdf_plus = "markitdown_pdf_plus"

[tool.hatch.build.targets.wheel]
packages = ["src/markitdown_pdf_plus"]
```

- [ ] **Step 4: Create `src/markitdown_pdf_plus/__init__.py` (registration stub)**

```python
"""markitdown-pdf-plus: enhanced PDF converter plugin for MarkItDown."""

__plugin_interface_version__ = 1


def register_converters(markitdown, **kwargs):
    """Entry point called by MarkItDown when plugins are enabled."""
    from ._converter import PdfPlusConverter
    from ._vlm import build_vlm_service

    vlm = build_vlm_service(**kwargs)
    config = {
        "full_page": kwargs.get("pdf_plus_full_page", False),
        "image_dir": kwargs.get("pdf_plus_image_dir"),
        "dpi": kwargs.get("pdf_plus_dpi", 200),
        "table_fallback": kwargs.get("pdf_plus_table_fallback", True),
    }
    markitdown.register_converter(PdfPlusConverter(vlm, config), priority=-1.0)
```

- [ ] **Step 5: Create minimal `README.md`** with name, one-paragraph description, install (`pip install markitdown-pdf-plus`), and a usage snippet (`MarkItDown(enable_plugins=True, llm_client=..., llm_model=...)`).

- [ ] **Step 6: Install editable + verify discovery**

Run:
```bash
../markitdown/.venv/bin/pip install -e ".[test]"
../markitdown/.venv/bin/markitdown --list-plugins
```
Expected: install succeeds; `--list-plugins` lists `pdf_plus`. (It will error on actual conversion until later tasks add `_converter`/`_vlm` — that's fine here.)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "chore: scaffold markitdown-pdf-plus package + entry point"
```

---

## Task 1: Data model (`_model.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_model.py`
- Test: `tests/test_model.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_model.py
from markitdown_pdf_plus._model import Line, Block


def test_line_fields():
    ln = Line(page=0, text="Hello", font_size=12.0, bold=False, bbox=(0, 0, 50, 12))
    assert ln.page == 0 and ln.text == "Hello" and ln.font_size == 12.0


def test_block_defaults():
    b = Block(kind="paragraph", page=1, top=100.0, text="body")
    assert b.kind == "paragraph" and b.level == 0 and b.markdown == ""
    assert b.image_path is None and b.cols == 0
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_model.py -v`
Expected: FAIL (ModuleNotFoundError: `_model`).

- [ ] **Step 3: Implement `_model.py`**

```python
from dataclasses import dataclass
from typing import Optional, Tuple

BBox = Tuple[float, float, float, float]  # (x0, top, x1, bottom), PDF points


@dataclass
class Line:
    page: int
    text: str
    font_size: float
    bold: bool
    bbox: BBox


@dataclass
class Block:
    kind: str  # "heading" | "paragraph" | "table" | "figure"
    page: int
    top: float
    x0: float = 0.0
    text: str = ""
    level: int = 0
    markdown: str = ""
    image_path: Optional[str] = None
    caption: Optional[str] = None
    bbox: Optional[BBox] = None
    cols: int = 0
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_model.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/markitdown_pdf_plus/_model.py tests/test_model.py
git commit -m "feat: Line and Block data model"
```

---

## Task 2: HeadingAnnotator (`_headings.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_headings.py`
- Test: `tests/test_headings.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_headings.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `_headings.py`**

```python
import re
from collections import Counter
from typing import List

from ._model import Line, Block

_NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s+\S")


def body_font_size(lines: List[Line]) -> float:
    sizes = Counter(round(ln.font_size, 1) for ln in lines if ln.text.strip())
    return sizes.most_common(1)[0][0] if sizes else 12.0


def heading_level(line: Line, body: float) -> int:
    """Return heading level 1-3, or 0 if not a heading."""
    size = round(line.font_size, 1)
    short = len(line.text) < 80 and not line.text.rstrip().endswith(".")
    if size >= body + 3:
        return 1 if short else 0
    if size >= body + 1.5:
        return 2 if short else 0
    if size >= body + 0.6:
        return 3 if short else 0
    # same size: promote only short bold lines, or numbered short lines
    if short and (line.bold or _NUMBERED.match(line.text.strip())):
        return 2
    return 0


class HeadingAnnotator:
    def annotate(self, lines: List[Line]) -> List[Block]:
        body = body_font_size(lines)
        blocks: List[Block] = []
        for ln in lines:
            if not ln.text.strip():
                continue
            lvl = heading_level(ln, body)
            if lvl:
                blocks.append(Block(kind="heading", page=ln.page, top=ln.bbox[1],
                                    x0=ln.bbox[0], text=ln.text.strip(), level=lvl))
            else:
                blocks.append(Block(kind="paragraph", page=ln.page, top=ln.bbox[1],
                                    x0=ln.bbox[0], text=ln.text.strip()))
        return blocks
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_headings.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/markitdown_pdf_plus/_headings.py tests/test_headings.py
git commit -m "feat: font-heuristic heading annotator"
```

---

## Task 3: MarkdownAssembler (`_assemble.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_assemble.py`
- Test: `tests/test_assemble.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_assemble.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Implement `_assemble.py`**

```python
from typing import List
from ._model import Block


class MarkdownAssembler:
    def assemble(self, blocks: List[Block]) -> str:
        ordered = sorted(blocks, key=lambda b: (b.page, b.top, b.x0))
        parts: List[str] = []
        for b in ordered:
            parts.append(self._render(b))
        return "\n\n".join(p for p in parts if p.strip())

    def _render(self, b: Block) -> str:
        if b.kind == "heading":
            return "#" * max(1, b.level) + " " + b.text
        if b.kind == "table":
            return b.markdown.strip()
        if b.kind == "figure":
            return f"![{b.caption or ''}]({b.image_path or ''})"
        return b.text  # paragraph
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_assemble.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/markitdown_pdf_plus/_assemble.py tests/test_assemble.py
git commit -m "feat: markdown assembler with reading-order sort"
```

---

## Task 4: CrossPageTableMerger (`_merge.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_merge.py`
- Test: `tests/test_merge.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_merge.py
from markitdown_pdf_plus._model import Block
from markitdown_pdf_plus._merge import CrossPageTableMerger

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
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_merge.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `_merge.py`**

```python
from typing import List
from ._model import Block


def _data_rows(md: str) -> List[str]:
    """Return only the body rows (skip header + separator)."""
    rows = [r for r in md.splitlines() if r.strip().startswith("|")]
    return rows[2:] if len(rows) >= 2 else rows


class CrossPageTableMerger:
    def merge(self, blocks: List[Block]) -> List[Block]:
        ordered = sorted(blocks, key=lambda b: (b.page, b.top, b.x0))
        out: List[Block] = []
        for b in ordered:
            prev = out[-1] if out else None
            if (
                b.kind == "table"
                and prev is not None
                and prev.kind == "table"
                and b.page == prev.page + 1
                and b.cols == prev.cols
                and b.cols > 0
            ):
                extra = _data_rows(b.markdown)
                prev.markdown = prev.markdown.rstrip() + ("\n" + "\n".join(extra) if extra else "")
            else:
                out.append(b)
        return out
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_merge.py -v`
Expected: PASS (3 passed).

> Note: the "heading between" case passes because the heading block lands between the two tables in reading order, so `prev` is the heading (not a table) when the second table is processed.

- [ ] **Step 5: Commit**

```bash
git add src/markitdown_pdf_plus/_merge.py tests/test_merge.py
git commit -m "feat: cross-page table merger"
```

---

## Task 5: Test fixtures + TextExtractor (`_extract.py`)

**Files:**
- Create: `tests/conftest.py`, `src/markitdown_pdf_plus/_extract.py`
- Test: `tests/test_extract.py`

- [ ] **Step 1: Create `tests/conftest.py` (reportlab fixture builder)**

```python
import io
import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter


@pytest.fixture
def headings_pdf_bytes():
    """One page: a 17pt heading, body text, and a 14pt subheading."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica-Bold", 17)
    c.drawString(72, 720, "1 Introduction")
    c.setFont("Helvetica", 12)
    c.drawString(72, 690, "This is body text that should remain a paragraph with spaces.")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 660, "1.1 Background")
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_extract.py
import io
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
```

- [ ] **Step 3: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_extract.py -v`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 4: Implement `_extract.py`**

```python
from typing import List
import pdfplumber
from ._model import Line


class TextExtractor:
    """Extract per-line text + font size + bbox via pdfplumber words (clean spacing)."""

    def __init__(self, y_tolerance: float = 3.0):
        self.y_tolerance = y_tolerance

    def extract(self, file_stream) -> List[Line]:
        out: List[Line] = []
        with pdfplumber.open(file_stream) as pdf:
            for page_index, page in enumerate(pdf.pages):
                words = page.extract_words(
                    extra_attrs=["size", "fontname"], use_text_flow=True
                )
                out.extend(self._group_lines(words, page_index))
        return out

    def _group_lines(self, words, page_index) -> List[Line]:
        rows = {}
        for w in words:
            key = round(w["top"] / self.y_tolerance) * self.y_tolerance
            rows.setdefault(key, []).append(w)
        lines = []
        for key in sorted(rows):
            ws = sorted(rows[key], key=lambda w: w["x0"])
            text = " ".join(w["text"] for w in ws).strip()
            if not text:
                continue
            sizes = [float(w.get("size", 0.0)) for w in ws]
            size = max(sizes) if sizes else 0.0
            bold = any("Bold" in (w.get("fontname") or "") for w in ws)
            bbox = (ws[0]["x0"], min(w["top"] for w in ws),
                    ws[-1]["x1"], max(w["bottom"] for w in ws))
            lines.append(Line(page=page_index, text=text, font_size=size, bold=bold, bbox=bbox))
        return lines
```

- [ ] **Step 5: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_extract.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/conftest.py src/markitdown_pdf_plus/_extract.py tests/test_extract.py
git commit -m "feat: text extractor with font metadata + spacing guard"
```

---

## Task 6: TableDetector (`_tables.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_tables.py`
- Modify: `tests/conftest.py` (add `table_pdf_bytes`)
- Test: `tests/test_tables.py`

- [ ] **Step 1: Add fixture to `tests/conftest.py`**

```python
@pytest.fixture
def table_pdf_bytes():
    """One page with a bordered 2x3 table."""
    from reportlab.platypus import SimpleDocTemplate, Table
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    data = [["H1", "H2"], ["1", "2"], ["3", "4"]]
    t = Table(data, style=[("GRID", (0, 0), (-1, -1), 1, (0, 0, 0))])
    doc.build([t])
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_tables.py
import io
import pdfplumber
from markitdown_pdf_plus._tables import TableDetector


def test_detects_table_region(table_pdf_bytes):
    with pdfplumber.open(io.BytesIO(table_pdf_bytes)) as pdf:
        bboxes = TableDetector().detect(pdf.pages[0])
    assert len(bboxes) >= 1
    x0, top, x1, bottom = bboxes[0]
    assert x1 > x0 and bottom > top
```

- [ ] **Step 3: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_tables.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement `_tables.py`**

```python
from typing import List
from ._model import BBox


class TableDetector:
    def detect(self, page) -> List[BBox]:
        return [tuple(t.bbox) for t in page.find_tables()]

    def extract_grid_markdown(self, page, bbox: BBox) -> str:
        """Fallback markdown when no VLM: pdfplumber's own extraction for the region."""
        cropped = page.crop(bbox)
        tables = cropped.extract_tables()
        if not tables or not tables[0]:
            return ""
        rows = [[c if c is not None else "" for c in row] for row in tables[0]]
        rows = [r for r in rows if any(str(c).strip() for c in r)]
        if not rows:
            return ""
        header = "| " + " | ".join(str(c) for c in rows[0]) + " |"
        sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = ["| " + " | ".join(str(c) for c in r) + " |" for r in rows[1:]]
        return "\n".join([header, sep, *body])
```

- [ ] **Step 5: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_tables.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/markitdown_pdf_plus/_tables.py tests/conftest.py tests/test_tables.py
git commit -m "feat: table region detector + pdfplumber grid fallback"
```

---

## Task 7: FigureExtractor + crop renderer (`_figures.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_figures.py`
- Modify: `tests/conftest.py` (add `image_pdf_bytes`)
- Test: `tests/test_figures.py`

- [ ] **Step 1: Add fixture to `tests/conftest.py`**

```python
@pytest.fixture
def image_pdf_bytes(tmp_path):
    """One page containing a small embedded raster image."""
    from PIL import Image
    img_path = tmp_path / "blue.png"
    Image.new("RGB", (120, 80), (0, 0, 255)).save(img_path)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawImage(str(img_path), 100, 500, width=120, height=80)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_figures.py
import io
import pdfplumber
from markitdown_pdf_plus._figures import FigureExtractor, render_bbox_png_b64


def test_extracts_figure_block(image_pdf_bytes, tmp_path):
    data = image_pdf_bytes
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        figs = FigureExtractor(image_dir=str(tmp_path), dpi=150).extract(
            pdf.pages[0], page_index=0, pdf_bytes=data
        )
    assert len(figs) == 1
    f = figs[0]
    assert f.kind == "figure" and f.image_path is not None
    assert (tmp_path / f.image_path.split("/")[-1]).exists()


def test_render_bbox_returns_base64_png(image_pdf_bytes):
    b64 = render_bbox_png_b64(image_pdf_bytes, page_index=0, bbox=(100, 500, 220, 580), dpi=100)
    import base64
    raw = base64.b64decode(b64)
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
```

- [ ] **Step 3: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_figures.py -v`
Expected: FAIL.

- [ ] **Step 4: Implement `_figures.py`**

```python
import base64
import io
import os
from typing import List, Optional
import pypdfium2 as pdfium
from ._model import Block, BBox


def _render_page_pil(pdf_bytes: bytes, page_index: int, dpi: int):
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[page_index]
    scale = dpi / 72.0
    pil = page.render(scale=scale).to_pil()
    return pil, scale, float(page.get_size()[1])  # (image, scale, page_height_pts)


def render_bbox_png_b64(pdf_bytes: bytes, page_index: int, bbox: BBox, dpi: int = 200) -> str:
    pil, scale, page_h = _render_page_pil(pdf_bytes, page_index, dpi)
    x0, top, x1, bottom = bbox
    crop = pil.crop((int(x0 * scale), int(top * scale), int(x1 * scale), int(bottom * scale)))
    out = io.BytesIO()
    crop.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode()


class FigureExtractor:
    def __init__(self, image_dir: Optional[str], dpi: int = 200):
        self.image_dir = image_dir
        self.dpi = dpi

    def extract(self, page, page_index: int, pdf_bytes: bytes) -> List[Block]:
        blocks: List[Block] = []
        pil, scale, page_h = _render_page_pil(pdf_bytes, page_index, self.dpi)
        for i, img in enumerate(page.images):
            bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
            image_path = None
            if self.image_dir:
                os.makedirs(self.image_dir, exist_ok=True)
                name = f"page{page_index}_fig{i}.png"
                crop = pil.crop((int(bbox[0] * scale), int(bbox[1] * scale),
                                 int(bbox[2] * scale), int(bbox[3] * scale)))
                crop.save(os.path.join(self.image_dir, name))
                image_path = os.path.join(self.image_dir, name)
            blocks.append(Block(kind="figure", page=page_index, top=bbox[1],
                                x0=bbox[0], bbox=bbox, image_path=image_path))
        return blocks
```

- [ ] **Step 5: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_figures.py -v`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add src/markitdown_pdf_plus/_figures.py tests/conftest.py tests/test_figures.py
git commit -m "feat: figure extractor + pypdfium2 bbox crop renderer"
```

---

## Task 8: VlmService (`_vlm.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_vlm.py`
- Test: `tests/test_vlm.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_vlm.py
from markitdown_pdf_plus._vlm import VlmService, build_vlm_service


class _Msg:
    def __init__(self, content): self.message = type("M", (), {"content": content})


class _Resp:
    def __init__(self, content): self.choices = [_Msg(content)]


class MockClient:
    def __init__(self, content): self._content = content
    @property
    def chat(self):
        outer = self
        class C:
            class completions:
                @staticmethod
                def create(**kwargs): return _Resp(outer._content)
        return C


def test_no_client_is_noop():
    assert build_vlm_service() is None


def test_transcribe_strips_code_fences():
    svc = VlmService(MockClient("```markdown\n| a | b |\n| - | - |\n| 1 | 2 |\n```"), "m")
    md = svc.transcribe_table("BASE64")
    assert md == "| a | b |\n| - | - |\n| 1 | 2 |"


def test_transcribe_rejects_non_table():
    svc = VlmService(MockClient("I cannot read this image."), "m")
    assert svc.transcribe_table("BASE64") is None


def test_failure_returns_none():
    class Boom:
        @property
        def chat(self): raise RuntimeError("network")
    svc = VlmService(Boom(), "m")
    assert svc.transcribe_table("BASE64") is None
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_vlm.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `_vlm.py`**

```python
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_TABLE_PROMPT = (
    "Convert this table image to a GitHub-flavored Markdown pipe table. Preserve every "
    "row label, column header, numeric value, parenthesized standard error, and significance "
    "marker exactly. Output only the table."
)
DEFAULT_CAPTION_PROMPT = (
    "Describe this figure for someone who can't see it: chart type, axes, series, and the "
    "main trend in 1-3 sentences. If it shows discrete values, add a small Markdown table."
)

_FENCE = re.compile(r"^```[a-zA-Z]*\n|\n```$")


def _strip_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    return t.strip()


class VlmService:
    def __init__(self, client, model, table_prompt=DEFAULT_TABLE_PROMPT,
                 caption_prompt=DEFAULT_CAPTION_PROMPT, max_tokens=4096):
        self.client = client
        self.model = model
        self.table_prompt = table_prompt
        self.caption_prompt = caption_prompt
        self.max_tokens = max_tokens

    def _call(self, b64_png: str, prompt: str) -> Optional[str]:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}"}},
                    {"type": "text", "text": prompt},
                ]}],
                max_tokens=self.max_tokens, temperature=0,
            )
            return resp.choices[0].message.content
        except Exception as e:  # noqa: BLE001
            logger.warning("VLM call failed: %s", e)
            return None

    def transcribe_table(self, b64_png: str) -> Optional[str]:
        raw = self._call(b64_png, self.table_prompt)
        if raw is None:
            return None
        md = _strip_fences(raw)
        return md if "|" in md else None

    def caption_figure(self, b64_png: str) -> Optional[str]:
        raw = self._call(b64_png, self.caption_prompt)
        return _strip_fences(raw) if raw else None


def build_vlm_service(**kwargs) -> Optional[VlmService]:
    client = kwargs.get("llm_client")
    model = kwargs.get("llm_model")
    if client is None or model is None:
        return None
    return VlmService(
        client, model,
        table_prompt=kwargs.get("pdf_plus_table_prompt", DEFAULT_TABLE_PROMPT),
        caption_prompt=kwargs.get("pdf_plus_caption_prompt", DEFAULT_CAPTION_PROMPT),
        max_tokens=kwargs.get("pdf_plus_max_tokens", 4096),
    )
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_vlm.py -v`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/markitdown_pdf_plus/_vlm.py tests/test_vlm.py
git commit -m "feat: VlmService with fence-strip, validation, graceful failure"
```

---

## Task 9: PdfPlusConverter (`_converter.py`)

**Files:**
- Create: `src/markitdown_pdf_plus/_converter.py`
- Test: `tests/test_converter.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run to verify fail**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_converter.py -v`
Expected: FAIL.

- [ ] **Step 3: Implement `_converter.py`**

```python
import io
from typing import Any, BinaryIO, List, Optional
import pdfplumber
from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

from ._model import Block, Line
from ._extract import TextExtractor
from ._headings import HeadingAnnotator
from ._tables import TableDetector
from ._figures import FigureExtractor, render_bbox_png_b64
from ._merge import CrossPageTableMerger
from ._assemble import MarkdownAssembler


def _inside(line_bbox, region_bbox) -> bool:
    lx0, ltop, lx1, lbottom = line_bbox
    rx0, rtop, rx1, rbottom = region_bbox
    cx, cy = (lx0 + lx1) / 2, (ltop + lbottom) / 2
    return rx0 <= cx <= rx1 and rtop <= cy <= rbottom


class PdfPlusConverter(DocumentConverter):
    def __init__(self, vlm, config: dict):
        self.vlm = vlm
        self.config = config or {}

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext == ".pdf" or mime.startswith("application/pdf") or mime.startswith("application/x-pdf")

    def convert(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> DocumentConverterResult:
        data = file_stream.read()
        dpi = self.config.get("dpi", 200)
        image_dir = self.config.get("image_dir")
        fallback = self.config.get("table_fallback", True)

        lines = TextExtractor().extract(io.BytesIO(data))
        blocks: List[Block] = HeadingAnnotator().annotate(lines)

        td = TableDetector()
        fx = FigureExtractor(image_dir=image_dir, dpi=dpi)
        line_by_id = {id(b): b for b in blocks}

        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pi, page in enumerate(pdf.pages):
                # tables
                for bbox in td.detect(page):
                    md = None
                    if self.vlm is not None:
                        crop = render_bbox_png_b64(data, pi, bbox, dpi)
                        md = self.vlm.transcribe_table(crop)
                    if md is None and fallback:
                        md = td.extract_grid_markdown(page, bbox)
                    if not md:
                        continue
                    cols = self._col_count(md)
                    blocks.append(Block(kind="table", page=pi, top=bbox[1], x0=bbox[0],
                                        markdown=md, bbox=bbox, cols=cols))
                    # drop paragraph lines inside this table region
                    blocks = [b for b in blocks
                              if not (b.kind == "paragraph" and b.page == pi
                                      and self._line_inside(b, bbox, lines))]
                # figures
                figs = fx.extract(page, pi, data)
                for fig in figs:
                    if self.vlm is not None:
                        crop = render_bbox_png_b64(data, pi, fig.bbox, dpi)
                        fig.caption = self.vlm.caption_figure(crop)
                blocks.extend(figs)

        blocks = CrossPageTableMerger().merge(blocks)
        markdown = MarkdownAssembler().assemble(blocks)
        return DocumentConverterResult(markdown=markdown)

    @staticmethod
    def _col_count(md: str) -> int:
        for row in md.splitlines():
            if row.strip().startswith("|"):
                return row.count("|") - 1
        return 0

    @staticmethod
    def _line_inside(block: Block, bbox, lines: List[Line]) -> bool:
        # block has no bbox; match by position against original lines on same page/top
        for ln in lines:
            if ln.page == block.page and abs(ln.bbox[1] - block.top) < 0.5 and ln.text == block.text:
                return _inside(ln.bbox, bbox)
        return False
```

- [ ] **Step 4: Run to verify pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_converter.py -v`
Expected: PASS (3 passed). If `test_table_replaced...` fails on dedup, verify `_line_inside` matches the body line's bbox center inside the table region; adjust the center test only (do not weaken the dedup intent).

- [ ] **Step 5: Run the full suite**

Run: `../markitdown/.venv/bin/python -m pytest -v`
Expected: all tasks 1-9 pass.

- [ ] **Step 6: Commit**

```bash
git add src/markitdown_pdf_plus/_converter.py tests/test_converter.py
git commit -m "feat: PdfPlusConverter orchestration with table-text dedup"
```

---

## Task 10: Plugin registration end-to-end

**Files:**
- Modify: `src/markitdown_pdf_plus/__init__.py` (already written in Task 0 — verify)
- Test: `tests/test_plugin.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_plugin.py
from markitdown import MarkItDown
from markitdown_pdf_plus._converter import PdfPlusConverter


def test_plugin_registers_and_overrides_builtin_pdf():
    md = MarkItDown(enable_builtins=True, enable_plugins=True)
    # our converter must be registered and appear before the built-in PDF converter
    convs = [r.converter for r in md._converters]
    assert any(isinstance(c, PdfPlusConverter) for c in convs)


def test_end_to_end_via_markitdown(headings_pdf_bytes, tmp_path):
    p = tmp_path / "h.pdf"
    p.write_bytes(headings_pdf_bytes)
    md = MarkItDown(enable_builtins=True, enable_plugins=True)
    result = md.convert(str(p))
    assert "# 1 Introduction" in result.markdown
```

- [ ] **Step 2: Run to verify fail/pass**

Run: `../markitdown/.venv/bin/python -m pytest tests/test_plugin.py -v`
Expected: PASS if `register_converters` (Task 0) is correct. If `_converters` is private/renamed in the installed markitdown, adjust the introspection to the public API (`md.convert` of a `.pdf` returns headings → proves override).

- [ ] **Step 3: Commit**

```bash
git add tests/test_plugin.py
git commit -m "test: plugin registration + end-to-end override"
```

---

## Task 11: Eval harness

**Files:**
- Create: `tests/eval/run_eval.py`

- [ ] **Step 1: Write `tests/eval/run_eval.py`**

```python
"""Score markitdown-pdf-plus on the real paper vs the markitdown-0.1.6 baseline.

Usage:
  ../markitdown/.venv/bin/python tests/eval/run_eval.py            # no VLM (structure only)
  PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py   # + Qwen via Ollama
"""
import os
import re
import sys

PDF = "../markitdown/2025059pap.pdf"


def metrics(md: str) -> dict:
    lines = md.splitlines()
    runtogether = sum(1 for l in lines if any(len(w) >= 18 for w in l.split()))
    return {
        "headings": sum(1 for l in lines if l.startswith("#")),
        "pipe_rows": sum(1 for l in lines if l.strip().startswith("|")),
        "figures": md.count("!["),
        "runtogether_lines": runtogether,
        "chars": len(md),
    }


def main():
    from markitdown import MarkItDown
    kwargs = {"enable_builtins": True, "enable_plugins": True, "pdf_plus_image_dir": "tests/_tmp/figs"}
    if os.getenv("PDFPLUS_OLLAMA"):
        from openai import OpenAI
        kwargs["llm_client"] = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        kwargs["llm_model"] = "qwen2.5vl:7b"

    plus = MarkItDown(**kwargs).convert(PDF).markdown
    baseline = MarkItDown(enable_builtins=True, enable_plugins=False).convert(PDF).markdown

    print(f"{'metric':<22}{'baseline':>12}{'pdf-plus':>12}")
    for k in ("headings", "pipe_rows", "figures", "runtogether_lines", "chars"):
        print(f"{k:<22}{metrics(baseline)[k]:>12}{metrics(plus)[k]:>12}")


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run the eval (structure-only)**

Run: `cd <repo> && ../markitdown/.venv/bin/python tests/eval/run_eval.py`
Expected: pdf-plus shows **headings > 0** (baseline 0), **runtogether_lines** much lower than baseline's ~788, figures > 0.

- [ ] **Step 3: Run the eval with VLM (optional, needs Ollama up)**

Run: `PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py`
Expected: pipe_rows reflect real tables; spot-check Table 3 grid in the output is well-formed.

- [ ] **Step 4: Commit**

```bash
git add tests/eval/run_eval.py
git commit -m "test: eval harness vs markitdown-0.1.6 baseline"
```

---

## Task 12: Integration smoke test, CI, README polish

**Files:**
- Create: `tests/test_integration.py`, `.github/workflows/ci.yml`
- Modify: `README.md`

- [ ] **Step 1: Opt-in integration smoke test**

```python
# tests/test_integration.py
import io
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_VLM_INTEGRATION"), reason="set RUN_VLM_INTEGRATION=1 + run Ollama"
)


def test_qwen_transcribes_table(table_pdf_bytes):
    from openai import OpenAI
    from markitdown_pdf_plus._vlm import VlmService
    from markitdown_pdf_plus._figures import render_bbox_png_b64
    import pdfplumber
    from markitdown_pdf_plus._tables import TableDetector

    with pdfplumber.open(io.BytesIO(table_pdf_bytes)) as pdf:
        bbox = TableDetector().detect(pdf.pages[0])[0]
    b64 = render_bbox_png_b64(table_pdf_bytes, 0, bbox, dpi=200)
    svc = VlmService(OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"), "qwen2.5vl:7b")
    md = svc.transcribe_table(b64)
    assert md is not None and "|" in md
```

- [ ] **Step 2: Run it (with Ollama up)**

Run: `RUN_VLM_INTEGRATION=1 ../markitdown/.venv/bin/python -m pytest tests/test_integration.py -v`
Expected: PASS (skipped without the env var).

- [ ] **Step 3: Create `.github/workflows/ci.yml`**

```yaml
name: ci
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[test]"
      - run: python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval
```

- [ ] **Step 4: Expand `README.md`** with: features, install, Python-API usage (no-endpoint + with-endpoint examples), `pdf_plus_*` options table, env-var CLI note, known limitations (single-column, scanned PDFs), and the eval numbers from Task 11.

- [ ] **Step 5: Run full offline suite**

Run: `../markitdown/.venv/bin/python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add tests/test_integration.py .github/workflows/ci.yml README.md
git commit -m "test: integration smoke test + CI + README"
```

---

## Self-Review (completed during planning)

- **Spec coverage:** structure layer (Tasks 2,5), figures (7), VLM tables (8,9), cross-page merge (4), captioning (8,9), tables-only + full-page config (0,9 — note full-page mode is wired via config flag; its render-each-page branch is a thin addition in `convert()` and is covered by README + config, implemented in Task 9's `convert` as a guarded branch if `config["full_page"]`), graceful no-op (8,9,10), packaging/CI (0,12), eval (11). **Gap flagged:** the full-page branch body is described but Task 9's code shows the tables-only path; the executor must add the `if self.config.get("full_page") and self.vlm:` branch (render each page → `vlm._call(page_png, table_prompt)` → concat) — added as an explicit sub-step note here so it isn't missed.
- **Placeholder scan:** no TBD/TODO; all code blocks complete.
- **Type consistency:** `Line`/`Block` fields, `VlmService(client, model, …)`, `render_bbox_png_b64(pdf_bytes, page_index, bbox, dpi)`, `FigureExtractor(image_dir, dpi).extract(page, page_index, pdf_bytes)`, `TableDetector().detect(page)` / `.extract_grid_markdown(page, bbox)`, `build_vlm_service(**kwargs)` are consistent across tasks 1-12.

**Full-page mode (explicit, so it isn't dropped):** in Task 9 `convert()`, before the per-page table/figure loop, add:
```python
if self.config.get("full_page") and self.vlm is not None:
    import base64
    from ._figures import _render_page_pil
    pages_md = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        n = len(pdf.pages)
    for pi in range(n):
        pil, _, _ = _render_page_pil(data, pi, dpi)
        buf = io.BytesIO(); pil.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        page_md = self.vlm._call(b64, self.vlm.table_prompt) or ""
        pages_md.append(page_md)
    return DocumentConverterResult(markdown="\n\n".join(pages_md).strip())
```
Add a test in `tests/test_converter.py` (`test_full_page_mode_uses_vlm_per_page` with `MockClient` returning `"# Page md"` and `config={"full_page": True, ...}`) asserting the mock content appears once per page.
