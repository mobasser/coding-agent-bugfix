from agent.guards import Budget, truncate_output


def test_truncate_keeps_short_output():
    assert truncate_output("short", limit=100) == "short"


def test_truncate_shortens_long_output_and_marks_it():
    text = "a" * 500 + "b" * 500
    out = truncate_output(text, limit=100)
    assert out.startswith("a" * 50)
    assert out.endswith("b" * 50)
    assert "900 characters omitted" in out


def test_budget_stops_on_step_limit():
    budget = Budget(max_steps=2)
    assert budget.exhausted_reason() is None
    budget.charge_step()
    budget.charge_step()
    assert budget.exhausted_reason() == "step budget exhausted (2/2)"


def test_budget_stops_on_cost_limit():
    budget = Budget(max_cost_usd=0.10)
    budget.add_cost(0.12)
    assert budget.exhausted_reason().startswith("cost budget exhausted")
