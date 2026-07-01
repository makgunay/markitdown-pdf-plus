from typing import Any, BinaryIO

from markitdown import DocumentConverter, DocumentConverterResult, StreamInfo

from ._backends import build_backend


class PdfPlusConverter(DocumentConverter):
    """Thin MarkItDown converter: accepts PDFs and delegates to a selectable backend."""

    def __init__(self, vlm: Any, config: dict[str, Any]):
        self.vlm = vlm
        self.config = config or {}
        self.backend = build_backend(vlm, self.config)

    def accepts(self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any) -> bool:
        ext = (stream_info.extension or "").lower()
        mime = (stream_info.mimetype or "").lower()
        return ext == ".pdf" or mime.startswith("application/pdf") or mime.startswith("application/x-pdf")

    def convert(
        self, file_stream: BinaryIO, stream_info: StreamInfo, **kwargs: Any
    ) -> DocumentConverterResult:
        data = file_stream.read()
        return DocumentConverterResult(markdown=self.backend.convert(data))
