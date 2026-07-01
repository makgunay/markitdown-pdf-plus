import base64
import io
import json
import urllib.error
import urllib.request

import pytest

from markitdown_pdf_plus._backends import build_backend
from markitdown_pdf_plus._mistral import MistralOcrBackend, MistralOcrError, _urllib_post


def _canned(*pages):
    return lambda url, payload, headers, timeout: {"pages": list(pages)}


def test_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    backend = MistralOcrBackend({}, poster=_canned())
    with pytest.raises(MistralOcrError):
        backend.convert(b"%PDF-1.4")


def test_assembles_pages_in_order():
    backend = MistralOcrBackend(
        {"mistral_api_key": "k"},
        poster=_canned({"markdown": "# Page 1"}, {"markdown": "## Page 2"}, {"markdown": ""}),
    )
    md = backend.convert(b"%PDF-1.4")
    assert md == "# Page 1\n\n## Page 2"  # empty page dropped, order preserved


def test_payload_carries_model_and_base64_pdf():
    seen = {}

    def poster(url, payload, headers, timeout):
        seen["url"] = url
        seen["payload"] = payload
        seen["headers"] = headers
        return {"pages": [{"markdown": "ok"}]}

    backend = MistralOcrBackend(
        {"mistral_api_key": "secret", "mistral_model": "mistral-ocr-4-0"}, poster=poster
    )
    backend.convert(b"%PDF-bytes")

    assert seen["payload"]["model"] == "mistral-ocr-4-0"
    doc_url = seen["payload"]["document"]["document_url"]
    assert doc_url.startswith("data:application/pdf;base64,")
    assert base64.b64decode(doc_url.split(",", 1)[1]) == b"%PDF-bytes"
    assert seen["headers"]["Authorization"] == "Bearer secret"


def test_saves_images_and_rewrites_refs(tmp_path):
    png = base64.b64encode(b"\x89PNG\r\n").decode()
    page = {"markdown": "see ![img-0.png](img-0.png)", "images": [{"id": "img-0.png", "image_base64": png}]}
    backend = MistralOcrBackend({"mistral_api_key": "k", "image_dir": str(tmp_path)}, poster=_canned(page))
    md = backend.convert(b"%PDF")
    saved = tmp_path / "img-0.png"
    assert saved.exists() and saved.read_bytes() == b"\x89PNG\r\n"
    assert f"]({saved})" in md  # reference rewritten to the local path


def test_build_backend_selects_mistral():
    backend = build_backend(None, {"backend": "mistral_ocr", "mistral_api_key": "k"})
    assert isinstance(backend, MistralOcrBackend)


def test_unknown_backend_raises():
    with pytest.raises(ValueError, match="unknown pdf_plus_backend"):
        build_backend(None, {"backend": "nope"})


def test_save_images_handles_data_uri_and_skips_incomplete(tmp_path):
    good = "data:image/png;base64," + base64.b64encode(b"PNGDATA").decode()
    page = {
        "markdown": "![a](a.png) ![b](b.png)",
        "images": [{"id": "a.png", "image_base64": good}, {"id": "b.png"}],  # b has no bytes -> skipped
    }
    backend = MistralOcrBackend({"mistral_api_key": "k", "image_dir": str(tmp_path)}, poster=_canned(page))
    md = backend.convert(b"%PDF")
    assert (tmp_path / "a.png").read_bytes() == b"PNGDATA"
    assert not (tmp_path / "b.png").exists()
    assert f"]({tmp_path / 'a.png'})" in md and "](b.png)" in md


def test_urllib_post_success(monkeypatch):
    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"pages": [{"markdown": "ok"}]}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=0: FakeResp())
    assert _urllib_post("https://x/v1/ocr", {"a": 1}, {"H": "v"}, 1.0) == {"pages": [{"markdown": "ok"}]}


def test_urllib_post_http_error_wrapped(monkeypatch):
    def boom(req, timeout=0):
        raise urllib.error.HTTPError("https://x", 401, "Unauthorized", {}, io.BytesIO(b"bad key"))

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    with pytest.raises(MistralOcrError, match="401"):
        _urllib_post("https://x/v1/ocr", {}, {}, 1.0)
