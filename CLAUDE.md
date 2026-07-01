# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`markitdown-pdf-plus` is a [MarkItDown](https://github.com/microsoft/markitdown) plugin that
**overrides the built-in PDF converter** (priority −1.0). It adds always-on font-heuristic headings
and figure extraction, plus opt-in, model-agnostic VLM table transcription, cross-page table merging,
and figure captioning. MIT, Python ≥3.10, no bundled ML. Published at
https://github.com/Akgunay-Labs/markitdown-pdf-plus (`main`, v0.1.0).

**Core principle: graceful degradation.** Useful output at every capability tier, never worse than
the built-in converter. No `llm_client` → font headings + pdfplumber tables + uncaptioned figures.
With an OpenAI-compatible `llm_client` → VLM tables + captions.

## Commands

Development and tests run against the **sibling venv** `../markitdown/.venv` (has markitdown 0.1.6 +
deps). There is no venv in this repo.

```bash
# One-time: install editable into the sibling venv
# (add the `eval` extra for the TEDS table-quality metric: apted)
../markitdown/.venv/bin/pip install -e ".[test,dev,eval]"

# Lint / format / type-check (configs live in pyproject.toml)
ruff check src tests
ruff check src tests --fix     # auto-fix the safe ones
ruff format src tests          # apply the formatter (Black-compatible)
ruff format --check src tests  # verify formatting
../markitdown/.venv/bin/python -m mypy   # strict type-check of src/

# Dead code + duplication + dependency hygiene (also wired into pre-commit / CI)
../markitdown/.venv/bin/python -m vulture   # dead code (whitelist: vulture_whitelist.py)
npx --yes jscpd@4                            # copy-paste detection (.jscpd.json)
../markitdown/.venv/bin/python -m deptry .   # unused / missing / transitive deps

# Auto-generated docs + AGENTS.md freshness (CI `docs` job enforces both)
../markitdown/.venv/bin/python scripts/gen_api_docs.py        # regenerate docs/API.md
../markitdown/.venv/bin/python scripts/gen_api_docs.py --check # fail if committed copy is stale
../markitdown/.venv/bin/python scripts/validate_docs.py        # AGENTS.md/CLAUDE.md links + tools

# Pre-commit hooks (ruff + ruff-format + mypy + vulture + large-file/secret checks).
# CI runs `pre-commit run --all-files` plus a jscpd duplication job; install locally with:
pre-commit install
pre-commit run --all-files

# Dev container (reproducible env: Python 3.12 + all test/dev tooling).
# Builds and starts the container defined in .devcontainer/devcontainer.json:
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . bash -lc "pytest -q"   # run anything inside

# Full offline suite (what CI runs)
../markitdown/.venv/bin/python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval

# Same suite with the coverage gate enforced (branch coverage; ~90% baseline, 88% floor)
../markitdown/.venv/bin/python -m pytest -q --cov --cov-report=term-missing

# Test isolation / flakiness tooling (plugins in the `test` extra)
# - order is randomized each run (pytest-randomly) to catch hidden coupling;
#   reproduce a failure with the seed printed at the top of the run.
# - parallel:  ../markitdown/.venv/bin/python -m pytest -n auto
# - flaky hunt: ../markitdown/.venv/bin/python -m pytest --reruns 2 --reruns-delay 1

# A single test
../markitdown/.venv/bin/python -m pytest tests/test_tables.py::test_detects_table_region -v

# Live-VLM integration test (needs Ollama up with qwen2.5vl:7b)
RUN_VLM_INTEGRATION=1 ../markitdown/.venv/bin/python -m pytest tests/test_integration.py -v

# Real-document eval — structure only, then with the Qwen VLM pass
../markitdown/.venv/bin/python tests/eval/run_eval.py
PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py

# Table-quality metrics (needs the `eval` extra): deterministic TEDS vs a
# reference-model pseudo-GT (default ref: mistral_ocr), and a vision LLM-judge.
MISTRAL_API_KEY=... ../markitdown/.venv/bin/python tests/eval/run_eval.py --teds
PDFPLUS_JUDGE_BASE=https://api.openai.com/v1 PDFPLUS_JUDGE_KEY=sk-... \
  ../markitdown/.venv/bin/python tests/eval/run_eval.py --judge --judge-model gpt-4o

# Confirm the plugin registers / overrides the built-in PDF converter
../markitdown/.venv/bin/markitdown --list-plugins
```

## Architecture

A pipeline of small, single-purpose stages orchestrated by a thin `PdfPlusConverter`, registered as
a `markitdown.plugin` entry point. Understanding the data flow requires reading several files
together — `_converter.py` is the orchestrator that wires the rest.

