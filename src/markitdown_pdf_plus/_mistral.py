"""Mistral OCR 4 cloud backend (opt-in).

Routes the whole PDF through Mistral's dedicated ``/v1/ocr`` document model, which
returns structured per-page Markdown (tables as markdown/HTML, equations, figure
bounding boxes) in one call. This closes the two gaps the local heuristic path
cannot: equations->LaTeX and multi-column reading order.

Privacy note: this sends the document to a third-party cloud API. It is opt-in
(``pdf_plus_backend="mistral_ocr"``), never the default.

No new runtime dependency: the HTTP call uses the standard library so the backend
works without installing an SDK. Set ``pdf_plus_mistral_api_key`` or ``MISTRAL_API_KEY``.
"""

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"
DEFAULT_MODEL = "mistral-ocr-4-0"  # pin the version; never "-latest" (cloud aliases drift)

Poster = Callable[[str, dict[str, Any], dict[str, str], float], dict[str, Any]]


class MistralOcrError(RuntimeError):
    pass


def _urllib_post(
    url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float
) -> dict[str, Any]:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (fixed https endpoint)
            return json.loads(r.read().decode())  # type: ignore[no-any-return]
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise MistralOcrError(f"Mistral OCR HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise MistralOcrError(f"Mistral OCR request failed: {e}") from e


class MistralOcrBackend:
    """Convert a PDF via the Mistral OCR document API. ``poster`` is injectable for tests."""

    def __init__(self, config: dict[str, Any], poster: Poster | None = None):
        self.config = config or {}
        self.api_key = self.config.get("mistral_api_key") or os.getenv("MISTRAL_API_KEY")
        self.model = self.config.get("mistral_model", DEFAULT_MODEL)
        self.image_dir = self.config.get("image_dir")
        self.endpoint = self.config.get("mistral_endpoint", MISTRAL_OCR_URL)
        self.timeout = float(self.config.get("mistral_timeout", 180))
        self._post: Poster = poster or _urllib_post

    def convert(self, data: bytes) -> str:
        if not self.api_key:
            raise MistralOcrError(
                "Mistral OCR backend needs an API key: pass pdf_plus_mistral_api_key or set MISTRAL_API_KEY."
            )
        resp = self._post(self.endpoint, self._payload(data), self._headers(), self.timeout)
        return self._assemble(resp)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _payload(self, data: bytes) -> dict[str, Any]:
        b64 = base64.b64encode(data).decode()
        return {
            "model": self.model,
            "document": {"type": "document_url", "document_url": f"data:application/pdf;base64,{b64}"},
            "include_image_base64": bool(self.image_dir),
        }

    def _assemble(self, resp: dict[str, Any]) -> str:
        pages = resp.get("pages") or []
        parts: list[str] = []
        for page in pages:
            md = page.get("markdown") or ""
            if self.image_dir:
                md = self._save_images(page, md)
            if md.strip():
                parts.append(md)
        return "\n\n".join(parts).strip()

    def _save_images(self, page: dict[str, Any], md: str) -> str:
        """Persist returned image bytes and rewrite their Markdown references to local paths."""
        images = page.get("images") or []
        if not images or not self.image_dir:
            return md
        os.makedirs(self.image_dir, exist_ok=True)
        for img in images:
            img_id = img.get("id")
            b64 = img.get("image_base64")
            if not img_id or not b64:
                continue
            if "," in b64 and b64.strip().startswith("data:"):
                b64 = b64.split(",", 1)[1]
            try:
                raw = base64.b64decode(b64)
            except (ValueError, TypeError) as e:  # malformed image -> skip, keep the doc
                logger.warning("Mistral image %s decode failed: %s", img_id, e)
                continue
            path = os.path.join(self.image_dir, img_id)
            with open(path, "wb") as fh:
                fh.write(raw)
            md = md.replace(f"]({img_id})", f"]({path})")
        return md
