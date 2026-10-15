import json
from pathlib import Path

import pytest

from agent.agent import run_agent
from agent.guards import Budget
from agent.llm import Reply
from agent.tools import Tools

BUG = {"id": "bug_01", "description": "count is wrong", "expected_test": "tests/test_x.py::test_y"}


class ScriptedLLM:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete(self, messages, tools):
        self.calls += 1
        return self.replies.pop(0)


def reply(tool_calls=(), content=None, cost=0.0):
    return Reply(content, list(tool_calls), cost)


def call(name, args, call_id="c1"):
    return {"id": call_id, "name": name, "arguments": json.dumps(args)}


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    return tmp_path


def passing_runner(workspace, test_path=None):
    return 0, "1 passed"


def test_stops_when_finish_is_called(repo):
    llm = ScriptedLLM([
        reply([call("edit_file", {"path": "mod.py", "old": "return 1", "new": "return 2"})], cost=0.01),
        reply([call("finish", {"summary": "changed return value"}, "c2")], cost=0.01),
    ])
    result = run_agent(BUG, Tools(repo, runner=passing_runner), llm, Budget())
    assert result.status == "finished"
    assert result.summary == "changed return value"
    assert result.steps == 2
    assert result.cost_usd == pytest.approx(0.02)
    assert "return 2" in (repo / "mod.py").read_text(encoding="utf-8")


def test_stops_when_target_test_passes(repo):
    llm = ScriptedLLM([reply([call("run_tests", {"test_path": "tests/test_x.py::test_y"})])])
    result = run_agent(BUG, Tools(repo, runner=passing_runner), llm, Budget())
    assert result.status == "tests_passed"
    assert result.steps == 1


def test_other_test_pass_does_not_stop_the_run(repo):
    llm = ScriptedLLM([
        reply([call("run_tests", {"test_path": "tests/test_other.py"})]),
        reply([call("finish", {"summary": "done"}, "c2")]),
    ])
    result = run_agent(BUG, Tools(repo, runner=passing_runner), llm, Budget())
    assert result.status == "finished"


def test_stops_when_step_budget_runs_out(repo):
    llm = ScriptedLLM([reply([call("search_code", {"pattern": "return"})])] * 5)
    result = run_agent(BUG, Tools(repo), llm, Budget(max_steps=2))
    assert result.status == "budget_exhausted"
    assert result.steps == 2
    assert llm.calls == 2


def test_stops_when_cost_budget_runs_out(repo):
    llm = ScriptedLLM([reply([call("search_code", {"pattern": "return"})], cost=0.30)] * 5)
    result = run_agent(BUG, Tools(repo), llm, Budget(max_cost_usd=0.50))
    assert result.status == "budget_exhausted"
    assert llm.calls == 2


def test_model_without_tool_call_ends_run(repo):
    llm = ScriptedLLM([reply(content="I think it is fixed")])
    result = run_agent(BUG, Tools(repo), llm, Budget())
    assert result.status == "no_tool_call"
    assert result.detail == "I think it is fixed"


def test_invalid_json_arguments_go_back_to_model(repo):
    bad = {"id": "c1", "name": "read_file", "arguments": "{bad"}
    llm = ScriptedLLM([reply([bad]), reply([call("finish", {"summary": "ok"}, "c2")])])
    result = run_agent(BUG, Tools(repo), llm, Budget())
    assert result.trace[0]["result"] == "ERROR: arguments are not valid JSON"
    assert result.status == "finished"


def test_trace_is_written_as_jsonl(repo, tmp_path):
    trace = tmp_path / "traces" / "run.jsonl"
    llm = ScriptedLLM([
        reply([call("read_file", {"path": "mod.py"})]),
        reply([call("finish", {"summary": "done"}, "c2")]),
    ])
    run_agent(BUG, Tools(repo), llm, Budget(), trace)
    lines = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert [e["tool"] for e in lines] == ["read_file", "finish"]
    assert lines[0]["step"] == 1
    assert "return 1" in lines[0]["result"]
