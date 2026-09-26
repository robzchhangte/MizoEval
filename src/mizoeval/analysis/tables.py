"""Build every table the paper cites, straight from results/raw/.

Every number here traces back to a specific `Run` (task, regime, model,
variant) via `load.discover_runs`, and every interval/test is recomputed at
full resample count from the per-item records -- never taken from a
manifest's quick summary. That is what lets a reviewer, or a future revision
of this paper, verify a headline number by re-running this module rather than
re-reading a paragraph.

CLI:
    python -m mizoeval.analysis.tables
"""

from __future__ import annotations

import csv
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

import pandas as pd

from mizoeval.analysis.load import (
    ALL_MODELS,
    LLM_MODELS,
    MT_FIVE_SHOT_COMPLETE_MODELS,
    RAW_DIR,
    Run,
    discover_runs,
    find,
    load_records,
)
from mizoeval.metrics.stats import bootstrap_interval, holm_bonferroni, mcnemar_test, wilson_interval
from mizoeval.metrics.tasks import (
    position_bias,
    score_mcq,
    score_mt_by_stratum,
    score_ner,
    score_sentiment,
)

ROOT = Path(__file__).resolve().parents[3]
TABLES_DIR = ROOT / "results" / "tables"

RESAMPLES = 1000  # full count; the manifest's own summary uses 200 as a quick check only

# (task, regime, variant, display_label) -- the headline non-MT cells, in the
# order the paper's Table 1 presents them.
HEADLINE_CELLS: list[tuple[str, str, str, str]] = [
    ("mcq", "zero_shot", "", "MCQ zero-shot"),
    ("mcq", "zero_shot", "permuted", "MCQ zero-shot (permuted)"),
    ("mcq", "five_shot", "", "MCQ five-shot"),
    ("mcq", "zero_shot", "all", "MCQ zero-shot (all formats)"),
    ("mcq", "cot", "", "MCQ CoT"),
    ("mcq", "cot", "permuted", "MCQ CoT (permuted)"),
    ("sentiment", "zero_shot", "", "Sentiment zero-shot"),
    ("sentiment", "five_shot", "", "Sentiment five-shot"),
    ("ner", "few_shot", "test", "NER (official test)"),
    ("ner", "few_shot", "docsplit-test", "NER (document-disjoint test)"),
]


def _fmt(point: float, low: float, high: float) -> str:
    return f"{point:.3f} [{low:.3f}, {high:.3f}]"


# --------------------------------------------------------------------------- Table 1: main grid


def build_main_results(runs: list[Run]) -> pd.DataFrame:
    """Tidy long-format table: one row per (model, cell, metric)."""
    rows: list[dict[str, Any]] = []
    for model in ALL_MODELS:
        for task, regime, variant, label in HEADLINE_CELLS:
            run = find(runs, task=task, model=model, regime=regime, variant=variant)
            if run is None:
                continue
            records = load_records(run)
            if task == "mcq":
                r = score_mcq(records)
                rows.append({"model": model, "cell": label, "metric": "accuracy",
                             "point": r.accuracy.point, "ci_low": r.accuracy.low,
                             "ci_high": r.accuracy.high, "n": r.n,
                             "parse_failure_rate": r.parse_failure_rate})
            elif task == "sentiment":
                r = score_sentiment(records, resamples=RESAMPLES)
                rows.append({"model": model, "cell": label, "metric": "macro_f1",
                             "point": r.macro_f1.point, "ci_low": r.macro_f1.low,
                             "ci_high": r.macro_f1.high, "n": r.n,
                             "parse_failure_rate": r.parse_failure_rate})
            elif task == "ner":
                ok = [rec for rec in records if rec["parse_ok"]]
                r = score_ner([rec["gold_tags"] for rec in records],
                              [rec["pred_tags"] for rec in records],
                              parse_failures=len(records) - len(ok),
                              resamples=RESAMPLES)
                rows.append({"model": model, "cell": label, "metric": "micro_f1",
                             "point": r.micro_f1.point, "ci_low": r.micro_f1.low,
                             "ci_high": r.micro_f1.high,
                             "n": r.n_sentences, "parse_failure_rate": r.parse_failure_rate})
    return pd.DataFrame(rows)


