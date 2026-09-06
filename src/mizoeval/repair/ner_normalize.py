"""Normalise the Mizo NER CoNLL files into an evaluation-ready release.

The India-Data Mizo NER release is annotated in a non-standard scheme that
`seqeval` and every off-the-shelf NER tool will mis-score as-is:

1. Tags are lowercase (`b-NEP`, `i-NEP`) rather than BIO (`B-NEP`, `I-NEP`).
2. `KEYWORD` -- a *different task* (keyword identification) -- shares the tag
   layer with the named-entity labels. 1,714 of the training spans are
   KEYWORD, so leaving them in makes the reported entity F1 meaningless.
3. `NETE`, `NEU` and `NEDA` have <=3 training instances each and zero in the
   validation and test splits, so they cannot be learned or scored.
4. The third file ships as `gold_.conll` with no split name.

This module emits one BIO file per split for each of the two tasks, and runs a
cross-split leakage check -- every sentence carries a source URL, and all three
splits are drawn from the same news site, so overlap is a live risk that would
invalidate the test scores if unreported.

Run:
    python -m mizoeval.repair.ner_normalize
"""

from __future__ import annotations

import argparse
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

# `gold_.conll` is unnamed in the release. It holds 447 sentences -- the same
# count as the validation split -- and a disjoint URL set, which is what a
# held-out test split looks like. The leakage check below verifies that claim
# rather than assuming it.
SPLIT_FILES = {
    "train": "gold_train.conll",
    "valid": "gold_valid.conll",
    "test": "gold_.conll",
}

# Retained entity types. NETE/NEU/NEDA are dropped: 3, 1 and 1 training
# instances respectively, and absent from valid and test.
KEEP_ENTITIES = {"NEP", "NEL", "NEO", "NEMI", "NETI", "NEF", "NEAR"}
DROP_ENTITIES = {"NETE", "NEU", "NEDA"}
KEYWORD_TAG = "KEYWORD"

PUNCT_ONLY = re.compile(r"^[^\w-￿]+$")


@dataclass
class Sentence:
    url: str | None
    sent_id: str | None
    tokens: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


@dataclass
class NormStats:
    sentences: int = 0
    tokens: int = 0
    tag_counts: Counter = field(default_factory=Counter)
    entity_spans: Counter = field(default_factory=Counter)
    keyword_spans: int = 0
    dropped_spans: Counter = field(default_factory=Counter)
    orphan_i_repaired: int = 0
    punct_boundary_trimmed: int = 0


def parse_conll(path: Path) -> list[Sentence]:
    """Parse the release format: `# URL:` / `# Sentence_Id:` then idx\ttoken\ttag."""
    sents: list[Sentence] = []
    cur = Sentence(url=None, sent_id=None)
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("# URL:"):
            if cur.tokens:
                sents.append(cur)
            cur = Sentence(url=stripped[len("# URL:"):].strip(), sent_id=None)
        elif stripped.startswith("# Sentence_Id:"):
            cur.sent_id = stripped[len("# Sentence_Id:"):].strip()
        elif not stripped:
            continue
        else:
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            cur.tokens.append(parts[1].strip())
            cur.tags.append(parts[2].strip())
    if cur.tokens:
        sents.append(cur)
    return sents


def to_bio(tag: str) -> tuple[str, str | None]:
    """`b-NEP` -> `('B', 'NEP')`; `O` -> `('O', None)`."""
    if tag in ("O", ""):
        return "O", None
    prefix, _, typ = tag.partition("-")
    return prefix.upper(), typ.upper() or None


def spans_from_tags(tags: list[str]) -> list[tuple[int, int, str]]:
    """Extract (start, end_exclusive, type) spans, repairing orphan `I-`.

    An `I-X` with no preceding `B-X`/`I-X` is treated as a span start. That is
    the standard IOB2 repair and it is more faithful than dropping the token,
    which would silently delete annotated entities.
    """
    spans: list[tuple[int, int, str]] = []
    start, cur_type = None, None
    for i, tag in enumerate(tags):
        prefix, typ = to_bio(tag)
        if prefix == "B":
            if cur_type is not None:
                spans.append((start, i, cur_type))
            start, cur_type = i, typ
        elif prefix == "I":
            if cur_type is None or typ != cur_type:  # orphan or type switch
                if cur_type is not None:
                    spans.append((start, i, cur_type))
                start, cur_type = i, typ
        else:
            if cur_type is not None:
                spans.append((start, i, cur_type))
            start, cur_type = None, None
    if cur_type is not None:
        spans.append((start, len(tags), cur_type))
    return spans


