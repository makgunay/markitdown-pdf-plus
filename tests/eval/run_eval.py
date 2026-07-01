"""Score markitdown-pdf-plus on real PDFs, with wall-clock timing and a backend selector.

The unit suite's reportlab fixtures do not exercise borderless tables, justified
text, captions, equations, or multi-column layout. This harness runs the plugin on
*real* documents so quality and latency are measured numbers, not assertions.

Usage:
  # default doc (the 82-page Fed paper), structure only
  ../markitdown/.venv/bin/python tests/eval/run_eval.py

  # one or more PDFs / folders, write the markdown out, time each run
  ../markitdown/.venv/bin/python tests/eval/run_eval.py path/to/a.pdf path/to/dir --out tests/_tmp/eval

  # pick a backend (default: local)
  ../markitdown/.venv/bin/python tests/eval/run_eval.py --backend mistral_ocr   # needs MISTRAL_API_KEY
  ../markitdown/.venv/bin/python tests/eval/run_eval.py --backend paddleocr_vl  # needs an OpenAI-compat endpoint

  # add a local VLM to the *local* backend (region table transcription + captions)
  PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py
  PDFPLUS_OPENAI_BASE=http://localhost:8111/v1 PDFPLUS_OPENAI_MODEL=PaddleOCR-VL-0.9B \
    ../markitdown/.venv/bin/python tests/eval/run_eval.py

  # quality metrics: TEDS vs a reference backend (pseudo-GT) + vision LLM-judge
  ../markitdown/.venv/bin/python tests/eval/run_eval.py --backend local --teds   # ref: mistral_ocr
  ../markitdown/.venv/bin/python tests/eval/run_eval.py --teds --teds-ref tests/eval/golden
  PDFPLUS_JUDGE_BASE=https://api.openai.com/v1 PDFPLUS_JUDGE_KEY=sk-... \
    ../markitdown/.venv/bin/python tests/eval/run_eval.py --judge --judge-model gpt-4o

Env knobs:
  PDFPLUS_OLLAMA=1                 use a local Ollama Qwen2.5-VL endpoint as llm_client
  PDFPLUS_OPENAI_BASE / _MODEL / _KEY   any OpenAI-compatible endpoint as llm_client
  MISTRAL_API_KEY                  credentials for --backend mistral_ocr (and TEDS reference)
  PDFPLUS_CONCURRENCY              parallel VLM calls (default 4)
  PDFPLUS_JUDGE_BASE / _MODEL / _KEY    OpenAI-compatible vision endpoint for --judge
"""

import argparse
import io
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from judge import judge_tables
from teds import doc_teds, extract_tables, md_table_to_html
from teds import teds as teds_score

DEFAULT_PDF = "../markitdown/2025059pap.pdf"
_METRIC_KEYS = (
    "seconds",
    "headings",
    "pipe_rows",
    "md_tables",
    "html_tables",
    "figures",
    "equations",
    "runtogether_lines",
    "chars",
)
# Quality metrics (TEDS / judge), printed after the structural counts when present.
_EXTRA_KEYS = (
    "teds",
    "teds_struct",
    "n_reference_tables",
    "n_predicted_tables",
    "judge_mean",
    "n_judged",
)


def metrics(md: str, seconds: float) -> dict[str, Any]:
    lines = md.splitlines()
    runtogether = sum(1 for ln in lines if any(len(w) >= 18 for w in ln.split()))
    return {
        "seconds": round(seconds, 2),
        "headings": sum(1 for ln in lines if ln.startswith("#")),
        "pipe_rows": sum(1 for ln in lines if ln.strip().startswith("|")),
        "md_tables": sum(1 for ln in lines if set(ln.strip()) <= {"|", "-", ":", " "} and "-" in ln),
        "html_tables": md.count("<table"),
        "figures": md.count("!["),
        "equations": md.count("$$") + md.count(r"\("),
        "runtogether_lines": runtogether,
        "chars": len(md),
    }


def _llm_kwargs() -> dict:
    """Build llm_client kwargs for the local backend from env, if configured."""
    if os.getenv("PDFPLUS_OLLAMA"):
        from openai import OpenAI

        return {
            "llm_client": OpenAI(base_url="http://localhost:11434/v1", api_key="ollama"),
            "llm_model": "qwen2.5vl:7b",
        }
    base = os.getenv("PDFPLUS_OPENAI_BASE")
    if base:
        from openai import OpenAI

        return {
            "llm_client": OpenAI(base_url=base, api_key=os.getenv("PDFPLUS_OPENAI_KEY", "x")),
            "llm_model": os.getenv("PDFPLUS_OPENAI_MODEL", "gpt-4o-mini"),
        }
    return {}


def _backend_kwargs(backend: str) -> dict:
    kwargs: dict = {"pdf_plus_backend": backend}
    if backend == "mistral_ocr" and os.getenv("MISTRAL_API_KEY"):
        kwargs["pdf_plus_mistral_api_key"] = os.environ["MISTRAL_API_KEY"]
    return kwargs


def _iter_pdfs(paths: list[str]):
    for p in paths:
        path = Path(p)
        if path.is_dir():
            yield from sorted(path.rglob("*.pdf"))
        elif path.exists():
            yield path
        else:
            print(f"!! skipping missing path: {p}", file=sys.stderr)


def _convert(pdf: Path, plugin_kwargs: dict) -> tuple[str, float]:
    from markitdown import MarkItDown

    t0 = time.perf_counter()
    md = MarkItDown(**plugin_kwargs).convert(str(pdf)).markdown
    return md, time.perf_counter() - t0


