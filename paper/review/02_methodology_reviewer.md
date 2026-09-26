# Peer Review Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 1

---

## Reviewer Information

### Reviewer Role
Peer Reviewer 1 (Methodology)

### Reviewer Identity
Evaluation statistician with a background in MT metric meta-evaluation (WMT metrics-task style).

### Review Focus
Statistical reporting consistency; numeric accuracy of in-text claims against the paper's own tables; whether the register-based contamination claim is adequately separated from a genre/difficulty confound; reproducibility.

---

## Overall Assessment

### Recommendation
- [x] **Major Revision**

### Confidence Score
5

### Summary Assessment
The bootstrap/Wilson/Holm-Bonferroni apparatus described in Section 4.4 is applied correctly where it is applied (Tables 1–3 all trace to the underlying analysis output), and the position-bias test in Table 2 is a genuinely well-executed use of paired McNemar testing. But the paper does not consistently apply its own stated standard: I found one numeric claim in the prose that is flatly wrong relative to the paper's own Table 1, one metric (NER F1) reported with no interval despite a blanket claim that every corpus metric carries one, and a computed pairwise significance table that never appears. Separately, the register-gap-as-contamination argument needs a difficulty control I do not see: the strongest counter-evidence against pure memorization, that a supervised MT baseline shows a comparable gap, is currently read only as corroboration and not also as a competing explanation.

---

## Strengths

### S1: The chrF++ bootstrap and Wilson interval reporting is correctly and consistently applied in Tables 1–3
Every value I spot-checked against `results/tables/SUMMARY.md` matches to the reported precision, and the choice of chrF++ over BLEU as primary is properly justified and cited (Popovic 2015, 2017).

### S2: The position-bias significance test (Table 2) is exemplary for this literature
Reporting per-model significance after correction, rather than a single pooled test, is the right level of granularity, and the paper does not overclaim past what the corrected p-values support (Section 5.2 explicitly notes GPT 5.4 and Gemini 3.5 Flash do not reach significance).

### S3: The verse-completion probe's calibration step is methodologically sound
Confirming the probe fires on a known-memorized anchor (John 3:16) and stays quiet on fresh, unpublished Mizo sentences before applying it to the main sample (Section 4.3) is exactly the right control, and it is a control many contamination-detection papers skip.

---

## Weaknesses

### W1: The five-shot sentiment gain claim in Section 5.1 is numerically wrong against the paper's own Table 1
**Problem**: Section 5.1 states five-shot exemplars produce gains "most notably lifting Gemma 4 31B and GPT 5.4 by fifteen to twenty macro F1 points over their zero shot scores." Computing directly from Table 1: GPT 5.4 gains 11.7 points (0.589 → 0.706), and Gemma 4 31B gains only 5.7 points (0.583 → 0.640) — the smallest gain of all five models, not one of the largest. GPT 5.4 mini (9.9 points) is closer to "most notable" than Gemma 4 31B.
**Why it matters**: This is a directly checkable claim against a table three paragraphs away, and it is wrong in a way that misidentifies which model the finding is about.
**Suggestion**: Replace with "most notably lifting GPT 5.4 and GPT 5.4 mini by roughly ten to twelve macro F1 points."
**Severity**: Major

### W2: Table 1 reports NER F1 with no confidence interval, contradicting Section 4.4's stated protocol
**Problem**: Section 4.4 states "every corpus level metric, including chrF++ and macro averaged F1, carries a percentile bootstrap interval computed over 1,000 resamples." Entity-level F1 is exactly this kind of corpus-level metric, and Table 1 reports it as a bare point estimate for all five models and both splits.
**Why it matters**: Readers cannot tell whether the ranking implied by, for example, 0.260 (Gemini) vs. 0.233 (Gemma) on the official split is distinguishable from noise, especially since the NER F1 values themselves are surprisingly low across the board (0.18–0.26 for four of five models, a range that would normally prompt a question about whether the span-alignment procedure described in Section 4.2 is working as intended).
**Suggestion**: Either compute and report the interval, or explicitly state in Section 4.4 that entity-level F1 is the one metric excluded from the bootstrap protocol and say why.
**Severity**: Major

