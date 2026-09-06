"""Loaders for the repaired datasets in `data/processed/`.

Each loader returns plain dicts and never touches the network, so a run is
reproducible from the committed processed files alone.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path.name} not found -- run the mizoeval.repair modules first"
        )
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


# --------------------------------------------------------------------------- MCQ


def load_mcq(subset: str = "mcq4", permuted: bool = False) -> list[dict[str, Any]]:
    """MCQ items. `subset` is 'mcq4' (headline), 'all', 'tf', 'roman', 'other'."""
    if permuted:
        if subset != "mcq4":
            raise ValueError("only the mcq4 subset has a permuted variant")
        return _read_jsonl(PROCESSED / "mizoeval-mcq-v1-mcq4-permuted.jsonl")
    name = {
        "all": "mizoeval-mcq-v1.jsonl",
        "mcq4": "mizoeval-mcq-v1-mcq4.jsonl",
    }.get(subset)
    if name:
        return _read_jsonl(PROCESSED / name)
    fmt = {"tf": "mcq_tf", "roman": "mcq_roman", "other": "mcq_other"}[subset]
    return [r for r in _read_jsonl(PROCESSED / "mizoeval-mcq-v1.jsonl") if r["format"] == fmt]


def mcq_exemplars(k: int = 5, seed: int = 20260907, exclude_ids: set[str] | None = None) -> list[dict]:
    """Few-shot exemplars for MCQ, drawn from the mcq4 pool.

    Held fixed by seed across all models so the few-shot condition is identical
    for everyone. Exemplars are excluded from scoring by the runner.
    """
    pool = [r for r in load_mcq("mcq4") if not exclude_ids or r["id"] not in exclude_ids]
    rng = random.Random(seed)
    # Spread exemplars across answer positions so the shots do not themselves
    # teach a position preference.
    by_pos: dict[str, list[dict]] = {p: [] for p in "ABCD"}
    for r in pool:
        by_pos[r["answer"]].append(r)
    picks: list[dict] = []
    for p in "ABCD":
        rng.shuffle(by_pos[p])
    i = 0
    while len(picks) < k:
        p = "ABCD"[i % 4]
        if by_pos[p]:
            picks.append(by_pos[p].pop())
        i += 1
        if i > 4 * k:
            break
    return picks[:k]


# --------------------------------------------------------------------------- MT


def load_mt(stratum: str = "all") -> list[dict[str, Any]]:
    """Translation pairs. `stratum` in {'all', 'scripture', 'religious', 'secular'}."""
    name = {
        "all": "mizoeval-mt-all.jsonl",
        "scripture": "mizoeval-mt-scripture.jsonl",
        "religious": "mizoeval-mt-religious.jsonl",
        "secular": "mizoeval-mt-secular.jsonl",
    }[stratum]
    return _read_jsonl(PROCESSED / name)


def mt_exemplars(direction: str, k: int = 5, seed: int = 20260907) -> list[dict]:
    """Few-shot pairs for MT, taken only from the secular stratum.

    Secular exemplars keep the demonstration out of the scripture register that
    the contamination analysis is trying to isolate.
    """
    src, tgt = direction.split("2")
    rng = random.Random(f"{seed}:{direction}")
    pool = load_mt("secular")
    picks = rng.sample(pool, min(k, len(pool)))
    return [{src: p["en"] if src == "en" else p["mz"],
             tgt: p["en"] if tgt == "en" else p["mz"]} for p in picks]


# --------------------------------------------------------------------------- sentiment


def load_sentiment(fold: int | None = None, exclude_fold: int | None = None) -> list[dict[str, Any]]:
    rows = _read_jsonl(PROCESSED / "mizoeval-sentiment-v1.jsonl")
    if fold is not None:
        rows = [r for r in rows if r["fold"] == fold]
    if exclude_fold is not None:
        rows = [r for r in rows if r["fold"] != exclude_fold]
    return rows


def sentiment_exemplars(k: int = 6, seed: int = 20260907, from_fold: int = 0) -> list[dict]:
    """Class-balanced exemplars from a single held-out fold.

    Balanced across the three labels despite the corpus imbalance, so the shots
    do not nudge the model toward the majority class.
    """
    rng = random.Random(seed)
    pool = load_sentiment(fold=from_fold)
    by_label: dict[str, list[dict]] = {}
    for r in pool:
        by_label.setdefault(r["label"], []).append(r)
    per = max(1, k // len(by_label))
    picks: list[dict] = []
    for label, items in by_label.items():
        rng.shuffle(items)
        picks.extend(items[:per])
    rng.shuffle(picks)
    return picks[:k]


# --------------------------------------------------------------------------- NER


def load_ner_conll(split: str, docsplit: bool = False) -> list[dict[str, Any]]:
    """Return sentences as {tokens, tags, url, sent_id}.

    `docsplit=True` selects the document-disjoint re-split; the default is the
    official split, for comparability with prior work.
    """
    prefix = "mizoeval-ner-docsplit" if docsplit else "mizoeval-ner"
    path = PROCESSED / f"{prefix}-{split}.conll"
    if not path.exists():
        raise FileNotFoundError(f"{path.name} not found -- run mizoeval.repair.ner_normalize")

    sents: list[dict[str, Any]] = []
    cur: dict[str, Any] = {"tokens": [], "tags": [], "url": None, "sent_id": None}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# URL:"):
            if cur["tokens"]:
                sents.append(cur)
            cur = {"tokens": [], "tags": [], "url": line[6:].strip(), "sent_id": None}
        elif line.startswith("# Sentence_Id:"):
            cur["sent_id"] = line[14:].strip()
        elif line.strip():
            parts = line.split("\t")
            if len(parts) >= 3:
                cur["tokens"].append(parts[1])
                cur["tags"].append(parts[2].strip())
    if cur["tokens"]:
        sents.append(cur)
    return sents


def ner_exemplars(k: int = 3, seed: int = 20260907, docsplit: bool = False) -> list[dict]:
    """Few-shot NER sentences from train, with gold spans pre-serialised to JSON."""
    from mizoeval.prompts.templates import NER_TAG_DEFINITIONS

    rng = random.Random(seed)
    train = load_ner_conll("train", docsplit=docsplit)
    # Prefer sentences that actually contain a few entities, so the shots
    # demonstrate the task rather than the empty case.
    with_ents = [s for s in train if any(t != "O" for t in s["tags"])]
    picks = rng.sample(with_ents, min(k, len(with_ents)))
    out = []
    for s in picks:
        spans = _spans(s["tokens"], s["tags"], set(NER_TAG_DEFINITIONS))
        out.append({
            "tokens": s["tokens"],
            "entities_json": json.dumps(
                [{"text": t, "type": ty} for t, ty in spans], ensure_ascii=False
            ),
        })
    return out


def _spans(tokens: list[str], tags: list[str], valid: set[str]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    buf: list[str] = []
    cur: str | None = None
    for tok, tag in zip(tokens, tags):
        if tag.startswith("B-"):
            if cur:
                out.append((" ".join(buf), cur))
            cur, buf = tag[2:], [tok]
        elif tag.startswith("I-") and cur == tag[2:]:
            buf.append(tok)
        else:
            if cur:
                out.append((" ".join(buf), cur))
            cur, buf = None, []
    if cur:
        out.append((" ".join(buf), cur))
    return [(s, t) for s, t in out if t in valid]


def iter_batches(items: list, size: int) -> Iterator[list]:
    for i in range(0, len(items), size):
        yield items[i:i + size]
