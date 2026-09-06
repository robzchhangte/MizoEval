"""Run one (task, model, regime) evaluation and persist raw + parsed records.

Design rules:
- Every raw model reply is written to `results/raw/` before it is parsed, so a
  parser change never requires re-querying a model.
- The response cache makes an interrupted run resumable and a repeat run free
  and byte-identical.
- A manifest alongside the results records the model id, prompt-template
  hashes, seed, item count, parse-failure rate and cost, so any number in the
  paper can be traced back to the exact conditions that produced it.

CLI:
    python -m mizoeval.runners.run_task --task mcq --regime zero_shot --model mock --limit 5
    python -m mizoeval.runners.run_task --task mt --regime zero_shot --direction en2mz --model gpt-5-mini
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

from mizoeval.datasets import loaders as L
from mizoeval.metrics.tasks import score_mcq, score_mt_by_stratum, score_ner, score_sentiment
from mizoeval.models.base import Message
from mizoeval.models.cache import ResponseCache
from mizoeval.models.providers import ModelClient
from mizoeval.models.roster import get_spec
from mizoeval.parsing.answers import (
    align_spans_to_tokens,
    clean_translation,
    parse_entity_json,
    parse_mcq,
    parse_sentiment,
)
from mizoeval.prompts.templates import NER_TAG_DEFINITIONS, get_template

ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = ROOT / "results" / "raw"

SEED = 20260907
NER_TYPES = set(NER_TAG_DEFINITIONS)


# --------------------------------------------------------------------------- per-task drivers


def _run_mcq(client: ModelClient, regime: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    tmpl = get_template("mcq", regime)
    items = L.load_mcq(args.mcq_subset, permuted=args.permuted)
    exemplars = L.mcq_exemplars(5, seed=SEED, exclude_ids={i["id"] for i in items}) \
        if regime == "five_shot" else []
    if args.limit:
        items = items[: args.limit]

    out = []
    for it in items:
        user = tmpl.render(question=it["question"], choices=it["choices"], exemplars=exemplars)
        resp = client.chat([Message("system", tmpl.system), Message("user", user)],
                           max_tokens=768 if regime == "cot" else 16)
        parsed = parse_mcq(resp.text)
        out.append({
            "id": it["id"], "category": it.get("category"), "gold": it["answer"],
            "predicted": parsed.value, "parse_strategy": parsed.strategy,
            "raw_text": resp.text, "cached": resp.cached, "error": resp.error,
            "prompt_tokens": resp.prompt_tokens, "completion_tokens": resp.completion_tokens,
        })
    return out


def _run_sentiment(client: ModelClient, regime: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    tmpl = get_template("sentiment", regime)
    items = L.load_sentiment(exclude_fold=0) if regime == "five_shot" else L.load_sentiment()
    exemplars = L.sentiment_exemplars(6, seed=SEED, from_fold=0) if regime == "five_shot" else []
    if args.limit:
        items = items[: args.limit]

    out = []
    for it in items:
        user = tmpl.render(text=it["text"], exemplars=exemplars)
        resp = client.chat([Message("system", tmpl.system), Message("user", user)], max_tokens=16)
        parsed = parse_sentiment(resp.text)
        out.append({
            "id": it["id"], "gold": it["label"], "predicted": parsed.value,
            "parse_strategy": parsed.strategy, "oov_rate": it.get("oov_rate"),
            "raw_text": resp.text, "cached": resp.cached, "error": resp.error,
            "prompt_tokens": resp.prompt_tokens, "completion_tokens": resp.completion_tokens,
        })
    return out


def _run_mt(client: ModelClient, regime: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    if not args.direction:
        sys.exit("--direction en2mz or mz2en is required for the mt task")
    tmpl = get_template("mt", regime)
    src, tgt = args.direction.split("2")
    items = L.load_mt("all")
    exemplars = L.mt_exemplars(args.direction, 5, seed=SEED) if regime == "five_shot" else []
    if args.limit:
        items = items[: args.limit]

    out = []
    for it in items:
        source = it["en"] if src == "en" else it["mz"]
        reference = it["en"] if tgt == "en" else it["mz"]
        user = tmpl.render(source=source, direction=args.direction, exemplars=exemplars)
        resp = client.chat([Message("system", tmpl.system), Message("user", user)], max_tokens=512)
        out.append({
            "id": it["id"], "stratum": it["stratum"], "direction": args.direction,
            "source": source, "reference": reference,
            "hypothesis": clean_translation(resp.text),
            "raw_text": resp.text, "cached": resp.cached, "error": resp.error,
            "prompt_tokens": resp.prompt_tokens, "completion_tokens": resp.completion_tokens,
        })
    return out


def _run_ner(client: ModelClient, regime: str, args: argparse.Namespace) -> list[dict[str, Any]]:
    tmpl = get_template("ner", regime)
    sents = L.load_ner_conll(args.ner_split, docsplit=args.docsplit)
    exemplars = L.ner_exemplars(3, seed=SEED, docsplit=args.docsplit)
    if args.limit:
        sents = sents[: args.limit]

    out = []
    for s in sents:
        user = tmpl.render(tokens=s["tokens"], exemplars=exemplars)
        resp = client.chat([Message("system", tmpl.system), Message("user", user)], max_tokens=512)
        parsed = parse_entity_json(resp.text)
        if parsed.ok:
            pred_tags = align_spans_to_tokens(s["tokens"], parsed.value, NER_TYPES)
            parse_ok = True
        else:
            pred_tags = ["O"] * len(s["tokens"])
            parse_ok = False
        out.append({
            "sent_id": s.get("sent_id"), "url": s.get("url"),
            "tokens": s["tokens"], "gold_tags": s["tags"], "pred_tags": pred_tags,
            "parse_ok": parse_ok, "parse_strategy": parsed.strategy,
            "raw_text": resp.text, "cached": resp.cached, "error": resp.error,
            "prompt_tokens": resp.prompt_tokens, "completion_tokens": resp.completion_tokens,
        })
    return out


_DRIVERS = {"mcq": _run_mcq, "sentiment": _run_sentiment, "mt": _run_mt, "ner": _run_ner}


# --------------------------------------------------------------------------- scoring summary


def _summarise(task: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    """A quick score for the manifest. The authoritative analysis is separate."""
    try:
        if task == "mcq":
            r = score_mcq(records)
            return {"accuracy": r.accuracy.point, "accuracy_ci": [r.accuracy.low, r.accuracy.high],
                    "parse_failure_rate": r.parse_failure_rate, "n": r.n}
        if task == "sentiment":
            r = score_sentiment(records, resamples=200)
            return {"macro_f1": r.macro_f1.point, "accuracy": r.accuracy.point,
                    "parse_failure_rate": r.parse_failure_rate, "n": r.n}
        if task == "mt":
            by = score_mt_by_stratum(records)
            return {s: {"chrf": v.chrf.point, "bleu": v.bleu, "n": v.n} for s, v in by.items()}
        if task == "ner":
            ok = [rec for rec in records if rec["parse_ok"]]
            fails = len(records) - len(ok)
            r = score_ner([rec["gold_tags"] for rec in records],
                          [rec["pred_tags"] for rec in records], parse_failures=fails)
            return {"micro_f1": r.micro_f1, "macro_f1": r.macro_f1,
                    "parse_failure_rate": r.parse_failure_rate, "n": r.n_sentences}
    except Exception as exc:  # noqa: BLE001 - a summary failure must not lose the raw data
        return {"summary_error": f"{type(exc).__name__}: {exc}"}
    return {}


# --------------------------------------------------------------------------- entrypoint


def _run_key(args: argparse.Namespace) -> str:
    parts = [args.task, args.regime, args.model]
    if args.task == "mt":
        parts.append(args.direction or "nodir")
    if args.task == "ner":
        parts.append(("docsplit-" if args.docsplit else "") + args.ner_split)
    if args.task == "mcq" and args.permuted:
        parts.append("permuted")
    if args.limit:
        parts.append(f"limit{args.limit}")
    return "__".join(parts)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task", required=True, choices=list(_DRIVERS))
    ap.add_argument("--regime", required=True)
    ap.add_argument("--model", required=True, help="a name from configs/models.yaml")
    ap.add_argument("--direction", choices=["en2mz", "mz2en"], help="mt only")
    ap.add_argument("--mcq-subset", default="mcq4", help="mcq only: mcq4|all|tf|roman|other")
    ap.add_argument("--permuted", action="store_true", help="mcq only: choice-permuted variant")
    ap.add_argument("--ner-split", default="test", choices=["train", "valid", "test"])
    ap.add_argument("--docsplit", action="store_true", help="ner: document-disjoint re-split")
    ap.add_argument("--limit", type=int, default=0, help="cap items (smoke test); 0 = all")
    ap.add_argument("--temperature", type=float, default=None, help="override roster default")
    ap.add_argument("--no-cache", action="store_true", help="bypass the response cache")
    ap.add_argument("--cache", type=Path, default=None,
                    help="response-cache path (default: results/cache.sqlite)")
    ap.add_argument("--out-dir", type=Path, default=RAW_DIR)
    args = ap.parse_args(argv)

    spec = get_spec(args.model)
    client = ModelClient(spec, cache=ResponseCache(args.cache), use_cache=not args.no_cache)
    if args.temperature is not None:
        client.spec.params = {**(client.spec.params or {}), "temperature": args.temperature}

    tmpl = get_template(args.task, args.regime)
    started = dt.datetime.now(dt.timezone.utc)
    records = _DRIVERS[args.task](client, args.regime, args)
    finished = dt.datetime.now(dt.timezone.utc)

    errors = sum(1 for r in records if r.get("error"))
    manifest = {
        "run_key": _run_key(args),
        "task": args.task, "regime": args.regime,
        "model_name": spec.name, "model_id": spec.model_id, "provider": spec.provider,
        "params": client.spec.params,
        "template_id": tmpl.id, "template_hash": tmpl.hash, "template_system": tmpl.system,
        "seed": SEED,
        "n_items": len(records), "n_api_errors": errors,
        "cache_hits": client.n_cache_hits, "live_calls": client.n_calls,
        "cost_usd": round(client.cost_usd, 6),
        "prompt_tokens": sum(r.get("prompt_tokens", 0) for r in records),
        "completion_tokens": sum(r.get("completion_tokens", 0) for r in records),
        "started_utc": started.isoformat(), "finished_utc": finished.isoformat(),
        "summary": _summarise(args.task, records),
        "cli": {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    key = _run_key(args)
    (args.out_dir / f"{key}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8"
    )
    (args.out_dir / f"{key}.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[{key}]")
    print(f"  items={len(records)}  live_calls={client.n_calls}  cache_hits={client.n_cache_hits}  "
          f"api_errors={errors}  cost=${client.cost_usd:.4f}")
    print(f"  summary: {json.dumps(manifest['summary'], ensure_ascii=False)}")
    if errors:
        print(f"  WARNING: {errors} API errors -- rerun to fill gaps (cache keeps the successes)")


if __name__ == "__main__":
    main()
