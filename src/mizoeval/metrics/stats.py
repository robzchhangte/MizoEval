"""Confidence intervals and significance tests.

A benchmark table of bare point estimates invites over-reading: with ~1,700 MCQ
items, two models a point apart are indistinguishable, and with only 809 secular
translation pairs the intervals are wider still. Every headline number in the
paper therefore carries an interval, and every model-versus-model claim carries
a paired test corrected for the size of the comparison grid.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

DEFAULT_RESAMPLES = 1000
DEFAULT_SEED = 20260907


@dataclass
class Interval:
    point: float
    low: float
    high: float
    n: int

    def __str__(self) -> str:
        return f"{self.point:.3f} [{self.low:.3f}, {self.high:.3f}]"


def wilson_interval(successes: int, n: int, z: float = 1.96) -> Interval:
    """Wilson score interval for a proportion.

    Preferred over the normal approximation because accuracy on small
    per-category slices runs close to 0 or 1, where the normal interval can
    extend past the [0, 1] boundary.
    """
    if n == 0:
        return Interval(0.0, 0.0, 0.0, 0)
    p = successes / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return Interval(p, max(0.0, centre - half), min(1.0, centre + half), n)


def bootstrap_interval(
    items: Sequence,
    statistic: Callable[[Sequence], float],
    resamples: int = DEFAULT_RESAMPLES,
    alpha: float = 0.05,
    seed: int = DEFAULT_SEED,
) -> Interval:
    """Percentile bootstrap for any statistic over a set of items.

    Used for corpus-level metrics such as chrF++ and macro-F1, which are not
    means of per-item scores and so have no closed-form interval.
    """
    if not items:
        return Interval(0.0, 0.0, 0.0, 0)
    rng = np.random.default_rng(seed)
    n = len(items)
    idx = np.arange(n)
    draws = [statistic([items[i] for i in rng.choice(idx, size=n, replace=True)])
             for _ in range(resamples)]
    return Interval(
        point=statistic(list(items)),
        low=float(np.percentile(draws, 100 * alpha / 2)),
        high=float(np.percentile(draws, 100 * (1 - alpha / 2))),
        n=n,
    )


def paired_bootstrap_test(
    items_a: Sequence,
    items_b: Sequence,
    statistic: Callable[[Sequence], float],
    resamples: int = DEFAULT_RESAMPLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, float]:
    """Two-sided paired bootstrap over the *same* items scored by two systems.

    Pairing matters: item difficulty varies enormously across this benchmark,
    so an unpaired test would attribute to the models a difference that is
    really the luck of which items each happened to get.
    """
    if len(items_a) != len(items_b):
        raise ValueError("paired test requires aligned item lists")
    if not items_a:
        return {"observed_diff": 0.0, "p_value": 1.0, "n": 0}

    rng = np.random.default_rng(seed)
    n = len(items_a)
    idx = np.arange(n)
    observed = statistic(list(items_a)) - statistic(list(items_b))

    count = 0
    for _ in range(resamples):
        pick = rng.choice(idx, size=n, replace=True)
        diff = statistic([items_a[i] for i in pick]) - statistic([items_b[i] for i in pick])
        # Centre on the observed difference: under the null the resampled
        # differences should scatter around it, so we count how often the
        # deviation is at least as large as the observation itself.
        if abs(diff - observed) >= abs(observed):
            count += 1
    return {"observed_diff": observed, "p_value": count / resamples, "n": n}


def mcnemar_test(correct_a: Sequence[bool], correct_b: Sequence[bool]) -> dict[str, float]:
    """Exact McNemar test for two classifiers on identical items.

    The right test for paired binary outcomes (MCQ, sentiment): it looks only at
    the items where the two models disagree, which is where the evidence is.
    """
    from scipy import stats

    if len(correct_a) != len(correct_b):
        raise ValueError("McNemar requires aligned item lists")
    b = sum(1 for a, c in zip(correct_a, correct_b) if a and not c)
    c = sum(1 for a, cc in zip(correct_a, correct_b) if not a and cc)
    n = b + c
    if n == 0:
        return {"b": 0, "c": 0, "p_value": 1.0}
    p = min(1.0, 2 * stats.binom.cdf(min(b, c), n, 0.5))
    return {"b": float(b), "c": float(c), "p_value": float(p)}


def holm_bonferroni(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Holm-Bonferroni correction across a family of comparisons.

    A full model-by-task grid runs dozens of tests, so at alpha=0.05 several
    "significant" results are expected by chance alone. Holm is uniformly more
    powerful than plain Bonferroni while controlling the same family-wise error
    rate, so there is no reason to prefer the latter.
    """
    ordered = sorted(pvalues.items(), key=lambda kv: kv[1])
    m = len(ordered)
    out: dict[str, dict] = {}
    max_so_far = 0.0
    for i, (key, p) in enumerate(ordered):
        adjusted = min(1.0, (m - i) * p)
        # Enforce monotonicity: an adjusted p-value may never fall below one
        # assigned to a smaller raw p-value.
        max_so_far = max(max_so_far, adjusted)
        out[key] = {
            "p_raw": p,
            "p_adjusted": max_so_far,
            "significant": max_so_far < alpha,
        }
    return out


def cohens_h(p1: float, p2: float) -> float:
    """Effect size for a difference between two proportions.

    Reported alongside p-values: with thousands of items a trivial difference
    can be significant, and the size of the gap is what a reader actually needs.
    """
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
