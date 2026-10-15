import subprocess
from unittest.mock import patch

import pytest

from agent import sandbox


def test_create_workspace_copies_repo_without_caches(tmp_path):
    src = tmp_path / "repo"
    (src / "src").mkdir(parents=True)
    (src / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (src / "__pycache__").mkdir()
    (src / "__pycache__" / "a.pyc").write_bytes(b"")
    dest = sandbox.create_workspace(src)
    assert (dest / "src" / "a.py").read_text(encoding="utf-8") == "x = 1\n"
    assert not (dest / "__pycache__").exists()
    assert dest != src


def test_run_pytest_uses_docker_without_network(tmp_path):
    completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="1 passed", stderr="")
    with patch("agent.sandbox.subprocess.run", return_value=completed) as run:
        code, output = sandbox.run_pytest(tmp_path, "tests/test_x.py")
    cmd = run.call_args.args[0]
    assert cmd[:2] == ["docker", "run"]
    assert "--network" in cmd and cmd[cmd.index("--network") + 1] == "none"
    assert f"{tmp_path.resolve()}:/repo" in cmd
    assert cmd[-1] == "tests/test_x.py"
    assert (code, output) == (0, "1 passed")


def test_run_pytest_reports_timeout(tmp_path):
    with patch("agent.sandbox.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=5)):
        code, output = sandbox.run_pytest(tmp_path, timeout=5)
    assert code == 124
    assert "timed out after 5s" in output


def test_run_pytest_local_reports_pass_and_fail(tmp_path):
    (tmp_path / "test_ok.py").write_text("def test_ok():\n    assert 1 + 1 == 2\n", encoding="utf-8")
    assert sandbox.run_pytest_local(tmp_path)[0] == 0
    (tmp_path / "test_bad.py").write_text("def test_bad():\n    assert False\n", encoding="utf-8")
    code, output = sandbox.run_pytest_local(tmp_path, "test_bad.py")
    assert code == 1
    assert "1 failed" in output


PYTEST_OUTPUT = (
    "FAILED tests/test_a.py::test_target - AssertionError\n"
    "FAILED tests/test_b.py::test_old - assert 1 == 2\n"
)


def test_failed_tests_parses_summary_lines():
    assert sandbox.failed_tests(PYTEST_OUTPUT) == {"tests/test_a.py::test_target", "tests/test_b.py::test_old"}


def test_is_fixed_requires_target_pass_and_no_new_failures():
    baseline = {"tests/test_a.py::test_target", "tests/test_b.py::test_old"}
    assert sandbox.is_fixed(1, "tests/test_a.py::test_target", baseline, "FAILED tests/test_b.py::test_old - x")
    assert not sandbox.is_fixed(1, "tests/test_a.py::test_target", baseline, PYTEST_OUTPUT)
    assert not sandbox.is_fixed(1, "tests/test_a.py::test_target", {"tests/test_b.py::test_old"}, "FAILED tests/test_c.py::test_new - x")


def test_is_fixed_rejects_collection_errors():
    assert not sandbox.is_fixed(2, "tests/test_a.py::test_target", set(), "")
    assert not sandbox.is_fixed(124, "tests/test_a.py::test_target", set(), "tests timed out")


def test_run_pytest_fails_clearly_without_docker(tmp_path):
    with patch("agent.sandbox.subprocess.run", side_effect=FileNotFoundError("docker")):
        with pytest.raises(RuntimeError, match="Docker is not installed"):
            sandbox.run_pytest(tmp_path)
