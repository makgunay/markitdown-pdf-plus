from dataclasses import dataclass
from typing import Optional, Tuple

BBox = Tuple[float, float, float, float]  # (x0, top, x1, bottom), PDF points


@dataclass
class Line:
    page: int
    text: str
    font_size: float
    bold: bool
    bbox: BBox


@dataclass
class Block:
    kind: str  # "heading" | "paragraph" | "table" | "figure"
    page: int
    top: float
    x0: float = 0.0
    text: str = ""
    level: int = 0
    markdown: str = ""
    image_path: Optional[str] = None
    caption: Optional[str] = None
    bbox: Optional[BBox] = None
    cols: int = 0
