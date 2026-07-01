# Testing

The project has three test layers: a fast offline unit suite (what CI runs), a real-document eval harness (manual, the real safety net for table and heading work), and a live-VLM integration smoke test.

## The offline unit suite

Pure stages are tested with hand-built `Line`/`Block` fixtures and no PDF or network. PDF-touching stages use tiny reportlab fixtures defined in `tests/conftest.py` (a headings page, a ruled table, a borderless table, a prose page, an embedded image). The VLM path uses a deterministic `MockClient` (defined in `tests/test_vlm.py`).

Run it:

```bash
../markitdown/.venv/bin/python -m pytest -v --ignore=tests/test_integration.py --ignore=tests/eval
```

The default `pytest` config (in `pyproject.toml`) already ignores the integration test and the eval harness, so a plain `pytest` runs the offline suite.

| Test file | Covers |
| --- | --- |
| `tests/test_extract.py` | pdfminer line extraction, font metadata |
| `tests/test_headings.py` | font-tier promotion, numbered-row rejection, short-bold rule |
| `tests/test_tables.py` | ruled + borderless detection, prose rejection, grid fallback, a real-paper regression |
| `tests/test_figures.py` | figure-region extraction |
| `tests/test_vlm.py` | fence stripping, non-table rejection, exception → `None`, the `MockClient` |
| `tests/test_merge.py` | cross-page merge conditions |
| `tests/test_assemble.py` | reading-order rendering |
| `tests/test_model.py` | the dataclasses |
| `tests/test_converter.py` | end-to-end orchestration, de-dup, full-page mode |
| `tests/test_plugin.py` | registration and override of the built-in converter |
| `tests/test_integration.py` | live-VLM smoke test (skipped unless `RUN_VLM_INTEGRATION=1`) |

## Coverage gate

Branch coverage is on, with a measured baseline near 90% and a floor of 88% (`fail_under = 88` in `pyproject.toml`). Run with the gate enforced:

```bash
../markitdown/.venv/bin/python -m pytest -q --cov --cov-report=term-missing
```

## The real-document eval (the actual safety net)

The reportlab fixtures do not exercise the real failure modes: borderless detection, justified-text spacing, and caption preservation only surface on a real academic PDF. `tests/eval/run_eval.py` scores the plugin against the markitdown-0.1.6 baseline on `../markitdown/2025059pap.pdf`, reporting headings, pipe rows, figures, run-together lines, and character count.

```bash
# structure only (no VLM)
../markitdown/.venv/bin/python tests/eval/run_eval.py

# with the Qwen VLM pass
PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py
```

Run this before trusting any table or heading change. Green unit tests are necessary, not sufficient. The one borderless-detection regression that is also a unit test (`tests/test_tables.py`) self-skips when the real paper is not present.

## Live-VLM integration test

```bash
RUN_VLM_INTEGRATION=1 ../markitdown/.venv/bin/python -m pytest tests/test_integration.py -v
```

This needs a running Ollama with `qwen2.5vl:7b`. It is excluded from CI.

## Isolation and flakiness tooling

The `test` extra adds plugins that harden the suite:

- **pytest-randomly** randomizes test order each run to catch hidden coupling; reproduce a failure with the seed printed at the top of the run.
- **Parallel:** `../markitdown/.venv/bin/python -m pytest -n auto` (pytest-xdist).
- **Flaky hunt:** `../markitdown/.venv/bin/python -m pytest --reruns 2 --reruns-delay 1` (pytest-rerunfailures). CI has a dedicated `flaky` job that re-runs failures.

See [Tooling](tooling.md) for the rest of the quality stack and [Build findings](../background/build-findings.md) for why the eval exists.
