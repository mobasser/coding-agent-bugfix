import argparse
import json
import os
import shutil
import time
from collections import Counter
from pathlib import Path

import yaml
from dotenv import load_dotenv

from agent.agent import run_agent
from agent.approve import changed_files
from agent.guards import Budget
from agent.llm import DEFAULT_MODEL, OpenAIChat
from agent.sandbox import RUNNERS, create_workspace, failed_tests, is_fixed
from agent.tools import Tools

ROOT = Path(__file__).resolve().parent.parent
DEMO_REPO = ROOT / "demo_repo"
RESULTS_DIR = ROOT / "evals" / "results"


def category(status: str, fixed: bool) -> str:
    if fixed:
        return "fixed"
    return status if status in ("budget_exhausted", "no_tool_call") else "wrong_fix"


def evaluate(bug: dict, run_no: int, llm, max_steps: int, max_cost: float, trace_dir: Path, run_tests) -> dict:
    workspace = create_workspace(DEMO_REPO)
    try:
        started = time.time()
        _, baseline_output = run_tests(workspace)
        baseline = failed_tests(baseline_output)
        result = run_agent(bug, Tools(workspace, runner=run_tests), llm, Budget(max_steps, max_cost), trace_dir / f"{bug['id']}_run{run_no}.jsonl")
        code, output = run_tests(workspace)
        fixed = is_fixed(code, bug["expected_test"], baseline, output)
        return {
            "bug": bug["id"], "run": run_no, "status": result.status, "fixed": fixed,
            "category": category(result.status, fixed), "steps": result.steps,
            "cost_usd": round(result.cost_usd, 6), "seconds": round(time.time() - started, 1),
            "changed_files": changed_files(DEMO_REPO, workspace), "summary": result.summary,
        }
    finally:
        shutil.rmtree(workspace.parent, ignore_errors=True)


def summarize(rows: list[dict]) -> dict:
    runs = len(rows)
    fixed = sum(r["fixed"] for r in rows)
    cost = sum(r["cost_usd"] for r in rows)
    return {
        "runs": runs,
        "fixed": fixed,
        "pass_rate": round(fixed / runs, 3) if runs else 0.0,
        "mean_steps": round(sum(r["steps"] for r in rows) / runs, 2) if runs else 0.0,
        "total_cost_usd": round(cost, 4),
        "cost_per_solved_bug_usd": round(cost / fixed, 4) if fixed else None,
        "categories": dict(Counter(r["category"] for r in rows)),
    }


def main(argv=None) -> int:
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(prog="evals")
    parser.add_argument("--model")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--only", help="comma-separated bug ids, e.g. bug_01,bug_05")
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--max-cost", type=float, default=0.50)
    parser.add_argument("--sandbox", choices=sorted(RUNNERS), default="docker", help="local = no isolation")
    args = parser.parse_args(argv)

    bugs = yaml.safe_load((ROOT / "evals" / "bugs.yaml").read_text(encoding="utf-8"))["bugs"]
    if args.only:
        wanted = set(args.only.split(","))
        bugs = [b for b in bugs if b["id"] in wanted]
    model = args.model or os.getenv("AGENT_MODEL", DEFAULT_MODEL)
    llm = OpenAIChat(model)
    out_dir = RESULTS_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{model}"

    rows = []
    for bug in bugs:
        for run_no in range(1, args.runs + 1):
            row = evaluate(bug, run_no, llm, args.max_steps, args.max_cost, out_dir / "traces", RUNNERS[args.sandbox])
            rows.append(row)
            print(f"{bug['id']} run {run_no}: {row['category']} steps={row['steps']} cost=${row['cost_usd']:.4f}")

    summary = summarize(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps({"model": model, "summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"written to {out_dir / 'results.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
