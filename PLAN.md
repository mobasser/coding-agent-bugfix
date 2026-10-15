# Coding Agent for Bug Fixes: Project Plan

## 1. Goal

Build a command-line agent that takes a bug description and a failing test, reads and edits a small Python repo, runs the tests until they pass or a step budget runs out, and shows the diff for human approval before committing to a git branch. Measure its fix rate on a set of seeded bugs.

## 2. Scope

**In scope**
- Python repos only
- Seeded bugs in a demo repo, each with a failing test
- Local git branch and diff output (no real GitHub PR)
- OpenAI models through one provider wrapper
- Docker sandbox for running tests
- Evaluation report with pass rate, steps, and cost per fix

**Out of scope (for v1)**
- Real GitHub issue and PR integration
- Languages other than Python
- Multi-agent setups
- Web UI

## 3. Architecture

```
CLI (main.py)
  └── Agent loop (agent.py)
        ├── LLM client (llm.py, OpenAI, wrapped for swapping providers)
        ├── Tools (tools.py)
        │     ├── read_file(path, start, end)
        │     ├── edit_file(path, old, new)     exact string replace
        │     ├── search_code(pattern)
        │     ├── run_tests(test_path)          runs inside Docker
        │     └── finish(summary)
        ├── Guardrails (guards.py)
        │     ├── step budget (default 15)
        │     ├── token/cost budget per run
        │     ├── per-tool timeout
        │     └── output truncation
        └── Approval gate (approve.py)
              shows diff, asks y/n, then commits to branch
```

**Loop logic**
1. Send the bug report and failing test output to the model.
2. Model returns a tool call. Execute it and append the result.
3. Stop when `finish` is called, tests pass, or the budget is exhausted.
4. If tests pass, show the diff and wait for approval.

## 4. Key Design Decisions

| Decision | Choice | Reason |
|---|---|---|
| Agent loop | Raw OpenAI SDK function calling, written by hand | Keeps the loop visible for interviews |
| Edit format | Exact string replace | Simpler and safer than whole-file rewrites |
| Execution | Docker container, no network, mounted copy of the repo | Agent code can't touch your machine or credentials |
| Stop condition | Tests pass, `finish` called, or budget hit | Prevents infinite loops |
| Approval | Terminal diff review; `--auto-approve` for evals | Human stays in control before any commit |
| Model access | Wrapper function in `llm.py`; model set in config | Lets you compare models and providers |
| Dev model | Cheap model (set in config) | Keeps development cost near zero |
| Eval model | One mid-tier model, plus one cheap model for comparison | Reports pass rate and cost per solved bug |
| Tests for the agent | Recorded or scripted LLM responses | Deterministic and free |

## 5. Project Structure

