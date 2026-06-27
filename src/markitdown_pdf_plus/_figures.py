import base64
import io
import os
from typing import Any

import pypdfium2 as pdfium

from ._model import BBox, Block


def _render_page_pil(pdf_bytes: bytes, page_index: int, dpi: int) -> tuple[Any, float, float]:
    pdf = pdfium.PdfDocument(pdf_bytes)
    page = pdf[page_index]
    scale = dpi / 72.0
    pil = page.render(scale=scale).to_pil()
    return pil, scale, float(page.get_size()[1])  # (image, scale, page_height_pts)


def render_bbox_png_b64(pdf_bytes: bytes, page_index: int, bbox: BBox, dpi: int = 200) -> str:
    pil, scale, _ = _render_page_pil(pdf_bytes, page_index, dpi)
    x0, top, x1, bottom = bbox
    crop = pil.crop((int(x0 * scale), int(top * scale), int(x1 * scale), int(bottom * scale)))
    out = io.BytesIO()
    crop.save(out, format="PNG")
    return base64.b64encode(out.getvalue()).decode()


class FigureExtractor:
    def __init__(self, image_dir: str | None, dpi: int = 200):
        self.image_dir = image_dir
        self.dpi = dpi

    def extract(self, page: Any, page_index: int, pdf_bytes: bytes) -> list[Block]:
        blocks: list[Block] = []
        pil, scale, _ = _render_page_pil(pdf_bytes, page_index, self.dpi)
        for i, img in enumerate(page.images):
            bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
            image_path = None
            if self.image_dir:
                os.makedirs(self.image_dir, exist_ok=True)
                name = f"page{page_index}_fig{i}.png"
                crop = pil.crop(
                    (int(bbox[0] * scale), int(bbox[1] * scale), int(bbox[2] * scale), int(bbox[3] * scale))
                )
                crop.save(os.path.join(self.image_dir, name))
                image_path = os.path.join(self.image_dir, name)
            blocks.append(
                Block(
                    kind="figure", page=page_index, top=bbox[1], x0=bbox[0], bbox=bbox, image_path=image_path
                )
            )
        return blocks
