import logging
import re
from typing import Any, cast

logger = logging.getLogger(__name__)

DEFAULT_TABLE_PROMPT = (
    "Convert this table image to a GitHub-flavored Markdown pipe table. Preserve every "
    "row label, column header, numeric value, parenthesized standard error, and significance "
    "marker exactly. Output only the table."
)
DEFAULT_CAPTION_PROMPT = (
    "Describe this figure for someone who can't see it: chart type, axes, series, and the "
    "main trend in 1-3 sentences. If it shows discrete values, add a small Markdown table."
)


def _strip_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```[a-zA-Z]*\s*\n", "", t)
    t = re.sub(r"\n```\s*$", "", t)
    return t.strip()


class VlmService:
    def __init__(
        self,
        client: Any,
        model: str,
        table_prompt: str = DEFAULT_TABLE_PROMPT,
        caption_prompt: str = DEFAULT_CAPTION_PROMPT,
        max_tokens: int = 4096,
    ):
        self.client = client
        self.model = model
        self.table_prompt = table_prompt
        self.caption_prompt = caption_prompt
        self.max_tokens = max_tokens

    def _call(self, b64_png: str, prompt: str) -> str | None:
        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_png}"}},
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=0,
            )
            return cast("str | None", resp.choices[0].message.content)
        except Exception as e:  # noqa: BLE001
            logger.warning("VLM call failed: %s", e)
            return None

    def transcribe_table(self, b64_png: str) -> str | None:
        raw = self._call(b64_png, self.table_prompt)
        if raw is None:
            return None
        md = _strip_fences(raw)
        return md if "|" in md else None

    def caption_figure(self, b64_png: str) -> str | None:
        raw = self._call(b64_png, self.caption_prompt)
        return _strip_fences(raw) if raw else None


def build_vlm_service(**kwargs: Any) -> VlmService | None:
    client = kwargs.get("llm_client")
    model = kwargs.get("llm_model")
    if client is None or model is None:
        return None
    return VlmService(
        client,
        model,
        table_prompt=kwargs.get("pdf_plus_table_prompt", DEFAULT_TABLE_PROMPT),
        caption_prompt=kwargs.get("pdf_plus_caption_prompt", DEFAULT_CAPTION_PROMPT),
        max_tokens=kwargs.get("pdf_plus_max_tokens", 4096),
    )
