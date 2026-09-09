"""Run the contamination probes for one model and write results/contamination/.

    python -m mizoeval.contamination.run_probes --model gpt-5.4-mini
    python -m mizoeval.contamination.run_probes --model gemma4-31b --only verse,canary
    python -m mizoeval.contamination.run_probes --model gpt-5.4-mini --calibrate-only

Every model call goes through the shared SQLite response cache, so re-runs are
free and the probes are resumable. ``temporal`` needs no API calls -- it
re-buckets an existing results/raw/mcq__*.jsonl file by source_year.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
from pathlib import Path

from mizoeval.contamination import probes
from mizoeval.env import load_env
from mizoeval.models.cache import ResponseCache
from mizoeval.models.providers import ModelClient
from mizoeval.models.roster import get_spec

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "results" / "contamination"
RAW = ROOT / "results" / "raw"


def _write(name: str, payload: dict) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _mcq_records(model: str) -> list[dict] | None:
    """Prefer the all-format zero-shot file (widest year coverage), fall back to mcq4."""
    for stem in (f"mcq__zero_shot__{model}__all", f"mcq__zero_shot__{model}"):
        p = RAW / f"{stem}.jsonl"
        if p.exists():
            return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return None


def main(argv: list[str] | None = None) -> dict:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--model", required=True, help="a name from configs/models.yaml")
    ap.add_argument("--only", default="verse,canary,temporal",
                    help="comma list of: verse, canary, temporal")
    ap.add_argument("--n-verse", type=int, default=150, help="pairs per stratum per side")
    ap.add_argument("--n-canary", type=int, default=300)
    ap.add_argument("--frac", type=float, default=0.5, help="prefix fraction for completion")
    ap.add_argument("--cache", type=Path, default=None)
    ap.add_argument("--calibrate-only", action="store_true")
    ap.add_argument("--skip-calibrate", action="store_true")
    args = ap.parse_args(argv)

    load_env()
    want = {w.strip() for w in args.only.split(",") if w.strip()}
    cache = ResponseCache(args.cache)
    client = ModelClient(get_spec(args.model), cache=cache)
    stamp = dt.datetime.now(dt.timezone.utc).isoformat()
    written: dict[str, str] = {}
    result: dict = {"model": args.model, "at": stamp}

    if not args.skip_calibrate:
        cal = probes.calibrate(args.model, client=client)
        result["calibration"] = cal
        written["calibration"] = str(_write(f"{args.model}__calibration.json", cal))
        print(f"calibration: kjv chrf={cal['kjv_anchor']['chrf']} "
              f"fresh chrf={cal['fresh_mizo_mean']['chrf']} separates={cal['separates']}")
        if not cal["separates"] and not args.calibrate_only:
            print("  WARNING: probe does not cleanly separate memorised from fresh text; "
                  "completion numbers below are unreliable.")

    if args.calibrate_only:
        return result

    if "verse" in want:
        run = probes.verse_completion(args.model, n_per_stratum=args.n_verse,
                                      frac=args.frac, client=client)
        payload = dataclasses.asdict(run)
        written["verse_completion"] = str(_write(f"{args.model}__verse_completion.json", payload))
        result["verse_completion"] = run.summary
        print(f"verse_completion: {json.dumps(run.summary)}")

    if "canary" in want:
        run = probes.mcq_canary(args.model, n=args.n_canary, client=client)
        payload = dataclasses.asdict(run)
        written["mcq_canary"] = str(_write(f"{args.model}__mcq_canary.json", payload))
        result["mcq_canary"] = run.summary
        print(f"mcq_canary: {json.dumps(run.summary)}")

    if "temporal" in want:
        recs = _mcq_records(args.model)
        if recs is None:
            print(f"temporal: no results/raw/mcq__zero_shot__{args.model}[__all].jsonl -- "
                  f"run the MCQ cell first; skipping")
        else:
            ts = probes.temporal_split(recs)
            written["temporal_split"] = str(_write(f"{args.model}__temporal_split.json", ts))
            result["temporal_split"] = ts
            print(f"temporal_split: {json.dumps(ts)}")

    result["files"] = written
    print(f"\nwrote {len(written)} file(s) under {OUT}")
    return result


if __name__ == "__main__":
    main()
