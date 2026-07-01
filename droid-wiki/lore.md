# Lore

The story of how this codebase came to be. It is short, because the project was built in a single concentrated arc, but that arc has distinct phases worth recording. Dates come from git commit timestamps.

## The eras

### Research and decision (late May – early Jun 2026)

The project did not start as "build a plugin." It started as a research question: how good can PDF-to-Markdown conversion get on a hard document, and what is the cheapest way to close the gap? The team benchmarked MarkItDown's built-in converter, Marker, and several local OCR specialists on one 82-page Federal Reserve working paper, scored everything on a weighted rubric, and concluded the distance to the quality ceiling was almost entirely structure (headings) and tables, both recoverable cheaply. That conclusion, plus open community demand on MarkItDown's issue tracker, made "build a plugin" the answer. The reasoning is preserved in [Research and benchmarks](background/research-and-benchmarks.md).

### Design and planning (Jun 6, 2026)

The first two commits in the repo are not code. They are `docs: design spec for markitdown-pdf-plus` and `docs: TDD implementation plan for markitdown-pdf-plus` (`00f8522`, `adef2dd`), both on 2026-06-06. The design spec and the task-by-task plan came before a single line of the library, under `docs/superpowers/`.

### The TDD build (Jun 6, 2026)

The pipeline was then built stage by stage, each as its own `feat:` commit with tests: the data model (`ec3f2ab`), the heading annotator, the markdown assembler, the cross-page merger, the text extractor, the table detector, the figure extractor, the VLM service (`9f1e25b`), and finally the orchestrator (`45ddb90`). The unit suite went green.

### The post-green fixes (Jun 6, 2026)

Then the build was run end-to-end on the real paper, and the simple fixtures' blind spots showed. A cluster of `fix:` commits landed in quick succession: pdfminer text extraction for clean spacing plus a tighter heading heuristic (`790b516`), borderless-table detection via the text strategy and a numeric-density validator (`c00beaf`, `d1944d1`), caption preservation through paragraph-only de-dup (`77e3d4d`), and the grid fallback using the text strategy so borderless tables render instead of flattening (`3f86fde`). This phase produced the project's load-bearing lesson: verify a tests-green build on a real document. See [Build findings](background/build-findings.md).

### Release and hardening (Jun 6 – Jun 27, 2026)

v0.1.0 shipped with the README and CHANGELOG (`0f484fc`, `bd920d3`) on 2026-06-06. Three weeks later, on 2026-06-27, two things happened: the durable context docs were added (`CLAUDE.md`, `AGENTS.md`, and the `docs/memory/` set, including a Mistral OCR 4 fit assessment), and the repo's tooling, CI, and governance were hardened for agent-readiness in a single large commit (`2a2c3fc`, the first and so far only pull request).

## Longest-standing code

Every source module dates from the same 2026-06-06 build, so there is no old-versus-new split yet. The modules that have weathered the most change since are the orchestrator (`_converter.py`, 6 revisions) and the table detector (`_tables.py`, 5 revisions), both because the real-document fixes concentrated there. The data model (`_model.py`) and the assembler (`_assemble.py`) have barely changed since they were written.

## Deprecated and parked

Nothing has been deprecated; the project is at its first release. One significant body of work is parked rather than shipped: the TATR-routed structure-model-first hybrid (measured end-to-end, validated, never integrated), reframed in June 2026 by the Mistral OCR 4 assessment into a "local tier vs cloud tier" v0.2 framing. See [Roadmap](background/roadmap.md).

## Growth trajectory

The repo went from empty to a released, CI-green, fully-tooled PyPI package within its first day of commits, then added a documentation and governance layer three weeks later. It remains a one-author project (Mehmet Akgunay), built with heavy AI assistance recorded in commit co-authorship.
