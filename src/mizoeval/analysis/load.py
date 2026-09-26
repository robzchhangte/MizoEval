"""Discover and load completed evaluation runs from results/raw/.

The manifest written by `run_task.py` already carries a quick summary (see its
`_summarise`), but that summary uses a cheap 200-resample bootstrap and omits
cross-model comparisons. Tables built for the paper recompute every statistic
from the raw per-item records at the full resample count, so a manifest is
used here only to locate and identify a run -- never as the source of a
reported number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "results" / "raw"

# Models with a paper-quality run: gemini-flash / gpt-5 / qwen3 / deepseek-v3
# are legacy roster aliases that were never run (superseded by the pinned
# gemini-3.5-flash / gpt-5.4 / gpt-5.4-mini snapshots); llama-3.1-8b and
# qwen-2.5-14b were never run. Filtering here keeps stray manifests from an
# abandoned model name out of every table without hand-editing each one.
LLM_MODELS = ["gpt-5.4-mini", "gpt-5.4", "gemini-3.5-flash", "gemma4-31b", "gpt-oss-120b"]
MT_ONLY_MODELS = ["nllb-200-3.3b"]
ALL_MODELS = LLM_MODELS + MT_ONLY_MODELS

# MT five-shot is out of scope for this study (decided 2026-09-26): only
# gemma4-31b / gpt-oss-120b / nllb-200-3.3b have complete five-shot MT from
# before that decision. gemini-3.5-flash, gpt-5.4-mini and gpt-5.4 have
# partial five-shot MT samples that must not be reported as results.
MT_FIVE_SHOT_COMPLETE_MODELS = ["gemma4-31b", "gpt-oss-120b", "nllb-200-3.3b"]


@dataclass
class Run:
    run_key: str
    task: str
    regime: str
    model: str
    variant: str  # "" for the headline cell, else e.g. "permuted", "all", "en2mz"
    manifest: dict[str, Any]
    jsonl_path: Path

    @property
    def n_items(self) -> int:
        return self.manifest.get("n_items", 0)


def _classify(manifest: dict[str, Any]) -> tuple[str, str]:
    """Return (model, variant) parsed out of the manifest's own fields.

    Reading `cli` args rather than re-parsing the run_key string avoids
    duplicating `_run_key`'s ordering logic and stays correct if that ordering
    ever changes.
    """
    cli = manifest.get("cli", {})
    model = manifest.get("model_name", cli.get("model", "unknown"))
    task = manifest["task"]
    parts = []
    if task == "mt":
        parts.append(cli.get("direction") or "nodir")
    if task == "ner":
        split = cli.get("ner_split", "test")
        parts.append(("docsplit-" if cli.get("docsplit") else "") + split)
    if task == "mcq":
        subset = cli.get("mcq_subset", "mcq4")
        if subset not in ("mcq4", None):
            parts.append(subset)
        if cli.get("permuted"):
            parts.append("permuted")
    return model, "__".join(parts)


def discover_runs(raw_dir: Path = RAW_DIR, models: list[str] | None = None) -> list[Run]:
    """Scan results/raw/ for every (task, regime, model, variant) manifest.

    Deliberately does not filter out partial runs (`budget_stopped: true` or
    a nonzero `n_api_errors`) -- "complete enough to report" is a per-table
    judgement call, not a fixed rule, so callers filter on `Run.manifest`
    fields themselves.
    """
    runs: list[Run] = []
    for mpath in sorted(raw_dir.glob("*.manifest.json")):
        try:
            manifest = json.loads(mpath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        model, variant = _classify(manifest)
        if models is not None and model not in models:
            continue
        jsonl_path = mpath.with_suffix("").with_suffix(".jsonl")
        if not jsonl_path.exists():
            continue
        runs.append(Run(
            run_key=manifest.get("run_key", mpath.stem),
            task=manifest["task"], regime=manifest["regime"],
            model=model, variant=variant,
            manifest=manifest, jsonl_path=jsonl_path,
        ))
    return runs


def load_records(run: Run) -> list[dict[str, Any]]:
    with run.jsonl_path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def find(runs: list[Run], *, task: str, model: str, regime: str,
         variant: str = "") -> Run | None:
    for r in runs:
        if r.task == task and r.model == model and r.regime == regime and r.variant == variant:
            return r
    return None
