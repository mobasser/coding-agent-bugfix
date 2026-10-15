import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

IMAGE = "coding-agent-sandbox:latest"
DEFAULT_TIMEOUT = 60
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache")


def create_workspace(source: Path) -> Path:
    """Copy the repo to a temp folder so the agent never edits the original."""
    dest = Path(tempfile.mkdtemp(prefix="bugfix-")) / Path(source).name
    shutil.copytree(source, dest, ignore=IGNORE)
    return dest


def run_pytest(workspace: Path, test_path: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
    """Run pytest inside a Docker container with no network access."""
    cmd = [
        "docker", "run", "--rm",
        "--network", "none", "--memory", "512m", "--cpus", "1",
        "-v", f"{Path(workspace).resolve()}:/repo", "-w", "/repo",
        IMAGE, "python", "-m", "pytest", "-q", "-p", "no:cacheprovider",
        *([test_path] if test_path else []),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise RuntimeError("Docker is not installed or not on PATH") from e
    except subprocess.TimeoutExpired:
        return 124, f"tests timed out after {timeout}s"
    return proc.returncode, proc.stdout + proc.stderr


def run_pytest_local(workspace: Path, test_path: str | None = None, timeout: int = DEFAULT_TIMEOUT) -> tuple[int, str]:
    """Run pytest directly on the host, with no isolation. Use only for trusted repos."""
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *([test_path] if test_path else [])]
    try:
        proc = subprocess.run(cmd, cwd=Path(workspace).resolve(), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, f"tests timed out after {timeout}s"
    return proc.returncode, proc.stdout + proc.stderr


RUNNERS = {"docker": run_pytest, "local": run_pytest_local}


def failed_tests(output: str) -> set[str]:
    return {line[len("FAILED "):].split(" - ")[0].strip() for line in output.splitlines() if line.startswith("FAILED ")}


def is_fixed(exit_code: int, expected_test: str, baseline_failed: set[str], output: str) -> bool:
    if exit_code not in (0, 1):
        return False
    failed = failed_tests(output)
    return expected_test not in failed and failed <= baseline_failed
