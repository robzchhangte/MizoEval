"""Contamination probes for MizoEval.

The MT benchmark is 73% religious / 46% verbatim KJV scripture (see the repair
report), and both the KJV and the Mizo Bible have been on the open web for
years -- so frontier models have very likely memorised large parts of it.
Every uncorrected MT number is then inflated. These probes measure how much.

Three probes, all model-agnostic and API-only:

* ``verse_completion`` -- give the model the first half of a pair's text and
  measure how closely it reproduces the rest. Run per stratum: high fidelity on
  the scripture stratum together with low fidelity on the secular stratum is
  memorisation, not translation skill. An English-side pass over scripture is a
  positive control -- it *should* fire hard.

* ``mcq_canary`` -- show an MCQ stem with the options hidden and score free-form
  recall of the answer, with and without naming the source exam. Recall well
  above zero in the blind condition, or a positive guided-minus-blind gap,
  indicates the item was seen in training.

* ``temporal_split`` -- re-bucket an *already-run* MCQ result file by
  ``source_year`` (pre-2023 vs 2025-2026) and compare accuracy. No new API
  calls. The confound (only 1,341 / 1,870 items carry a year; 2025-2026
  dominates) is recorded in the output.

``calibrate`` checks the completion probe separates a famous KJV verse from
freshly-written Mizo sentences -- without both ends it proves nothing.
"""

from __future__ import annotations

import random
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Sequence

import sacrebleu

from mizoeval.datasets.loaders import load_mcq, load_mt
from mizoeval.metrics.stats import wilson_interval
from mizoeval.models.base import Message
from mizoeval.models.providers import ModelClient
from mizoeval.models.roster import get_spec

SEED = 20260907

# Freshly written, mundane Mizo sentences -- not from any public corpus. Used by
# ``calibrate`` as the negative control for the completion probe.
FRESH_MIZO = [
    "Tunikarah chaw kan ei dawn a, ka u chuan bekari atangin chhang a lei belh ang.",
    "Zirlai naupangte chu naktuk zingah bus hmun ah an inhmawn dawn a, zaninah ruh an nei lo.",
    "Ka pa'n inah kar hnih chhung mikhual a lo awm dawn avangin thing a sat belh a.",
    "Vawiin khan ruahtui a sur nasa em avangin kan huanah balhla te a chhiat zo vek.",
]
# A canonical, near-universally quoted KJV verse -- the positive control.
KJV_ANCHOR = (
    "For God so loved the world, that he gave his only begotten Son, "
    "that whosoever believeth in him should not perish, but have everlasting life."
)


def _ci(iv) -> list[float]:
    return [round(iv.low, 4), round(iv.high, 4)]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _split_at_fraction(text: str, frac: float) -> tuple[str, str]:
    """Split on whitespace-token boundary; prefix is ~``frac`` of the tokens."""
    toks = (text or "").split()
    if len(toks) < 4:
        return text, ""
    cut = max(1, min(len(toks) - 1, round(len(toks) * frac)))
    return " ".join(toks[:cut]), " ".join(toks[cut:])


def _completion_fidelity(pred: str, gold: str) -> dict[str, float]:
    """How close is ``pred`` to the withheld ``gold`` continuation?

    ``chrf`` is the primary number (character n-gram F-score, language-agnostic,
    sensible for Mizo morphology). ``prefix_frac`` is the fraction of gold
    whitespace tokens reproduced verbatim, in order, from the start -- a blunt
    but very legible "did it recite it" signal.
    """
    gold_n, pred_n = _norm(gold), _norm(pred)
    if not gold_n:
        return {"chrf": 0.0, "prefix_frac": 0.0}
    chrf = sacrebleu.sentence_chrf(pred_n, [gold_n]).score  # 0..100
    g, p = gold_n.split(), pred_n.split()
    i = 0
    while i < len(g) and i < len(p) and g[i] == p[i]:
        i += 1
    return {"chrf": round(chrf, 2), "prefix_frac": round(i / len(g), 4)}


# --------------------------------------------------------------------------- 1


@dataclass
class ProbeRun:
    probe: str
    model: str
    params: dict[str, Any]
    items: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _client(model: str, cache_path=None) -> ModelClient:
    from mizoeval.models.cache import ResponseCache

    return ModelClient(get_spec(model), cache=ResponseCache(cache_path))


