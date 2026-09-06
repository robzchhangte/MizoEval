"""Stratify the en-mz translation benchmark by register, for contamination control.

Why this exists. The 3,000-pair benchmark draws on `gold` (1,800) and `glosbe`
(1,200) sources, and the English side turns out to be overwhelmingly religious:
King James scripture in the `gold` portion (archaic register, verse citations,
strings like "Quicken me after thy lovingkindness") and Watchtower publications
in the `glosbe` portion. The KJV is among the most duplicated texts on the open
web; the Mizo Bible and jw.org's Mizo output are freely available too. Both
sides of those pairs are therefore almost certainly in the pretraining data of
every model under test. A model reproducing a memorised verse is not
translating, so an aggregate score over this benchmark reports memorisation as
translation quality.

We label every pair into three registers and report them separately:

  scripture   verbatim Bible text, in any translation. Highest memorisation
              risk -- the model has very likely seen this exact string pair.
  religious   Christian institutional prose that quotes no verse. Published in
              Mizo and heavily crawled, so still plausibly memorised.
  secular     everything else: Mizoram news, government and general prose.
              The only stratum that measures translation ability cleanly.

Six signals feed the decision and are all retained per pair, so any single
classification can be audited:

  kjv_hits / kjv_ngram  6-grams shared verbatim with the full KJV -- the
                        strongest and least gameable signal. Both the absolute
                        count and the fraction are used, because a short verse
                        can match few n-grams and still be plainly scripture.
  verse_cite            an explicit book chapter:verse reference, English or Mizo
  strong_en / strong_mz vocabulary decisive on a single occurrence ("Jehovah",
                        "Pathian") -- kept apart from weak terms ("faith",
                        "kingdom"), which need corroboration
  biblical_names        proper names and register vocabulary, which catch
                        modern-translation scripture that shares no KJV n-grams
  archaic               KJV-era morphology (thou/thee/thy, -eth, -est)
  jw_marker             Watchtower publication vocabulary

Known limitation: the signals are lexical, so the secular stratum still retains
some modern-translation scripture that names no person and quotes no verse.
Every figure this produces is therefore a *lower bound* on religious-domain
share. `--sample` writes a stratified packet whose hand-labelling measures the
residual error rate; the paper reports that measurement rather than assuming
the classifier is exact.

Run:
    python -m mizoeval.repair.mt_stratify
"""

from __future__ import annotations

import argparse
import json
import re
import string
import unicodedata
import urllib.request
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
EXTERNAL = ROOT / "data" / "external"
HUMAN_EVAL = ROOT / "data" / "human_eval"

HF_REPO = "robzchhangte/en-mz-benchmark"
HF_FILE = "en-mz-benchmark.jsonl"
KJV_URL = "https://www.gutenberg.org/cache/epub/10/pg10.txt"
KJV_PATH = EXTERNAL / "kjv.txt"

NGRAM_N = 6
# A sentence sharing >=15% of its 6-grams with the KJV is reproducing
# scripture, not coinciding with it: an ordinary English sentence essentially
# never matches a 6-gram of the KJV by chance. Validated against the
# hand-checked sample written by `--sample`.
KJV_THRESHOLD = 0.15

BOOKS = (
    "Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|"
    "Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song of Solomon|"
    "Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|"
    "Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|"
    "Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|"
    "Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation|"
    # Mizo book names, as they appear in the Mizo Bible
    "Genesis|Exodus|Matthaia|Marka|Luka|Johana|Rom|Korinth|Galatia|Ephesi|Philippi|"
    "Kolossa|Thessalonika|Timothea|Titus|Hebrai|Jakoba|Petera|Juda|Thupuan|Sam|Thufingte"
)
VERSE_CITE_RE = re.compile(rf"\b({BOOKS})\.?\s+\d+\s*:\s*\d+", re.IGNORECASE)

