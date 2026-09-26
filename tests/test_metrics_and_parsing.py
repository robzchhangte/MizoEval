"""Metric and parser sanity checks.

The plan's verification rule: feed gold as the prediction and every metric must
be perfect; feed shuffled predictions and every metric must collapse to chance.
A metric that fails either end is broken, and a broken metric produces a
plausible-looking number that no later review would catch.
"""

from __future__ import annotations

import random

import pytest

from mizoeval.metrics.stats import (
    bootstrap_interval,
    cohens_h,
    holm_bonferroni,
    mcnemar_test,
    paired_bootstrap_test,
    wilson_interval,
)
from mizoeval.metrics.tasks import (
    position_bias,
    score_mcq,
    score_mt,
    score_ner,
    score_sentiment,
)
from mizoeval.parsing.answers import (
    align_spans_to_tokens,
    clean_translation,
    parse_entity_json,
    parse_mcq,
    parse_sentiment,
)

LABELS = ["Positive", "Neutral", "Negative"]


# --------------------------------------------------------------------------- MCQ parsing


@pytest.mark.parametrize(
    "text,expected",
    [
        ("B", "B"),
        ("  c ", "C"),
        ("(D)", "D"),
        ("A.", "A"),
        ("[ANSWER: C]", "C"),
        ("[answer: b]", "B"),
        ("Let me think... The final answer is B.", "B"),
        ("Answer: D", "D"),
        ("The answer is (A)", "A"),
        ("Option C is correct.", "C"),
        ("C) Tibeto-Burman family", "C"),
        ("Based on the passage, the correct choice is D", "D"),
    ],
)
def test_parse_mcq_recovers_the_letter(text, expected):
    r = parse_mcq(text)
    assert r.value == expected, f"{text!r} -> {r.value!r} via {r.strategy}"


@pytest.mark.parametrize("text", ["", "   ", "I don't know.", "Both A and B could work."])
def test_parse_mcq_refuses_when_ambiguous_or_absent(text):
    """An ambiguous reply must fail loudly rather than be guessed at.

    Guessing among candidates would add coin flips to the accuracy and inflate
    every model's score by the same invisible amount.
    """
    assert parse_mcq(text).value is None


def test_parse_mcq_reports_which_rule_fired():
    assert parse_mcq("[ANSWER: A]").strategy == "answer_tag"
    assert parse_mcq("B").strategy == "bare_letter"


# --------------------------------------------------------------------------- other parsers


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Positive", "Positive"),
        ("negative", "Negative"),
        ("  NEUTRAL  ", "Neutral"),
        ("Sentiment: Positive", "Positive"),
        ("The label is negative", "Negative"),
        ("This comment is clearly Positive.", "Positive"),
    ],
)
def test_parse_sentiment(text, expected):
    assert parse_sentiment(text).value == expected


def test_parse_entity_json_tolerates_fences_and_prose():
    for blob in (
        '[{"text": "Aizawl", "type": "NEL"}]',
        '```json\n[{"text": "Aizawl", "type": "NEL"}]\n```',
        'Here are the entities:\n[{"text": "Aizawl", "type": "NEL"}]\nHope this helps.',
        '{"entities": [{"text": "Aizawl", "type": "NEL"}]}',
    ):
        r = parse_entity_json(blob)
        assert r.value == [{"text": "Aizawl", "type": "NEL"}], blob


def test_align_spans_prefers_the_longest_match():
    """A nested short span must not steal tokens from the longer one."""
    tokens = ["Central", "YMA", "chuan", "Aizawl", "a", "awm"]
    spans = [{"text": "YMA", "type": "NEO"},
             {"text": "Central YMA", "type": "NEO"},
             {"text": "Aizawl", "type": "NEL"}]
    tags = align_spans_to_tokens(tokens, spans, {"NEO", "NEL"})
    assert tags == ["B-NEO", "I-NEO", "O", "B-NEL", "O", "O"]


