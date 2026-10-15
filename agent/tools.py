import re
from pathlib import Path

from .guards import truncate_output
from .sandbox import run_pytest

TOOL_NAMES = {"read_file", "edit_file", "search_code", "run_tests", "finish"}
SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache"}


class ToolError(Exception):
    pass


SCHEMAS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read lines of a file in the repo. Line numbers are 1-based and inclusive.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Replace one exact occurrence of old with new in a source file. Test files cannot be edited.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["path", "old", "new"]}}},
    {"type": "function", "function": {
        "name": "search_code",
        "description": "Search all Python files in the repo for a regular expression. Returns file:line matches.",
        "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "run_tests",
        "description": "Run pytest in the sandbox. Optionally pass one test file or test id.",
        "parameters": {"type": "object", "properties": {"test_path": {"type": "string"}}}}},
    {"type": "function", "function": {
        "name": "finish",
        "description": "Call when the fix is done. Give a short summary of the change.",
        "parameters": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]}}},
]


class Tools:
    def __init__(self, root: Path, runner=run_pytest):
        self.root = Path(root).resolve()
        self._runner = runner
        self.finished_summary: str | None = None

    def _path(self, path: str) -> Path:
        if not path:
            raise ToolError("path is required")
        target = (self.root / path).resolve()
        if target != self.root and self.root not in target.parents:
            raise ToolError(f"path is outside the repo: {path}")
        return target

    def _is_test_file(self, target: Path) -> bool:
        rel = target.relative_to(self.root)
        return rel.parts[0] == "tests" or rel.name.startswith("test_")

    def read_file(self, path: str, start: int = 1, end: int | None = None) -> str:
        lines = self._path(path).read_text(encoding="utf-8").splitlines()
        selected = lines[start - 1:end]
        return truncate_output("\n".join(f"{i}: {line}" for i, line in enumerate(selected, start)))

    def edit_file(self, path: str, old: str, new: str) -> str:
        target = self._path(path)
        if self._is_test_file(target):
            raise ToolError("editing test files is not allowed")
        text = target.read_text(encoding="utf-8")
        count = text.count(old)
        if count != 1:
            raise ToolError(f"old text must match exactly once, found {count} matches")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")
        return f"edited {path}"

    def search_code(self, pattern: str) -> str:
        try:
            regex = re.compile(pattern)
        except re.error as e:
            raise ToolError(f"invalid regex: {e}") from e
        hits = []
        for file in sorted(self.root.rglob("*.py")):
            if SKIP_DIRS & set(file.relative_to(self.root).parts):
                continue
            rel = file.relative_to(self.root).as_posix()
            for i, line in enumerate(file.read_text(encoding="utf-8").splitlines(), 1):
                if regex.search(line):
                    hits.append(f"{rel}:{i}: {line.strip()}")
        return truncate_output("\n".join(hits) or "no matches")

    def run_tests(self, test_path: str | None = None) -> str:
        if test_path:
            self._path(test_path)
        exit_code, output = self._runner(self.root, test_path)
        return truncate_output(f"exit_code: {exit_code}\n{output}")

    def finish(self, summary: str) -> str:
        self.finished_summary = summary
        return "finished"

    def call(self, name: str, args: dict) -> str:
        """Run a tool by name. Errors are returned as text so the model can recover."""
        if name not in TOOL_NAMES:
            return f"ERROR: unknown tool {name}"
        try:
            return getattr(self, name)(**args)
        except (ToolError, OSError, TypeError) as e:
            return f"ERROR: {e}"