def count_orphan_i(tags: list[str]) -> int:
    n, prev_type = 0, None
    for tag in tags:
        prefix, typ = to_bio(tag)
        if prefix == "I" and (prev_type is None or typ != prev_type):
            n += 1
        prev_type = typ if prefix in ("B", "I") else None
    return n


def trim_punct_boundary(
    tokens: list[str], span: tuple[int, int, str]
) -> tuple[int, int, str] | None:
    """Drop standalone-punctuation tokens from a span's edges.

    Only tokens that are *entirely* punctuation are trimmed. Punctuation
    attached to a word (`YMA,`) is left alone: that is the corpus tokenisation,
    and gold and predictions are aligned against the same tokens, so altering
    the token text would break the alignment for no gain.
    """
    s, e, typ = span
    while s < e and PUNCT_ONLY.match(tokens[s]):
        s += 1
    while e > s and PUNCT_ONLY.match(tokens[e - 1]):
        e -= 1
    return (s, e, typ) if e > s else None


def build_tags(n: int, spans: list[tuple[int, int, str]]) -> list[str]:
    tags = ["O"] * n
    for s, e, typ in spans:
        tags[s] = f"B-{typ}"
        for i in range(s + 1, e):
            tags[i] = f"I-{typ}"
    return tags


def normalize_split(sents: list[Sentence]) -> tuple[list[Sentence], list[Sentence], NormStats]:
    """Split one file into (entity-task sentences, keyword-task sentences)."""
    stats = NormStats()
    ner_out: list[Sentence] = []
    kw_out: list[Sentence] = []

    for s in sents:
        stats.sentences += 1
        stats.tokens += len(s.tokens)
        stats.orphan_i_repaired += count_orphan_i(s.tags)
        for t in s.tags:
            stats.tag_counts[t] += 1

        ner_spans, kw_spans = [], []
        for span in spans_from_tags(s.tags):
            trimmed = trim_punct_boundary(s.tokens, span)
            if trimmed is None:
                stats.punct_boundary_trimmed += 1
                continue
            if trimmed != span:
                stats.punct_boundary_trimmed += 1
            _, _, typ = trimmed
            if typ == KEYWORD_TAG:
                kw_spans.append(trimmed)
                stats.keyword_spans += 1
            elif typ in KEEP_ENTITIES:
                ner_spans.append(trimmed)
                stats.entity_spans[typ] += 1
            else:
                stats.dropped_spans[typ] += 1

        ner_out.append(Sentence(s.url, s.sent_id, s.tokens, build_tags(len(s.tokens), ner_spans)))
        kw_out.append(Sentence(s.url, s.sent_id, s.tokens, build_tags(len(s.tokens), kw_spans)))
    return ner_out, kw_out, stats


