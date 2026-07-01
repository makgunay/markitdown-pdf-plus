from types import SimpleNamespace

from tests.eval.judge import judge_tables, score_table


class _FakeClient:
    def __init__(self, content=None, exc=None):
        self._content = content
        self._exc = exc
        self.seen = {}

    @property
    def chat(self):
        client = self

        class _Completions:
            @staticmethod
            def create(**kwargs):
                if client._exc:
                    raise client._exc
                client.seen = kwargs
                msg = SimpleNamespace(content=client._content)
                return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

        return SimpleNamespace(completions=_Completions)


def test_parses_plain_json():
    client = _FakeClient('{"score": 87, "issues": ["minor"]}')
    result = score_table(client, "m", "B64", "| a | b |")
    assert result["score"] == 87
    assert result["issues"] == ["minor"]


def test_strips_code_fences():
    client = _FakeClient('```json\n{"score": 50, "issues": []}\n```')
    assert score_table(client, "m", "B64", "md")["score"] == 50


def test_float_score_coerced_to_int():
    client = _FakeClient('{"score": 72.0}')
    result = score_table(client, "m", "B64", "md")
    assert result["score"] == 72
    assert result["issues"] == []


def test_unparseable_response_is_fail_soft():
    assert score_table(_FakeClient("I cannot tell"), "m", "B64", "md")["score"] is None


def test_missing_score_field_is_none():
    assert score_table(_FakeClient('{"issues": ["x"]}'), "m", "B64", "md")["score"] is None


def test_client_exception_is_fail_soft():
    result = score_table(_FakeClient(exc=RuntimeError("network")), "m", "B64", "md")
    assert result["score"] is None
    assert "network" in result["issues"][0]


def test_image_and_prompt_are_sent():
    client = _FakeClient('{"score": 100}')
    score_table(client, "model-x", "ABC123", "PREDICTED")
    content = client.seen["messages"][0]["content"]
    assert content[0]["image_url"]["url"].endswith("ABC123")
    assert "PREDICTED" in content[1]["text"]
    assert client.seen["temperature"] == 0


def test_judge_tables_means_valid_scores():
    client = _FakeClient('{"score": 80}')
    result = judge_tables(client, "m", [("img1", "t1"), ("img2", "t2")])
    assert result["judge_mean"] == 80.0
    assert result["n_judged"] == 2


def test_judge_tables_empty_is_none():
    client = _FakeClient('{"score": 80}')
    result = judge_tables(client, "m", [])
    assert result["judge_mean"] is None
    assert result["n_judged"] == 0
