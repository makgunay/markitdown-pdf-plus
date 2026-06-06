from typing import List
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTTextLine, LTChar
from ._model import Line


class TextExtractor:
    """Per-line text + font size + bbox via pdfminer (clean word spacing).

    pdfminer (not pdfplumber.extract_words) because on justified/kerned PDFs
    pdfplumber merges words and loses spaces; pdfminer's layout analysis keeps
    spacing. pdfminer uses a bottom-left origin, so y is converted to a top-left
    'top' to match the pdfplumber bboxes used by table/figure detection.
    """

    def extract(self, file_stream) -> List[Line]:
        out: List[Line] = []
        for page_index, layout in enumerate(extract_pages(file_stream)):
            page_height = layout.height
            for element in layout:
                if not isinstance(element, LTTextContainer):
                    continue
                for line in element:
                    if not isinstance(line, LTTextLine):
                        continue
                    text = line.get_text().strip()
                    if not text:
                        continue
                    chars = [c for c in line if isinstance(c, LTChar)]
                    if not chars:
                        continue
                    sizes = sorted(c.size for c in chars)
                    size = sizes[len(sizes) // 2]
                    bold = sum(1 for c in chars if "Bold" in (c.fontname or "")) > len(chars) / 2
                    x0 = min(c.x0 for c in chars)
                    x1 = max(c.x1 for c in chars)
                    y0 = min(c.y0 for c in chars)
                    y1 = max(c.y1 for c in chars)
                    out.append(Line(page=page_index, text=text, font_size=round(size, 1),
                                    bold=bold, bbox=(x0, page_height - y1, x1, page_height - y0)))
        return out
