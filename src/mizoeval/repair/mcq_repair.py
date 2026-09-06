"""Repair the Mizoram MCQ benchmark into an evaluation-ready release.

The raw file (`data/raw/mizoram_mcq_with_answers.json`, 2,400 items) carries four
defects that make it unusable as-published for LLM evaluation:

1. 456 duplicate rows. Duplicates double-count items and inflate N.
2. Some duplicate groups disagree on the gold answer. These are hard label
   noise: at most one member can be right. We never guess -- they are exported
   for native-speaker adjudication and quarantined until resolved.
3. The dataset card promises "4-option MCQ" but 111 items have 2, 3 or 5
   choices and 66 use TRUE/FALSE or Roman-numeral answer keys. Rather than
   discard them we partition by declared `format` so the headline subset is
   homogeneous and the remainder stays available.
4. Gold answers are position-biased (A 30%, D 14%), so a model that always
   answers "A" beats random by a wide margin. We emit a choice-order-permuted
   variant to separate knowledge from position preference.

Run:
    python -m mizoeval.repair.mcq_repair
"""

from __future__ import annotations

import argparse
import json
import random
import re
import string
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw" / "mizoram_mcq_with_answers.json"
PROCESSED = ROOT / "data" / "processed"
HUMAN_EVAL = ROOT / "data" / "human_eval"

# Roman-numeral keys used by a handful of engineering-paper items.
ROMAN_KEYS = {"I", "II", "III", "IV", "V"}
TF_KEYS = {"TRUE", "FALSE"}
ABCD = ("A", "B", "C", "D")

# Matches "all of the above" / "none of these" and the usual variants. These
# options interact badly with choice permutation (an "above" reference is
# meaningless once options are reordered), so permuted items exclude them.
POSITIONAL_OPTION_RE = re.compile(
    r"\b(all|none|both|any)\s+of\s+(the\s+)?(above|these|them)\b", re.IGNORECASE
)

_PUNCT_TABLE = str.maketrans({c: " " for c in string.punctuation})


def norm_text(s: str | None) -> str:
    """Normalise for *matching only*. Never used for emitted content.

    NFKC-normalises, lowercases, drops ASCII punctuation and collapses
    whitespace. Mizo diacritics (ṭ, â, ê, î, ô, û) are preserved -- they are
    phonemic, and stripping them would collapse genuinely distinct strings.
    """
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s).lower()
    s = s.translate(_PUNCT_TABLE)
    return " ".join(s.split())


def choice_signature(choices: dict[str, str]) -> tuple[str, ...]:
    """Order-independent signature of a choice set, for duplicate detection."""
    return tuple(sorted(norm_text(v) for v in choices.values()))


def classify_format(item: dict[str, Any]) -> str:
    """Partition an item by answer-key shape.

    `mcq4` is the headline subset: exactly four options keyed A-D. Everything
    else is retained but reported separately so the primary metric is computed
    over a homogeneous population.
    """
    keys = set(item["choices"])
    answer = item["answer"]
    if keys == set(ABCD) and answer in ABCD:
        return "mcq4"
    if keys <= TF_KEYS and answer in TF_KEYS:
        return "mcq_tf"
    if keys <= ROMAN_KEYS and answer in ROMAN_KEYS:
        return "mcq_roman"
    return "mcq_other"


def has_positional_option(choices: dict[str, str]) -> bool:
    return any(POSITIONAL_OPTION_RE.search(v or "") for v in choices.values())


@dataclass
class RepairStats:
    """Every count the paper's Table 1 and the repair report need."""

    raw_total: int = 0
    dup_groups: int = 0
    dup_rows_removed: int = 0
    conflict_groups: int = 0
    conflict_items_quarantined: int = 0
    stem_only_collisions: int = 0
    format_counts: Counter = field(default_factory=Counter)
    positional_option_items: int = 0
    kept_total: int = 0
    answer_positions: Counter = field(default_factory=Counter)
    categories: Counter = field(default_factory=Counter)
    languages: Counter = field(default_factory=Counter)
    years: Counter = field(default_factory=Counter)
    invalid_answer_key: int = 0


def load_raw(path: Path = RAW) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        payload = json.load(fh)
    return payload["questions"]


def group_duplicates(items: Iterable[dict[str, Any]]) -> dict[tuple, list[dict]]:
    """Group on (normalised stem, order-independent choice set).

    Keying on the stem alone would merge legitimately distinct questions that
    reuse a stem with different options; keying on stem+choices means a group
    is a genuine repeat of the same question, so a disagreement inside a group
    is a real contradiction rather than an artefact of the key.
    """
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for it in items:
        groups[(norm_text(it["question"]), choice_signature(it["choices"]))].append(it)
    return groups


def resolve_group(group: list[dict[str, Any]]) -> tuple[dict | None, list[dict] | None]:
    """Collapse a duplicate group.

    Returns ``(kept_item, None)`` when every member agrees on the answer, or
    ``(None, group)`` when they disagree -- disagreements are never resolved
    automatically. The kept representative is the member with the richest
    provenance (a known year and the longest explanation), because that is the
    variant a reader can most easily trace back to a source paper.
    """
    answers = {norm_text(it.get("answer_text")) for it in group}
    if len(answers) > 1:
        return None, group
    best = max(
        group,
        key=lambda it: (
            it.get("source_year") is not None,
            len(it.get("explanation") or ""),
            len(it.get("source_exam") or ""),
        ),
    )
    kept = dict(best)
    kept["duplicate_count"] = len(group)
    # Preserve provenance of every merged variant so the merge stays auditable.
    kept["merged_sources"] = sorted(
        {
            f"{it.get('source_exam')}|{it.get('source_paper')}|{it.get('source_year')}"
            for it in group
        }
    )
    return kept, None


