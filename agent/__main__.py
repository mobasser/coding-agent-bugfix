import argparse
import shutil
import time
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .agent import run_agent
from .approve import apply_fix, changed_files, diff_text, ensure_clean_baseline
from .guards import Budget
from .llm import OpenAIChat
from .sandbox import RUNNERS, create_workspace, failed_tests, is_fixed
from .tools import Tools

ROOT = Path(__file__).resolve().parent.parent
TRACE_DIR = ROOT / "evals" / "results" / "traces"


def load_bug(bug_id: str) -> dict:
    bugs = yaml.safe_load((ROOT / "evals" / "bugs.yaml").read_text(encoding="utf-8"))["bugs"]
    for bug in bugs:
        if bug["id"] == bug_id:
            return bug
    raise SystemExit(f"unknown bug id: {bug_id}")


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(prog="agent")
    sub = parser.add_subparsers(dest="command", required=True)
    fix = sub.add_parser("fix", help="fix one seeded bug")
    fix.add_argument("--bug", required=True)
    fix.add_argument("--repo", default=str(ROOT / "demo_repo"))
    fix.add_argument("--model")
    fix.add_argument("--max-steps", type=int, default=15)
    fix.add_argument("--max-cost", type=float, default=0.50)
    fix.add_argument("--auto-approve", action="store_true")
    fix.add_argument("--sandbox", choices=sorted(RUNNERS), default="docker", help="local = no isolation")
    args = parser.parse_args(argv)

    bug = load_bug(args.bug)
    repo = Path(args.repo).resolve()
    run_tests = RUNNERS[args.sandbox]
    ensure_clean_baseline(repo)
    workspace = create_workspace(repo)
    try:
        _, baseline_output = run_tests(workspace)
        baseline = failed_tests(baseline_output)
        if bug["expected_test"] not in baseline:
            print(f"{bug['expected_test']} does not fail at baseline; check the bug setup")
            return 1
        trace = TRACE_DIR / f"{bug['id']}_{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        result = run_agent(bug, Tools(workspace, runner=run_tests), OpenAIChat(args.model), Budget(args.max_steps, args.max_cost), trace)
        print(f"status: {result.status}  steps: {result.steps}  cost: ${result.cost_usd:.4f}")
        print(f"trace: {trace}")
        if result.summary:
            print(f"summary: {result.summary}")
        files = changed_files(repo, workspace)
        if not files:
            print("no changes made; nothing to apply")
            return 1
        code, output = run_tests(workspace)
        if not is_fixed(code, bug["expected_test"], baseline, output):
            print("target test still fails or other tests broke; not offering to apply")
            print(output[-2000:])
            return 1
        print(diff_text(repo, workspace, files))
        if not args.auto_approve and input(f"Apply to branch fix/{bug['id']}? [y/N] ").strip().lower() != "y":
            print("rejected; no changes applied")
            return 1
        branch = apply_fix(repo, workspace, files, f"fix/{bug['id']}", f"Fix {bug['id']}: {bug['description']}")
        print(f"committed to branch {branch}")
        return 0
    finally:
        shutil.rmtree(workspace.parent, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
