# Peer Review Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 1

---

## Reviewer Information

### Reviewer Role
EIC

### Reviewer Identity
TACL Action Editor specializing in multilingual evaluation and benchmark methodology.

### Review Focus
Journal fit; whether the paper's central claim is supported with the rigor it promises itself; internal consistency across sections.

---

## Overall Assessment

### Recommendation
- [x] **Major Revision** — Substantial revisions needed, re-review required after revision

### Confidence Score
5

### Summary Assessment
The paper assembles a genuinely new multi-task benchmark for an uncovered language and, more importantly, adds a register-stratification-plus-probe protocol for detecting religious-text contamination in low-resource MT, which is the paper's real bid for TACL rather than a resource venue. The audit-as-contribution framing (Section 3) is well executed and every MCQ, NER, and sentiment figure I checked traces cleanly to the underlying repair report. However, the section carrying the paper's strongest evidence, the contamination probes (5.4), reports no quantitative values at all, which is inconsistent with the rigor the paper claims for itself in Section 4.4, and I found a direct, checkable contradiction between Sections 3.4 and 7 concerning whether the MT secular-share estimate is an upper or lower bound, compounded by Section 7 claiming a validation was completed that the paper's own results do not show. These are correctable without new data collection, which is why I am not recommending reject, but the paper cannot go to review again, let alone print, in its current state.

---

## Strengths

### S1: The data audit is the paper's real contribution and is well substantiated
Every MCQ figure I checked (2,400 raw items, 315 duplicate groups, 117 conflicting-gold groups covering 283 items, 1,870 released, 1,747 in the `mcq4` headline subset, position distribution 30.1/29.9/24.8/15.2) matches the underlying repair report exactly. This is not a superficial "we cleaned the data" gesture; the quarantine-rather-than-guess decision on the 283 conflicting items (Section 3.1) is a defensible, citable methodological choice.

### S2: The NER document-level leakage finding is a genuinely useful methodological contribution on its own
Measuring, rather than assuming, that 99.6% of the official test split shares a source article with training (Section 3.2), and shipping a zero-overlap alternative split alongside it, is exactly the kind of finding that gets cited by later benchmark papers independent of the MT contamination story.

### S3: The permutation control and the position-bias significance test are used correctly
Table 2 reports per-model significance after Holm-Bonferroni correction, and the paper is honest that the effect holds for three of five models, not all five (Section 5.2). This kind of qualified claim, rather than a blanket "LLMs show position bias," is exactly right for a Q1 venue.

---

## Weaknesses

### W1: Section 5.4 reports the paper's central corroborating evidence with no numbers at all
**Problem**: Section 4.4 promises "every headline number in the paper is reported with a bootstrap or Wilson confidence interval." Section 5.4, which describes the verse-completion, canary, and temporal probes, contains not a single chrF value, verbatim rate, recall percentage, or confidence interval — only qualitative language ("well above," "a smaller but still positive gap," "a meaningful share"). The underlying data exists in full (calibrated chrF deltas of +54.0/+46.2/+11.0 on the English side, +18.5/+2.9/+1.6 on the Mizo side, canary recall of 0.180–0.260 with 95% CIs, temporal deltas of -13 to -21 points) and is simply not surfaced.
**Why it matters**: This is the section a TACL reviewer will scrutinize hardest, since it is what turns "scripture scores higher than secular" from a correlational pattern into a causal contamination claim. A qualitative paraphrase of a quantitative result invites exactly the skepticism the probes were designed to pre-empt.
**Suggestion**: Add a compact table (probe, model, side/register, statistic, CI) mirroring the existing contamination report; three rows of numbers would resolve this.
**Severity**: Critical

### W2: Sections 3.4 and 7 directly contradict each other on the direction of the secular-share bound, and Section 7 asserts a validation that has not occurred
**Problem**: Section 3.4 states the 27.0% secular figure is "an upper bound on the true secular share." Section 7 calls the same figure "a lower bound... validated against a native speaker annotated sample as described in Section 3.4." Section 3.4 does not describe a completed validation; it says a sample "is held for native speaker validation... reported alongside the main results in Section 5," and Section 5 contains no such report.
**Why it matters**: This is not a stylistic inconsistency; it is a factual claim (upper vs. lower bound) stated both ways in the same manuscript, plus a claim that a validation step happened when the paper's own results show it has not. A careful reader who reads Sections 3, 5, and 7 together will lose confidence in every other number in the paper.
**Suggestion**: Fix Section 7 to say "upper bound" and to describe the validation as planned/ongoing rather than completed, matching Section 3.4.
**Severity**: Critical

### W3: The paper's own pairwise significance analysis across all five models is computed but never shown
**Problem**: Section 4.4 describes exactly this analysis ("Model versus model comparisons on the multiple choice task use an exact McNemar test... with a Holm Bonferroni correction applied"), and the underlying result exists (ten pairwise comparisons, four significant after correction), but no such table appears anywhere in the manuscript. Only the narrower position-bias comparison (Table 2) is shown.
**Why it matters**: "Which models are actually better than which, with significance" is a natural reader question for a benchmark paper, and the paper has already answered it without telling the reader.
**Suggestion**: Add this as a second panel of Table 2 or a new Table.
**Severity**: Major

---

## Detailed Comments

### Abstract
The claim that "every evaluated model's secular stratum score sits well below its scripture stratum score" is true directionally but "well below" oversells the smallest observed gap (2.6 chrF points for Gemma 4 31B, en→mz); consider "consistently above, from 2.6 to 21.0 points" instead.

### Discussion / Conclusion
"Validated by three independent probes" (Conclusion) overstates Section 5.4's own finding that the temporal probe is inconclusive and is explicitly not used as contamination evidence. Two probes corroborate; the third is reported honestly as a limitation. The framing elsewhere in the paper should match that honesty.

### Section 4.1
The claim that models are "pinned to an exact, dated version identifier" is never substantiated with an actual identifier anywhere in the paper, including an appendix. If reproducibility is claimed, the identifiers should appear somewhere, even if only in supplementary material.

---

## Questions for Authors

1. Which of "upper bound" (Section 3.4) or "lower bound" (Section 7) is correct for the 27.0% secular-share figure, and has the native-speaker validation of the register classifier actually been run?
2. Why does Section 5.4 report no quantitative values when the underlying probe results are fully computed?
3. Is there a reason the pairwise MCQ significance results are omitted from the manuscript despite being computed?

---

## Minor Issues

### Language / Grammar
None beyond what R1 and R2 note.

### Figures and Tables
Table 1 reports NER F1 with no interval despite Section 4.4's blanket claim that every corpus-level metric carries one; see R1's report for detail.

---

## Dimension Scores

| Dimension | Score (0-100) | Descriptor | Notes |
|-----------|--------------|------------|-------|
| Originality (20%) | 78 | Strong | Genuine coverage gap, real protocol contribution |
| Methodological Rigor (25%) | 58 | Weak | Undercut by W1/W2/W3 |
| Evidence Sufficiency (25%) | 60 | Weak | Evidence exists but is not shown where it matters most |
| Argument Coherence (15%) | 55 | Weak | Direct self-contradiction between Sections 3.4 and 7 |
| Writing Quality (15%) | 80 | Strong | Clear, well organized prose |
| **Weighted Average** | 65 | | **Major Revision** |