# Lexicons are split by how much a single occurrence tells us. A sentence
# containing "Jehovah" or "Pathian" is religious; one containing "faith" or
# "kingdom" might be about anything, so those need corroboration.
STRONG_EN = {
    "jehovah", "jesus", "christ", "bible", "scripture", "scriptures", "apostle",
    "apostles", "gospel", "satan", "psalm", "psalms", "messiah", "saviour",
    "savior", "sabbath", "pharisee", "pharisees", "disciple", "disciples",
    "watchtower", "resurrection", "corinthians", "thessalonians", "leviticus",
}
WEAK_EN = {
    "god", "godly", "lord", "holy", "spirit", "kingdom", "sin", "sins",
    "sinner", "righteous", "righteousness", "prayer", "pray", "prayed",
    "worship", "prophet", "prophets", "angel", "angels", "devil", "salvation",
    "repent", "repentance", "commandment", "commandments", "covenant", "temple",
    "priest", "priests", "israel", "israelites", "jerusalem", "pharaoh",
    "levites", "sacrifice", "faith", "faithful", "heaven", "hell", "eternal",
    "everlasting", "blessed", "congregation", "brethren", "ministry",
}
# Biblical proper names and register-specific vocabulary. Modern-translation
# scripture (the New World Translation, used throughout the Glosbe portion)
# shares few 6-grams with the KJV and uses no archaic morphology, so without
# these it slips into the secular bucket -- "the Israelite Achan", "the
# psalmist", "Why should we never yield to apostasy?" were all misfiled.
BIBLICAL_NAMES = {
    "moses", "abraham", "isaac", "jacob", "joseph", "david", "solomon", "elijah",
    "elisha", "samuel", "saul", "noah", "adam", "eve", "cain", "abel", "achan",
    "joshua", "gideon", "daniel", "ezekiel", "isaiah", "jeremiah", "habakkuk",
    "jonah", "job", "ruth", "esther", "peter", "paul", "timothy", "titus",
    "barnabas", "stephen", "judas", "mary", "martha", "lazarus", "pilate",
    "herod", "nebuchadnezzar", "babylon", "nineveh", "corinth", "ephesus",
    "galilee", "nazareth", "bethlehem", "judah", "judea", "canaan", "zion",
    "psalmist", "apostasy", "firstfruits", "tabernacle", "circumcision",
    "idolatry", "blasphemy", "anointed", "baptism", "baptized", "baptised",
}
STRONG_MZ = {
    "pathian", "pathiana", "pathianin", "lalpa", "lalpan", "isua", "isuan",
    "krista", "kristan", "setana", "setanan", "bible", "bibl", "jehova",
    "jehovan", "kohhran", "vantirhkoh", "thuthlung", "tirhkoh", "tirhkohte",
}
WEAK_MZ = {
    "thlarau", "ramhuai", "sual", "sualna", "tawngtaina", "tawngtai", "chibai",
    "zirtir", "zirtirte", "chatuan", "vanram", "thawhlehna", "simna",
    "lalram", "malsawmna", "hmangaihna", "inkhawm", "unau", "unaute",
}
# Watchtower/JW publications are a large share of the Glosbe portion. jw.org
# publishes in Mizo and is heavily crawled, so this register carries a
# contamination risk comparable to scripture even when it quotes no verse.
JW_MARKER_RE = re.compile(
    r"\b(watchtower|awake!|kingdom hall|governing body|field service|"
    r"congregation book study|ministry school|yearbook|jw\.org|"
    r"circuit overseer|pioneer(s)? |publisher(s)? )\b",
    re.IGNORECASE,
)
ARCHAIC_RE = re.compile(
    r"\b(thou|thee|thy|thine|ye|hath|hast|doth|dost|shalt|wilt|unto|"
    r"whither|thither|behold|verily|saith|cometh|goeth|maketh|giveth)\b",
    re.IGNORECASE,
)

_PUNCT = str.maketrans({c: " " for c in string.punctuation})


def norm_words(s: str) -> list[str]:
    s = unicodedata.normalize("NFKC", s).lower().translate(_PUNCT)
    return s.split()


def ngrams(words: list[str], n: int = NGRAM_N) -> list[tuple[str, ...]]:
    return [tuple(words[i:i + n]) for i in range(len(words) - n + 1)]


def ensure_kjv() -> Path:
    """Download the Project Gutenberg KJV once; cached thereafter."""
    if KJV_PATH.exists() and KJV_PATH.stat().st_size > 1_000_000:
        return KJV_PATH
    EXTERNAL.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(KJV_URL, timeout=60) as r:
        KJV_PATH.write_bytes(r.read())
    return KJV_PATH


def build_kjv_index(n: int = NGRAM_N) -> set[tuple[str, ...]]:
    text = ensure_kjv().read_text(encoding="utf-8", errors="replace")
    return set(ngrams(norm_words(text), n))


@dataclass
class Signals:
    kjv_hits: int
    kjv_ngram: float
    verse_cite: bool
    strong_en: int
    weak_en: int
    biblical_names: int
    strong_mz: int
    weak_mz: int
    archaic: int
    jw_marker: bool
    n_ngrams: int

    @property
    def stratum(self) -> str:
        """Three registers, ordered by how strongly memorisation is implied.

        `scripture` is verbatim Bible text -- the KJV and the Mizo Bible are
        among the most duplicated documents on the web, so a model reproducing
        them is reciting, not translating. `religious` is Christian
        institutional prose (largely Watchtower material here): published in
        Mizo, heavily crawled, and so also plausibly memorised, but not
        word-for-word canonical. `secular` is everything else and is the only
        stratum that measures translation ability without that confound.
        """
        # Absolute hit count as well as fraction: a short verse can match only
        # a few 6-grams and still be unambiguously scripture, which a
        # fraction-only rule misses.
        if self.kjv_hits >= 3 or (self.n_ngrams and self.kjv_ngram >= KJV_THRESHOLD):
            return "scripture"
        if self.verse_cite and (self.strong_en or self.strong_mz or self.weak_en >= 1):
            return "scripture"
        if (
            self.strong_en
            or self.biblical_names
            or self.strong_mz
            or self.jw_marker
            or self.verse_cite
            or self.weak_en + self.weak_mz >= 2
            or self.archaic >= 2
        ):
            return "religious"
        return "secular"

    @property
    def is_religious_domain(self) -> bool:
        return self.stratum in ("scripture", "religious")


