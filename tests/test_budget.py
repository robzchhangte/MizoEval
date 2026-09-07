"""Token-budget cap: stops spending at the cap, counts only paid calls."""

from __future__ import annotations

import json

import pytest

from mizoeval.models.base import Message, ModelSpec, Response
from mizoeval.models.budget import BudgetExceeded, TokenBudget
from mizoeval.models.cache import ResponseCache
from mizoeval.models.providers import ModelClient
from mizoeval.runners import run_task


class _CountingProvider:
    """Returns a fixed 100-prompt / 50-completion Response, counting calls."""

    name = "counter"

    def __init__(self):
        self.calls = 0

    def complete(self, model, messages, **params):
        self.calls += 1
        return Response(text="A", model=model, provider=self.name,
                        prompt_tokens=100, completion_tokens=50)


def _client(cap, cache_path):
    spec = ModelSpec(name="counter", provider="counter", model_id="c")
    c = ModelClient(spec, cache=ResponseCache(cache_path), budget=TokenBudget(cap=cap))
    c._provider = _CountingProvider()
    return c


def test_budget_blocks_further_calls_once_the_cap_is_reached(tmp_path):
    c = _client(cap=450, cache_path=tmp_path / "c.sqlite")
    # 150 tokens per call -> 3 calls reach 450, the 4th must be refused.
    for _ in range(3):
        assert c.chat([Message("user", f"q{_}")]).ok
    with pytest.raises(BudgetExceeded):
        c.chat([Message("user", "one too many")])
    assert c._provider.calls == 3
    assert c.budget.spent == 450
    assert c.budget.remaining == 0


def test_cache_hits_do_not_count_against_the_budget(tmp_path):
    c = _client(cap=300, cache_path=tmp_path / "c.sqlite")
    c.chat([Message("user", "same")])   # 150 tokens, live
    for _ in range(10):
        r = c.chat([Message("user", "same")])  # served from cache
        assert r.cached and r.ok
    assert c._provider.calls == 1
    assert c.budget.spent == 150  # the 10 cache hits added nothing


def test_no_budget_means_no_cap(tmp_path):
    spec = ModelSpec(name="counter", provider="counter", model_id="c")
    c = ModelClient(spec, cache=ResponseCache(tmp_path / "c.sqlite"), budget=None)
    c._provider = _CountingProvider()
    for i in range(20):
        assert c.chat([Message("user", f"q{i}")]).ok
    assert c._provider.calls == 20


def test_run_task_stops_cleanly_and_records_partial_results(tmp_path, monkeypatch):
    """A capped run writes the items it managed and flags budget_stopped."""
    manifest = run_task.main([
        "--task", "mcq", "--regime", "zero_shot", "--model", "mock",
        "--out-dir", str(tmp_path), "--cache", str(tmp_path / "c.sqlite"),
        "--token-budget", "500",   # mock reports ~a dozen prompt tokens/call
    ])
    assert manifest["budget_stopped"] is True
    assert manifest["token_budget"]["spent"] >= 500
    # fewer than the full mcq4 set, but what ran is on disk and scored
    recs = [json.loads(l) for l in
            (tmp_path / f"{manifest['run_key']}.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    assert 0 < len(recs) < 1747
    assert manifest["summary"]["n"] == len(recs)


def test_openai_adapter_swaps_max_tokens_for_reasoning_models():
    from mizoeval.models.providers import OpenAIProvider

    p = OpenAIProvider.__new__(OpenAIProvider)  # no network
    assert p._adapt_params("gpt-5.4-mini-2026-03-17", {"max_tokens": 16}) == {
        "max_completion_tokens": 16
    }
    assert p._adapt_params("gpt-4o-mini", {"max_tokens": 16}) == {"max_tokens": 16}
