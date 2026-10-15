# Coding Agent for Bug Fixes

A command-line agent that reads a failing test, edits a small Python repo, runs the tests inside a Docker sandbox until they pass or a budget runs out, then shows the diff for approval before committing to a git branch.

The agent uses OpenAI function calling in a hand-written loop. The model chooses the tools and the next step.

## Requirements

- Python 3.12 or newer
- Git
- Docker Desktop with the WSL2 backend (the test runner uses Docker)
- An OpenAI API key with billing enabled

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then set OPENAI_API_KEY
docker build -t coding-agent-sandbox:latest .
```

## Usage

Fix one seeded bug. The diff is shown, and nothing is committed until you approve it:

```bash
python -m agent fix --bug bug_03
```

Options:
- `--model` picks the model (default: `AGENT_MODEL` from `.env`, else `gpt-5-nano`)
- `--max-steps` (default 15) and `--max-cost` (default $0.50) cap each run
- `--auto-approve` skips the prompt and applies the fix. Use it only for evaluations.

Approved fixes are committed to a branch named `fix/<bug_id>`. The demo repo must be committed as a baseline first, since the approval step checks that it has no uncommitted changes.

## Evaluation

Run the agent on the seeded bugs and write a results file:

```bash
python -m evals.run_evals --model gpt-5-nano --runs 3
python -m evals.run_evals --model gpt-5.6-terra --runs 3 --only bug_01,bug_10
```

Each run is checked by running the full test suite in the sandbox. A run counts as fixed only if every test passes. Results go to `evals/results/<timestamp>_<model>/results.json`, and per-step traces go to the `traces/` folder beside it.

Metrics reported: pass rate, mean steps, total cost, and cost per solved bug. Failures are grouped as `wrong_fix`, `budget_exhausted`, or `no_tool_call`.

## Results

Not yet run. The evaluation needs Docker and an API key. Fill this table in after running the evaluation:

| Model | Runs | Pass rate | Mean steps | Total cost | Cost per solved bug |
|---|---|---|---|---|---|
| _to be run_ | | | | | |

## Architecture

```
python -m agent fix
  └── agent/agent.py      loop: model -> tool call -> result, until finish / tests pass / budget
        ├── agent/llm.py      OpenAI chat wrapper, returns tool calls and cost
        ├── agent/tools.py    read_file, edit_file, search_code, run_tests, finish
        ├── agent/guards.py   step and cost budgets, output truncation
        ├── agent/sandbox.py  temp copy of the repo, Docker run with no network
        └── agent/approve.py  diff, approval, git branch and commit
```

See `DESIGN.md` for the design decisions and trade-offs.

## Tests

```bash
python -m pytest
```

The unit tests use scripted model responses and a fake test runner, so they need no API key and no Docker. The demo repo has its own tests, which fail on purpose until the bugs are fixed:

```bash
cd demo_repo && python -m pytest -q
```

## Limitations

- Python only, and only the seeded demo repo has been tested.
- Real GitHub issues and pull requests are not supported. The output is a local branch.
- No multi-agent setup and no web UI.
- Model cost depends on the prices in `agent/llm.py`. Update them when OpenAI changes prices, or the cost figures will be wrong.
