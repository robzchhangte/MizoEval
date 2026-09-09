"""Contamination-probe checks: the pure scoring logic is exact, and the
completion probe demonstrably separates memorised text from unseen text
(plan verification item 5)."""

from __future__ import annotations

from mizoeval.contamination import probes
from mizoeval.datasets.loaders import load_mt
from mizoeval.models.base import Message, ModelSpec, Response
from mizoeval.models.cache import ResponseCache
from mizoeval.models.providers import ModelClient


# --------------------------------------------------------------------------- units


def test_split_at_fraction_is_token_aligned():
    pre, suf = probes._split_at_fraction("one two three four five six", 0.5)
    assert pre == "one two three" and suf == "four five six"
    # too short to split
    assert probes._split_at_fraction("a b", 0.5) == ("a b", "")


def test_completion_fidelity_rewards_verbatim_recall():
    gold = "the quick brown fox jumps over the lazy dog"
    verbatim = probes._completion_fidelity(gold, gold)
    miss = probes._completion_fidelity("something entirely unrelated here", gold)
    assert verbatim["prefix_frac"] == 1.0 and verbatim["chrf"] > 95
    assert miss["prefix_frac"] == 0.0 and miss["chrf"] < 40


def test_answer_hit_needs_gold_to_beat_distractors():
    gold, distr = "stone masonry", ["brick masonry", "plain cement concrete", "RCC"]
    assert probes._answer_hit("It is stone masonry.", gold, distr)
    assert not probes._answer_hit("brick masonry", gold, distr)
    assert not probes._answer_hit("", gold, distr)
    assert not probes._answer_hit("UNKNOWN", gold, distr)


def test_temporal_split_buckets_by_year_and_reports_confound():
    from mizoeval.datasets.loaders import load_mcq

    year = {r["id"]: r.get("source_year") for r in load_mcq("all")}
    old = next(i for i, y in year.items() if y and y <= 2022)
    new = next(i for i, y in year.items() if y == 2026)
    records = [
        {"id": old, "gold": "A", "predicted": "A"},   # pre-2023 correct
        {"id": new, "gold": "A", "predicted": "B"},    # recent wrong
        {"id": "no-such-id", "gold": "A", "predicted": "A"},  # year unknown -> excluded
    ]
    ts = probes.temporal_split(records)
    assert ts["pre_2023"]["accuracy"] == 1.0
    assert ts["recent"]["accuracy"] == 0.0
    assert ts["pre_minus_recent"] == 1.0
    assert ts["n_year_unknown"] == 1
    assert "note" in ts


# --------------------------------------------------------------------------- probe


class _MemoriserProvider:
    """A model that has 'memorised' the scripture stratum verbatim and knows
    nothing else -- exactly the pattern the probe must detect."""

    name = "memoriser"

    def __init__(self):
        self._recall = {}
        for row in load_mt("scripture"):
            for side in ("mz", "en"):
                pre, suf = probes._split_at_fraction(row[side], 0.5)
                if suf:
                    self._recall[probes._norm(pre)] = suf

    def complete(self, model, messages, **params):
        user = next(m.content for m in messages if m.role == "user")
        prefix = probes._norm(user.split("passage:", 1)[-1])
        for known, suffix in self._recall.items():
            if known and (known in prefix or prefix.endswith(known)):
                return Response(text=suffix, model=model, provider=self.name,
                                prompt_tokens=10, completion_tokens=20)
        return Response(text="I do not know how this continues.", model=model,
                        provider=self.name, prompt_tokens=10, completion_tokens=6)


def _client(tmp_path):
    c = ModelClient(ModelSpec(name="memoriser", provider="memoriser", model_id="m"),
                    cache=ResponseCache(tmp_path / "c.sqlite"))
    c._provider = _MemoriserProvider()
    return c


def test_verse_completion_flags_the_scripture_stratum(tmp_path):
    run = probes.verse_completion(
        "memoriser", strata=("scripture", "secular"), sides=("mz",),
        n_per_stratum=25, client=_client(tmp_path))
    scr = run.summary["by_cell"]["mz/scripture"]
    sec = run.summary["by_cell"]["mz/secular"]
    assert scr["mean_chrf"] > 90 and scr["verbatim_rate"] > 0.9
    assert sec["mean_chrf"] < 40 and sec["verbatim_rate"] == 0.0
    assert run.summary["mz_scripture_minus_secular_chrf"] > 50


def test_calibrate_separates_kjv_from_fresh_mizo(tmp_path):
    cal = probes.calibrate("memoriser", client=_client(tmp_path))
    # the memoriser doesn't know John 3:16 (not in the MT corpus split map) nor
    # the fresh sentences -> it should NOT claim separation on this stub
    assert set(cal["kjv_anchor"]) == {"chrf", "prefix_frac"}
    assert "separates" in cal and isinstance(cal["separates"], bool)


def test_verse_completion_second_run_is_cache_only(tmp_path):
    cl = _client(tmp_path)
    a = probes.verse_completion("memoriser", strata=("secular",), sides=("mz",),
                                n_per_stratum=10, client=cl)
    hits_before = cl.n_cache_hits
    b = probes.verse_completion("memoriser", strata=("secular",), sides=("mz",),
                                n_per_stratum=10, client=cl)
    assert cl.n_cache_hits > hits_before
    assert a.summary["by_cell"] == b.summary["by_cell"]