def score_pair(en: str, mz: str, kjv: set[tuple[str, ...]]) -> Signals:
    en_words = norm_words(en)
    en_set = set(en_words)
    grams = ngrams(en_words)
    hits = sum(1 for g in grams if g in kjv)
    mz_set = set(norm_words(mz))
    return Signals(
        kjv_hits=hits,
        kjv_ngram=hits / len(grams) if grams else 0.0,
        verse_cite=bool(VERSE_CITE_RE.search(en) or VERSE_CITE_RE.search(mz)),
        strong_en=sum(1 for w in en_set if w in STRONG_EN),
        weak_en=sum(1 for w in en_set if w in WEAK_EN),
        biblical_names=sum(1 for w in en_set if w in BIBLICAL_NAMES),
        strong_mz=sum(1 for w in mz_set if w in STRONG_MZ),
        weak_mz=sum(1 for w in mz_set if w in WEAK_MZ),
        archaic=len(ARCHAIC_RE.findall(en)),
        jw_marker=bool(JW_MARKER_RE.search(en)),
        n_ngrams=len(grams),
    )


def load_mt() -> list[dict]:
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(HF_REPO, HF_FILE, repo_type="dataset")
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def run(sample_size: int = 200, seed: int = 20260907) -> Counter:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    HUMAN_EVAL.mkdir(parents=True, exist_ok=True)

    kjv = build_kjv_index()
    rows = load_mt()
    out: list[dict] = []
    counts: Counter = Counter()

    for i, r in enumerate(rows):
        en, mz = r["translation"]["en"], r["translation"]["mz"]
        sig = score_pair(en, mz, kjv)
        rec = {
            "id": f"mt{i:05d}",
            "en": en,
            "mz": mz,
            "source": r.get("source"),
            "quality": r.get("quality"),
            "stratum": sig.stratum,
            "religious_domain": sig.is_religious_domain,
            "signals": asdict(sig),
        }
        out.append(rec)
        counts[sig.stratum] += 1
        counts[f"{r.get('source')}::{sig.stratum}"] += 1

    write_jsonl(PROCESSED / "mizoeval-mt-all.jsonl", out)
    for stratum in ("scripture", "religious", "secular"):
        write_jsonl(PROCESSED / f"mizoeval-mt-{stratum}.jsonl",
                    [r for r in out if r["stratum"] == stratum])

    write_validation_sample(out, sample_size, seed)
    return counts


def write_validation_sample(rows: list[dict], n: int, seed: int) -> None:
    """Balanced packet for hand-validating the stratifier's precision/recall.

    The stratifier is an ensemble of heuristics, so its own error rate has to be
    measured before any claim rests on it. Sampling both strata equally means
    the packet estimates precision and recall, not just precision.
    """
    import csv
    import random

    rng = random.Random(seed)
    strata = ("scripture", "religious", "secular")
    per = n // len(strata)
    picked = []
    for s_name in strata:
        pool = [r for r in rows if r["stratum"] == s_name]
        picked += rng.sample(pool, min(per, len(pool)))
    rng.shuffle(picked)

    with (HUMAN_EVAL / "mt_stratum_validation.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "en", "mz", "source", "predicted_stratum",
                    "kjv_ngram", "HUMAN_LABEL_scripture_religious_or_secular", "NOTES"])
        for r in picked:
            w.writerow([r["id"], r["en"], r["mz"], r["source"], r["stratum"],
                        f"{r['signals']['kjv_ngram']:.3f}", "", ""])


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sample", type=int, default=200,
                    help="size of the hand-validation packet")
    args = ap.parse_args()
    counts = run(sample_size=args.sample)
    strata = ("scripture", "religious", "secular")
    total = sum(counts[k] for k in strata)
    print(f"total pairs      : {total}")
    for k in strata:
        print(f"  {k:<14s}: {counts[k]:5d} ({100 * counts[k] / total:5.1f}%)")
    rel = counts["scripture"] + counts["religious"]
    print(f"  {'religious dom.':<14s}: {rel:5d} ({100 * rel / total:5.1f}%)")
    print("\nby source:")
    for k in sorted(counts):
        if "::" in k:
            print(f"  {k}: {counts[k]}")


if __name__ == "__main__":
    main()
