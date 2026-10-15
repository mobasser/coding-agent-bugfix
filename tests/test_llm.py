from types import SimpleNamespace

import pytest

from agent.llm import OpenAIChat, call_cost


def fake_response(content=None, tool_calls=None, prompt=1000, cached=0, completion=100):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    usage = SimpleNamespace(prompt_tokens=prompt, completion_tokens=completion,
                            prompt_tokens_details=SimpleNamespace(cached_tokens=cached))
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)], usage=usage)


class FakeClient:
    def __init__(self, response):
        self.response = response
        self.kwargs = None
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def test_call_cost_separates_cached_input():
    usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=100,
                            prompt_tokens_details=SimpleNamespace(cached_tokens=400))
    expected = (600 * 0.05 + 400 * 0.005 + 100 * 0.40) / 1_000_000
    assert call_cost("gpt-5-nano", usage) == pytest.approx(expected)


def test_call_cost_rejects_unpriced_model():
    usage = SimpleNamespace(prompt_tokens=1, completion_tokens=1, prompt_tokens_details=None)
    with pytest.raises(ValueError, match="no price configured"):
        call_cost("unknown-model", usage)


def test_complete_parses_tool_calls_and_cost():
    tc = SimpleNamespace(id="call_1", function=SimpleNamespace(name="read_file", arguments='{"path": "a.py"}'))
    client = FakeClient(fake_response(tool_calls=[tc]))
    reply = OpenAIChat("gpt-5-nano", client=client).complete([{"role": "user", "content": "hi"}], [])
    assert client.kwargs["model"] == "gpt-5-nano"
    assert reply.tool_calls == [{"id": "call_1", "name": "read_file", "arguments": '{"path": "a.py"}'}]
    assert reply.cost_usd > 0


def test_complete_returns_plain_text_reply():
    client = FakeClient(fake_response(content="done", tool_calls=None))
    reply = OpenAIChat("gpt-5-nano", client=client).complete([], [])
    assert reply.content == "done"
    assert reply.tool_calls == []
