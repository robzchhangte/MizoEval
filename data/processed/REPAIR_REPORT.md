# MizoEval — Data Repair Report

Generated 2026-09-07 by `python -m mizoeval.repair.make_report`.
Every figure below is produced by re-running the repair modules; none is hand-entered.

---

## 1. MCQ benchmark

Source: `data/raw/mizoram_mcq_with_answers.json`

| Step | Count |
|---|---|
| Raw items | 2400 |
| Duplicate groups (stem + choice set) | 315 |
| Duplicate rows merged away | 247 |
| **Groups with conflicting gold answers (quarantined)** | **117** |
| Items removed by that quarantine | 283 |
| Items with an answer key outside their own choices | 0 |
| **Released items** | **1870** |

### Format partition

The dataset card promises a uniform 4-option MCQ benchmark. It is not one, so
items are partitioned by answer-key shape rather than silently discarded.
`mcq4` is the headline subset; the rest are reported separately.

| Format | Items |
|---|---|
| `mcq4` | 1747 |
| `mcq_other` | 57 |
| `mcq_tf` | 54 |
| `mcq_roman` | 12 |

39 items contain an "all/none of the above" option. These
are flagged and excluded from the permuted variant, whose reordering would
make such an option meaningless.

### Answer-position bias

Gold answers are not uniformly distributed across positions, so a model that
always answers `A` beats random guessing. The permuted variant removes this.

| Position | `mcq4` gold | Permuted variant |
|---|---|---|
| A | 525 (30.1%) | 439 (25.7%) |
| B | 522 (29.9%) | 417 (24.4%) |
| C | 434 (24.8%) | 425 (24.9%) |
| D | 266 (15.2%) | 427 (25.0%) |

### Corrections to the published dataset card

- Card states English 97.9% / Mizo 2.1%. Actual, on the released set: English 1848 (98.8%), Mizo 22 (1.2%).
- Card states "100% validated 4-option choices". 123 released items are not 4-option.
- Card states "100% ground-truth answer key coverage". Coverage is complete, but 117 repeated questions carry mutually contradictory keys.

### Outstanding — requires native-speaker adjudication

`data/human_eval/mcq_conflicts.csv` holds the 117 conflicting groups
(283 items) for panel adjudication. They are excluded from
the release until resolved. No conflict is resolved automatically: each is a case where
two official-looking sources disagree, and guessing would inject silent label noise.

## 2. NER corpus

| Split | Sentences | Tokens | Entity spans | Keyword spans |
|---|---|---|---|---|
| train | 3576 | 92699 | 5038 | 1714 |
| valid | 447 | 11769 | 584 | 199 |
| test | 447 | 11801 | 698 | 170 |

Changes applied:

- Lowercase `b-`/`i-` prefixes uppercased to standard BIO.
- `KEYWORD` split into its own task files (`mizoeval-keyword-*.conll`). It is keyword
  identification, not named-entity recognition; leaving it in the entity layer would
  have inflated the entity count by 1714 spans in train alone.
- Dropped `NETE`, `NEU`, `NEDA`: {'NEU': 1, 'NEDA': 1, 'NETE': 3} instances in train, none in valid or test.
- Retained tagset: `NEAR`, `NEF`, `NEL`, `NEMI`, `NEO`, `NEP`, `NETI`.
- `gold_.conll` is unnamed in the release; it is the test split, confirmed by the
  leakage analysis below.
- Token text is never modified — only tags and span boundaries.

### Leakage in the released split — a blocking finding

All three splits come from the same news site, and the release assigns *sentences*
rather than *articles*, so sentences from one article land in different splits:

| Pair | Shared source articles | Identical sentences |
|---|---|---|
| train / valid | 302 | 5 |
| train / test | 286 | 8 |
| valid / test | 153 | 1 |

Measured directly: **100% of validation sentences and 99.6% of test sentences come
from an article that also appears in training.** Any model fine-tuned on this split
has seen the same article, entities and context at training time, so its reported
test F1 is optimistic.

### Document-disjoint re-split

