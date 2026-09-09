"""End-to-end runner and roster checks, all offline via the mock provider.

These verify the plumbing the plan's verification section calls for: every
task/regime runs, raw output is persisted before parsing, a manifest records
the conditions, and a repeat run is a pure cache hit with no cost.
"""

from __future__ import annotations

import json

import pytest

from mizoeval.models.base import Message, ModelSpec
from mizoeval.models.cache import ResponseCache
from mizoeval.models.providers import ModelClient
from mizoeval.models.roster import load_roster
from mizoeval.prompts.templates import all_template_hashes, get_template
from mizoeval.runners import run_task


@pytest.mark.parametrize(
    "argv",
    [
        ["--task", "mcq", "--regime", "zero_shot"],
        ["--task", "mcq", "--regime", "cot"],
        ["--task", "mcq", "--regime", "five_shot"],
        ["--task", "mcq", "--regime", "zero_shot", "--permuted"],
        ["--task", "sentiment", "--regime", "zero_shot"],
        ["--task", "sentiment", "--regime", "five_shot"],
        ["--task", "mt", "--regime", "zero_shot", "--direction", "en2mz"],
        ["--task", "mt", "--regime", "five_shot", "--direction", "mz2en"],
        ["--task", "ner", "--regime", "few_shot"],
        ["--task", "ner", "--regime", "few_shot", "--docsplit"],
    ],
)
def test_every_task_regime_runs_end_to_end(argv, tmp_path):
    run_task.main(argv + ["--model", "mock", "--limit", "6",
                          "--out-dir", str(tmp_path), "--cache", str(tmp_path / "c.sqlite")])

    manifests = list(tmp_path.glob("*.manifest.json"))
    assert len(manifests) == 1
    m = json.loads(manifests[0].read_text(encoding="utf-8"))
    assert m["n_items"] == 6
    assert m["n_api_errors"] == 0
    assert m["template_hash"]  # provenance recorded
    assert "summary" in m and m["summary"]

    records = [
        json.loads(l)
        for l in (tmp_path / f"{m['run_key']}.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    assert len(records) == 6
    # Raw model text is persisted for every item, before any parsing.
    assert all("raw_text" in r for r in records)


def test_repeat_run_is_a_pure_cache_hit(tmp_path):
    args = ["--task", "mcq", "--regime", "zero_shot", "--model", "mock",
            "--limit", "10", "--out-dir", str(tmp_path), "--cache", str(tmp_path / "c.sqlite")]

    run_task.main(args)
    first = json.loads(next(tmp_path.glob("*.manifest.json")).read_text(encoding="utf-8"))
    assert first["live_calls"] == 10 and first["cache_hits"] == 0

    run_task.main(args)
    second = json.loads(next(tmp_path.glob("*.manifest.json")).read_text(encoding="utf-8"))
    assert second["live_calls"] == 0
    assert second["cache_hits"] == 10
    assert second["cost_usd"] == 0.0
    assert second["summary"] == first["summary"]  # byte-identical result


def test_failed_calls_are_not_cached(tmp_path):
    """A transient error must never become a permanent cached answer."""

    class Flaky:
        name = "flaky"
        calls = 0

        def complete(self, model, messages, **params):
            Flaky.calls += 1
            raise RuntimeError("boom")

    spec = ModelSpec(name="flaky", provider="flaky", model_id="x")
    client = ModelClient(spec, cache=ResponseCache(tmp_path / "c.sqlite"), max_retries=1)
    client._provider = Flaky()

    r1 = client.chat([Message("user", "hi")])
    r2 = client.chat([Message("user", "hi")])
    assert r1.error and r2.error
    assert Flaky.calls == 2  # second call was retried, not served from cache


def test_mcq_subset_does_not_collide_in_the_output_key(tmp_path):
    """mcq4 and `all` are different runs -- one must not overwrite the other."""
    common = ["--task", "mcq", "--regime", "zero_shot", "--model", "mock",
              "--limit", "6", "--out-dir", str(tmp_path), "--cache", str(tmp_path / "c.sqlite")]
    m4 = run_task.main(common + ["--mcq-subset", "mcq4"])
    m_all = run_task.main(common + ["--mcq-subset", "all"])
    assert m4["run_key"] != m_all["run_key"]
    assert "__all" not in m4["run_key"]      # headline set keeps the bare name
    assert m_all["run_key"] == m4["run_key"].replace("__limit", "__all__limit")
    assert len(list(tmp_path.glob("mcq__zero_shot__mock*.jsonl"))) == 2


def test_roster_every_enabled_entry_has_a_known_provider():
    from mizoeval.models.providers import PROVIDERS

    for spec in load_roster(enabled_only=False):
        assert spec.provider in PROVIDERS, spec.name
        assert spec.model_id and "latest" not in spec.model_id


def test_template_hashes_are_stable_and_distinct():
    h1 = all_template_hashes()
    h2 = all_template_hashes()
    assert h1 == h2, "hashing must be deterministic"
    assert len(set(h1.values())) == len(h1), "every template needs a distinct hash"


def test_cot_template_asks_for_the_answer_tag():
    t = get_template("mcq", "cot")
    rendered = t.render(question="Q?", choices={"A": "a", "B": "b", "C": "c", "D": "d"})
    assert "[ANSWER: X]" in rendered


def test_mt_exemplars_are_secular_only():
    """Few-shot MT demos must not come from the register the study isolates."""
    from mizoeval.datasets.loaders import load_mt, mt_exemplars

    secular_en = {r["en"] for r in load_mt("secular")}
    for ex in mt_exemplars("en2mz", k=5):
        assert ex["en"] in secular_en
