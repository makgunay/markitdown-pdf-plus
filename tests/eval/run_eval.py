"""Score markitdown-pdf-plus on the real paper vs the markitdown-0.1.6 baseline.

Usage:
  ../markitdown/.venv/bin/python tests/eval/run_eval.py            # no VLM (structure only)
  PDFPLUS_OLLAMA=1 ../markitdown/.venv/bin/python tests/eval/run_eval.py   # + Qwen via Ollama
"""

import os
import sys

PDF = "../markitdown/2025059pap.pdf"


def metrics(md: str) -> dict:
    lines = md.splitlines()
    runtogether = sum(1 for ln in lines if any(len(w) >= 18 for w in ln.split()))
    return {
        "headings": sum(1 for ln in lines if ln.startswith("#")),
        "pipe_rows": sum(1 for ln in lines if ln.strip().startswith("|")),
        "figures": md.count("!["),
        "runtogether_lines": runtogether,
        "chars": len(md),
    }


def main():
    from markitdown import MarkItDown

    kwargs = {"enable_builtins": True, "enable_plugins": True, "pdf_plus_image_dir": "tests/_tmp/figs"}
    if os.getenv("PDFPLUS_OLLAMA"):
        from openai import OpenAI

        kwargs["llm_client"] = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        kwargs["llm_model"] = "qwen2.5vl:7b"

    plus = MarkItDown(**kwargs).convert(PDF).markdown
    baseline = MarkItDown(enable_builtins=True, enable_plugins=False).convert(PDF).markdown

    print(f"{'metric':<22}{'baseline':>12}{'pdf-plus':>12}")
    for k in ("headings", "pipe_rows", "figures", "runtogether_lines", "chars"):
        print(f"{k:<22}{metrics(baseline)[k]:>12}{metrics(plus)[k]:>12}")


if __name__ == "__main__":
    sys.exit(main())
