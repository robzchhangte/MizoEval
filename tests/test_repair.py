"""Invariants the repaired datasets must satisfy.

These are the checks the plan's verification section calls for: they run against
the emitted files, so a regression in any repair module fails here rather than
surfacing as a wrong number in the paper.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"

ABCD = ("A", "B", "C", "D")


def load_jsonl(name: str) -> list[dict]:
    path = PROCESSED / name
    if not path.exists():
        pytest.skip(f"{name} not built yet -- run the repair modules first")
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def load_conll(name: str) -> list[list[tuple[str, str]]]:
    path = PROCESSED / name
    if not path.exists():
        pytest.skip(f"{name} not built yet -- run mizoeval.repair.ner_normalize first")
    sents, cur = [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        if not line.strip():
            if cur:
                sents.append(cur)
                cur = []
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            cur.append((parts[1], parts[2]))
    if cur:
        sents.append(cur)
    return sents


# --------------------------------------------------------------------------- MCQ


def test_mcq_no_duplicate_stems():
    """Dedup must leave no repeated (stem, choice-set) pair."""
    rows = load_jsonl("mizoeval-mcq-v1.jsonl")
    from mizoeval.repair.mcq_repair import choice_signature, norm_text

    keys = [(norm_text(r["question"]), choice_signature(r["choices"])) for r in rows]
    dupes = [k for k, n in Counter(keys).items() if n > 1]
    assert not dupes, f"{len(dupes)} duplicate keys survived dedup"


def test_mcq_answer_key_is_always_a_valid_choice():
    for r in load_jsonl("mizoeval-mcq-v1.jsonl"):
        assert r["answer"] in r["choices"], r["id"]
        assert r["choices"][r["answer"]] == r["answer_text"], r["id"]


def test_mcq4_subset_is_strictly_four_option():
    rows = load_jsonl("mizoeval-mcq-v1-mcq4.jsonl")
    assert rows, "mcq4 subset is empty"
    for r in rows:
        assert set(r["choices"]) == set(ABCD), r["id"]
        assert r["answer"] in ABCD, r["id"]


def test_permutation_preserves_the_gold_answer_and_option_set():
    """A permuted item must be the same question with the options reordered.

    If permutation changed the gold answer's *text* or the option multiset it
    would be measuring a different item, and the position-bias comparison
    against the unpermuted set would be meaningless.
    """
    base = {r["id"]: r for r in load_jsonl("mizoeval-mcq-v1-mcq4.jsonl")}
    perm = load_jsonl("mizoeval-mcq-v1-mcq4-permuted.jsonl")
    assert perm, "permuted subset is empty"
    for p in perm:
        o = base[p["id"]]
        assert p["answer_text"] == o["answer_text"], p["id"]
        assert p["choices"][p["answer"]] == o["choices"][o["answer"]], p["id"]
        assert sorted(p["choices"].values()) == sorted(o["choices"].values()), p["id"]


def test_permutation_flattens_answer_position():
    """The whole point of the permuted variant: no position may dominate.

    Gold answers in the source are A-heavy (30% A vs 14% D), so a model can
    beat chance by always answering A. After permutation each position should
    sit near 25%.
    """
    perm = load_jsonl("mizoeval-mcq-v1-mcq4-permuted.jsonl")
    counts = Counter(r["answer"] for r in perm)
    for pos in ABCD:
        share = counts[pos] / len(perm)
        assert 0.20 <= share <= 0.30, f"position {pos} at {share:.1%} after permutation"


def test_positional_options_excluded_from_permutation():
    """"All of the above" cannot survive reordering, so it must not be permuted."""
    for r in load_jsonl("mizoeval-mcq-v1-mcq4-permuted.jsonl"):
        assert not r["has_positional_option"], r["id"]


# --------------------------------------------------------------------------- NER


@pytest.mark.parametrize("split", ["train", "valid", "test"])
def test_ner_tags_are_well_formed_bio(split):
    """Uppercase BIO, and no `I-X` that does not continue an `X` span."""
    for sent in load_conll(f"mizoeval-ner-{split}.conll"):
        prev_type = None
        for tok, tag in sent:
            assert tag == "O" or tag[:2] in ("B-", "I-"), f"{split}: bad tag {tag!r}"
            if tag.startswith("I-"):
                assert tag[2:] == prev_type, f"{split}: orphan {tag!r} after {prev_type!r}"
            prev_type = tag[2:] if tag != "O" else None


@pytest.mark.parametrize("split", ["train", "valid", "test"])
def test_keyword_layer_is_separated_from_entities(split):
    """KEYWORD is a different task and must not appear in the NER files."""
    for sent in load_conll(f"mizoeval-ner-{split}.conll"):
        for _, tag in sent:
            assert "KEYWORD" not in tag, f"{split}: KEYWORD leaked into the NER layer"


@pytest.mark.parametrize("split", ["train", "valid", "test"])
def test_ner_uses_only_the_retained_tagset(split):
    from mizoeval.repair.ner_normalize import DROP_ENTITIES, KEEP_ENTITIES

    for sent in load_conll(f"mizoeval-ner-{split}.conll"):
        for _, tag in sent:
            if tag != "O":
                assert tag[2:] in KEEP_ENTITIES, f"{split}: unexpected type {tag}"
                assert tag[2:] not in DROP_ENTITIES


def test_tokens_are_never_altered_by_normalisation():
    """Normalisation may change tags; it must not change the corpus text."""
    from mizoeval.repair.ner_normalize import RAW, SPLIT_FILES, parse_conll

    for split, fname in SPLIT_FILES.items():
        raw = parse_conll(RAW / fname)
        out = load_conll(f"mizoeval-ner-{split}.conll")
        assert len(raw) == len(out), split
        for r, o in zip(raw, out):
            assert r.tokens == [t for t, _ in o], split


def test_document_disjoint_resplit_has_no_leakage():
    """The re-split exists to remove the official split's document overlap.

    In the released split 100% of validation and 99.6% of test sentences come
    from an article that also appears in training. If this test fails, the
    re-split is not delivering the property it was built for.
    """
    from mizoeval.repair.ner_normalize import PROCESSED as P

    def urls_and_texts(split):
        path = P / f"mizoeval-ner-docsplit-{split}.conll"
        if not path.exists():
            pytest.skip("document-disjoint re-split not built yet")
        urls, texts, cur = set(), set(), []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# URL:"):
                if cur:
                    texts.add(" ".join(cur))
                    cur = []
                urls.add(line[len("# URL:"):].strip())
            elif line.strip() and not line.startswith("#"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    cur.append(parts[1])
        if cur:
            texts.add(" ".join(cur))
        return urls, texts

    tr_u, tr_t = urls_and_texts("train")
    for split in ("valid", "test"):
        u, t = urls_and_texts(split)
        assert not (tr_u & u), f"train/{split} share {len(tr_u & u)} source articles"
        assert not (tr_t & t), f"train/{split} share {len(tr_t & t)} identical sentences"


# --------------------------------------------------------------------------- MT


def test_mt_strata_partition_the_corpus_totally_and_disjointly():
    all_rows = load_jsonl("mizoeval-mt-all.jsonl")
    parts = {s: load_jsonl(f"mizoeval-mt-{s}.jsonl")
             for s in ("scripture", "religious", "secular")}
    ids = [r["id"] for rows in parts.values() for r in rows]
    assert len(ids) == len(all_rows), "strata do not cover every pair"
    assert len(set(ids)) == len(ids), "a pair appears in more than one stratum"
    assert set(ids) == {r["id"] for r in all_rows}


def test_mt_stratifier_flags_a_known_kjv_verse():
    """Calibration: the classifier must fire on unambiguous scripture."""
    from mizoeval.repair.mt_stratify import build_kjv_index, score_pair

    kjv = build_kjv_index()
    sig = score_pair(
        "The LORD is my shepherd; I shall not want. He maketh me to lie down "
        "in green pastures: he leadeth me beside the still waters.",
        "LALPA chu ka vengtu a ni a, ka tlachham lo vang.",
        kjv,
    )
    assert sig.stratum == "scripture", f"Psalm 23 classified as {sig.stratum}"


def test_mt_stratifier_stays_quiet_on_secular_mizoram_text():
    """The other half of calibration -- a probe that fires on everything is useless."""
    from mizoeval.repair.mt_stratify import build_kjv_index, score_pair

    kjv = build_kjv_index()
    sig = score_pair(
        "Mizoram was allotted two seats in Parliament, one each in the Lok "
        "Sabha and in the Rajya Sabha.",
        "Mizoram chuan Parliament-ah thutthlengna hnih a chang a.",
        kjv,
    )
    assert sig.stratum == "secular", f"secular news classified as {sig.stratum}"


# --------------------------------------------------------------------------- sentiment


def test_sentiment_has_no_duplicate_texts_and_complete_folds():
    rows = load_jsonl("mizoeval-sentiment-v1.jsonl")
    keys = [" ".join(r["text"].split()).lower() for r in rows]
    assert len(set(keys)) == len(keys), "duplicate texts survived"
    assert all("fold" in r for r in rows), "an item was not assigned a fold"
    assert set(r["label"] for r in rows) == {"Positive", "Neutral", "Negative"}


def test_sentiment_folds_are_stratified():
    """Each fold must mirror the corpus label distribution.

    The corpus is imbalanced (57% Positive), so an unstratified split could
    leave a fold with almost no Negative items and make per-class F1 unstable.
    """
    rows = load_jsonl("mizoeval-sentiment-v1.jsonl")
    overall = Counter(r["label"] for r in rows)
    n = len(rows)
    for fold in {r["fold"] for r in rows}:
        sub = [r for r in rows if r["fold"] == fold]
        for label, count in Counter(r["label"] for r in sub).items():
            assert abs(count / len(sub) - overall[label] / n) < 0.05, (fold, label)