def test_align_spans_drops_hallucinated_text():
    """A span the model invented has no alignment and must not be fabricated."""
    tokens = ["Aizawl", "khua"]
    tags = align_spans_to_tokens(tokens, [{"text": "Lunglei", "type": "NEL"}], {"NEL"})
    assert tags == ["O", "O"]


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Lalpa chu ka vengtu a ni", "Lalpa chu ka vengtu a ni"),
        ("Sure! Here is the translation: Lalpa chu ka vengtu", "Lalpa chu ka vengtu"),
        ('"Lalpa chu ka vengtu"', "Lalpa chu ka vengtu"),
        ("Lalpa chu ka vengtu\n\nNote: this is a common phrase.", "Lalpa chu ka vengtu"),
    ],
)
def test_clean_translation_strips_scaffolding(raw, expected):
    assert clean_translation(raw) == expected


# --------------------------------------------------------------------------- metric ends


def _mcq_records(n=400, seed=0, perfect=True):
    rng = random.Random(seed)
    recs = []
    for i in range(n):
        gold = rng.choice("ABCD")
        pred = gold if perfect else rng.choice("ABCD")
        recs.append({"gold": gold, "predicted": pred, "category": f"cat{i % 4}",
                     "parse_strategy": "bare_letter"})
    return recs


def test_mcq_scores_perfectly_on_gold_and_at_chance_on_random():
    perfect = score_mcq(_mcq_records(perfect=True))
    assert perfect.accuracy.point == 1.0
    assert perfect.parse_failure_rate == 0.0

    chance = score_mcq(_mcq_records(perfect=False, seed=1))
    assert 0.15 < chance.accuracy.point < 0.35, chance.accuracy


def test_mcq_counts_unparsed_as_wrong_but_reports_it_separately():
    """The two accuracies must diverge exactly when replies are unparseable."""
    recs = [{"gold": "A", "predicted": "A"}] * 8 + [{"gold": "A", "predicted": None}] * 2
    r = score_mcq(recs)
    assert r.accuracy.point == pytest.approx(0.8)
    assert r.accuracy_parsed_only.point == pytest.approx(1.0)
    assert r.parse_failure_rate == pytest.approx(0.2)


def test_position_bias_detects_a_constant_answerer():
    always_a = [{"gold": "B", "predicted": "A"} for _ in range(100)]
    assert position_bias(always_a)["max_deviation_from_uniform"] == pytest.approx(0.75)

    uniform = [{"gold": "A", "predicted": p} for p in "ABCD" * 25]
    assert position_bias(uniform)["max_deviation_from_uniform"] == pytest.approx(0.0)


def test_mt_scores_perfectly_when_hypothesis_is_the_reference():
    refs = ["Lalpa chu ka vengtu a ni a, ka tlachham lo vang.",
            "Mizoram chuan Parliament-ah thutthlengna hnih a chang a.",
            "Chapchar Kut chu Mizo kut pawimawh ber a ni."]
    recs = [{"hypothesis": r, "reference": r} for r in refs]
    res = score_mt(recs, resamples=50)
    assert res.chrf.point == pytest.approx(100.0, abs=1e-6)
    assert res.bleu == pytest.approx(100.0, abs=1e-6)
    assert res.empty_output_rate == 0.0


def test_mt_collapses_on_unrelated_output():
    refs = ["Lalpa chu ka vengtu a ni a, ka tlachham lo vang."] * 3
    recs = [{"hypothesis": "zzzz qqqq wwww", "reference": r} for r in refs]
    assert score_mt(recs, resamples=50).chrf.point < 20.0


