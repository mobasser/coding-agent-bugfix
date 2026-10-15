# Tasks for the coding model: Web UI for the bug-fix agent

Read `README.md` and `DESIGN.md` first.

**Project:** A command-line bug-fixing agent (`python -m agent fix --bug bug_03`).

**Goal:** Add a local web UI. A user enters a git repo URL, the app finds failing tests, runs the existing agent on them, and shows the results (diff, steps, cost, trace, pass/fail).

## Rules for every step

- Do not edit `agent/agent.py`, `agent/tools.py`, `agent/guards.py`, or any file in `tests/` or `demo_repo/tests/`. Add new code alongside them. If a change to them seems necessary, stop and report why.
- Follow the existing style: short functions, type hints, no new comments unless asked, no emojis.
- Never print, log, or commit secrets. Read `OPENAI_API_KEY` from `.env` only.
- Run `python -m pytest` after each step. All existing tests must still pass.
- Before adding any dependency, check that it isn't already in `requirements.txt`. Pin exact versions.
- Stop and ask if a step is unclear. Do not guess.

---

## Step 1: Understand the existing code (read only)

1. Read `agent/__main__.py`, `agent/agent.py`, `agent/sandbox.py`, `agent/approve.py`, `evals/run_evals.py`.
2. Write a short list in your reply: the function that runs one bug end to end, what a "bug" dict needs (`id`, `description`, `expected_test`), and how the workspace is created and cleaned up.

**Done when:** you can state those three things without looking.

## Step 2: Add a repo intake module

Create `agent/intake.py` with:

- `clone_repo(url: str, dest: Path) -> Path`: runs `git clone --depth 1` into a temp folder. Reject URLs that don't start with `https://`.
- `discover_failures(repo: Path) -> list[dict]`: runs pytest in the sandbox runner, parses `FAILED <test_id> - <message>` lines with `failed_tests` from `sandbox.py`, and returns one bug dict per failing test: `{"id": "rN_k", "description": <message>, "expected_test": <test_id>}`.

**Tests (`tests/test_intake.py`):** a fake runner returns canned pytest output; check the parsed bug list. Mock `subprocess` for the clone, and test that a non-https URL raises `ValueError`.

**Done when:** tests pass and no network is needed for them.

## Step 3: Add a run service

Create `agent/service.py` with `run_repo(url: str, runner) -> dict` that:

1. Clones the repo (step 2).
2. Calls `ensure_clean_baseline` on the clone. If that fails, return a clear error message.
3. Calls `discover_failures`. If there are none, return `{"status": "no_failures"}`.
4. For each failing test, calls `create_workspace`, then `run_agent` with `Tools`, a `Budget`, and `OpenAIChat`, then `changed_files` and `diff_text` as in `__main__.py`.
5. Returns a list of results: bug id, status, steps, cost, diff, summary, and `is_fixed` result.

Use `run_tests` and `RUNNERS` as `__main__.py` does. Use `--sandbox docker` by default.

**Tests (`tests/test_service.py`):** use a scripted fake LLM and fake runner (see `tests/test_agent.py` for the pattern). Cover: no failures, one fixed bug, one budget-exhausted bug.

**Done when:** all tests pass.

## Step 4: Add the web app

1. Add `fastapi` and `uvicorn` to `requirements.txt` with pinned versions.
2. Create `web/app.py`:
   - `GET /`: HTML form with a repo URL field and a submit button.
   - `POST /runs`: calls `run_repo` and renders the results.
   - Keep results in memory (a dict keyed by run id). No database.
3. Create `web/templates/index.html` and `web/templates/results.html`. Plain HTML, no JavaScript frameworks.
4. Results page shows, per bug: status, steps, cost, summary, and the diff in a `<pre>` block. Escape all output (Jinja2 autoescape does this by default).

**Tests (`tests/test_web.py`):** use FastAPI's `TestClient`. Mock `run_repo`. Check that `GET /` returns 200 and that `POST /runs` shows the mocked results.

**Done when:** tests pass and `uvicorn web.app:app` starts.

## Step 5: Safety checks

1. Confirm that `intake.py` only clones `https://` URLs and never runs code from the clone outside the Docker runner. The `--sandbox local` option must not be the default in the web app.
2. Confirm that the web app binds to `127.0.0.1` by default.
3. Confirm no secrets appear in any template or response.

**Done when:** you list each check and say how you verified it.

## Step 6: Update docs

Add a "Web UI" section to `README.md` with the start command. Do not change the other sections.

## Step 7: Final verification (on a machine with Docker)

1. `docker build -t coding-agent-sandbox:latest .`
2. `python -m pytest`: all tests pass.
3. `uvicorn web.app:app --port 8000`, then open `http://127.0.0.1:8000`.
4. Submit a local copy of `demo_repo` as a git repo URL (or a `file://` path, if you add that as an explicit dev option). Check that the 10 bugs appear and results display.
5. Report: test counts, what you ran, and anything that failed.

---

## Report format at the end

List files added or changed, the test results, the commands you ran, and any step you couldn't finish and why.
