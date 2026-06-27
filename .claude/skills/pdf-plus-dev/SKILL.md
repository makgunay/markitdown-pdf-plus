---
name: pdf-plus-dev
description: Development workflow for the markitdown-pdf-plus MarkItDown PDF plugin. Use when adding or editing a conversion stage (text extraction, headings, tables, figures, VLM, merge, assembly), running the test/eval suite, or debugging borderless-table / heading-heuristic / table-text de-dup behavior.
---

# pdf-plus-dev

You are working on `markitdown-pdf-plus`, a MarkItDown plugin that overrides the
built-in PDF converter. Read `CLAUDE.md` for the full architecture and invariants;
this skill is the fast-path operational guide.

## Pipeline (do not thicken the orchestrator)

```
convert → TextExtractor → HeadingAnnotator → per page:
  TableDetector.detect → (VlmService.transcribe_table | extract_grid_markdown)
  FigureExtractor.extract
→ CrossPageTableMerger → MarkdownAssembler
```

Each stage is a single-purpose module in `src/markitdown_pdf_plus/`. Keep new logic
in the stage it belongs to, not in `_converter.py`.

## Non-negotiable invariants (breaking these silently regresses output)

- Text comes from **pdfminer**, not pdfplumber `extract_words`. `_extract.py`
  converts pdfminer's bottom-left y to a top-left `top` so bboxes match pdfplumber.
  Break the y conversion → table-text de-dup silently fails.
- Borderless-table detection = pdfplumber **`text` strategy** + **numeric density
  ≥ 0.25**. The no-VLM grid fallback must also try the text strategy or borderless
  tables collapse to flat text.
- Table-text de-dup drops **paragraphs only, never headings** (headings inside a
  table region are real "Table N." captions). Safe only because the heading
  heuristic promotes same-size lines only when short AND bold.
- **No in-process ML as a core dependency.** The VLM path is endpoint-based.
- Fail soft: never abort a document over one bad crop/call; the VLM path catches
  per-call and falls back.

## Commands (sibling venv `../markitdown/.venv`)

```bash
../markitdown/.venv/bin/pip install -e ".[test,dev]"
ruff check src tests && ruff format --check src tests
../markitdown/.venv/bin/python -m mypy
../markitdown/.venv/bin/python -m pytest -q --cov --cov-report=term-missing
pre-commit run --all-files
```

## Before trusting a table or heading change

The unit suite's reportlab fixtures do **not** cover borderless detection,
justified-text spacing, or caption preservation. Always also run the real-document
eval against `../markitdown/2025059pap.pdf`:

```bash
../markitdown/.venv/bin/python tests/eval/run_eval.py
```

Green unit tests are necessary, not sufficient.

## Workflow

1. Reproduce / understand the stage in isolation with hand-built `Line`/`Block`
   fixtures (pure stages) or tiny reportlab PDFs (PDF-touching stages).
2. TDD: write the failing test, implement, run the full offline suite + coverage
   gate (88% floor, ~90% baseline).
3. If the change touches tables, headings, or text extraction, run the real-paper
   eval before considering it done.
4. Commit frequently, matching the existing history style.