def render_main_results_markdown(df: pd.DataFrame) -> str:
    """Pivot the tidy table into the model x cell grid a reader expects."""
    cells = [c[3] for c in HEADLINE_CELLS]
    models = [m for m in ALL_MODELS if m in df["model"].unique()]
    lines = ["| Model | " + " | ".join(cells) + " |",
             "|---" * (len(cells) + 1) + "|"]
    for model in models:
        row = [model]
        for cell in cells:
            sub = df[(df["model"] == model) & (df["cell"] == cell)]
            if sub.empty:
                row.append("--")
            else:
                r = sub.iloc[0]
                if r["ci_low"] is not None and pd.notna(r["ci_low"]):
                    row.append(f"{r['point']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]")
                else:
                    row.append(f"{r['point']:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------- position bias


def build_position_bias(runs: list[Run]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for model in LLM_MODELS:
        zs = find(runs, task="mcq", model=model, regime="zero_shot", variant="")
        perm = find(runs, task="mcq", model=model, regime="zero_shot", variant="permuted")
        if zs is None or perm is None:
            continue
        zs_records = load_records(zs)
        perm_records = load_records(perm)
        zs_r = score_mcq(zs_records)
        perm_r = score_mcq(perm_records)
        zs_bias = position_bias(zs_records)
        perm_bias = position_bias(perm_records)

        # Paired McNemar restricted to the item ids both variants share --
        # a permuted item's re-lettered choices are still the same underlying
        # question, so "correct" is comparable id-for-id.
        by_id_zs = {r["id"]: r["predicted"] == r["gold"] for r in zs_records}
        by_id_perm = {r["id"]: r["predicted"] == r["gold"] for r in perm_records}
        shared = sorted(set(by_id_zs) & set(by_id_perm))
        mcnemar = mcnemar_test([by_id_zs[i] for i in shared], [by_id_perm[i] for i in shared])

        rows.append({
            "model": model,
            "zero_shot_accuracy": zs_r.accuracy.point,
            "permuted_accuracy": perm_r.accuracy.point,
            "delta": zs_r.accuracy.point - perm_r.accuracy.point,
            "zero_shot_max_deviation_from_uniform": zs_bias.get("max_deviation_from_uniform"),
            "permuted_max_deviation_from_uniform": perm_bias.get("max_deviation_from_uniform"),
            "mcnemar_p_raw": mcnemar["p_value"],
            "n_paired": len(shared),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        adj = holm_bonferroni(dict(zip(df["model"], df["mcnemar_p_raw"])))
        df["mcnemar_p_adjusted"] = df["model"].map(lambda m: adj[m]["p_adjusted"])
        df["significant"] = df["model"].map(lambda m: adj[m]["significant"])
    return df


# --------------------------------------------------------------------------- MT contamination


def _score_mt_cell(payload: tuple[str, str, str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Worker for one (model, direction, regime) cell -- run in its own process.

    The MT contamination table is the module's slowest step: 1000-resample
    bootstrap chrF over every (model, direction, regime, stratum) combination
    is tens of thousands of sacrebleu calls run serially. Each cell is
    independent of every other, so scoring them in a process pool turns wall
    time into (work / core_count) instead of (work / 1). Everything returned
    is a plain dict of floats/ints, not a dataclass, so it pickles cleanly
    back to the parent regardless of platform or multiprocessing start method.
    """
    model, direction, regime, records = payload
    by_stratum = score_mt_by_stratum(records)
    return {
        "model": model, "direction": direction, "regime": regime,
        "by_stratum": {
            s: {"chrf": r.chrf.point, "chrf_low": r.chrf.low, "chrf_high": r.chrf.high,
                "bleu": r.bleu, "n": r.n, "empty_output_rate": r.empty_output_rate}
            for s, r in by_stratum.items()
        },
    }


def build_mt_contamination(
    runs: list[Run], include_five_shot: bool = True, workers: int | None = None,
) -> pd.DataFrame:
    payloads: list[tuple[str, str, str, list[dict[str, Any]]]] = []
    regimes = ["zero_shot"] + (["five_shot"] if include_five_shot else [])
    for model in ALL_MODELS:
        for direction in ("mz2en", "en2mz"):
            for regime in regimes:
                if regime == "five_shot" and model not in MT_FIVE_SHOT_COMPLETE_MODELS:
                    continue  # partial five-shot samples are out of scope; see load.py
                run = find(runs, task="mt", model=model, regime=regime, variant=direction)
                if run is None:
                    continue
                payloads.append((model, direction, regime, load_records(run)))

    workers = workers or os.cpu_count() or 1
    rows: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(_score_mt_cell, payloads):
            strata = {s: v["chrf"] for s, v in result["by_stratum"].items()}
            for stratum, v in result["by_stratum"].items():
                rows.append({
                    "model": result["model"], "direction": result["direction"],
                    "regime": result["regime"], "stratum": stratum,
                    "chrf": v["chrf"], "chrf_ci_low": v["chrf_low"], "chrf_ci_high": v["chrf_high"],
                    "bleu": v["bleu"], "n": v["n"], "empty_output_rate": v["empty_output_rate"],
                    "gap_vs_scripture": strata.get("scripture", float("nan")) - strata.get("secular", float("nan")),
                    "gap_vs_religious": strata.get("religious", float("nan")) - strata.get("secular", float("nan")),
                })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- baselines


def build_baselines(runs: list[Run]) -> pd.DataFrame:
    """Majority-class / majority-position baselines, derived from gold labels.

    Gold labels are identical across every model's run of the same cell, so
    any one available run supplies them -- the choice of model here has no
    effect on the baseline value.
    """
    rows: list[dict[str, Any]] = []

    mcq_run = next((find(runs, task="mcq", model=m, regime="zero_shot", variant="")
                     for m in ALL_MODELS), None)
    mcq_run = mcq_run or next((r for r in runs if r.task == "mcq" and r.variant == ""), None)
    if mcq_run:
        records = load_records(mcq_run)
        gold = [r["gold"] for r in records]
        from collections import Counter
        counts = Counter(gold)
        majority_letter, majority_n = counts.most_common(1)[0]
        wi = wilson_interval(majority_n, len(gold))
        rows.append({"task": "mcq", "baseline": f"majority-position ({majority_letter})",
                      "value": wi.point, "ci_low": wi.low, "ci_high": wi.high, "n": len(gold)})
        rows.append({"task": "mcq", "baseline": "random (4-way)", "value": 0.25,
                      "ci_low": None, "ci_high": None, "n": len(gold)})

    sent_run = next((r for r in runs if r.task == "sentiment" and r.regime == "zero_shot"), None)
    if sent_run:
        records = load_records(sent_run)
        gold = [r["gold"] for r in records]
        from collections import Counter
        counts = Counter(gold)
        majority_label, majority_n = counts.most_common(1)[0]
        wi = wilson_interval(majority_n, len(gold))
        rows.append({"task": "sentiment", "baseline": f"majority-class ({majority_label})",
                      "value": wi.point, "ci_low": wi.low, "ci_high": wi.high, "n": len(gold)})

    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- pairwise significance (MCQ)


def build_mcq_pairwise_significance(runs: list[Run]) -> pd.DataFrame:
    """Holm-corrected McNemar between every pair of models, MCQ zero-shot mcq4."""
    per_model_correct: dict[str, dict[str, bool]] = {}
    for model in LLM_MODELS:
        run = find(runs, task="mcq", model=model, regime="zero_shot", variant="")
        if run is None:
            continue
        records = load_records(run)
        per_model_correct[model] = {r["id"]: r["predicted"] == r["gold"] for r in records}

    models = list(per_model_correct)
    pair_results: dict[tuple[str, str], dict[str, Any]] = {}
    for i, a in enumerate(models):
        for b in models[i + 1:]:
            shared = sorted(set(per_model_correct[a]) & set(per_model_correct[b]))
            res = mcnemar_test([per_model_correct[a][k] for k in shared],
                                [per_model_correct[b][k] for k in shared])
            pair_results[(a, b)] = {**res, "n_paired": len(shared)}

    pvalues = {f"{a}__vs__{b}": v["p_value"] for (a, b), v in pair_results.items()}
    adjusted = holm_bonferroni(pvalues)
    rows = []
    for (a, b), v in pair_results.items():
        key = f"{a}__vs__{b}"
        rows.append({"model_a": a, "model_b": b, "b": v["b"], "c": v["c"],
                      "n_paired": v["n_paired"], "p_raw": v["p_value"],
                      "p_adjusted": adjusted[key]["p_adjusted"],
                      "significant": adjusted[key]["significant"]})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- entrypoint


def main() -> None:
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    runs = discover_runs()

    main_df = build_main_results(runs)
    main_df.to_csv(TABLES_DIR / "table1_main_results.csv", index=False,
                    quoting=csv.QUOTE_MINIMAL)

    pos_bias_df = build_position_bias(runs)
    pos_bias_df.to_csv(TABLES_DIR / "position_bias.csv", index=False)

    mt_df = build_mt_contamination(runs)
    mt_df.to_csv(TABLES_DIR / "mt_contamination.csv", index=False)

    baselines_df = build_baselines(runs)
    baselines_df.to_csv(TABLES_DIR / "baselines.csv", index=False)

    sig_df = build_mcq_pairwise_significance(runs)
    sig_df.to_csv(TABLES_DIR / "mcq_pairwise_significance.csv", index=False)

    summary = ["# MizoEval — results tables\n",
               "Regenerate with `python -m mizoeval.analysis.tables`. Every number here is "
               "recomputed from `results/raw/*.jsonl` at the full 1000-resample bootstrap; "
               "none are copied from a run's own manifest.\n",
               "## Table 1: main results\n",
               render_main_results_markdown(main_df), "",
               "## Position bias (MCQ zero-shot vs. choice-permuted)\n",
               pos_bias_df.to_markdown(index=False) if not pos_bias_df.empty else "(no data)", "",
               "## MT by register (contamination signal)\n",
               mt_df.to_markdown(index=False) if not mt_df.empty else "(no data)", "",
               "## Baselines\n",
               baselines_df.to_markdown(index=False) if not baselines_df.empty else "(no data)", "",
               "## Pairwise MCQ significance (Holm-Bonferroni corrected)\n",
               sig_df.to_markdown(index=False) if not sig_df.empty else "(no data)", ""]
    (TABLES_DIR / "SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")

    print(f"wrote tables to {TABLES_DIR}")
    for name in ("table1_main_results.csv", "position_bias.csv", "mt_contamination.csv",
                 "baselines.csv", "mcq_pairwise_significance.csv", "SUMMARY.md"):
        print(f"  {name}")


if __name__ == "__main__":
    main()