def _reference_md(pdf: Path, args: argparse.Namespace, base_kwargs: dict) -> str | None:
    """Reference (pseudo-GT) Markdown for TEDS: a stored file, else a live reference backend."""
    if args.teds_ref:
        ref_path = Path(args.teds_ref)
        target = ref_path / f"{pdf.stem}.ref.md" if ref_path.is_dir() else ref_path
        if target.exists():
            return target.read_text()
    try:
        kwargs = {**base_kwargs, **_backend_kwargs(args.teds_ref_backend)}
        return _convert(pdf, kwargs)[0]
    except Exception as exc:
        # Reference is best-effort (e.g. missing MISTRAL_API_KEY): skip TEDS, don't abort.
        print(f"!! TEDS reference unavailable for {pdf.name}: {exc}", file=sys.stderr)
        return None


def _judge_client(args: argparse.Namespace) -> tuple[Any, str] | None:
    base = os.getenv("PDFPLUS_JUDGE_BASE")
    model = args.judge_model or os.getenv("PDFPLUS_JUDGE_MODEL")
    if not base or not model:
        return None
    from openai import OpenAI

    return OpenAI(base_url=base, api_key=os.getenv("PDFPLUS_JUDGE_KEY", "x")), model


def _judge_pairs(pdf: Path, plus_md: str, dpi: int = 200) -> list[tuple[str, str]]:
    """Pair each source table crop with the best-matching predicted table for judging."""
    import pdfplumber

    from markitdown_pdf_plus._figures import render_bbox_png_b64
    from markitdown_pdf_plus._tables import TableDetector

    data = pdf.read_bytes()
    candidates = extract_tables(plus_md)
    if not candidates:
        return []
    detector = TableDetector()
    pairs: list[tuple[str, str]] = []
    with pdfplumber.open(io.BytesIO(data)) as doc:
        for page_index, page in enumerate(doc.pages):
            for bbox in detector.detect(page):
                grid_html = md_table_to_html(detector.extract_grid_markdown(page, bbox) or "")
                best = max(candidates, key=lambda c, g=grid_html: teds_score(c, g))
                pairs.append((render_bbox_png_b64(data, page_index, bbox, dpi), best))
    return pairs


def _fmt(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _print_doc(name: str, rows: dict[str, dict[str, Any]]) -> None:
    cols = list(rows.keys())
    extra = [k for k in _EXTRA_KEYS if any(k in rows[c] for c in cols)]
    print(f"\n# {name}")
    print(f"{'metric':<20}" + "".join(f"{c:>16}" for c in cols))
    for k in (*_METRIC_KEYS, *extra):
        print(f"{k:<20}" + "".join(f"{_fmt(rows[c].get(k)):>16}" for c in cols))


def _eval_doc(
    pdf: Path, args: argparse.Namespace, plus_kwargs: dict, judge: tuple[Any, str] | None
) -> tuple[dict[str, dict[str, Any]], str]:
    rows: dict[str, dict[str, Any]] = {}
    plus_md, secs = _convert(pdf, plus_kwargs)
    row = metrics(plus_md, secs)
    if args.teds:
        ref_md = _reference_md(pdf, args, plus_kwargs)
        if ref_md is not None:
            row.update(doc_teds(plus_md, ref_md))
    if judge is not None:
        row.update(judge_tables(judge[0], judge[1], _judge_pairs(pdf, plus_md)))
    rows[f"plus/{args.backend}"] = row
    if not args.no_baseline:
        base_md, base_secs = _convert(pdf, {"enable_builtins": True, "enable_plugins": False})
        rows["baseline"] = metrics(base_md, base_secs)
    return rows, plus_md


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "paths", nargs="*", default=[DEFAULT_PDF], help="PDF files or folders (default: the Fed paper)"
    )
    ap.add_argument("--backend", default="local", choices=["local", "mistral_ocr", "paddleocr_vl"])
    ap.add_argument("--out", default=None, help="directory to write <doc>.<backend>.md + metrics.json")
    ap.add_argument("--no-baseline", action="store_true", help="skip the markitdown built-in comparison")
    ap.add_argument("--teds", action="store_true", help="score tables vs a reference backend (pseudo-GT)")
    ap.add_argument("--teds-ref", default=None, help="reference .md file or dir of <stem>.ref.md")
    ap.add_argument("--teds-ref-backend", default="mistral_ocr", help="backend run live as TEDS reference")
    ap.add_argument("--judge", action="store_true", help="score tables with a vision LLM-judge")
    ap.add_argument("--judge-model", default=None, help="vision model for --judge (or PDFPLUS_JUDGE_MODEL)")
    args = ap.parse_args()

    concurrency = int(os.getenv("PDFPLUS_CONCURRENCY", "4"))
    plus_kwargs = {
        "enable_builtins": True,
        "enable_plugins": True,
        "pdf_plus_image_dir": "tests/_tmp/figs",
        "pdf_plus_concurrency": concurrency,
        **_backend_kwargs(args.backend),
        **_llm_kwargs(),
    }
    out_dir = Path(args.out) if args.out else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    pdfs = list(_iter_pdfs(args.paths))
    if not pdfs:
        print("no PDFs found", file=sys.stderr)
        return 1

    judge = _judge_client(args) if args.judge else None
    if args.judge and judge is None:
        print(
            "!! --judge needs PDFPLUS_JUDGE_BASE + --judge-model/PDFPLUS_JUDGE_MODEL; skipping",
            file=sys.stderr,
        )

    for pdf in pdfs:
        rows, plus_md = _eval_doc(pdf, args, plus_kwargs, judge)
        _print_doc(pdf.name, rows)
        if out_dir:
            (out_dir / f"{pdf.stem}.{args.backend}.md").write_text(plus_md)
            (out_dir / f"{pdf.stem}.{args.backend}.metrics.json").write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
