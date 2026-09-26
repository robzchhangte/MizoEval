# Field Analysis Report

## Paper Basic Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Abstract length**: ~260 words
- **Full text length**: ~6,800 words
- **Number of references**: 33

## Field Analysis

| Dimension | Analysis Result |
|-----------|----------------|
| Primary Discipline | NLP — benchmark/resource construction for low-resource languages |
| Secondary Disciplines | MT evaluation, LLM data contamination/memorization, evaluation statistics |
| Research Paradigm | Quantitative |
| Methodology Type | Benchmark construction + comparative model evaluation (resource paper with an empirical contamination protocol) |
| Target Journal Tier | Q1 (TACL) — the paper aims to contribute a generalizable protocol, not only a new-language resource |
| Paper Maturity | Pre-submission. Structure is complete and most sections are fully data-traceable, but Section 5.4 (the paper's central corroborating evidence) reports no quantitative values, and two sections contain a direct, checkable self-contradiction (Sections 3.4 vs. 7). |

## Recommended Target Journals (Top 3)
1. **TACL** — as targeted; a strong fit if the contamination protocol is positioned as the primary contribution and the resource as secondary.
2. **Language Resources and Evaluation** (Springer) — best structural fit for a benchmark/resource paper if TACL's bar on generalizable methodology proves too high.
3. **ACM TALLIP** — closest topical match (Asian/low-resource language processing), lower bar on generalization beyond the target language.

## Reviewer Configuration Cards

### Card #1: EIC
**Identity**: TACL Action Editor specializing in multilingual evaluation and benchmark methodology.
**Focus**: journal fit and whether the contribution rises above "a benchmark for one more language"; internal consistency of the paper's central claims; whether Section 5.4 supports the weight the abstract and conclusion place on it.
**Will particularly care about**: whether the contamination finding is reported with the same rigor the paper promises in Section 4.4, since that promise is what elevates this from a resource paper to a methods paper.
**Possible blind spots**: fine-grained MT/statistical methodology (deferred to R1); community/data-provenance angle (deferred to R3).

### Card #2: Peer Reviewer 1 — Methodology
**Identity**: Evaluation statistician with MT metric meta-evaluation background (WMT metrics-task style).
**Focus**: statistical reporting consistency (Section 4.4's promises vs. Table 1's contents); numeric accuracy of in-text claims against the paper's own tables; whether register-based score differences are adequately distinguished from a genre/difficulty confound; reproducibility of the model roster.
**Will particularly care about**: whether every number in the paper traces to the tables/reports it should trace to.
**Possible blind spots**: sociolinguistic and community context (deferred to R3); literature completeness (deferred to R2).

### Card #3: Peer Reviewer 2 — Domain
**Identity**: Researcher in low-resource and Indic NLP, has built Indic-language benchmarks.
**Focus**: completeness of the related-work coverage; whether baselines that are already computed are surfaced to the reader; data licensing and redistribution risk for the MCQ (civil-service exam) and MT sources.
**Will particularly care about**: whether the released benchmark will actually be usable and legally distributable by other researchers.
**Possible blind spots**: fine-grained statistical methodology (deferred to R1).

### Card #4: Peer Reviewer 3 — Perspective
**Identity**: Language-documentation and data-sovereignty scholar working on community-centered NLP for Indigenous/minority languages.
**Focus**: whether claims resting on human validation (native-speaker adjudication panels, MT register validation) are appropriately scoped given that this validation has not yet occurred; consent and provenance for exam and social-media text; practical value of the benchmark for the Mizo-speaking community.
**Will particularly care about**: any place the manuscript describes already-completed validation that its own data files show is still pending.
**Possible blind spots**: statistical/methodological detail (deferred to R1).

### Card #5: Devil's Advocate
**Focus**: the central causal claim (register score gap = pretraining memorization) versus the alternative explanation (register score gap = genre/difficulty confound, independent of memorization); verifiability of the paper's most important section (5.4); scope of the "every evaluated model" language in the abstract relative to what was actually probed.

## Review Strategy Recommendations
- All five reviewers had access to `data/processed/REPAIR_REPORT.md`, `results/contamination/CONTAMINATION_REPORT.md`, and `results/tables/SUMMARY.md` as ground truth, and checked manuscript claims against them directly rather than reviewing prose in isolation.
- R1 and the Devil's Advocate cover overlapping ground (Section 5.4's missing numbers) from different angles: R1 as a statistical-reporting lapse, DA as a verifiability/inference problem. This is intentional, not duplication — the same defect has two different consequences.
- EIC's decision is sensitive to how straightforward the identified contradictions are to fix (they are: Section 7's mislabeled bound and Section 5.1's numeric claim are both text-only corrections against existing correct data), which favors Major Revision over Reject.
