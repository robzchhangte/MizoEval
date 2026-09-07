# MizoEval

A multi-task LLM evaluation benchmark for **Mizo** (`lus`; Lushai), a Tibeto-Burman
language of Mizoram, northeast India, written in Latin script and spoken by roughly
one million people. Mizo is absent from the major Indic LLM benchmarks — MILU,
IndicGLUE, IndicXTREME, Global-MMLU — all of which cover only Indo-Aryan and
Dravidian languages. MizoEval extends MILU's paradigm (benchmarks built from state
competitive examinations) to a genuinely uncovered typological and geographic gap,
and adds a contamination-aware evaluation protocol.

The project accompanies a journal paper in preparation.

## Tasks

| Task | Source | Released items | Primary metric |
|------|--------|---------------:|----------------|
| **MCQ** — regional knowledge | Mizoram civil-service exams (MPSC / MCS / departmental) | 1,870 (1,747 strictly 4-option) | accuracy + Wilson CI |
| **MT** — English ↔ Mizo | `robzchhangte/en-mz-benchmark` (3,000 pairs) | 3,000, register-stratified | chrF++ (bootstrap CI) |
| **Sentiment** — 3-class | `hillbyte/mizo-sentiment` | 1,150 | macro-F1 |
| **NER** — 7 entity types | India-Data Mizo NER (CoNLL) | 4,469 train / 584 valid / 698 test entity spans | entity-level F1 (seqeval) |

## Why the datasets needed repair

An audit of all four source datasets (`data/processed/REPAIR_REPORT.md`, regenerated
by `python -m mizoeval.repair.make_report`) found defects that would each invalidate a
straightforward evaluation. Repair is treated as methodology and reported in full.

- **MCQ.** 247 duplicate rows merged. **117 duplicate-question groups carry
  contradictory gold answers** — quarantined to `data/human_eval/mcq_conflicts.csv`
  for native-speaker adjudication, never auto-resolved. The dataset card promises a
  uniform 4-option format, but 123 released items are TRUE/FALSE or Roman-numeral;
  these are partitioned out by a `format` field. Gold answers are position-biased
  (A 30%, D 15%), so a **choice-permuted variant** ships alongside to separate
  knowledge from position preference.
- **NER.** Lowercase `b-`/`i-` normalised to standard BIO. `KEYWORD` (a different
  task — keyword identification) split out of the entity layer. Three tags with ≤3
  instances dropped. **The official split is document-leaky**: 100% of validation and
  99.6% of test sentences come from a news article that also appears in training
  (the release splits *sentences*, not *articles*). A **document-disjoint re-split**
  ships alongside the official one — both are published, the official for
  comparability and the re-split for the uninflated number.
- **MT.** ~73% of the 3,000 pairs are religious text (~46% verbatim scripture),
  detected by KJV 6-gram overlap plus five lexical signals. The KJV, the Mizo Bible
  and jw.org's Mizo output are all freely on the open web, so an aggregate score
  reports memorisation as translation quality. Pairs are stratified into
  `scripture` / `religious` / `secular`; only ~810 pairs are secular, and that is an
  upper bound. A stratified sample (`data/human_eval/mt_stratum_validation.csv`)
  measures the classifier's own error rate.
- **Sentiment.** 70 duplicate texts dropped, stratified 5-fold. The majority class
  is 57%, so accuracy is not a primary metric — macro-F1 is. A per-item
  out-of-Mizo-vocabulary rate is attached as a code-mixing covariate.

## Repository layout

```
data/
  raw/          the seven source files, committed untouched
  processed/    all repaired / derived artefacts (regenerable) + REPAIR_REPORT.md
  human_eval/   adjudication packets for the panel
  external/     public-domain KJV text for the MT stratifier (git-ignored, re-downloaded)
src/mizoeval/
  repair/       mcq_repair, ner_normalize, mt_stratify, sentiment_prep, make_report
  datasets/     offline loaders for the processed files
  models/       provider adapters, SQLite response cache, rotating key pool, roster
  prompts/      versioned + hashed prompt templates
  parsing/      answer extractors (report which strategy fired) + span alignment
  metrics/      per-task scoring + statistics (bootstrap, McNemar, Holm-Bonferroni)
  runners/      run_task (one cell), run_matrix (the full grid)
  contamination/  memorisation probes (in progress)
configs/
  models.yaml   the model roster — one pinned model_id per entry
  tasks.yaml    the evaluation matrix (14 cells)
results/
  raw/          one JSONL + manifest per run; cache.sqlite (git-ignored)
tests/          88 tests: repair invariants, metric two-sided sanity, runner plumbing
```

