# Getting started

This page covers installing the plugin, running it with and without a VLM, and setting up a development environment.

## Prerequisites

- Python ≥3.10
- MarkItDown (`markitdown>=0.1.5`) — installed as a dependency
- Optional: an OpenAI-compatible vision endpoint (local Ollama / LM Studio, or cloud OpenAI / Gemini) for the VLM table and caption path

The plugin ships no machine-learning weights. The runtime dependencies are light: `pdfplumber`, `pdfminer.six`, `pypdfium2`, and `Pillow`. See [Dependencies](../reference/dependencies.md).

## Install

```bash
pip install markitdown-pdf-plus
```

From source (editable, with test extras):

```bash
pip install -e ".[test]"
```

## Run without a VLM (always-on structure)

Font-heuristic headings, figure extraction, and pdfplumber table grids work with no endpoint:

```python
from markitdown import MarkItDown

md = MarkItDown(enable_plugins=True)
result = md.convert("document.pdf")
print(result.text_content)
```

## Run with a local Ollama model

```python
from markitdown import MarkItDown
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

md = MarkItDown(
    enable_plugins=True,
    llm_client=client,
    llm_model="qwen2.5vl:7b",
)
result = md.convert("document.pdf")
print(result.text_content)
```

## Run with OpenAI

```python
from markitdown import MarkItDown
import openai

client = openai.OpenAI()  # uses OPENAI_API_KEY

md = MarkItDown(enable_plugins=True, llm_client=client, llm_model="gpt-4o")
result = md.convert("document.pdf")
print(result.text_content)
```

## CLI usage

MarkItDown does not forward arbitrary environment variables to plugins through the CLI, but you can configure the endpoint before running and use the plugin's always-on structure path:

```bash
OPENAI_API_KEY=sk-... markitdown document.pdf --use-plugins
```

Confirm the plugin is registered and overrides the built-in PDF converter:

```bash
markitdown --list-plugins
```

## Configuration at a glance

Pass `pdf_plus_*` keyword arguments to tune behavior (full list in [Configuration](../reference/configuration.md)):

| Option | Default | Purpose |
| --- | --- | --- |
| `pdf_plus_dpi` | `200` | DPI for PNG crop rendering |
| `pdf_plus_image_dir` | `None` | directory to save figure PNGs; `None` keeps figures caption-only |
| `pdf_plus_table_fallback` | `True` | use pdfplumber grid when the VLM is absent or fails |
| `pdf_plus_full_page` | `False` | render whole pages to the VLM instead of per-region crops |

## Developer setup

Development and tests run against the sibling virtual environment `../markitdown/.venv` (which already has markitdown 0.1.6 and its dependencies). There is no venv committed in this repo.

```bash
# Install editable into the sibling venv (one time)
../markitdown/.venv/bin/pip install -e ".[test,dev]"

# Run the offline test suite (what CI runs)
../markitdown/.venv/bin/python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval

# Lint, format, type-check
ruff check src tests
ruff format --check src tests
../markitdown/.venv/bin/python -m mypy
```

Alternatively, use the reproducible dev container (Python 3.12 with all tooling):

```bash
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . bash -lc "pytest -q"
```

See [Development workflow](../how-to-contribute/development-workflow.md) and [Testing](../how-to-contribute/testing.md) for the full loop, and [Tooling](../how-to-contribute/tooling.md) for the lint/type/quality stack.

## A note on credentials

The plugin itself takes no secrets. You construct an OpenAI-compatible `llm_client` and pass it in; the `openai` client reads `OPENAI_API_KEY` / `OPENAI_BASE_URL` when you build it. Copy `.env.example` to a gitignored `.env` for local endpoint configuration. Never commit `.env`.
