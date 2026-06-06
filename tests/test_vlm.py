# tests/test_vlm.py
from markitdown_pdf_plus._vlm import VlmService, build_vlm_service


class _Msg:
    def __init__(self, content): self.message = type("M", (), {"content": content})


class _Resp:
    def __init__(self, content): self.choices = [_Msg(content)]


class MockClient:
    def __init__(self, content): self._content = content
    @property
    def chat(self):
        outer = self
        class C:
            class completions:
                @staticmethod
                def create(**kwargs): return _Resp(outer._content)
        return C


def test_no_client_is_noop():
    assert build_vlm_service() is None


def test_transcribe_strips_code_fences():
    svc = VlmService(MockClient("```markdown\n| a | b |\n| - | - |\n| 1 | 2 |\n```"), "m")
    md = svc.transcribe_table("BASE64")
    assert md == "| a | b |\n| - | - |\n| 1 | 2 |"


def test_transcribe_rejects_non_table():
    svc = VlmService(MockClient("I cannot read this image."), "m")
    assert svc.transcribe_table("BASE64") is None


def test_failure_returns_none():
    class Boom:
        @property
        def chat(self): raise RuntimeError("network")
    svc = VlmService(Boom(), "m")
    assert svc.transcribe_table("BASE64") is None
