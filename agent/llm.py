import os
from dataclasses import dataclass

from openai import OpenAI

DEFAULT_MODEL = "gpt-5-nano"
PRICES_PER_MTOK = {
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-6-sol": (2.00, 0.20, 10.00),
    "gpt-5.6-terra": (2.00, 0.20, 12.00),
}


@dataclass
class Reply:
    content: str | None
    tool_calls: list[dict]
    cost_usd: float


def call_cost(model: str, usage) -> float:
    if model not in PRICES_PER_MTOK:
        raise ValueError(f"no price configured for model {model!r}")
    inp, cached_rate, out = PRICES_PER_MTOK[model]
    cached = getattr(getattr(usage, "prompt_tokens_details", None), "cached_tokens", 0) or 0
    return ((usage.prompt_tokens - cached) * inp + cached * cached_rate + usage.completion_tokens * out) / 1_000_000


class OpenAIChat:
    def __init__(self, model: str | None = None, client=None):
        self.model = model or os.getenv("AGENT_MODEL", DEFAULT_MODEL)
        self.client = client or OpenAI()

    def complete(self, messages: list[dict], tools: list[dict]) -> Reply:
        resp = self.client.chat.completions.create(model=self.model, messages=messages, tools=tools)
        msg = resp.choices[0].message
        calls = [{"id": c.id, "name": c.function.name, "arguments": c.function.arguments} for c in msg.tool_calls or []]
        return Reply(msg.content, calls, call_cost(self.model, resp.usage))