def write_conll(path: Path, sents: list[Sentence]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for s in sents:
            if s.url:
                fh.write(f"# URL: {s.url}\n")
            if s.sent_id:
                fh.write(f"# Sentence_Id: {s.sent_id}\n")
            for i, (tok, tag) in enumerate(zip(s.tokens, s.tags), start=1):
                fh.write(f"{i}\t{tok}\t{tag}\n")
            fh.write("\n")


def leakage_report(raw_splits: dict[str, list[Sentence]]) -> dict[str, object]:
    """Cross-split URL and sentence-text overlap.

    All three splits are drawn from the same news site, so an overlap here
    would mean test sentences were visible during training -- a blocking
    finding for any fine-tuned baseline.
    """
    urls = {k: {s.url for s in v if s.url} for k, v in raw_splits.items()}
    texts = {k: {" ".join(s.tokens) for s in v} for k, v in raw_splits.items()}
    out: dict[str, object] = {}
    for a, b in (("train", "valid"), ("train", "test"), ("valid", "test")):
        out[f"url_overlap_{a}_{b}"] = len(urls[a] & urls[b])
        out[f"sent_overlap_{a}_{b}"] = len(texts[a] & texts[b])
    out["url_counts"] = {k: len(v) for k, v in urls.items()}
    out["duplicate_sentences_within_split"] = {
        k: len(v) - len(texts[k]) for k, v in raw_splits.items()
    }
    return out


def document_disjoint_resplit(
    raw_splits: dict[str, list[Sentence]],
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = 20260907,
) -> dict[str, list[Sentence]]:
    """Re-split the pooled corpus so no source article spans two splits.

    The released split assigns *sentences* at random, so 100% of validation and
    99.6% of test sentences come from an article that is also in training. A
    model fine-tuned on that split has seen the same article, the same entities
    and the same context at training time, so its test F1 is optimistic.

    This re-split assigns whole articles (URLs). Both splits are published:
    the official one for comparability with prior work, this one for the
    honest number.
    """
    import random

    by_url: dict[str | None, list[Sentence]] = defaultdict(list)
    for sents in raw_splits.values():
        for s in sents:
            by_url[s.url].append(s)

    urls = sorted(by_url, key=lambda u: (u is None, u or ""))
    rng = random.Random(seed)
    rng.shuffle(urls)

    total = sum(len(v) for v in by_url.values())
    targets = [ratios[0] * total, ratios[1] * total, ratios[2] * total]
    buckets: dict[str, list[Sentence]] = {"train": [], "valid": [], "test": []}
    names = ["train", "valid", "test"]

    # Greedy: place each article in whichever split is furthest below target.
    # Whole-article placement is what guarantees disjointness; the greedy step
    # only balances sizes.
    for url in urls:
        deficits = [targets[i] - len(buckets[names[i]]) for i in range(3)]
        buckets[names[deficits.index(max(deficits))]].extend(by_url[url])

    # A handful of sentences are reposted verbatim under different URLs, so
    # article-disjointness alone still leaves exact duplicates straddling the
    # splits. Drop those from valid/test -- train keeps its copy, so no
    # annotated data is lost, and the held-out sets become truly unseen.
    train_texts = {" ".join(s.tokens) for s in buckets["train"]}
    seen = set(train_texts)
    for name in ("valid", "test"):
        deduped = []
        for s in buckets[name]:
            text = " ".join(s.tokens)
            if text in seen:
                continue
            seen.add(text)
            deduped.append(s)
        buckets[name] = deduped
    return buckets


def run(resplit: bool = True) -> tuple[dict[str, NormStats], dict[str, object], dict[str, object]]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    raw_splits = {name: parse_conll(RAW / fn) for name, fn in SPLIT_FILES.items()}
    all_stats: dict[str, NormStats] = {}
    for name, sents in raw_splits.items():
        ner, kw, stats = normalize_split(sents)
        write_conll(PROCESSED / f"mizoeval-ner-{name}.conll", ner)
        write_conll(PROCESSED / f"mizoeval-keyword-{name}.conll", kw)
        all_stats[name] = stats

    resplit_report: dict[str, object] = {}
    if resplit:
        dd = document_disjoint_resplit(raw_splits)
        for name, sents in dd.items():
            ner, kw, _ = normalize_split(sents)
            write_conll(PROCESSED / f"mizoeval-ner-docsplit-{name}.conll", ner)
            write_conll(PROCESSED / f"mizoeval-keyword-docsplit-{name}.conll", kw)
        resplit_report = leakage_report(dd)
        resplit_report["sentences"] = {k: len(v) for k, v in dd.items()}
    return all_stats, leakage_report(raw_splits), resplit_report


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    stats, leaks, resplit = run()
    for name, s in stats.items():
        print(f"[{name}] sents={s.sentences} tokens={s.tokens} "
              f"entity_spans={sum(s.entity_spans.values())} keyword_spans={s.keyword_spans}")
        print(f"    by type : {dict(s.entity_spans.most_common())}")
        print(f"    dropped : {dict(s.dropped_spans)}")
        print(f"    orphan I- repaired={s.orphan_i_repaired} "
              f"punct-boundary trimmed={s.punct_boundary_trimmed}")
    print("\nLEAKAGE CHECK -- official split")
    for k, v in leaks.items():
        print(f"  {k}: {v}")
    print("\nLEAKAGE CHECK -- document-disjoint re-split")
    for k, v in resplit.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
