# Design: Coding Agent for Bug Fixes

## Problem

Given a bug description and a failing test, produce a fix in a small Python repo. A human approves the change before it is committed. The agent is measured by how many seeded bugs it fixes and what each fix costs.

## Approach

The agent is a loop, not a fixed pipeline. Each step, the model sees the conversation so far and chooses one of five tools:

- `read_file`, `search_code`: gather context
- `edit_file`: make one exact-match replacement in a source file
- `run_tests`: run pytest in the sandbox
- `finish`: end the run with a summary

The loop stops when `finish` is called, the full test suite passes, the step or cost budget runs out, or the model replies without a tool call. The loop is written by hand on the OpenAI SDK (`agent/agent.py`), so every decision is visible in the code.

## Key decisions

| Decision | Choice | Why |
|---|---|---|
| Edit format | Exact string replacement, must match once | Small, auditable diffs. Ambiguous edits are rejected instead of guessed. |
| Test files | `edit_file` refuses them | Prevents the model from "fixing" a bug by changing the test. |
| Workspace | Temp copy of the repo | The original is untouched until approval. |
| Sandbox | Docker, no network, memory and CPU caps, timeout | Generated code and tests run isolated from the host and credentials. |
| Stop rule | Full suite passes, not just the target test | A targeted pass can hide a regression elsewhere. |
| Verification | Harness re-runs the full suite after the agent stops | The agent's own claim of success is not trusted. |
| Approval | Terminal diff review, then a branch and commit | A human reviews every change before it enters git history. |
| Model access | `OpenAIChat.complete(messages, tools) -> Reply` | The loop depends on that one method, so another provider can be swapped in. |
| Cost tracking | Token counts times a price table, per step | Budgets are enforced during the run, not reported after it. |
| Errors | Tool errors are returned to the model as text | The model can recover, for example by fixing bad arguments. |

## Safety

- Paths are resolved and must stay inside the workspace.
- Tool output is truncated, which limits token cost and prompt injection from long outputs.
- Budgets cap the worst case per run.
- The sandbox has no network, so tests cannot send data out.

Limits: the sandbox is only as strong as Docker's default isolation, and the approval gate depends on a person reading the diff.

## Evaluation

- **Ground truth:** 10 seeded bugs, each with one failing test, in `evals/bugs.yaml`. Three are marked hard.
- **Success:** the full test suite passes after the agent stops.
- **Metrics:** pass rate, mean steps, total cost, and cost per solved bug.
- **Failure categories:** `wrong_fix`, `budget_exhausted`, `no_tool_call`.

## Known limitations and next steps

- No baseline yet. A single-shot prompt with no tools would show how much the loop adds.
- Only Python and one small demo repo are covered. The results say little about larger codebases.
- Pricing is hardcoded, so it has to be updated by hand.
- Next steps: a real GitHub issue and PR flow, stronger sandboxing (for example gVisor or a locked-down VM), multi-file reasoning benchmarks, and a planner step for harder bugs.
