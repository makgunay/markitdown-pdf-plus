# Dependencies

The plugin is deliberately light: no machine-learning weights, no torch, no transformers. The runtime closure is small enough to keep the package MIT-clean and fast to install. Dependencies are declared in `pyproject.toml` and built with hatchling.

## Runtime dependencies

| Package | Constraint | Why it's here |
| --- | --- | --- |
| `markitdown` | `>=0.1.5` | the host library this plugin extends; provides `DocumentConverter`, `StreamInfo`, the plugin entry-point contract |
| `pdfplumber` | `>=0.11` | table and figure geometry: region detection (ruled + text strategies), cell extraction, page cropping |
| `pdfminer.six` | `>=20220524` | body-text extraction with preserved word spacing (the reason text does not come from pdfplumber) |
| `pypdfium2` | `>=4` | rasterizing page and region crops to PNG for the VLM and saved figures |
| `Pillow` | `>=10` | image handling behind pypdfium2's `.to_pil()` and figure crop saving (used indirectly, not imported in `src`) |

## Optional dependency groups

Declared as extras and treated as dev groups by deptry so they are not flagged as unused:

| Group | Packages | Purpose |
| --- | --- | --- |
| `test` | `pytest`, `reportlab`, `pytest-cov`, `pytest-randomly`, `pytest-rerunfailures`, `pytest-xdist` | the unit suite, fixtures, coverage, order randomization, flaky re-runs, parallelism |
| `dev` | `ruff`, `mypy`, `pre-commit`, `vulture`, `deptry` | lint/format, type-check, hooks, dead-code, dependency hygiene |

## Notable absences

- **No OpenAI SDK as a hard dependency.** The VLM path takes any OpenAI-compatible `llm_client` the caller constructs, so the `openai` package is the caller's choice, not the plugin's.
- **No torch / transformers.** A future structure-model backend (TATR) would arrive as an optional `[tatr]` extra precisely to keep these out of the core. See [Roadmap](../background/roadmap.md).

## Deptry notes

Two configuration choices in `pyproject.toml` keep deptry honest: Pillow is exempt from the unused-dependency rule (DEP002) because its usage is indirect through pypdfium2, and the project's own package is declared `known_first_party` so the helper scripts importing it are not mistaken for an undeclared transitive dependency. See [Tooling](../how-to-contribute/tooling.md).
