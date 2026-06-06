import re
from collections import Counter
from typing import List

from ._model import Line, Block

_NUMBERED = re.compile(r"^\d+(\.\d+)*\.?\s+\S")


def body_font_size(lines: List[Line]) -> float:
    sizes = Counter(round(ln.font_size, 1) for ln in lines if ln.text.strip())
    return sizes.most_common(1)[0][0] if sizes else 12.0


def heading_level(line: Line, body: float) -> int:
    """Return heading level 1-3, or 0 if not a heading."""
    size = round(line.font_size, 1)
    short = len(line.text) < 80 and not line.text.rstrip().endswith(".")
    if size >= body + 3:
        return 1 if short else 0
    if size >= body + 1.5:
        return 2 if short else 0
    if size >= body + 0.6:
        return 3 if short else 0
    # same size: promote only short bold lines, or numbered short lines
    if short and (line.bold or _NUMBERED.match(line.text.strip())):
        return 2
    return 0


class HeadingAnnotator:
    def annotate(self, lines: List[Line]) -> List[Block]:
        body = body_font_size(lines)
        blocks: List[Block] = []
        for ln in lines:
            if not ln.text.strip():
                continue
            lvl = heading_level(ln, body)
            if lvl:
                blocks.append(Block(kind="heading", page=ln.page, top=ln.bbox[1],
                                    x0=ln.bbox[0], text=ln.text.strip(), level=lvl))
            else:
                blocks.append(Block(kind="paragraph", page=ln.page, top=ln.bbox[1],
                                    x0=ln.bbox[0], text=ln.text.strip()))
        return blocks
