# Project Memory

Durable context for `markitdown-pdf-plus` — the *why* behind the code, distilled from the
multi-day design + research + build session (2026-05-31 → 2026-06-07). Read these when you need
the reasoning that the code and git history don't capture.

| Doc | What's in it |
|---|---|
| [01-project-context.md](01-project-context.md) | What this plugin is, the origin story, every key decision and its rationale, the architecture at a glance, and the dev/test environment. |
| [02-research-and-benchmarks.md](02-research-and-benchmarks.md) | The full measured scoreboard (11 approaches on the same 82-page paper), the tooling research (Marker, OCR specialists, TATR/OTSL/TEDS), and what each experiment proved. |
| [03-build-findings.md](03-build-findings.md) | Hard-won findings the unit tests missed — the borderless-table fix, the pdfminer spacing fix, the heading-heuristic tightening, env conflicts, and the load-bearing lesson. |
| [04-roadmap-v0.2-tatr.md](04-roadmap-v0.2-tatr.md) | The parked TATR-routed hybrid (measured, not yet shipped): architecture, results, dependency cost, and the exact next steps when work resumes. |

## Companion docs (elsewhere in the repo)

- **Design spec** — [`../superpowers/specs/2026-06-06-markitdown-pdf-plus-design.md`](../superpowers/specs/2026-06-06-markitdown-pdf-plus-design.md) — motivation, goals/non-goals, component architecture, data flow, error handling, testing strategy. The authoritative "what we set out to build."
- **Implementation plan** — [`../superpowers/plans/2026-06-06-markitdown-pdf-plus.md`](../superpowers/plans/2026-06-06-markitdown-pdf-plus.md) — the task-by-task TDD plan actually executed.
- **`../../CHANGELOG.md`**, **`../../README.md`** — user-facing release notes and usage.

> Provenance: this work began in the sibling `tools/markitdown/` scratch directory (research +
> benchmarks) and the plugin itself was built in this repo. The original session transcript is at
> `~/.claude/projects/-Users-akgunay-Documents-CodingProjects-AkgunayLab-tools-markitdown/c0680546-….jsonl`.
