# MizoEval — Contamination Report

Generated from `results/contamination/*.json` (probe code: `src/mizoeval/contamination/probes.py`).
Three probes, all API-only, all responses cached. Models: `gemini-3.5-flash`
(Google API), `gpt-5.4-mini` (OpenAI API), `gemma4:31b-cloud` (open-weight, Ollama Cloud).

**Bottom line.** The MT benchmark is 73% religious / 46% verbatim KJV scripture.
The closed frontier models have memorised the parallel Bible — heavily on the
English (KJV) side, and, for `gemini-3.5-flash`, substantially on the Mizo side
too. The open-weight `gemma4:31b` shows only mild English-side recall. **The
honest MT number for every model is the secular-stratum score**; scripture and
religious strata are recall-inflated, most severely for `gemini-3.5-flash`.

---

## Probe calibration (verification item 5)

The completion probe must fire on known-memorised text and stay silent on
freshly-written Mizo. Anchor = John 3:16 (KJV); negative control = 4
hand-written mundane Mizo sentences in no public corpus.

| model | KJV anchor chrF | fresh Mizo mean chrF | separates? |
|---|--:|--:|:--:|
| gemini-3.5-flash | 100.0 | 16.1 | yes |
| gpt-5.4-mini | 100.0 | 17.5 | yes |
| gemma4:31b | 100.0 | 20.0 | yes |

All three complete the single most-quoted verse in English verbatim; none can
continue an unseen Mizo sentence. The probe is calibrated. (That every model
aces John 3:16 while differing sharply on a random 150-verse sample below is the
point: the calibration shows the probe *works*; the stratum sample shows *how
deep* each model's memorisation runs.)

---

## Probe 1 — verse completion (MT memorisation)

Feed the first half of a pair's text (word-boundary split), score the model's
continuation against the withheld half. `chrF` = character n-gram F (0–100);
`verbatim` = share of items reproducing ≥80% of the true continuation's words
in order. n = 150 per stratum per side.

### English side (KJV) — positive control

| model | scripture chrF | religious chrF | secular chrF | **scr − sec** | scripture verbatim |
|---|--:|--:|--:|--:|--:|
| gemini-3.5-flash | 73.7 | 23.3 | 19.6 | **+54.0** | **0.567** |
| gpt-5.4-mini | 67.0 | 23.9 | 20.8 | **+46.2** | **0.420** |
| gemma4:31b | 29.5 | 20.4 | 18.5 | **+11.0** | 0.007 |

### Mizo side — the side that inflates en→mz / mz→en MT

| model | scripture chrF | religious chrF | secular chrF | **scr − sec** | scripture verbatim |
|---|--:|--:|--:|--:|--:|
| gemini-3.5-flash | 38.3 | 23.8 | 19.8 | **+18.5** | 0.013 |
| gpt-5.4-mini | 21.0 | 17.7 | 18.1 | +2.9 | 0.000 |
| gemma4:31b | 20.8 | 20.3 | 19.1 | +1.6 | 0.000 |

**Reading.**
- Every model recites held-out KJV English far above its secular baseline
  (Δ +11 to +54). `gemini-3.5-flash` reproduces **57%** of held-out scripture
  halves near-verbatim, `gpt-5.4-mini` 42%.
- On the **Mizo** side the models diverge: `gemini-3.5-flash` has clearly
  ingested the Mizo Bible (Δ +18.5 chrF); `gpt-5.4-mini` and `gemma4:31b` have
  not (Δ ≈ +2). Contamination is **model-specific** and must be reported per
  model, not as a single benchmark-level caveat.
- Secular-stratum chrF sits at ~18–21 for all models on both sides — the floor,
  consistent with no memorisation. This is the score to trust.

---

## Probe 2 — MCQ canary (item leakage)

Show the stem with **all four options hidden**; score a hit only when the
free-text answer matches the gold option by chrF and beats every distractor by
≥10. `blind` = stem only; `guided` = stem prefixed with the source-exam name and
year. n = 300.

| model | blind recall [95% CI] | guided recall [95% CI] | guided − blind |
|---|---|---|--:|
| gemini-3.5-flash | 0.260 [0.214, 0.312] | 0.270 [0.223, 0.323] | +0.010 |
| gpt-5.4-mini | 0.200 [0.159, 0.249] | 0.203 [0.162, 0.253] | +0.003 |
| gemma4:31b | 0.180 [0.141, 0.227] | 0.170 [0.132, 0.217] | −0.010 |

**Reading.** With no option list to choose from, 18–26% of answers are recalled
outright — non-trivial item familiarity that tracks model capability. Naming the
source exam adds nothing for any model (Δ ≈ 0), so there is **no "guided
instruction" leak**: the models know some answers, but do not show a learned
association between the exam's title and its contents.

---

## Probe 3 — temporal split (training-cutoff leakage)

Re-bucket the already-run MCQ zero-shot (all-format) results by `source_year`:
pre-2023 (≤2022) vs 2025–2026. No API calls.

| model | pre-2023 acc [95% CI] (n) | 2025–26 acc [95% CI] (n) | pre − recent |
|---|---|---|--:|
| gemini-3.5-flash | 0.544 [0.498, 0.590] (439) | 0.675 [0.638, 0.710] (650) | −0.131 |
| gpt-5.4-mini | 0.500 [0.455, 0.545] (470) | 0.635 [0.597, 0.671] (657) | −0.135 |
| gemma4:31b | 0.514 [0.467, 0.560] (440) | 0.729 [0.693, 0.761] (656) | −0.215 |

**Reading — treat with caution.** All deltas are *negative*: recent items score
13–21 points **higher**, the opposite of a naive pre-cutoff-memorisation signal.
Confounds, all recorded in the probe output:
- These are 2026-cutoff models, so 2025–2026 items are still in-distribution.
- Only 1,341 / 1,870 dated items carry a year; 2025–2026 dominates that pool and
  pre-2023 is a small slice (~470 items).
- Recent MPSC papers may simply be more formulaic / easier, or more heavily
  represented in recent web crawls.

This probe does **not** support a clean contamination claim in either direction.
Report it as a limitation of year-based analysis on this dataset, not as
evidence.

---

## Implications for the paper

1. **MT results must be reported by stratum**, with the **secular stratum as the
   headline metric**. Scripture/religious chrF for `gemini-3.5-flash` (and to a
   lesser extent `gpt-5.4-mini` on the English side) reflects recall, not
   translation ability.
2. **The religious/secular gap is itself a finding**, now backed by a calibrated
   probe: the "gain" low-resource MT appears to show on this corpus is
   substantially memorisation.
3. **Contamination is model-specific** — `gemini-3.5-flash` ≫ `gpt-5.4-mini` ≈
   `gemma4:31b` on the Mizo side — so per-model reporting is required.
4. **MCQ**: models recall ~1 in 5 answers closed-book; acknowledge item
   familiarity as a ceiling effect but note there is no exam-name leak.
5. **Temporal analysis is inconclusive here** and should be presented as a
   methodological limitation, not a result.
