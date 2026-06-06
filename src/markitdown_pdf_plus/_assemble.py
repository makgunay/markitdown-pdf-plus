from typing import List
from ._model import Block


class MarkdownAssembler:
    def assemble(self, blocks: List[Block]) -> str:
        ordered = sorted(blocks, key=lambda b: (b.page, b.top, b.x0))
        parts: List[str] = []
        for b in ordered:
            parts.append(self._render(b))
        return "\n\n".join(p for p in parts if p.strip())

    def _render(self, b: Block) -> str:
        if b.kind == "heading":
            return "#" * max(1, b.level) + " " + b.text
        if b.kind == "table":
            return b.markdown.strip()
        if b.kind == "figure":
            return f"![{b.caption or ''}]({b.image_path or ''})"
        return b.text  # paragraph
