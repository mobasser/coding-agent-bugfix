import subprocess

import pytest

from agent import approve


@pytest.fixture
def git_repo(tmp_path, monkeypatch):
    for key, value in {"GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "test@example.com",
                       "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "test@example.com"}.items():
        monkeypatch.setenv(key, value)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "mod.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "base"], cwd=repo, check=True)
    return repo


@pytest.fixture
def workspace(tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "mod.py").write_text("x = 2\n", encoding="utf-8")
    return ws


def test_changed_files_and_diff(git_repo, workspace):
    files = approve.changed_files(git_repo, workspace)
    assert files == ["mod.py"]
    diff = approve.diff_text(git_repo, workspace, files)
    assert "-x = 1" in diff and "+x = 2" in diff


def test_unchanged_workspace_has_no_changes(git_repo, tmp_path):
    ws = tmp_path / "same"
    ws.mkdir()
    (ws / "mod.py").write_text("x = 1\n", encoding="utf-8")
    assert approve.changed_files(git_repo, ws) == []


def test_apply_fix_commits_to_new_branch(git_repo, workspace):
    approve.apply_fix(git_repo, workspace, ["mod.py"], "fix/bug_01", "Fix bug_01")
    branch = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=git_repo, capture_output=True, text=True).stdout.strip()
    assert branch == "fix/bug_01"
    assert (git_repo / "mod.py").read_text(encoding="utf-8") == "x = 2\n"
    log = subprocess.run(["git", "log", "--oneline"], cwd=git_repo, capture_output=True, text=True).stdout
    assert "Fix bug_01" in log


def test_baseline_must_be_clean(git_repo):
    approve.ensure_clean_baseline(git_repo)
    (git_repo / "mod.py").write_text("x = 9\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="commit the repo baseline first"):
        approve.ensure_clean_baseline(git_repo)
