from typing import List
from ._model import BBox


class TableDetector:
    def detect(self, page) -> List[BBox]:
        return [tuple(t.bbox) for t in page.find_tables()]

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
