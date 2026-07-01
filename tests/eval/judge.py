"""LLM-judge for table quality (human-correlated, no ground truth).

Scores a predicted Markdown table against the *source image* of the table region
(cropped from the original PDF). The "Beyond String Matching" finding
(docs/memory/02) is that an LLM-judge correlates with human grading far better than
TEDS (r=0.93 vs 0.65), so this is the quality gate and `teds.py` is the
deterministic regression tracker.

Source-grounded by design: it compares the prediction to the rendered table image,
so it needs no ground truth. Works with any OpenAI-compatible vision client and is
fail-soft (a failed or unparseable call yields score=None, never raises).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

JUDGE_PROMPT = (
    "You are grading how faithfully a Markdown rendering reproduces the table shown in "
    "the image. Find the table in the provided Markdown that corresponds to the image, "
    "then score 0-100 on: (1) structure (row/column counts and merged or spanning "
    "headers), (2) every cell value reproduced verbatim, including parenthesized "
    "standard errors and significance stars, (3) correct cell-to-header mapping, "
    "(4) completeness (no dropped or invented cells). If no corresponding table is "
    'present, score 0. Respond with ONLY JSON: {"score": <int 0-100>, "issues": ["..."]}.'
)


def _parse_json(text: str) -> dict[str, Any]:
    stripped = re.sub(r"^```[a-zA-Z]*\s*", "", text.strip())
    stripped = re.sub(r"\s*```$", "", stripped)
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        return {"score": None, "issues": ["unparseable judge response"]}
    try:
        obj = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"score": None, "issues": ["invalid JSON in judge response"]}
    score = obj.get("score")
    obj["score"] = int(score) if isinstance(score, int | float) else None
    obj.setdefault("issues", [])
    return obj


def score_table(
    client: Any,
    model: str,
    image_b64: str,
    predicted_md: str,
    prompt: str = JUDGE_PROMPT,
) -> dict[str, Any]:
    """Score one predicted table against its source-image crop. Fail-soft."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                        },
                        {"type": "text", "text": f"{prompt}\n\nMarkdown:\n{predicted_md}"},
                    ],
                }
            ],
            temperature=0,
            max_tokens=512,
        )
        content = resp.choices[0].message.content
    except Exception as exc:  # noqa: BLE001 - eval tool must never abort on a bad call
        logger.warning("judge call failed: %s", exc)
        return {"score": None, "issues": [f"judge call failed: {exc}"]}
    return _parse_json(content or "")


def judge_tables(
    client: Any,
    model: str,
    pairs: list[tuple[str, str]],
    prompt: str = JUDGE_PROMPT,
) -> dict[str, Any]:
    """Judge a list of (source-image crop, predicted table) pairs; mean valid score."""
    scores = [
        result["score"]
        for image_b64, predicted_md in pairs
        if (result := score_table(client, model, image_b64, predicted_md, prompt))["score"] is not None
    ]
    return {
        "judge_mean": round(sum(scores) / len(scores), 1) if scores else None,
        "n_judged": len(scores),
    }
