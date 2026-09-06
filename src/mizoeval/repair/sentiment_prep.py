"""Prepare the Mizo sentiment dataset for evaluation.

The source (`hillbyte/mizo-sentiment`, 1,220 rows) ships as a single train
split with no evaluation partition and two properties that shape how it must
be scored:

1. It is imbalanced -- Positive 716, Neutral 327, Negative 177. A model that
   answers "Positive" to everything scores 58.7% accuracy, so accuracy is
   uninformative here and macro-F1 is the primary metric.
2. It is code-mixed. The texts are social-media comments that switch between
   Mizo and English mid-sentence. We attach an out-of-Mizo-vocabulary rate to
   each item so code-mixing can serve as a covariate: if models do better on
   English-heavy comments, the benchmark is partly measuring English ability
   rather than Mizo understanding.

70 texts are exact duplicates and are dropped -- keeping them would let the
same item appear in two folds.

Run:
    python -m mizoeval.repair.sentiment_prep
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"

HF_REPO = "hillbyte/mizo-sentiment"
HF_FILE = "data/train-00000-of-00001.parquet"
LABELS = ("Positive", "Neutral", "Negative")

TOKEN_RE = re.compile(r"[A-Za-zÀ-ɏḀ-ỿ]+")
EMOJI_RE = re.compile(
    "[" "\U0001F300-\U0001FAFF" "\U00002600-\U000027BF" "\U0001F1E6-\U0001F1FF" "]"
)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(unicodedata.normalize("NFKC", text))]


def build_mizo_lexicon() -> set[str]:
    """Assemble a Mizo lexicon from the project's other Mizo corpora.

    ~15k types, drawn from the Mizo side of the MT benchmark and the NER news
    corpus. Used to measure code-mixing by vocabulary coverage.
    """
    lex: set[str] = set()

    mt_path = PROCESSED / "mizoeval-mt-all.jsonl"
    if mt_path.exists():
        for line in mt_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                lex.update(tokenize(json.loads(line)["mz"]))

    for split in ("train", "valid", "test"):
        p = PROCESSED / f"mizoeval-ner-{split}.conll"
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                lex.update(tokenize(parts[1]))

    if not lex:
        raise RuntimeError(
            "No Mizo corpus found -- run mizoeval.repair.mt_stratify and "
            "mizoeval.repair.ner_normalize first; the code-mixing measure is "
            "derived from their output."
        )
    return lex


def oov_rate(text: str, mizo_lexicon: set[str]) -> float:
    """Out-of-Mizo-vocabulary token rate: a coverage-based code-mixing proxy.

    Mizo is Latin-script, so code-mixing cannot be read off the script, and
    identifying the English half by wordlist fails here: the only large English
    corpus in this project is the MT benchmark's scripture-heavy source side,
    which contains none of the register these YouTube comments actually borrow
    ("subscribe", "comment", "house tour").

    Measuring coverage against the *Mizo* side sidesteps that entirely -- no
    English wordlist is needed. The rate over-counts slightly, since
    misspellings and rare Mizo words also fall outside a 15k-type lexicon, so
    it is reported as an out-of-vocabulary rate rather than as an English
    ratio, and used only as a monotone covariate.
    """
    toks = tokenize(text)
    if not toks:
        return 0.0
    return sum(1 for t in toks if t not in mizo_lexicon) / len(toks)


def load_raw() -> list[dict]:
    import pandas as pd
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(HF_REPO, HF_FILE, repo_type="dataset")
    df = pd.read_parquet(path)
    return df.to_dict("records")


def run(seed: int = 20260907, n_folds: int = 5) -> dict[str, object]:
    from sklearn.model_selection import StratifiedKFold

    PROCESSED.mkdir(parents=True, exist_ok=True)
    raw = load_raw()
    mizo_lexicon = build_mizo_lexicon()

    seen: set[str] = set()
    rows: list[dict] = []
    dropped_dupes = 0
    for i, r in enumerate(raw):
        text = str(r["text"])
        key = " ".join(text.split()).lower()
        if key in seen:
            dropped_dupes += 1
            continue
        seen.add(key)
        rows.append(
            {
                "id": f"sent{i:05d}",
                "text": text,
                "label": r["label"],
                "n_chars": len(text),
                "oov_rate": round(oov_rate(text, mizo_lexicon), 4),
                "n_emoji": len(EMOJI_RE.findall(text)),
                "has_person_placeholder": "[PERSON]" in text,
            }
        )

    labels = [r["label"] for r in rows]
    skf = StratifiedKFold(n_splits=n_folds, shuffle=True, random_state=seed)
    for fold, (_, test_idx) in enumerate(skf.split(range(len(rows)), labels)):
        for i in test_idx:
            rows[i]["fold"] = fold

    with (PROCESSED / "mizoeval-sentiment-v1.jsonl").open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    counts = Counter(labels)
    total = len(rows)
    majority = max(counts.values()) / total
    return {
        "raw_rows": len(raw),
        "dropped_duplicates": dropped_dupes,
        "kept": total,
        "label_counts": dict(counts),
        "majority_baseline_accuracy": round(majority, 4),
        "mizo_lexicon_types": len(mizo_lexicon),
        "mean_oov_rate": round(sum(r["oov_rate"] for r in rows) / total, 4),
        "items_oov_gt_0.3 (code-mixed)": sum(1 for r in rows if r["oov_rate"] > 0.3),
        "items_with_person_placeholder": sum(r["has_person_placeholder"] for r in rows),
        "fold_sizes": dict(Counter(r["fold"] for r in rows)),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seed", type=int, default=20260907)
    ap.add_argument("--folds", type=int, default=5)
    args = ap.parse_args()
    for k, v in run(seed=args.seed, n_folds=args.folds).items():
        print(f"{k:34s}: {v}")


if __name__ == "__main__":
    main()
