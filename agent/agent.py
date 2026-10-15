import json
from dataclasses import dataclass, field
from pathlib import Path

from .guards import Budget
from .tools import SCHEMAS, Tools

SYSTEM_PROMPT = (
    "You fix one bug in a small Python repo using the tools provided. "
    "Read the failing test and the code it exercises, make the smallest change to a source file, "
    "then run the failing test with run_tests, setting test_path to its id. "
    "Never edit test files. When that test passes, call finish with a short summary."
)


@dataclass
class RunResult:
    status: str
    summary: str | None
    steps: int
    cost_usd: float
    trace: list[dict] = field(default_factory=list)
    detail: str = ""


def run_agent(bug: dict, tools: Tools, llm, budget: Budget, trace_path: Path | None = None) -> RunResult:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Bug {bug['id']}: {bug['description']}\nFailing test: {bug['expected_test']}"},
    ]
    trace: list[dict] = []

    def done(status: str, detail: str = "") -> RunResult:
        return RunResult(status, tools.finished_summary, budget.steps, budget.cost_usd, trace, detail)

    while True:
        if reason := budget.exhausted_reason():
            return done("budget_exhausted", reason)
        budget.charge_step()
        reply = llm.complete(messages, SCHEMAS)
        budget.add_cost(reply.cost_usd)
        if not reply.tool_calls:
            return done("no_tool_call", reply.content or "")
        messages.append({"role": "assistant", "content": reply.content, "tool_calls": [
            {"id": c["id"], "type": "function", "function": {"name": c["name"], "arguments": c["arguments"]}}
            for c in reply.tool_calls]})
        for call in reply.tool_calls:
            result = _run_tool(tools, call)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
            entry = {"step": budget.steps, "tool": call["name"], "args": call["arguments"],
                     "result": result[:1000], "cost_usd": round(budget.cost_usd, 6)}
            trace.append(entry)
            if trace_path:
                _append_jsonl(trace_path, entry)
            if tools.finished_summary is not None:
                return done("finished")
            if _is_target_pass(call, result, bug["expected_test"]):
                return done("tests_passed")


def _run_tool(tools: Tools, call: dict) -> str:
    try:
        args = json.loads(call["arguments"] or "{}")
    except json.JSONDecodeError:
        return "ERROR: arguments are not valid JSON"
    if not isinstance(args, dict):
        return "ERROR: arguments must be a JSON object"
    return tools.call(call["name"], args)


def _is_target_pass(call: dict, result: str, expected_test: str) -> bool:
    if call["name"] != "run_tests" or not result.startswith("exit_code: 0"):
        return False
    return json.loads(call["arguments"] or "{}").get("test_path") == expected_test


def _append_jsonl(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
