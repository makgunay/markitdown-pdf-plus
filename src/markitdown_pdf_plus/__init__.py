"""markitdown-pdf-plus: enhanced PDF converter plugin for MarkItDown."""

from typing import Any

__plugin_interface_version__ = 1


def register_converters(markitdown: Any, **kwargs: Any) -> None:
    """Entry point called by MarkItDown when plugins are enabled."""
    from ._converter import PdfPlusConverter
    from ._vlm import build_vlm_service

    vlm = build_vlm_service(**kwargs)
    config = {
        "backend": kwargs.get("pdf_plus_backend", "local"),
        "full_page": kwargs.get("pdf_plus_full_page", False),
        "image_dir": kwargs.get("pdf_plus_image_dir"),
        "dpi": kwargs.get("pdf_plus_dpi", 200),
        "table_fallback": kwargs.get("pdf_plus_table_fallback", True),
        "concurrency": kwargs.get("pdf_plus_concurrency", 4),
        # Mistral OCR backend (used only when backend == "mistral_ocr").
        "mistral_api_key": kwargs.get("pdf_plus_mistral_api_key"),
        "mistral_model": kwargs.get("pdf_plus_mistral_model", "mistral-ocr-4-0"),
        # PaddleOCR-VL backend (used only when backend == "paddleocr_vl").
        "paddleocr_prompt": kwargs.get("pdf_plus_paddleocr_prompt"),
    }
    markitdown.register_converter(PdfPlusConverter(vlm, config), priority=-1.0)
