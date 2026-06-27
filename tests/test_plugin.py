from markitdown import MarkItDown

from markitdown_pdf_plus._converter import PdfPlusConverter


def test_plugin_registers_and_overrides_builtin_pdf():
    md = MarkItDown(enable_builtins=True, enable_plugins=True)
    # our converter must be registered and appear before the built-in PDF converter
    convs = [r.converter for r in md._converters]
    assert any(isinstance(c, PdfPlusConverter) for c in convs)


def test_end_to_end_via_markitdown(headings_pdf_bytes, tmp_path):
    p = tmp_path / "h.pdf"
    p.write_bytes(headings_pdf_bytes)
    md = MarkItDown(enable_builtins=True, enable_plugins=True)
    result = md.convert(str(p))
    assert "# 1 Introduction" in result.markdown
