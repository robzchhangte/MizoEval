"""Run the full evaluation matrix (configs/tasks.yaml) for one or more models.

Each cell is dispatched to `run_task.main`, which caches every model call, so
the matrix is resumable: stop it any time and re-run, and completed cells cost
nothing on the second pass. A progress line is printed per cell and a
`results/raw/_matrix_progress.json` file tracks what has finished.

    python -m mizoeval.runners.run_matrix --model gemma4-31b
    python -m mizoeval.runners.run_matrix --model gemma4-31b --only mcq,sentiment
    python -m mizoeval.runners.run_matrix --all-enabled
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import traceback
from pathlib import Path

import yaml

from mizoeval.models.roster import load_roster
from mizoeval.runners import run_task

ROOT = Path(__file__).resolve().parents[3]
MATRIX = ROOT / "configs" / "tasks.yaml"
PROGRESS = ROOT / "results" / "raw" / "_matrix_progress.json"


def _cell_argv(cell: dict, model: str) -> list[str]:
    argv = ["--task", cell["task"], "--regime", cell["regime"], "--model", model]
    if cell.get("direction"):
        argv += ["--direction", cell["direction"]]
    if cell.get("mcq_subset"):
        argv += ["--mcq-subset", cell["mcq_subset"]]
    if cell.get("permuted"):
        argv += ["--permuted"]
    if cell.get("ner_split"):
        argv += ["--ner-split", cell["ner_split"]]
    if cell.get("docsplit"):
        argv += ["--docsplit"]
    return argv


def _manifest_spent(manifest: dict) -> int:
    """Tokens a finished cell actually spent on live calls (cache hits are free)."""
    tb = manifest.get("token_budget") or {}
    return int(
        tb.get("spent")
        or manifest.get("prompt_tokens", 0) + manifest.get("completion_tokens", 0)
    )


def _load_progress() -> dict:
    if PROGRESS.exists():
        return json.loads(PROGRESS.read_text(encoding="utf-8"))
    return {}


def _save_progress(p: dict) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    PROGRESS.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", action="append", default=[], help="roster name; repeatable")
    ap.add_argument("--all-enabled", action="store_true",
                    help="run every enabled model in configs/models.yaml (except mock)")
    ap.add_argument("--only", default="", help="comma-separated task filter, e.g. mcq,mt")
    ap.add_argument("--matrix", type=Path, default=MATRIX)
    ap.add_argument("--limit", type=int, default=0, help="cap items per cell (for a dry run)")
    ap.add_argument("--token-budget", type=int, default=0,
                    help="hard cap on total tokens across the WHOLE matrix run (per model). "
                         "Each cell gets the remaining budget; when it reaches 0 the matrix "
                         "stops. 0 = no cap.")
    ap.add_argument("--cache", type=Path, default=None, help="response-cache path")
    ap.add_argument("--stop-on-error", action="store_true")
    args = ap.parse_args(argv)

    models = list(args.model)
    if args.all_enabled:
        models += [s.name for s in load_roster() if s.provider != "mock"]
    models = list(dict.fromkeys(models))
    if not models:
        ap.error("give --model NAME (repeatable) or --all-enabled")

    cells = yaml.safe_load(args.matrix.read_text(encoding="utf-8"))["cells"]
    if args.only:
        keep = {t.strip() for t in args.only.split(",")}
        cells = [c for c in cells if c["task"] in keep]

    progress = _load_progress()
    total = len(models) * len(cells)
    done = 0
    started = dt.datetime.now(dt.timezone.utc)
    print(f"matrix: {len(models)} model(s) x {len(cells)} cell(s) = {total} runs")
    print(f"models: {', '.join(models)}\n")

    for model in models:
        spent = 0  # cumulative tokens for THIS model across cells (paid calls only)
        for cell in cells:
            done += 1
            cell_argv = _cell_argv(cell, model)
            if args.limit:
                cell_argv += ["--limit", str(args.limit)]
            if args.cache:
                cell_argv += ["--cache", str(args.cache)]
            if args.token_budget:
                remaining = args.token_budget - spent
                if remaining <= 0:
                    print(f"[{done}/{total}] {model} :: token budget "
                          f"({args.token_budget:,}) reached after {spent:,} — stopping this model")
                    break
                cell_argv += ["--token-budget", str(remaining)]
            key = " ".join(cell_argv)
            tag = f"[{done}/{total}] {model} :: {cell['task']}/{cell['regime']}" + (
                f"/{cell.get('direction') or cell.get('mcq_subset') or cell.get('ner_split') or ''}"
            ) + (" +permuted" if cell.get("permuted") else "") + (
                " +docsplit" if cell.get("docsplit") else "")
            print(f"{tag}")
            try:
                manifest = run_task.main(cell_argv)
                spent += _manifest_spent(manifest or {})
                stopped = bool((manifest or {}).get("budget_stopped"))
                progress[key] = {"status": "ok", "budget_stopped": stopped,
                                 "at": dt.datetime.now(dt.timezone.utc).isoformat()}
                if stopped:
                    print(f"    token budget hit inside this cell "
                          f"({spent:,} / {args.token_budget:,}) — stopping this model")
                    break
            except Exception as exc:  # noqa: BLE001 - keep the matrix going past one bad cell
                progress[key] = {"status": "error", "error": f"{type(exc).__name__}: {exc}",
                                 "at": dt.datetime.now(dt.timezone.utc).isoformat()}
                print(f"    ERROR: {exc}")
                if args.stop_on_error:
                    _save_progress(progress)
                    raise
                traceback.print_exc()
            _save_progress(progress)

    elapsed = dt.datetime.now(dt.timezone.utc) - started
    ok = sum(1 for v in progress.values() if v["status"] == "ok")
    err = sum(1 for v in progress.values() if v["status"] == "error")
    print(f"\ndone in {elapsed}. cells ok={ok} error={err}. progress: {PROGRESS}")


if __name__ == "__main__":
    main()