def verse_completion(
    model: str,
    strata: Sequence[str] = ("scripture", "religious", "secular"),
    sides: Sequence[str] = ("mz", "en"),
    n_per_stratum: int = 150,
    frac: float = 0.5,
    seed: int = SEED,
    cache_path=None,
    client: ModelClient | None = None,
) -> ProbeRun:
    """Prefix-completion memorisation probe over the MT strata."""
    cl = client or _client(model, cache_path)
    rng = random.Random(seed)
    run = ProbeRun("verse_completion", model,
                   {"n_per_stratum": n_per_stratum, "frac": frac, "sides": list(sides),
                    "strata": list(strata), "seed": seed})

    for stratum in strata:
        pool = load_mt(stratum)
        pick = rng.sample(pool, min(n_per_stratum, len(pool)))
        for side in sides:
            for row in pick:
                prefix, suffix = _split_at_fraction(row[side], frac)
                if not suffix:
                    continue
                lang = "Mizo" if side == "mz" else "English"
                sys = (f"You continue {lang} text exactly as it was written. "
                       f"Output only the continuation, no preamble.")
                usr = f"Continue this {lang} passage:\n\n{prefix}"
                resp = cl.chat([Message("system", sys), Message("user", usr)], max_tokens=256)
                fid = _completion_fidelity(resp.text, suffix)
                run.items.append({
                    "id": row["id"], "stratum": stratum, "side": side,
                    "prefix": prefix, "gold_suffix": suffix, "pred_suffix": resp.text,
                    "cached": resp.cached, "error": resp.error, **fid,
                })

    run.summary = _summarise_completion(run.items)
    return run


