from typing import List
from ._model import BBox

_TEXT_SETTINGS = {"vertical_strategy": "text", "horizontal_strategy": "text"}


def _overlaps(a: BBox, b: BBox) -> bool:
    ax0, at0, ax1, ab0 = a
    bx0, bt0, bx1, bb0 = b
    return not (ax1 <= bx0 or bx1 <= ax0 or ab0 <= bt0 or bb0 <= at0)


class TableDetector:
    def detect(self, page) -> List[BBox]:
        found: List[BBox] = [tuple(t.bbox) for t in page.find_tables()]  # ruled tables
        for t in page.find_tables(_TEXT_SETTINGS):  # borderless / text-aligned
            bbox = tuple(t.bbox)
            if any(_overlaps(bbox, f) for f in found):
                continue
            if self._looks_like_table(t):
                found.append(bbox)
        return found

    @staticmethod
    def _looks_like_table(table) -> bool:
        rows = [r for r in table.extract() if any((c or "").strip() for c in r)]
        if len(rows) < 3:
            return False
        if max((len(r) for r in rows), default=0) < 2:
            return False
        cells = [str(c).strip() for r in rows for c in r if c and str(c).strip()]
        if not cells:
            return False
        long = sum(1 for c in cells if len(c) > 40)
        return long / len(cells) <= 0.3

    def extract_grid_markdown(self, page, bbox: BBox) -> str:
        """Fallback markdown when no VLM: pdfplumber's own extraction for the region."""
        cropped = page.crop(bbox)
        tables = cropped.extract_tables()
        if not tables or not tables[0]:
            return ""
        rows = [[c if c is not None else "" for c in row] for row in tables[0]]
        rows = [r for r in rows if any(str(c).strip() for c in r)]
        if not rows:
            return ""
        header = "| " + " | ".join(str(c) for c in rows[0]) + " |"
        sep = "| " + " | ".join("---" for _ in rows[0]) + " |"
        body = ["| " + " | ".join(str(c) for c in r) + " |" for r in rows[1:]]
        return "\n".join([header, sep, *body])
