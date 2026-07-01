"""PaddleOCR-VL / dots.ocr local full-document VLM backend (opt-in).

Routes the whole document through a local, OpenAI-compatible document-parsing VLM
(e.g. PaddleOCR-VL served via ``mlx_vlm.server`` on Apple Silicon, or vLLM on a GPU).
Each page is rendered to a PNG and sent to the endpoint, which returns structured
Markdown with tables, equations, and reading order in one pass per page.

This is the local, free, private SOTA tier. Unlike the Mistral cloud backend, no
document leaves the machine. Unlike the ``local`` backend's region-crop table path,
it closes the equations and multi-column gaps a heuristic pipeline cannot.

Requires an ``llm_client``/``llm_model`` pointing at a doc-parsing VLM endpoint.
No new core dependency -- it reuses the existing OpenAI-compatible ``VlmService``.
"""

from typing import Any

from ._concurrency import map_ordered
from ._figures import render_pages_b64

DOC_PARSE_PROMPT = (
    "OCR this page to Markdown. Preserve headings, paragraphs, lists, pipe tables "
    "(with header + separator rows), and block math as $$...$$. Output only the Markdown."
)


class PaddleOcrBackend:
    """Whole-document page-by-page VLM transcription using a local doc-parsing endpoint."""

    def __init__(self, vlm: Any, config: dict[str, Any]):
        # Validate the client lazily in convert(), not here: this backend is
        # constructed at plugin-registration time, so raising in __init__ would
        # crash MarkItDown construction rather than just PDF conversion.
        self.vlm = vlm
        self.config = config or {}
        self.concurrency = int(self.config.get("concurrency", 4))
        self.dpi = self.config.get("dpi", 200)
        self.prompt = self.config.get("paddleocr_prompt") or DOC_PARSE_PROMPT

    def convert(self, data: bytes) -> str:
        if self.vlm is None:
            raise ValueError(
                "paddleocr_vl backend needs an llm_client/llm_model pointing at a "
                "doc-parsing VLM (e.g. mlx_vlm.server or vLLM serving PaddleOCR-VL)."
            )
        page_b64 = render_pages_b64(data, self.dpi)
        pages_md = map_ordered(
            lambda b64: self.vlm.transcribe_page(b64, self.prompt), page_b64, self.concurrency
        )
        return "\n\n".join(pages_md).strip()
