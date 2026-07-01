# Tooling

The repo carries an unusually complete quality stack for its size. Everything is wired into pre-commit and CI so the gates run the same way locally and in the pipeline. All configuration lives in `pyproject.toml` unless noted.

## Lint, format, type-check

- **ruff** (lint + format). Line length 110, double quotes, space indent. The lint rule set: pycodestyle, pyflakes, isort, pyupgrade, bugbear, simplify, comprehensions, pep8-naming, mccabe (max complexity 10), and flake8-todos (tech-debt markers must be tracked or linked). Tests ignore line-length.
  ```bash
  ruff check src tests
  ruff check src tests --fix
  ruff format src tests
  ruff format --check src tests
  ```
- **mypy** (strict) over `src/` only. Third-party imports without stubs are treated as `Any` (`follow_imports = "skip"`); the few libraries without type info (`pdfplumber`, `pdfminer`, `pypdfium2`, `markitdown`) are listed with `ignore_missing_imports`. Subclassing MarkItDown's untyped `DocumentConverter` is allowed without losing strictness elsewhere.
  ```bash
  ../markitdown/.venv/bin/python -m mypy
  ```

## Dead code, duplication, dependency hygiene

- **vulture** (dead code), min confidence 70. Names called through MarkItDown's plugin contract that static analysis cannot see are listed in `vulture_whitelist.py` to mark them used.
  ```bash
  ../markitdown/.venv/bin/python -m vulture
  ```
- **jscpd** (copy-paste detection), configured in `.jscpd.json`, run as a CI job.
  ```bash
  npx --yes jscpd@4
  ```
- **deptry** (unused / missing / transitive dependencies). The `test` and `dev` extras are declared as dev groups so tooling is not flagged as unused; Pillow is whitelisted because pypdfium2's `.to_pil()` needs it even though `src` never imports `PIL` directly.
  ```bash
  ../markitdown/.venv/bin/python -m deptry .
  ```

## Auto-generated docs

- **`scripts/gen_api_docs.py`** introspects the package and regenerates `docs/API.md`. The CI `docs` job runs it with `--check` and fails if the committed copy is stale.
- **`scripts/validate_docs.py`** verifies that every local Markdown link in `AGENTS.md`/`CLAUDE.md` resolves and that the documented tools (`ruff`, `mypy`, `pytest`, `pre-commit`, `markitdown`) are actually invokable.
  ```bash
  ../markitdown/.venv/bin/python scripts/gen_api_docs.py --check
  ../markitdown/.venv/bin/python scripts/validate_docs.py
  ```

## pre-commit

`.pre-commit-config.yaml` wires ruff, ruff-format, mypy (strict, no filenames passed), vulture, gitleaks (secret scan), and the standard hygiene hooks (large-file check at 512 KB, end-of-file fixer, trailing whitespace, YAML/TOML checks, merge-conflict and private-key detection). Install and run:

```bash
pre-commit install
pre-commit run --all-files
```

## CI

`.github/workflows/ci.yml` runs on every push and pull request, with five jobs:

| Job | What it runs |
| --- | --- |
| `lint` | `pre-commit run --all-files` + `deptry .` |
| `duplication` | `jscpd@4` |
| `docs` | `gen_api_docs.py --check` + `validate_docs.py` |
| `test` | `pytest --cov` across Python 3.10, 3.11, 3.12 |
| `flaky` | the suite with `--reruns 2` to surface intermittent failures |

The `release` workflow publishes to PyPI on a version tag; see [Development workflow](development-workflow.md).

## Dev container

`.devcontainer/devcontainer.json` defines a reproducible Python 3.12 environment with the ruff, mypy, Pylance, TOML, YAML, and GitLens VS Code extensions, format-on-save via ruff, and a `postCreateCommand` that installs the `[test,dev]` extras and `pre-commit install`. A named volume backs the venv. Bring it up with the devcontainers CLI (see [Getting started](../overview/getting-started.md)).

## Dependency automation

Dependabot (`.github/dependabot.yml`) groups weekly updates for pip and GitHub Actions with a release-age cooldown (7 days, 14 for majors). See [Development workflow](development-workflow.md).
