from evals.run_evals import category, summarize


def row(fixed, status="finished", steps=3, cost=0.01):
    return {"fixed": fixed, "category": category(status, fixed), "steps": steps, "cost_usd": cost}


def test_category_maps_outcomes():
    assert category("finished", True) == "fixed"
    assert category("finished", False) == "wrong_fix"
    assert category("budget_exhausted", False) == "budget_exhausted"
    assert category("no_tool_call", False) == "no_tool_call"


def test_summarize_reports_pass_rate_and_cost_per_solved_bug():
    rows = [row(True, cost=0.02), row(False, status="budget_exhausted", steps=15, cost=0.10), row(True, cost=0.02)]
    s = summarize(rows)
    assert s["runs"] == 3
    assert s["fixed"] == 2
    assert s["pass_rate"] == 0.667
    assert s["mean_steps"] == 7.0
    assert s["total_cost_usd"] == 0.14
    assert s["cost_per_solved_bug_usd"] == 0.07
    assert s["categories"] == {"fixed": 2, "budget_exhausted": 1}


def test_summarize_handles_no_solved_bugs_and_no_rows():
    assert summarize([row(False)])["cost_per_solved_bug_usd"] is None
    assert summarize([])["pass_rate"] == 0.0