Published alongside the official split (`mizoeval-ner-docsplit-*.conll`). Articles are
assigned whole, and sentences reposted verbatim under a different URL are dropped from
the held-out sets. Both splits ship: the official one for comparability with prior
work, this one for the uninflated number.

| Split | Sentences | Source articles |
|---|---|---|
| train | 3576 | 441 |
| valid | 444 | 59 |
| test | 436 | 56 |

Overlap after re-splitting: train/valid = 0 articles / 0 sentences, train/test = 0 articles / 0 sentences, valid/test = 0 articles / 0 sentences.

## 3. Translation benchmark

Source: `robzchhangte/en-mz-benchmark` (3,000 pairs, test split, currently private).

The benchmark is overwhelmingly religious text. The King James Version and the Mizo
Bible are both freely available on the open web, as is jw.org's Mizo output, so these
pairs are almost certainly memorised by the models under test. Scored in aggregate,
this benchmark reports memorisation as translation quality.

| Stratum | Pairs | Share |
|---|---|---|
| scripture | 1373 | 45.8% |
| religious | 818 | 27.3% |
| secular | 809 | 27.0% |
| **religious domain (scripture + religious)** | **2191** | **73.0%** |

| Source | scripture | religious | secular |
|---|---|---|---|
| `gold` | 1238 | 238 | 324 |
| `glosbe` | 135 | 580 | 485 |

Only **809 pairs (27.0%)** are secular,
and that is an upper bound: the classifier is lexical, so modern-translation scripture
that names no person and quotes no verse still slips through. Every religious-domain
figure here is therefore a **lower bound**.

`data/human_eval/mt_stratum_validation.csv` holds a stratified sample for hand-labelling,
which measures the classifier's actual precision and recall. The paper reports that
measurement rather than assuming the classifier is exact.

## 4. Sentiment corpus

Source: `hillbyte/mizo-sentiment`.

| Property | Value |
|---|---|
| Raw rows | 1220 |
| Duplicate texts dropped | 70 |
| Released items | 1150 |
| Label distribution | {'Neutral': 320, 'Positive': 653, 'Negative': 177} |
| Majority-class baseline (accuracy) | 56.8% |
| Mean out-of-Mizo-vocabulary rate | 0.143 |
| Code-mixed items (OOV > 0.3) | 151 |
| Items carrying a `[PERSON]` placeholder | 170 |

Because a constant "Positive" prediction already scores 56.8%, **accuracy is not reported as a primary
metric for this task — macro-F1 is.** Five stratified folds are assigned so every fold
mirrors the corpus label distribution.

Undocumented in the source card and therefore unknown: the annotation guidelines, the
number of annotators, and inter-annotator agreement. Stated as a limitation rather than
reconstructed.

---

## Released files

- `data/processed/mizoeval-keyword-docsplit-test.conll`
- `data/processed/mizoeval-keyword-docsplit-train.conll`
- `data/processed/mizoeval-keyword-docsplit-valid.conll`
- `data/processed/mizoeval-keyword-test.conll`
- `data/processed/mizoeval-keyword-train.conll`
- `data/processed/mizoeval-keyword-valid.conll`
- `data/processed/mizoeval-mcq-v1-mcq4-permuted.jsonl`
- `data/processed/mizoeval-mcq-v1-mcq4.jsonl`
- `data/processed/mizoeval-mcq-v1.jsonl`
- `data/processed/mizoeval-mt-all.jsonl`
- `data/processed/mizoeval-mt-religious.jsonl`
- `data/processed/mizoeval-mt-scripture.jsonl`
- `data/processed/mizoeval-mt-secular.jsonl`
- `data/processed/mizoeval-ner-docsplit-test.conll`
- `data/processed/mizoeval-ner-docsplit-train.conll`
- `data/processed/mizoeval-ner-docsplit-valid.conll`
- `data/processed/mizoeval-ner-test.conll`
- `data/processed/mizoeval-ner-train.conll`
- `data/processed/mizoeval-ner-valid.conll`
- `data/processed/mizoeval-sentiment-v1.jsonl`

## Pending human adjudication

- `data/human_eval/mcq_conflicts.csv`
- `data/human_eval/mt_stratum_validation.csv`
