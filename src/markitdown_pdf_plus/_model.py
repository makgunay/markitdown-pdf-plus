from dataclasses import dataclass

BBox = tuple[float, float, float, float]  # (x0, top, x1, bottom), PDF points


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
    image_path: str | None = None
    caption: str | None = None
    bbox: BBox | None = None
    cols: int = 0
