from dataclasses import dataclass

MAX_OUTPUT_CHARS = 4000


def truncate_output(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    omitted = len(text) - 2 * half
    return f"{text[:half]}\n...[{omitted} characters omitted]...\n{text[-half:]}"


@dataclass
class Budget:
    max_steps: int = 15
    max_cost_usd: float = 0.50
    steps: int = 0
    cost_usd: float = 0.0

    def charge_step(self) -> None:
        self.steps += 1

    def add_cost(self, usd: float) -> None:
        self.cost_usd += usd

    def exhausted_reason(self) -> str | None:
        if self.steps >= self.max_steps:
            return f"step budget exhausted ({self.steps}/{self.max_steps})"
        if self.cost_usd >= self.max_cost_usd:
            return f"cost budget exhausted (${self.cost_usd:.4f}/${self.max_cost_usd:.2f})"
        return None