def test_sentiment_perfect_and_chance_and_majority_baseline():
    gold = (["Positive"] * 60) + (["Neutral"] * 25) + (["Negative"] * 15)
    perfect = score_sentiment([{"gold": g, "predicted": g} for g in gold], resamples=50)
    assert perfect.macro_f1.point == pytest.approx(1.0)
    assert perfect.accuracy.point == pytest.approx(1.0)

    # The point of macro-F1 here: always predicting the majority class scores
    # 60% accuracy but must score poorly on macro-F1.
    majority = score_sentiment([{"gold": g, "predicted": "Positive"} for g in gold], resamples=50)
    assert majority.accuracy.point == pytest.approx(0.60)
    assert majority.macro_f1.point < 0.30
    assert majority.majority_baseline == pytest.approx(0.60)


def test_ner_perfect_and_zero():
    gold = [["B-NEP", "I-NEP", "O", "B-NEL"], ["O", "B-NEO", "O"]]
    perfect = score_ner(gold, [list(s) for s in gold], resamples=50)
    assert perfect.micro_f1.point == pytest.approx(1.0)
    assert perfect.micro_f1.low == pytest.approx(1.0)
    assert perfect.micro_f1.high == pytest.approx(1.0)

    nothing = [["O"] * len(s) for s in gold]
    zero = score_ner(gold, nothing, resamples=50)
    assert zero.micro_f1.point == pytest.approx(0.0)


# --------------------------------------------------------------------------- statistics


def test_wilson_interval_brackets_the_point_and_respects_bounds():
    i = wilson_interval(50, 100)
    assert i.low < i.point < i.high
    assert wilson_interval(0, 30).low >= 0.0
    assert wilson_interval(30, 30).high <= 1.0
    # A larger sample must give a tighter interval.
    assert (wilson_interval(500, 1000).high - wilson_interval(500, 1000).low) < (
        wilson_interval(50, 100).high - wilson_interval(50, 100).low
    )


def test_bootstrap_interval_is_reproducible_and_brackets_the_point():
    data = [1.0] * 40 + [0.0] * 60
    stat = lambda xs: sum(xs) / len(xs)  # noqa: E731
    a = bootstrap_interval(data, stat, resamples=200)
    b = bootstrap_interval(data, stat, resamples=200)
    assert (a.point, a.low, a.high) == (b.point, b.low, b.high)
    assert a.low < a.point < a.high


def test_paired_bootstrap_separates_a_real_gap_from_no_gap():
    stat = lambda xs: sum(xs) / len(xs)  # noqa: E731
    strong = [1.0] * 90 + [0.0] * 10
    weak = [1.0] * 40 + [0.0] * 60
    assert paired_bootstrap_test(strong, weak, stat, resamples=300)["p_value"] < 0.05
    assert paired_bootstrap_test(strong, list(strong), stat, resamples=300)["p_value"] > 0.05


def test_mcnemar_uses_only_the_disagreements():
    a = [True] * 40 + [False] * 60
    b = [False] * 40 + [False] * 60
    assert mcnemar_test(a, b)["p_value"] < 0.05
    assert mcnemar_test(a, list(a))["p_value"] == 1.0


def test_holm_is_monotone_and_less_strict_than_bonferroni():
    ps = {"a": 0.001, "b": 0.02, "c": 0.04, "d": 0.9}
    out = holm_bonferroni(ps)
    adjusted = [out[k]["p_adjusted"] for k in sorted(ps, key=lambda k: ps[k])]
    assert adjusted == sorted(adjusted), "adjusted p-values must be non-decreasing"
    assert out["a"]["significant"]
    assert not out["d"]["significant"]
    # Holm's smallest adjustment equals Bonferroni's; later ones are gentler.
    assert out["a"]["p_adjusted"] == pytest.approx(4 * 0.001)
    assert out["c"]["p_adjusted"] < 4 * 0.04


def test_cohens_h_is_zero_for_equal_proportions_and_signed_otherwise():
    assert cohens_h(0.5, 0.5) == pytest.approx(0.0)
    assert cohens_h(0.8, 0.5) > 0
    assert cohens_h(0.2, 0.5) < 0