## Setup

```bash
pip install -e ".[providers,dev]"
```

Regenerate the processed datasets from `data/raw/` (needs Hugging Face access for the
two HF datasets):

```bash
python -m mizoeval.repair.mt_stratify        # also downloads the KJV reference text
python -m mizoeval.repair.ner_normalize
python -m mizoeval.repair.sentiment_prep
python -m mizoeval.repair.mcq_repair
python -m mizoeval.repair.make_report        # writes data/processed/REPAIR_REPORT.md
```

## Credentials

Put keys in `.env` (git-ignored) or the environment. Nothing runs against a paid API
until you enable that model in `configs/models.yaml`.

| Provider | Auth |
|----------|------|
| OpenAI | `OPENAI_API_KEY` |
| Google Vertex AI | `gcloud auth application-default login` + `GOOGLE_CLOUD_PROJECT` (and optional `GOOGLE_CLOUD_LOCATION`) |
| Ollama Cloud | `keys.txt` — one API key per line, git-ignored; the pool rotates to the next key on a rate-limit and cools the spent one. Falls back to `OLLAMA_API_KEY`. |

Every `model_id` in `configs/models.yaml` is **pinned to an exact version** — the
loader rejects `latest`/`preview` aliases, since an alias makes a published number
unreproducible. The committed values are placeholders marked `CONFIRM`; verify each
against its provider before the first paid run.

## Running an evaluation

One cell:

```bash
python -m mizoeval.runners.run_task --task mcq --regime zero_shot --model gemma4-31b
python -m mizoeval.runners.run_task --task mt  --regime zero_shot --direction en2mz --model gemma4-31b
python -m mizoeval.runners.run_task --task mcq --regime zero_shot --model gemma4-31b --limit 5   # smoke test
```

The whole 14-cell matrix for one or more models:

```bash
python -m mizoeval.runners.run_matrix --model gemma4-31b
python -m mizoeval.runners.run_matrix --all-enabled --only mcq,sentiment
```

Every model call is cached in `results/cache.sqlite`, keyed on the full request
(model, prompt, parameters). Runs are **resumable** — stop any time and re-run, and
completed work costs nothing on the second pass. Each run writes
`results/raw/<key>.jsonl` (raw reply persisted *before* parsing) and
`<key>.manifest.json` (model id, prompt-template hashes, seed, parse-failure rate,
token counts, cost). No number in the paper is reported without a manifest behind it.

## Results so far

`gemma4:31b-cloud` via Ollama Cloud, temperature 0. MCQ cells complete; MT / sentiment
/ NER in progress.

| Cell | Score | 95% CI | Parse-fail |
|------|------:|--------|-----------:|
| MCQ zero-shot (4-option) | 61.6% | 59.3–63.9 | 0.2% |
| MCQ five-shot (4-option) | 62.4% | 60.2–64.7 | 0.2% |
| MCQ chain-of-thought (4-option) | 61.8% | 59.5–64.0 | 0.3% |
| MCQ zero-shot, **choice-permuted** | **56.3%** | 53.9–58.6 | 0.1% |
| MCQ CoT, **choice-permuted** | **56.7%** | 54.4–59.1 | 0.1% |
| MCQ zero-shot, all formats | 60.3% | 58.0–62.5 | 2.2% |

Permuting the answer choices to a uniform position distribution costs ~5 accuracy
points — the model is partly exploiting the source data's A-heavy gold distribution.
This is why the permuted variant exists, and it is a headline methodological point:
naive MCQ accuracy on this benchmark is inflated by roughly 5 points.

## Status

Done: repository scaffold; repair of all four datasets; the evaluation harness
(providers, cache, key rotation, parsers, metrics, statistics); the first full model
run (Ollama Cloud, `gemma4:31b-cloud`).

Next: contamination probes (verse-completion, MCQ canary, temporal split); add
`gpt-5-mini` (OpenAI) and Gemini Flash (Vertex) once their model IDs are confirmed
(estimated ≈ $7–8 for both full runs at placeholder prices); native-speaker human
evaluation (MT adequacy/fluency, MCQ conflict adjudication); manuscript.

## Licensing (unresolved)

The four sources carry different terms — MT is CC-BY-4.0 and currently **private**,
sentiment is MIT, NER carries an India-Data DUA, and MCQ provenance is government
examination papers. Redistribution terms for the MCQ material and public release of
the MT benchmark are open questions that gate the artefact release.

## Citation

Paper in preparation. Please open an issue before using MizoEval in published work so
we can point you at the current version and its known limitations.