```
coding-agent-bugfix/
├── agent/
│   ├── __init__.py
│   ├── __main__.py       # CLI entry point (python -m agent fix --bug bug_03)
│   ├── agent.py          # main loop
│   ├── llm.py            # OpenAI client wrapper
│   ├── tools.py          # tool definitions and implementations
│   ├── guards.py         # budgets, timeouts, truncation
│   ├── sandbox.py        # Docker execution
│   └── approve.py        # diff display and commit
├── demo_repo/            # the project the agent fixes
│   ├── src/
│   └── tests/            # one failing test per seeded bug
├── evals/
│   ├── bugs.yaml         # 10 bugs: id, description, expected test
│   ├── run_evals.py      # runs agent on each bug, records results
│   └── results/          # JSON output per run
├── tests/                # unit tests for the agent itself
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 6. Phases and Milestones

**Phase 0: Setup (half a day)**
- Create the repo, virtual environment, `.gitignore`, and `.env.example`
- Install Docker Desktop with the WSL2 backend and confirm `docker info` works
- Confirm the OpenAI key works with a single test call

**Phase 1: Demo repo and seeded bugs (1 day)**
- Write a small Python text-utilities library (about 300 to 500 lines)
- Seed 10 bugs of varied difficulty: off-by-one, wrong operator, missing edge case, wrong return type, and so on
- Each bug has one failing test, and the full suite passes once the bug is fixed

**Phase 2: Tools and sandbox (2 days)**
- Implement the five tools with unit tests
- Build the Docker runner: copies the repo in, runs pytest, returns output and exit code
- Enforce timeouts and output truncation

**Phase 3: Agent loop and guardrails (2 days)**
- Implement the loop with the model's tool calls
- Add step, cost, and timeout budgets
- Add a structured trace log of each step (tool name, arguments, result, tokens)
- Test the loop with scripted model responses

**Phase 4: Approval and git (1 day)**
- Show the diff in the terminal
- On approval, create a branch, commit, and print the branch name
- On rejection, discard the changes

**Phase 5: Evaluation (1 to 2 days)**
- Run all 10 bugs, ideally 3 times each to check consistency
- Record pass rate, average steps, tokens, cost, and failure reasons
- Write a results table in the README

**Phase 6: Documentation and polish (1 day)**
- README with setup, usage, architecture diagram, and results
- A short design write-up covering trade-offs and next steps (real PR integration, more languages, stronger sandboxing)

Estimated total: about 2 to 3 weeks of part-time work.

## 7. Evaluation Plan

- **Metrics:** fix rate (tests pass and no other tests break), mean steps per fix, cost per fix, cost per solved bug, and time per fix
- **Failure categories:** wrong fix, edited the wrong file, looped, budget exhausted, tool error
- **Baseline:** compare against a single-shot prompt with no tools, to show the value of the agent loop
- **Model comparison:** run the same bugs on one cheap and one mid-tier model

## 8. Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Agent runs harmful commands | Docker with no network; only the five defined tools |
| Costs grow out of control | Per-run budget plus a hard monthly limit in the OpenAI dashboard |
| Agent edits tests to make them pass | Forbid edits to test files in `edit_file`; check this in evals |
| Docker setup is slow on Windows | Build the image once; keep the demo repo small |
| Results look good only on easy bugs | Include hard bugs that need multi-file reasoning |
| Model output is not reproducible | Log everything; report results across multiple runs |

## 9. Deliverables

1. Working CLI: `python -m agent fix --bug bug_03`
2. Demo repo with 10 seeded bugs
3. Evaluation results in `evals/results/`
4. README with setup, usage, and results table
5. Design write-up (one to two pages)

## 10. Decisions (defaults chosen; change as needed)

1. **Dev model:** a cheap OpenAI model, set in config. Mid-tier model for the final evaluation.
2. **Demo repo domain:** text utilities.
3. **Repo location:** `C:\Projects\coding-agent-bugfix`, separate from the other projects.
4. **Approval behavior:** always ask, with an `--auto-approve` flag for evaluations.

## 11. Status

- Phase 0 partly done: folder, git repo, dependencies, and venv are ready. Still needed: Docker Desktop (WSL2) and an OpenAI key in `.env`.
- Phase 3 code done: OpenAI wrapper with per-step cost (`agent/llm.py`), agent loop with budgets and JSONL trace (`agent/agent.py`). Tested with scripted model responses.
- Phase 4 code done: diff display, approval prompt, branch and commit (`agent/approve.py`, `agent/__main__.py`). The demo repo must be committed as a baseline before the approval step will run.
- Phase 5 harness done: `python -m evals.run_evals` runs the bugs and verifies each with the full suite. Live results still need Docker and an API key.
- Phase 6 done: README.md and DESIGN.md. The results table is marked "to be run".
- Phase 2 code done: five tools with schemas (`agent/tools.py`), output truncation and budgets (`agent/guards.py`), Docker runner and temp-copy workspace (`agent/sandbox.py`), and `Dockerfile`. 19 unit tests pass. The Docker runner is tested with a mocked subprocess until Docker is installed.
- Phase 1 done: `demo_repo/` has 10 seeded bugs (`evals/bugs.yaml`). The buggy suite fails exactly 10 tests, one per bug. Applying the 10 correct fixes makes all 19 tests pass.
