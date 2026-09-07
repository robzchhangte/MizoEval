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
        for cell in cells:
            done += 1
            cell_argv = _cell_argv(cell, model)
            if args.limit:
                cell_argv += ["--limit", str(args.limit)]
            key = " ".join(cell_argv)
            tag = f"[{done}/{total}] {model} :: {cell['task']}/{cell['regime']}" + (
                f"/{cell.get('direction') or cell.get('mcq_subset') or cell.get('ner_split') or ''}"
            ) + (" +permuted" if cell.get("permuted") else "") + (
                " +docsplit" if cell.get("docsplit") else "")
            print(f"{tag}")
            try:
                run_task.main(cell_argv)
                progress[key] = {"status": "ok", "at": dt.datetime.now(dt.timezone.utc).isoformat()}
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
