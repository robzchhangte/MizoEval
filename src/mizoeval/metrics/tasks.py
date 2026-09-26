"""Per-task scoring.

Each task's primary metric is chosen for the shape of its data, not by
convention:

MCQ        accuracy with a Wilson interval, plus the parse-failure rate as a
           separate figure -- an unparseable reply is not a wrong answer, and
           conflating them misattributes a formatting problem to knowledge.
MT         chrF++ is primary. BLEU is unreliable at this resource level and
           penalises the morphological variation Mizo shows freely; chrF++
           operates on character n-grams and degrades far more gracefully.
Sentiment  macro-F1 is primary. The corpus is 57% Positive, so accuracy
           rewards a model that never predicts the minority classes.
NER        entity-level F1 via seqeval -- token-level accuracy is dominated by
           the ~79% of tokens tagged O and would look high for a model that
           found nothing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Sequence

from mizoeval.metrics.stats import Interval, bootstrap_interval, wilson_interval


# --------------------------------------------------------------------------- MCQ


@dataclass
class MCQResult:
    n: int
    n_parsed: int
    n_correct: int
    accuracy: Interval
    accuracy_parsed_only: Interval
    parse_failure_rate: float
    by_category: dict[str, Interval] = field(default_factory=dict)
    predicted_positions: dict[str, int] = field(default_factory=dict)
    strategies: dict[str, int] = field(default_factory=dict)


def score_mcq(records: Sequence[dict[str, Any]]) -> MCQResult:
    """Score MCQ predictions.

    Two accuracies are reported. The headline figure counts an unparseable
    reply as wrong, which is the honest end-to-end number. The parsed-only
    figure conditions on a usable reply, which separates knowledge from output
    compliance. Reporting only one of the two hides which is failing.
    """
    n = len(records)
    parsed = [r for r in records if r.get("predicted") is not None]
    correct = sum(1 for r in records if r.get("predicted") == r["gold"])
    correct_parsed = sum(1 for r in parsed if r["predicted"] == r["gold"])

    by_cat: dict[str, Interval] = {}
    cats = {r.get("category") for r in records if r.get("category")}
    for cat in sorted(c for c in cats if c):
        sub = [r for r in records if r.get("category") == cat]
        by_cat[cat] = wilson_interval(sum(1 for r in sub if r.get("predicted") == r["gold"]),
                                      len(sub))

    return MCQResult(
        n=n,
        n_parsed=len(parsed),
        n_correct=correct,
        accuracy=wilson_interval(correct, n),
        accuracy_parsed_only=wilson_interval(correct_parsed, len(parsed)),
        parse_failure_rate=(n - len(parsed)) / n if n else 0.0,
        by_category=by_cat,
        predicted_positions=dict(Counter(r["predicted"] for r in parsed)),
        strategies=dict(Counter(r.get("parse_strategy", "none") for r in records)),
    )


def position_bias(records: Sequence[dict[str, Any]]) -> dict[str, float]:
    """How far a model's answer distribution departs from uniform.

    A model that answers "A" disproportionately is exploiting the source data's
    A-heavy gold distribution rather than answering the question. Compared
    against the permuted variant, this separates the two.
    """
    parsed = [r["predicted"] for r in records if r.get("predicted")]
    if not parsed:
        return {}
    counts = Counter(parsed)
    total = len(parsed)
    shares = {p: counts.get(p, 0) / total for p in "ABCD"}
    return {
        **{f"share_{p}": s for p, s in shares.items()},
        "max_deviation_from_uniform": max(abs(s - 0.25) for s in shares.values()),
    }


# --------------------------------------------------------------------------- MT


@dataclass
class MTResult:
    n: int
    chrf: Interval
    bleu: float
    ter: float
    empty_output_rate: float


def _corpus_chrf(pairs: Sequence[tuple[str, str]]) -> float:
    import sacrebleu

    if not pairs:
        return 0.0
    hyps = [h for h, _ in pairs]
    refs = [[r for _, r in pairs]]
    # word_order=2 is chrF++, which adds word bigrams to the character n-grams.
    return sacrebleu.corpus_chrf(hyps, refs, word_order=2).score


def score_mt(records: Sequence[dict[str, Any]], resamples: int = 1000) -> MTResult:
    import numpy as np
    import sacrebleu
    from sacrebleu.metrics import CHRF

    from mizoeval.metrics.stats import DEFAULT_SEED

    if not records:
        return MTResult(0, Interval(0.0, 0.0, 0.0, 0), 0.0, 0.0, 0.0)

    pairs = [(r.get("hypothesis") or "", r["reference"]) for r in records]
    hyps = [h for h, _ in pairs]
    refs = [[r for _, r in pairs]]

    chrf = CHRF(word_order=2)
    stats = chrf._extract_corpus_statistics(hyps, refs)
    stats_np = np.array(stats, dtype="float32")

    n = len(pairs)
    point_score = chrf.corpus_score(hyps, refs).score

    if resamples > 0 and n > 0:
        rng = np.random.default_rng(DEFAULT_SEED)
        idx = np.arange(n)
        draws = []
        for _ in range(resamples):
            sample_idx = rng.choice(idx, size=n, replace=True)
            sample_stats = stats_np[sample_idx].sum(axis=0)
            draws.append(chrf._compute_score_from_stats(sample_stats.tolist()).score)
        low = float(np.percentile(draws, 2.5))
        high = float(np.percentile(draws, 97.5))
    else:
        low, high = point_score, point_score

    return MTResult(
        n=n,
        chrf=Interval(point=point_score, low=low, high=high, n=n),
        bleu=sacrebleu.corpus_bleu(hyps, refs).score if records else 0.0,
        ter=sacrebleu.corpus_ter(hyps, refs).score if records else 0.0,
        empty_output_rate=sum(1 for h in hyps if not h.strip()) / len(hyps) if hyps else 0.0,
    )


def score_mt_by_stratum(records: Sequence[dict[str, Any]]) -> dict[str, MTResult]:
    """Score each register separately.

    This is the paper's central MT comparison: a large scripture-versus-secular
    gap indicates memorisation rather than translation ability, and only the
    secular figure measures the latter.
    """
    out: dict[str, MTResult] = {}
    for stratum in ("scripture", "religious", "secular"):
        sub = [r for r in records if r.get("stratum") == stratum]
        if sub:
            out[stratum] = score_mt(sub)
    return out


# --------------------------------------------------------------------------- sentiment


@dataclass
class SentimentResult:
    n: int
    accuracy: Interval
    macro_f1: Interval
    per_class_f1: dict[str, float]
    confusion: dict[str, dict[str, int]]
    parse_failure_rate: float
    majority_baseline: float


def _macro_f1(records: Sequence[dict[str, Any]]) -> float:
    from sklearn.metrics import f1_score

    if not records:
        return 0.0
    gold = [r["gold"] for r in records]
    # An unparseable reply becomes an explicit non-label so it counts against
    # the model, rather than being dropped and quietly raising the score.
    pred = [r.get("predicted") or "__UNPARSED__" for r in records]
    labels = sorted(set(gold))
    return float(f1_score(gold, pred, labels=labels, average="macro", zero_division=0))


def score_sentiment(records: Sequence[dict[str, Any]], resamples: int = 1000) -> SentimentResult:
    from sklearn.metrics import f1_score

    n = len(records)
    gold = [r["gold"] for r in records]
    pred = [r.get("predicted") or "__UNPARSED__" for r in records]
    labels = sorted(set(gold))

    per_class = dict(
        zip(labels, f1_score(gold, pred, labels=labels, average=None, zero_division=0))
    )
    confusion: dict[str, dict[str, int]] = {g: Counter() for g in labels}
    for g, p in zip(gold, pred):
        confusion[g][p] += 1

    counts = Counter(gold)
    return SentimentResult(
        n=n,
        accuracy=wilson_interval(sum(1 for g, p in zip(gold, pred) if g == p), n),
        macro_f1=bootstrap_interval(list(records), _macro_f1, resamples=resamples),
        per_class_f1={k: float(v) for k, v in per_class.items()},
        confusion={g: dict(c) for g, c in confusion.items()},
        parse_failure_rate=sum(1 for r in records if r.get("predicted") is None) / n if n else 0.0,
        majority_baseline=max(counts.values()) / n if n else 0.0,
    )


# --------------------------------------------------------------------------- NER


@dataclass
class NERResult:
    n_sentences: int
    micro_f1: float
    macro_f1: float
    precision: float
    recall: float
    per_type: dict[str, dict[str, float]]
    parse_failure_rate: float


def score_ner(
    gold_tags: Sequence[Sequence[str]],
    pred_tags: Sequence[Sequence[str]],
    parse_failures: int = 0,
) -> NERResult:
    from seqeval.metrics import (
        classification_report,
        f1_score,
        precision_score,
        recall_score,
    )

    gold = [list(g) for g in gold_tags]
    pred = [list(p) for p in pred_tags]
    if not gold:
        return NERResult(0, 0.0, 0.0, 0.0, 0.0, {}, 0.0)

    report = classification_report(gold, pred, output_dict=True, zero_division=0)
    per_type = {
        k: {"precision": v["precision"], "recall": v["recall"],
            "f1": v["f1-score"], "support": v["support"]}
        for k, v in report.items()
        if k not in ("micro avg", "macro avg", "weighted avg")
    }
    return NERResult(
        n_sentences=len(gold),
        micro_f1=float(f1_score(gold, pred, average="micro", zero_division=0)),
        macro_f1=float(f1_score(gold, pred, average="macro", zero_division=0)),
        precision=float(precision_score(gold, pred, average="micro", zero_division=0)),
        recall=float(recall_score(gold, pred, average="micro", zero_division=0)),
        per_type=per_type,
        parse_failure_rate=parse_failures / len(gold),
    )