def permute_choices(item: dict[str, Any], rng: random.Random) -> dict[str, Any] | None:
    """Re-key an mcq4 item under a random option order.

    Returns None for items that cannot be safely permuted -- those containing
    an "all of the above"-style option, whose meaning depends on the original
    ordering.
    """
    if item["format"] != "mcq4" or item["has_positional_option"]:
        return None
    texts = [item["choices"][k] for k in ABCD]
    order = list(range(4))
    rng.shuffle(order)
    new_choices = {ABCD[i]: texts[order[i]] for i in range(4)}
    gold_text = item["choices"][item["answer"]]
    new_answer = next(k for k, v in new_choices.items() if v == gold_text)
    out = dict(item)
    out["choices"] = new_choices
    out["answer"] = new_answer
    out["answer_text"] = gold_text
    out["original_answer"] = item["answer"]
    return out


def repair(seed: int = 20260907) -> RepairStats:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    HUMAN_EVAL.mkdir(parents=True, exist_ok=True)

    raw = load_raw()
    stats = RepairStats(raw_total=len(raw))

    # Stem-only collisions are reported for transparency: they are *not* treated
    # as duplicates, but a large number would suggest the stricter key is hiding
    # near-duplicates that still deserve a look.
    stem_groups = defaultdict(list)
    for it in raw:
        stem_groups[norm_text(it["question"])].append(it)
    stats.stem_only_collisions = sum(len(v) - 1 for v in stem_groups.values() if len(v) > 1)

    groups = group_duplicates(raw)
    kept: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []

    for key, group in groups.items():
        if len(group) > 1:
            stats.dup_groups += 1
        item, conflict = resolve_group(group)
        if conflict is not None:
            stats.conflict_groups += 1
            stats.conflict_items_quarantined += len(conflict)
            conflicts.append({"stem": group[0]["question"], "members": conflict})
            continue
        if len(group) > 1:
            stats.dup_rows_removed += len(group) - 1
        kept.append(item)

    # Annotate, validate, and drop internal inconsistencies.
    clean: list[dict[str, Any]] = []
    for it in kept:
        if it["answer"] not in it["choices"]:
            stats.invalid_answer_key += 1
            continue
        it["format"] = classify_format(it)
        it["has_positional_option"] = has_positional_option(it["choices"])
        it["n_choices"] = len(it["choices"])
        stats.format_counts[it["format"]] += 1
        stats.positional_option_items += int(it["has_positional_option"])
        stats.answer_positions[it["answer"]] += 1
        stats.categories[it["category"]] += 1
        stats.languages[it["language"]] += 1
        stats.years[it.get("source_year")] += 1
        clean.append(it)

    stats.kept_total = len(clean)

    write_jsonl(PROCESSED / "mizoeval-mcq-v1.jsonl", clean)
    write_jsonl(
        PROCESSED / "mizoeval-mcq-v1-mcq4.jsonl",
        [it for it in clean if it["format"] == "mcq4"],
    )

    rng = random.Random(seed)
    permuted = [p for it in clean if (p := permute_choices(it, rng)) is not None]
    write_jsonl(PROCESSED / "mizoeval-mcq-v1-mcq4-permuted.jsonl", permuted)

    write_conflicts_csv(HUMAN_EVAL / "mcq_conflicts.csv", conflicts)
    (HUMAN_EVAL / "mcq_conflicts.json").write_text(
        json.dumps(conflicts, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return stats


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_conflicts_csv(path: Path, conflicts: list[dict[str, Any]]) -> None:
    """Adjudication packet: one row per candidate answer, blank verdict column."""
    import csv

    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "conflict_id", "question", "option_A", "option_B", "option_C", "option_D",
                "claimed_answer", "claimed_answer_text", "source_exam", "source_year",
                "explanation", "ADJUDICATED_ANSWER", "ANNOTATOR", "NOTES",
            ]
        )
        for i, c in enumerate(conflicts):
            for m in c["members"]:
                ch = m["choices"]
                w.writerow(
                    [
                        f"C{i:04d}", m["question"],
                        ch.get("A", ""), ch.get("B", ""), ch.get("C", ""), ch.get("D", ""),
                        m["answer"], m.get("answer_text", ""),
                        m.get("source_exam", ""), m.get("source_year", ""),
                        (m.get("explanation") or "").replace("\n", " "),
                        "", "", "",
                    ]
                )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260907, help="permutation seed")
    args = ap.parse_args()
    s = repair(seed=args.seed)

    print(f"raw items                     : {s.raw_total}")
    print(f"stem-only collisions (FYI)    : {s.stem_only_collisions}")
    print(f"duplicate groups              : {s.dup_groups}")
    print(f"duplicate rows removed        : {s.dup_rows_removed}")
    print(f"conflicting groups quarantined: {s.conflict_groups} "
          f"({s.conflict_items_quarantined} items)")
    print(f"invalid answer key dropped    : {s.invalid_answer_key}")
    print(f"kept items                    : {s.kept_total}")
    print(f"  by format                   : {dict(s.format_counts)}")
    print(f"  positional-option items     : {s.positional_option_items}")
    print(f"  answer positions            : {dict(s.answer_positions.most_common())}")
    print(f"  languages                   : {dict(s.languages)}")
    print(f"  categories                  : {dict(s.categories.most_common())}")


if __name__ == "__main__":
    main()
