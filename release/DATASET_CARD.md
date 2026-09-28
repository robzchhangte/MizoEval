---
pretty_name: MizoEval
language:
  - lus
  - en
task_categories:
  - multiple-choice
  - text-classification
  - token-classification
  - translation
size_categories:
  - 1K<n<10K
---

# MizoEval

MizoEval is a four task benchmark for evaluating large language models on Mizo (`lus`, Tibeto Burman, roughly one million speakers, Mizoram, northeast India). It accompanies the paper *MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol*.

Every task was assembled from text that was already publicly available. This release contains the audited and repaired versions, together with the audit trail, so that every number in the paper can be traced to a documented data decision.

## Tasks and sources

| Task | Config | Files | Source | Terms |
|---|---|---|---|---|
| Regional knowledge MCQ | `mcq` | `mizoeval-mcq-v1.jsonl`, `-mcq4.jsonl`, `-mcq4-permuted.jsonl` | Past question papers published by the Mizoram Public Service Commission, <https://mpsc.mizoram.gov.in/> | Question text belongs to the Commission. Answer keys, explanations, and repair annotations by the MizoEval authors: CC-BY-4.0. |
| Sentiment | `sentiment` | `mizoeval-sentiment-v1.jsonl` | `hillbyte/mizo-sentiment` (Mizo social media text, names replaced by `[PERSON]`) | MIT |
| Named entity recognition and keyword identification | `ner`, `keyword` | `mizoeval-ner-*.conll`, `mizoeval-keyword-*.conll` | Mizo NER Datasets, India Data (owner: Parameswari Krishnamurthy), <https://india-data.org/dataset-details/5e9b5054-b0a6-46dc-b586-1f44f3d9da8c>; text originates from Mizo news | Governed by the India Data for NLP Data User Agreement. Users of this release must also comply with that agreement. |
| English to Mizo translation | `mt` | `mizoeval-mt-{all,scripture,religious,secular}.jsonl` | Publicly available English Mizo parallel text collected by the authors; the `source` field on each pair records its origin (`gold` or `glosbe`). Bible text is included in both languages. | CC-BY-4.0 for the authors' compilation, stratification labels, and annotations. Underlying texts remain with their respective rights holders. |

## What was repaired

Each source was audited before use. The full before and after counts are in `REPAIR_REPORT.md`. In summary: duplicate and conflicting MCQ items removed or quarantined, the keyword layer separated from the NER tags, the NER splits made document disjoint, and the translation set stratified by register into scripture, other religious text, and secular text.

## Intended use

Evaluation of language models on Mizo. Not intended for training; the MT scripture stratum in particular is likely to be present in model pretraining data, which is the reason the register labels are provided.

## Personal information

Sentiment text was anonymised at source (`[PERSON]` placeholders). No new data was collected from human participants for this release.

## Takedown

If you are a rights holder for any included text and would like it removed or attributed differently, contact the corresponding author (dt21cs003@nitmz.ac.in). Requests will be handled promptly and reflected in a new release version.

## Citation

Please cite the paper and the Zenodo record (DOI assigned on release).
