from pathlib import Path

import pytest

from agent.tools import Tools


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "mod.py").write_text("def f(x):\n    return x + 1\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text("def test_f():\n    assert True\n", encoding="utf-8")
    return tmp_path


def fake_runner(calls, exit_code=0, output="1 passed"):
    def run(workspace, test_path=None):
        calls.append((Path(workspace), test_path))
        return exit_code, output
    return run


def test_read_file_numbers_selected_lines(repo):
    out = Tools(repo).read_file("src/mod.py", 2, 2)
    assert out == "2:     return x + 1"


def test_edit_file_replaces_unique_match(repo):
    Tools(repo).edit_file("src/mod.py", "x + 1", "x + 2")
    assert "return x + 2" in (repo / "src" / "mod.py").read_text(encoding="utf-8")


def test_edit_file_rejects_missing_or_ambiguous_match(repo):
    tools = Tools(repo)
    assert tools.call("edit_file", {"path": "src/mod.py", "old": "nothing", "new": "x"}).startswith("ERROR: old text must match exactly once, found 0")
    (repo / "src" / "dup.py").write_text("a\na\n", encoding="utf-8")
    assert "found 2 matches" in tools.call("edit_file", {"path": "src/dup.py", "old": "a", "new": "b"})


def test_edit_file_blocks_test_files(repo):
    out = Tools(repo).call("edit_file", {"path": "tests/test_mod.py", "old": "True", "new": "False"})
    assert out == "ERROR: editing test files is not allowed"
    assert "assert True" in (repo / "tests" / "test_mod.py").read_text(encoding="utf-8")


def test_paths_cannot_escape_repo(repo):
    out = Tools(repo).call("read_file", {"path": "../secret.txt"})
    assert out.startswith("ERROR: path is outside the repo")


def test_search_code_finds_matches_and_skips_venv(repo):
    (repo / ".venv").mkdir()
    (repo / ".venv" / "x.py").write_text("return x + 1\n", encoding="utf-8")
    out = Tools(repo).search_code(r"x \+ 1")
    assert out == "src/mod.py:2: return x + 1"


def test_search_code_reports_invalid_regex(repo):
    assert Tools(repo).call("search_code", {"pattern": "("}).startswith("ERROR: invalid regex")


def test_run_tests_uses_runner_and_reports_exit_code(repo):
    calls = []
    out = Tools(repo, runner=fake_runner(calls, exit_code=1, output="1 failed")).run_tests("tests/test_mod.py")
    assert calls == [(repo.resolve(), "tests/test_mod.py")]
    assert out == "exit_code: 1\n1 failed"


def test_run_tests_rejects_path_outside_repo(repo):
    calls = []
    out = Tools(repo, runner=fake_runner(calls)).call("run_tests", {"test_path": "../../x.py"})
    assert out.startswith("ERROR: path is outside the repo")
    assert calls == []


def test_finish_records_summary(repo):
    tools = Tools(repo)
    assert tools.call("finish", {"summary": "fixed off-by-one"}) == "finished"
    assert tools.finished_summary == "fixed off-by-one"


def test_unknown_tool_and_bad_arguments_return_errors(repo):
    tools = Tools(repo)
    assert tools.call("delete_repo", {}) == "ERROR: unknown tool delete_repo"
    assert tools.call("read_file", {"wrong": "x"}).startswith("ERROR:")
    assert tools.call("read_file", {"path": "missing.py"}).startswith("ERROR:")
