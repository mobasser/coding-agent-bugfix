import difflib
import shutil
import subprocess
from pathlib import Path

IGNORED_DIRS = {"__pycache__", ".pytest_cache"}


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def ensure_clean_baseline(repo: Path) -> None:
    _git(repo, "rev-parse", "--verify", "HEAD")
    if _git(repo, "status", "--porcelain", "--", ".").strip():
        raise RuntimeError("commit the repo baseline first; it must have no uncommitted changes")


def changed_files(original: Path, workspace: Path) -> list[str]:
    changed = []
    for f in sorted(p for p in workspace.rglob("*") if p.is_file()):
        rel = f.relative_to(workspace)
        if IGNORED_DIRS & set(rel.parts):
            continue
        orig = original / rel
        if not orig.exists() or orig.read_bytes() != f.read_bytes():
            changed.append(rel.as_posix())
    return changed


def diff_text(original: Path, workspace: Path, files: list[str]) -> str:
    out = []
    for rel in files:
        a = (original / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        b = (workspace / rel).read_text(encoding="utf-8").splitlines(keepends=True)
        out.extend(difflib.unified_diff(a, b, f"a/{rel}", f"b/{rel}"))
    return "".join(out)


def apply_fix(repo: Path, workspace: Path, files: list[str], branch: str, message: str) -> str:
    _git(repo, "checkout", "-b", branch)
    for rel in files:
        shutil.copyfile(workspace / rel, repo / rel)
    _git(repo, "add", "--", *files)
    _git(repo, "commit", "-m", message, "--", *files)
    return branch
