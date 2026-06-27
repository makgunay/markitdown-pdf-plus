"""markitdown-pdf-plus: enhanced PDF converter plugin for MarkItDown."""

from typing import Any

__plugin_interface_version__ = 1


def register_converters(markitdown: Any, **kwargs: Any) -> None:
    """Entry point called by MarkItDown when plugins are enabled."""
    from ._converter import PdfPlusConverter
    from ._vlm import build_vlm_service

    vlm = build_vlm_service(**kwargs)
    config = {
        "full_page": kwargs.get("pdf_plus_full_page", False),
        "image_dir": kwargs.get("pdf_plus_image_dir"),
        "dpi": kwargs.get("pdf_plus_dpi", 200),
        "table_fallback": kwargs.get("pdf_plus_table_fallback", True),
    }
    markitdown.register_converter(PdfPlusConverter(vlm, config), priority=-1.0)
