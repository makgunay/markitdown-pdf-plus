# Background and history

This section captures the reasoning the code and git history do not: why the plugin exists, how it was designed, the hard-won fixes the unit tests missed, and where it could go next. It distills the project's `docs/memory/` notes, written during a multi-day design, research, and build session.

## The short version

`markitdown-pdf-plus` was not a "let's build a plugin" idea from day one. It was a research arc that concluded a plugin was the right move. The team benchmarked the built-in converter and a range of alternatives on one dense academic PDF, found that the gap to the quality ceiling was almost entirely structure (headings) and tables, and that both were recoverable cheaply (font heuristics plus a VLM endpoint) without a heavy layout model. The plugin ships exactly those two levers.

## Pages

| Page | What's in it |
| --- | --- |
| [Design decisions](design-decisions.md) | Every key decision and its rationale: the enhance pattern, pdfminer for text, model-agnostic VLM, priority −1.0 |
| [Research and benchmarks](research-and-benchmarks.md) | The measured scoreboard of 11 approaches on the same paper, and what each experiment proved |
| [Build findings](build-findings.md) | The fixes the end-to-end eval forced after the unit suite was green, and the load-bearing lesson |
| [Roadmap](roadmap.md) | The parked TATR-routed local hybrid and the Mistral OCR 4 cloud-backend assessment |

## The load-bearing lesson

> Always verify a "tests-green" build end-to-end on a real target document. Simple fixtures pass while the real document fails. Borderless tables, justified text, and table captions are exactly the cases a toy fixture does not exercise.

This is why the repo keeps a real-document eval harness (`tests/eval/run_eval.py`) separate from the unit suite, and why the contribution guidance insists on running it before trusting any table or heading change.

## Source notes

The detail behind these pages lives in `docs/memory/`:

- `docs/memory/01-project-context.md` — what it is, origin story, decisions, environment
- `docs/memory/02-research-and-benchmarks.md` — the scoreboard and tooling research
- `docs/memory/03-build-findings.md` — the post-green fixes
- `docs/memory/04-roadmap-v0.2-tatr.md` — the parked TATR hybrid
- `docs/memory/05-mistral-ocr-4-assessment.md` — the Mistral OCR 4 fit assessment

The authoritative design spec and the task-by-task implementation plan are under `docs/superpowers/`.
