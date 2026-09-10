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
  runners/      run_task (one cell), run_matrix (the full grid, token-budget capped)
  contamination/  memorisation probes: verse-completion, MCQ canary, temporal split
configs/
  models.yaml   the model roster — one pinned model_id per entry
  tasks.yaml    the evaluation matrix (14 cells)
results/
  raw/          one JSONL + manifest per run; cache.sqlite (git-ignored)
  contamination/  per-model probe outputs + CONTAMINATION_REPORT.md
tests/          102 tests: repair invariants, metric two-sided sanity, runner
                plumbing, key-pool rotation, token budget, contamination scoring
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
| Google (Gemini API) | `GEMINI_API_KEY` — the `google` provider; Gemini 2.5+/3.x Flash "thinking" is disabled by default so tokens stay counted, and a 120 s HTTP timeout guards against hung calls |
| Google Vertex AI | the `vertex` provider — same models over `gcloud auth application-default login` + `GOOGLE_CLOUD_PROJECT` (optional `GOOGLE_CLOUD_LOCATION`) |
| Ollama Cloud | `keys.txt` — one API key per line, git-ignored; the pool rotates to the next key on a rate-limit and cools the spent one. Falls back to `OLLAMA_API_KEY`. Free tier serves one request at a time; `gpt-oss:120b` is the only free `-cloud`-eligible model. Reasoning models get a `num_predict` floor so short-answer tasks still parse. |

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
python -m mizoeval.runners.run_matrix --model gpt-5.4-mini --token-budget 1000000
```

`--token-budget N` caps total *live* tokens (prompt + completion, reasoning
included) across the whole matrix for that model; cache replays do not count, so a
capped resume spends the budget only on cells not yet run. The run stops cleanly at
the cap and writes partial results with `budget_stopped` set.

Every model call is cached in `results/cache.sqlite`, keyed on the full request
(model, prompt, parameters). Runs are **resumable** — stop any time and re-run, and
completed work costs nothing on the second pass. Each run writes
`results/raw/<key>.jsonl` (raw reply persisted *before* parsing) and
`<key>.manifest.json` (model id, prompt-template hashes, seed, parse-failure rate,
token counts, cost). No number in the paper is reported without a manifest behind it.

Contamination probes for one model:

```bash
python -m mizoeval.contamination.run_probes --model gemini-3.5-flash
```

This runs verse-completion (prefix-completion fidelity per MT stratum, both
language sides), the MCQ canary (options-hidden answer recall, blind vs.
source-exam-guided) and the temporal split (re-buckets an existing MCQ result file
by `source_year`; no API calls), plus a calibration check that the completion probe
fires on a canonical KJV verse and stays quiet on freshly-written Mizo. Outputs land
in `results/contamination/`.

## Results so far

Temperature 0, seed 20260907. As of 2026-09-10; some model runs are still in
progress (token-budget capped, resumable) and partial cells are marked. Every number
traces to a manifest in `results/raw/`.

**MCQ — accuracy on the strict 4-option set (n ≈ 1,747)**

| Model | zero-shot | choice-permuted | five-shot | chain-of-thought |
|-------|----------:|----------------:|----------:|-----------------:|
| gemma4:31b (open, free) | 61.6% | **56.3%** | 62.4% | 61.8% |
| gemini-3.5-flash | 60.0% | **59.3%** | 60.3% | 60.4% |
| gpt-5.4-mini | 56.7% | **53.3%** | 56.4% | 56.9% |
| gpt-5.4 (flagship) | 54.1%¹ | — | — | — |
| gpt-oss:120b (open, free) | ~48% | — | — | 47.6% |

¹ partial (n = 1,290). — Random baseline 25%; majority-position (A) ≈ 30%.

Two findings hold across models: **choice-permutation costs 0.7–5.3 points** (largest
for gemma4, smallest for gemini) — naive accuracy is inflated by the source data's
A-heavy gold — and **chain-of-thought gives no gain** over zero-shot on any model.
The flagship `gpt-5.4` is (so far) the *weakest* on Mizoram regional knowledge:
bigger is not better here.

**Sentiment — macro-F1 (majority-class baseline 0.568)**

| Model | zero-shot | five-shot |
|-------|----------:|----------:|
| gemini-3.5-flash | 0.669 | **0.741** |
| gpt-5.4-mini | 0.568 | 0.667 |
| gemma4:31b | 0.583 | 0.640 |
| gpt-oss:120b | — | 0.459 (below baseline) |

**NER — entity-level micro-F1**

| Model | official test | document-disjoint re-split |
|-------|--------------:|--------------------------:|
| gemini-3.5-flash | 0.260 | 0.186 |
| gpt-5.4-mini | 0.236 | 0.182 |
| gemma4:31b | 0.233 | 0.191 |
| gpt-oss:120b | 0.04 (62% parse failure) | 0.06 |

Removing the document leak costs 4–7 F1 points. `gpt-oss:120b` cannot emit parseable
span output and is unusable for NER.

**MT — chrF++ by register stratum, zero-shot (scripture / religious / _secular_)**

| Model | direction | scripture | religious | _secular_ |
|-------|-----------|----------:|----------:|----------:|
| gpt-5.4-mini | mz→en | 45.0 | 46.7 | _35.0_ |
| gpt-5.4-mini | en→mz | 36.0¹ | 37.9¹ | _35.0¹_ |
| gemini-3.5-flash | mz→en | 65.5¹ | 56.4¹ | _42.6¹_ |
| gemma4:31b | mz→en | 38.4 | 42.8 | _33.6_ |
| gemma4:31b | en→mz | 29.6 | 31.5 | _27.1_ |
| gpt-oss:120b | either | < 8 | < 8 | _< 8_ |

¹ partial cell. The **_secular_ column is the honest number**; scripture/religious
scores are inflated by memorisation (see below). `gpt-oss:120b` fails at Mizo
translation outright (chrF near zero).

## Contamination

`results/contamination/CONTAMINATION_REPORT.md`. Three probes, all calibrated so the
completion probe fires on a canonical KJV verse (chrF 100) and not on freshly-written
Mizo (chrF ≈ 17).

**Verse-completion** — feed the first half of a pair's text, score the model's
continuation against the withheld half. Gap between the scripture and secular strata
(chrF; English side / Mizo side):

| Model | scripture − secular (EN) | verbatim recall (EN) | scripture − secular (MZ) |
|-------|------------------------:|---------------------:|------------------------:|
| gemini-3.5-flash | **+54.0** | 57% | **+18.5** |
| gpt-5.4-mini | **+46.2** | 42% | +2.9 |
| gemma4:31b | +11.0 | 1% | +1.6 |

All models recite held-out KJV English far above their secular baseline. On the
**Mizo** side only `gemini-3.5-flash` shows clear Mizo-Bible memorisation — so
contamination is model-specific and must be reported per model, and the
secular-stratum MT score is the one to trust.

**MCQ canary** (options-hidden answer recall): 18–26% blind recall, scaling with
model capability; naming the source exam adds nothing (no "guided instruction" leak).

**Temporal split**: all models score *higher* on 2025–2026 items than pre-2023 —
confounded by 2026 training cutoffs and uneven year coverage, so reported as a
limitation of year-based analysis, not as evidence.

## Status

Done: repository scaffold; repair of all four datasets; the evaluation harness
(providers, cache, key rotation, token budget, parsers, metrics, statistics); the
contamination-probe module and full 3-model probe runs; matrix runs for `gemma4:31b`
(complete), `gpt-5.4-mini`, `gemini-3.5-flash`, `gpt-oss:120b`, and a `gpt-5.4`
flagship sample (all resumable, several MT cells outstanding).

Next: finish the outstanding MT cells; classical and fine-tuned **baselines**
(majority / TF-IDF+LR / XLM-R / MuRIL, and NLLB-200 / IndicTrans2 for MT);
native-speaker **human evaluation** (MT adequacy/fluency, MCQ conflict adjudication,
NER spot-audit); the analysis module that assembles `results/` into the paper's
tables and figures; manuscript.

## Licensing (unresolved)

The four sources carry different terms — MT is CC-BY-4.0 and currently **private**,
sentiment is MIT, NER carries an India-Data DUA, and MCQ provenance is government
examination papers. Redistribution terms for the MCQ material and public release of
the MT benchmark are open questions that gate the artefact release.

## Citation

Paper in preparation. Please open an issue before using MizoEval in published work so
we can point you at the current version and its known limitations.