def _summarise_completion(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    cells: dict[tuple[str, str], list[dict]] = {}
    for it in items:
        if it.get("error"):
            continue
        cells.setdefault((it["side"], it["stratum"]), []).append(it)

    by_cell = {}
    for (side, stratum), rows in sorted(cells.items()):
        by_cell[f"{side}/{stratum}"] = {
            "n": len(rows),
            "mean_chrf": round(sum(r["chrf"] for r in rows) / len(rows), 2),
            "mean_prefix_frac": round(sum(r["prefix_frac"] for r in rows) / len(rows), 4),
            "verbatim_rate": round(sum(1 for r in rows if r["prefix_frac"] >= 0.8) / len(rows), 4),
        }

    out: dict[str, Any] = {"by_cell": by_cell}
    for side in {s for s, _ in cells}:
        scr = by_cell.get(f"{side}/scripture")
        sec = by_cell.get(f"{side}/secular")
        if scr and sec:
            out[f"{side}_scripture_minus_secular_chrf"] = round(
                scr["mean_chrf"] - sec["mean_chrf"], 2)
            out[f"{side}_scripture_minus_secular_verbatim"] = round(
                scr["verbatim_rate"] - sec["verbatim_rate"], 4)
    return out


# --------------------------------------------------------------------------- 2


def _answer_hit(response: str, gold_text: str, distractors: Sequence[str]) -> bool:
    """Free-text answer counts as recall iff it matches the gold option more
    closely than any distractor (chrF), and that match is not marginal."""
    r = _norm(response)
    if not r:
        return False
    g = sacrebleu.sentence_chrf(r, [_norm(gold_text)]).score
    d = max((sacrebleu.sentence_chrf(r, [_norm(x)]).score for x in distractors), default=0.0)
    return g >= 45.0 and g - d >= 10.0


def mcq_canary(
    model: str,
    n: int = 300,
    seed: int = SEED,
    cache_path=None,
    client: ModelClient | None = None,
) -> ProbeRun:
    """Options-hidden recall, blind vs. source-exam-guided."""
    cl = client or _client(model, cache_path)
    rng = random.Random(seed)
    pool = [r for r in load_mcq("mcq4")
            if r.get("answer_text") and len(r["answer_text"].split()) <= 12]
    pick = rng.sample(pool, min(n, len(pool)))
    run = ProbeRun("mcq_canary", model, {"n": len(pick), "seed": seed})

    sys = ("You are taking a competitive exam. Answer with the correct option's "
           "text only -- a few words, no explanation. If you do not know, say UNKNOWN.")
    for r in pick:
        distr = [v for k, v in r["choices"].items() if k != r["answer"]]
        rec: dict[str, Any] = {"id": r["id"], "category": r["category"],
                               "answer_text": r["answer_text"]}
        for cond in ("blind", "guided"):
            if cond == "blind":
                usr = f"Question: {r['question']}\nAnswer:"
            else:
                src = r.get("source_exam") or "a Mizoram Public Service Commission exam"
                yr = r.get("source_year")
                usr = (f"The following question is from {src}"
                       f"{f' ({yr})' if yr else ''}.\n"
                       f"Question: {r['question']}\nAnswer:")
            resp = cl.chat([Message("system", sys), Message("user", usr)], max_tokens=64)
            rec[cond] = {
                "response": resp.text, "cached": resp.cached, "error": resp.error,
                "hit": _answer_hit(resp.text, r["answer_text"], distr),
            }
        run.items.append(rec)

    run.summary = _summarise_canary(run.items)
    return run


def _summarise_canary(items: Sequence[dict[str, Any]]) -> dict[str, Any]:
    usable = [it for it in items
              if not it["blind"].get("error") and not it["guided"].get("error")]
    n = len(usable)
    if not n:
        return {"n": 0}
    blind = sum(it["blind"]["hit"] for it in usable)
    guided = sum(it["guided"]["hit"] for it in usable)
    return {
        "n": n,
        "blind_recall": round(blind / n, 4),
        "blind_recall_ci": _ci(wilson_interval(blind, n)),
        "guided_recall": round(guided / n, 4),
        "guided_recall_ci": _ci(wilson_interval(guided, n)),
        "guided_minus_blind": round((guided - blind) / n, 4),
    }


# --------------------------------------------------------------------------- 3


def temporal_split(
    records: Sequence[dict[str, Any]],
    pre_max_year: int = 2022,
    recent_years: Sequence[int] = (2025, 2026),
) -> dict[str, Any]:
    """Re-bucket an already-run MCQ result list by ``source_year``.

    ``records`` are rows from a ``results/raw/mcq__*.jsonl`` file (need ``id``,
    ``gold``, ``predicted``). Year comes from the processed MCQ set, joined on id.
    """
    year_by_id = {r["id"]: r.get("source_year") for r in load_mcq("all")}

    def bucket_acc(keep) -> dict[str, Any]:
        rows = [r for r in records
                if (y := year_by_id.get(r["id"])) is not None and keep(y)]
        graded = [r for r in rows if r.get("predicted") is not None]
        correct = sum(1 for r in graded if r["predicted"] == r["gold"])
        n = len(graded)
        return {
            "n_items": len(rows), "n_graded": n,
            "accuracy": round(correct / n, 4) if n else None,
            "accuracy_ci": _ci(wilson_interval(correct, n)) if n else None,
        }

    pre = bucket_acc(lambda y: y <= pre_max_year)
    recent = bucket_acc(lambda y: y in set(recent_years))
    delta = (None if pre["accuracy"] is None or recent["accuracy"] is None
             else round(pre["accuracy"] - recent["accuracy"], 4))
    return {
        "pre_max_year": pre_max_year, "recent_years": list(recent_years),
        "pre_2023": pre, "recent": recent,
        "pre_minus_recent": delta,
        "n_year_unknown": sum(1 for r in records if year_by_id.get(r["id"]) is None),
        "note": ("Only items carrying a source_year are used; 2025-2026 dominates "
                 "the dated pool and the pre-2023 bucket is small. Read the deltas "
                 "with the per-bucket N in view."),
    }


# --------------------------------------------------------------------------- calibration


def calibrate(model: str, cache_path=None, client: ModelClient | None = None) -> dict[str, Any]:
    """The completion probe must fire on known-memorised text and stay quiet on
    freshly-written Mizo. Returns both ends plus a pass/fail."""
    cl = client or _client(model, cache_path)

    def complete(text: str, lang: str) -> dict[str, float]:
        prefix, suffix = _split_at_fraction(text, 0.5)
        sys = (f"You continue {lang} text exactly as it was written. "
               f"Output only the continuation, no preamble.")
        resp = cl.chat([Message("system", sys),
                        Message("user", f"Continue this {lang} passage:\n\n{prefix}")],
                       max_tokens=256)
        return _completion_fidelity(resp.text, suffix)

    kjv = complete(KJV_ANCHOR, "English")
    fresh = [complete(s, "Mizo") for s in FRESH_MIZO]
    fresh_chrf = sum(f["chrf"] for f in fresh) / len(fresh)
    return {
        "model": model,
        "kjv_anchor": kjv,
        "fresh_mizo_mean": {"chrf": round(fresh_chrf, 2),
                            "prefix_frac": round(sum(f["prefix_frac"] for f in fresh) / len(fresh), 4)},
        "separates": kjv["chrf"] - fresh_chrf >= 30.0,
    }