### W3: The computed pairwise MCQ significance results are not reported anywhere in the manuscript
**Problem**: `results/tables/mcq_pairwise_significance.csv` contains ten Holm-Bonferroni-corrected pairwise McNemar comparisons across all five models (four significant), directly matching the methodology Section 4.4 describes, but no such table appears in Sections 5 or elsewhere.
**Why it matters**: The paper currently supports no claim about which models significantly outperform which others on the headline task; only raw accuracy ordering is visible in Table 1, which invites exactly the kind of unadjusted eyeballing the paper's own statistical framework is designed to prevent.
**Suggestion**: Add this table.
**Severity**: Major

### W4: The register-gap-as-contamination argument needs a genre/difficulty control it does not currently have
**Problem**: The paper's strongest independent evidence for contamination is the verse-completion probe (Section 4.3, 5.4), applied to three of five LLMs. For the two unprobed LLMs and for NLLB, the only evidence is the scripture-vs-secular score gap itself (Table 3), which is also consistent with scripture/religious text simply being a more formulaic, more repetitive, better-represented-in-any-training-corpus register, independent of memorization of these specific 3,000 pairs. The paper's own data shows NLLB, a supervised model whose relationship to "pretraining memorization" is different in kind from an LLM's, exhibits a comparable gap (15.2/11.7), which the Discussion (Section 6) reads as corroboration ("any system trained on commonly available parallel data... will tend to show inflated scores"). This is a legitimate reading, but it is equally consistent with "scripture is an easier register to translate," which would not be a contamination finding at all for the untested systems.
**Why it matters**: Without a length- or repetition-controlled comparison between the scripture and secular strata (e.g., matching mean sentence length or measuring n-gram repetition rate per stratum), the paper cannot fully rule out genre difficulty as an alternative explanation for the two-thirds of the model-and-direction cells in Table 3 that were never probed directly.
**Suggestion**: Report basic register-level text statistics (mean length, type-token ratio, or an n-gram repetition measure) for scripture vs. secular, and note explicitly whether the probed models' gap size correlates with any of these confounds. If it does not, this substantially strengthens the memorization reading; if it does, the paper should qualify its claim for the unprobed systems accordingly.
**Severity**: Major

---

## Detailed Comments

### Methodology / Research Design
Model roster (Section 4.1) never states an actual version identifier despite claiming models are pinned to one; for reproducibility this should appear at least once, ideally in an appendix or footnote.

### Results
GPT OSS 120B's near-total failure to produce usable translation output (28-93% empty, Section 5.3) is reported and appropriately excluded from the register table, but it is worth noting this model is included in every other headline table (Table 1) without a parallel discussion of whether its unusually low, but non-zero, scores there (e.g., 0.056/0.059 NER F1) reflect the same reliability problem rather than a comparably low but genuine capability.

---

## Questions for Authors

1. Can the five-shot sentiment gain figures in Section 5.1 be corrected against Table 1?
2. Is there a methodological reason NER F1 was excluded from the bootstrap protocol, or was this an oversight?
3. Has a length- or repetition-matched comparison between the scripture and secular MT strata been considered, to separate genre difficulty from memorization for the systems that were not directly probed?

---

## Minor Issues

### Figures and Tables
Table 3's caption should state explicitly that GPT OSS 120B and the five-shot Gemma cells (present in the underlying data but not shown) are omitted, and why, rather than leaving this only to the prose beneath the table.

---

## Dimension Scores

| Dimension | Score (0-100) | Descriptor | Notes |
|-----------|--------------|------------|-------|
| Originality (20%) | 75 | Strong | |
| Methodological Rigor (25%) | 55 | Weak | W1-W4 |
| Evidence Sufficiency (25%) | 62 | Weak | Evidence exists but under-reported (W2, W3) or under-controlled (W4) |
| Argument Coherence (15%) | 60 | Weak | |
| Writing Quality (15%) | 78 | Strong | |
| **Weighted Average** | 64 | | **Major Revision** |