```
convert(stream)
  → TextExtractor (_extract.py, pdfminer)   → list[Line]  (text + font size + bold + top-left bbox)
  → HeadingAnnotator (_headings.py)          → Blocks (heading / paragraph) by font tier
  → per page (pdfplumber):
      TableDetector.detect (_tables.py)      → bboxes (ruled + borderless)
        → VlmService.transcribe_table(crop)  (_vlm.py)        [VLM path, if client]
          └ else TableDetector.extract_grid_markdown(page,bbox) [pdfplumber fallback]
        → Table block; DROP paragraph lines inside the bbox  (de-dup — see gotcha below)
      FigureExtractor (_figures.py)          → Figure blocks (+ VLM caption if client)
  → CrossPageTableMerger (_merge.py)         → merged Blocks
  → MarkdownAssembler (_assemble.py)         → markdown, sorted by (page, top, x0)
```

`full_page` mode (config flag + a client) short-circuits all of the above: it renders each page to
PNG and sends the whole page to the VLM. It's the escape hatch for multi-column / scanned /
equation-heavy docs.

Data model (`_model.py`): `Line` (per-line text + font), `Block` (`heading`/`paragraph`/`table`/
`figure`, positioned). Config flows from `MarkItDown(...)` kwargs through `register_converters` in
`__init__.py`; CLI users set `pdf_plus_*` via env vars.

## Non-obvious things to know before editing

These cost real debugging time; they're invariants, not style choices. Full rationale in
`docs/memory/03-build-findings.md`.

- **Text comes from pdfminer, not pdfplumber `extract_words`.** pdfplumber jams words on justified/
  kerned academic text; pdfminer keeps spacing. pdfminer uses a **bottom-left origin** — `_extract.py`
  converts y to a top-left `top` so its bboxes match the pdfplumber geometry used by table/figure
  detection. Break that conversion and the table-text de-dup silently fails.
- **Borderless-table detection = text strategy + a numeric-density validator.** pdfplumber's default
  `'lines'` strategy finds zero borderless academic tables. `_tables.py` also runs the `'text'`
  strategy and gates each candidate on **numeric density ≥ 0.25** (data tables are number-dense,
  prose isn't) so prose isn't mistaken for a grid. The **no-VLM grid fallback must also try the text
  strategy** or borderless tables collapse back to flattened text.
- **Table-text de-dup drops paragraphs only, never headings.** Headings inside a table region are
  real captions ("Table N. ..."). This is safe *only because* the heading heuristic was tightened to
  not promote numbered/data rows — `_headings.py` promotes same-size lines only when short AND bold.
  Don't reintroduce numbered-line promotion without re-checking caption handling.
- **The unit suite (reportlab fixtures) does NOT cover the real failure modes.** Borderless
  detection, justified-text spacing, and caption preservation only surface on a real academic PDF.
  **Run `tests/eval/run_eval.py` against `../markitdown/2025059pap.pdf` before trusting any table or
  heading change.** Green unit tests are necessary, not sufficient.
- **No in-process ML.** The VLM path is endpoint-based on purpose (model-agnostic, MIT-clean, light).
  Any future structure model — e.g. the parked TATR work — must be an **optional extra** with pinned
  deps, never a core dependency (transformers 4.x/5.x conflicts are a recurring wall).

## Context / memory docs

Read these for the reasoning the code doesn't capture — start with `docs/memory/README.md` (index):

- **`docs/memory/01-project-context.md`** — what it is, the origin story, every key decision + why, dev/test env.
- **`docs/memory/02-research-and-benchmarks.md`** — the measured scoreboard (11 approaches) and tooling research.
- **`docs/memory/03-build-findings.md`** — the hard-won fixes the unit tests missed (expanded versions of the gotchas above).
- **`docs/memory/04-roadmap-v0.2-tatr.md`** — the parked, measured-but-unshipped TATR-routed hybrid and exact next steps.
- **`docs/superpowers/specs/2026-06-06-markitdown-pdf-plus-design.md`** — authoritative design spec.
- **`docs/superpowers/plans/2026-06-06-markitdown-pdf-plus.md`** — the task-by-task implementation plan.

## Conventions

- Stages are single-purpose and independently testable: pure stages with hand-built `Line`/`Block`
  fixtures, PDF-touching stages with tiny reportlab fixtures, the VLM path with a `MockClient`. Keep
  new logic in the stage it belongs to rather than thickening `_converter.py`.
- Fail soft: never abort a document over one bad crop/call. The VLM path catches per-call and falls
  back; keep that contract.
- TDD + frequent commits, matching the existing history.

## Dependency update policy

- Updates are automated via Dependabot (`.github/dependabot.yml`) for both the `pip` and
  `github-actions` ecosystems, grouped and opened weekly.
- **Minimum release age:** do not merge a dependency bump until the target release is at least
  **7 days old** (**14 days** for a major version). This guards against yanked or
  broken-on-release versions and supply-chain attacks that are caught and pulled shortly after
  publication. The waiting period is enforced automatically by the Dependabot `cooldown` setting,
  so Dependabot will not even open the PR until the window has elapsed.
