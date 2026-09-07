"""A hard token-spend cap for a run.

Given to a `ModelClient`, it counts every token that comes back (prompt +
completion, including any reasoning tokens the provider bills as output) and
raises `BudgetExceeded` once the cap is reached. The runner catches that, writes
whatever completed, and marks the run `budget_stopped` -- so a capped run stops
cleanly with partial results rather than overshooting.

Cache hits do not count: re-serving an answer that was already paid for costs
nothing.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


class BudgetExceeded(RuntimeError):
    def __init__(self, spent: int, cap: int) -> None:
        super().__init__(f"token budget exhausted: {spent:,} / {cap:,}")
        self.spent = spent
        self.cap = cap


@dataclass
class TokenBudget:
    cap: int
    spent_prompt: int = 0
    spent_completion: int = 0
    live_calls: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def spent(self) -> int:
        return self.spent_prompt + self.spent_completion

    @property
    def remaining(self) -> int:
        return max(0, self.cap - self.spent)

    def check(self) -> None:
        """Raise if the cap is already reached. Called before each live call."""
        if self.spent >= self.cap:
            raise BudgetExceeded(self.spent, self.cap)

    def record(self, prompt_tokens: int, completion_tokens: int) -> None:
        with self._lock:
            self.spent_prompt += max(0, prompt_tokens)
            self.spent_completion += max(0, completion_tokens)
            self.live_calls += 1

    def status(self) -> dict[str, int | float]:
        return {
            "cap": self.cap,
            "spent": self.spent,
            "spent_prompt": self.spent_prompt,
            "spent_completion": self.spent_completion,
            "remaining": self.remaining,
            "live_calls": self.live_calls,
            "fraction_used": round(self.spent / self.cap, 4) if self.cap else 0.0,
        }
