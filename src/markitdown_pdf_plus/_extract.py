from typing import List
import pdfplumber
from ._model import Line


class TextExtractor:
    """Extract per-line text + font size + bbox via pdfplumber words (clean spacing)."""

    def __init__(self, y_tolerance: float = 3.0):
        self.y_tolerance = y_tolerance

    def extract(self, file_stream) -> List[Line]:
        out: List[Line] = []
        with pdfplumber.open(file_stream) as pdf:
            for page_index, page in enumerate(pdf.pages):
                words = page.extract_words(
                    extra_attrs=["size", "fontname"], use_text_flow=True
                )
                out.extend(self._group_lines(words, page_index))
        return out

    def _group_lines(self, words, page_index) -> List[Line]:
        rows = {}
        for w in words:
            key = round(w["top"] / self.y_tolerance) * self.y_tolerance
            rows.setdefault(key, []).append(w)
        lines = []
        for key in sorted(rows):
            ws = sorted(rows[key], key=lambda w: w["x0"])
            text = " ".join(w["text"] for w in ws).strip()
            if not text:
                continue
            sizes = [float(w.get("size", 0.0)) for w in ws]
            size = max(sizes) if sizes else 0.0
            bold = any("Bold" in (w.get("fontname") or "") for w in ws)
            bbox = (ws[0]["x0"], min(w["top"] for w in ws),
                    ws[-1]["x1"], max(w["bottom"] for w in ws))
            lines.append(Line(page=page_index, text=text, font_size=size, bold=bold, bbox=bbox))
        return lines
