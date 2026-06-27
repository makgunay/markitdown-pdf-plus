"""Vulture whitelist: names that are used by MarkItDown via its plugin/converter
contract rather than from within this package, so static analysis can't see the
call sites. Referencing them here marks them as used.
"""

from markitdown_pdf_plus import register_converters  # plugin entry point
from markitdown_pdf_plus._converter import PdfPlusConverter

register_converters  # called by MarkItDown when enable_plugins=True
PdfPlusConverter.accepts  # DocumentConverter interface, called by MarkItDown
PdfPlusConverter.convert  # DocumentConverter interface, called by MarkItDown
