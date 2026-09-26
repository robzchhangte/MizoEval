# Editorial Decision

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Target Venue**: Transactions of the Association for Computational Linguistics (TACL)
- **Review Round**: 1

---

## Decision

### Major Revision

---

## Reviewer Summary

| Reviewer | Role | Recommendation | Confidence |
|----------|------|---------------|------------|
| EIC | TACL Action Editor, multilingual evaluation/benchmarking | Major Revision | 5 |
| Reviewer 1 | Evaluation statistician, MT metric meta-evaluation | Major Revision | 5 |
| Reviewer 2 | Low-resource/Indic NLP, benchmark builder | Minor-to-Major Revision | 4 |
| Reviewer 3 | Language documentation, data sovereignty | Major Revision | 4 |
| Devil's Advocate | — | Major Revision (2 CRITICAL findings) | — |

---

## Consensus Analysis

### Points of Agreement (Consensus)

**[CONSENSUS-5]** (All five reviewers, independently):
1. The paper's core idea, contribution, and data-audit execution are strong. Every reviewer's Strengths section credits the MCQ/NER/sentiment repair work as substantively correct and well-documented, and no reviewer questioned the value of the coverage gap the paper fills.
2. Section 5.4 (the contamination probes) is under-reported relative to what the underlying data supports, and this is the single most consequential fix required. EIC (W1), R1 (implicit in W2/W3 pattern), and DA (C1) converge on this from three different angles: rigor-consistency, statistical-reporting-consistency, and falsifiability, respectively.
3. Sections 3.4 and 7 contradict each other on the direction of the MT secular-share bound, and Section 7 additionally describes a native-speaker validation as completed when it is not. EIC (W2), R3 (W1, from the ethics angle), and DA (C2) all independently identified this as the same underlying defect.

### Points of Disagreement

**Disagreement 1: Overall severity of the decision (Minor-to-Major vs. Major)**
- **R2's view**: Domain coverage and literature integration are strong enough, and R2's own concerns (licensing, missing baselines table) are independently fixable without touching the paper's core claims, that R2's own recommendation leans toward the Minor end of Minor-to-Major.
- **EIC/R1/R3's view**: The Critical-severity findings (self-contradiction, unverifiable central evidence) are not cosmetic and must be resolved and re-reviewed, which places the paper in Major Revision territory regardless of how strong the surrounding sections are.
- **Disagreement type**: Severity disagreement.
- **Editor's Resolution**: Major Revision.
- **Resolution Rationale**: Per Checkpoint Rule 4 and the Anti-Patterns table, a Devil's Advocate CRITICAL finding forecloses an Accept-track decision, and two of the Devil's Advocate's findings (C1, C2) are Critical. R2's concerns are real but address different, non-overlapping defects (licensing, presentation) than the Critical findings; resolving R2's items does not resolve C1/C2, so the overall severity must track the more serious, independently-confirmed defects.

**Disagreement 2: Whether the register-gap-as-contamination argument needs a new experiment (difficulty control) or only a framing correction**
- **R1's view** (W4): A length/repetition-matched control between strata should be added or at least attempted, to more fully separate genre difficulty from memorization for the unprobed systems.
- **DA's view** (M1): The more immediate fix is narrower — stop using NLLB's comparable gap as corroboration for LLM-specific memorization in Section 6, since that framing actively undercuts the paper's own causal story, whether or not a new control is added.
- **Disagreement type**: Scope of required fix.
- **Editor's Resolution**: Both. The Section 6 framing fix (DA's narrower ask) is required for this revision; the length/repetition control (R1's broader ask) is strongly suggested but not required, since it may not be achievable without new probe runs the paper's other constraints (five-shot MT and expanded probe coverage are both explicitly out of scope for this study, per the authors' own stated project decisions) may not accommodate on this timeline.
- This distinction is reflected in the Required vs. Suggested revision lists below.

---

## Decision Rationale

Every reviewer, independently, found the paper's underlying empirical work sound and its central idea, an audited multi-task Mizo benchmark plus a validated register-contamination protocol, publishable at this venue. What blocks acceptance in this round is not the science but how faithfully the manuscript currently represents that science: two sections state opposite things about the same number (Sections 3.4 and 7), the section carrying the paper's strongest causal evidence reports no numbers where the underlying data has precise, calibrated ones (Section 5.4), a headline claim about which model gained most from few-shot prompting is contradicted by the paper's own table (Section 5.1), and a fully computed pairwise-significance analysis is never shown to the reader (Section 4.4's promise, unmet). None of these require new data collection or new experiments to fix; they require the manuscript to say what the data already says, correctly and completely. This is precisely the situation Major Revision (rather than Reject) exists for: serious, but fixable within the paper's existing evidence base. The Devil's Advocate's genre-difficulty counter-argument (M1) is the one substantive scientific question raised in this round, and it is addressed by a framing correction rather than new data, which keeps it within Major Revision's scope as well. Given four of five reviewers independently converged on Major Revision, and the fifth's narrower Minor-to-Major concerns are additive rather than contradictory, this decision is not close.

---

## Required Revisions (Must Fix)

| # | Revision Item | Source Reviewer | Severity | Section | Estimated Effort |
|---|--------------|----------------|----------|---------|-----------------|
| R1 | Report the actual chrF deltas, verbatim-match rates, canary recall percentages, and their confidence intervals for all three contamination probes | EIC (W1), R1 (implicit), DA (C1) | Critical | 5.4 | 1-2 days |
| R2 | Resolve the Section 3.4 / Section 7 contradiction on the secular-share bound direction, and correct Section 7 to state the native-speaker validation is planned/in progress, not completed | EIC (W2), R3 (W1), DA (C2) | Critical | 3.4, 7 | < 1 day |
| R3 | Correct the five-shot sentiment gain claim in Section 5.1 to match Table 1 (GPT 5.4 and GPT 5.4 mini gain most, roughly 10-12 points; Gemma 4 31B gains least, 5.7 points) | R1 (W1) | Major | 5.1 | < 1 day |
| R4 | Add the computed pairwise MCQ significance table (or fold its content into Table 2) | EIC (W3), R1 (W3) | Major | 4.4 / 5 | 1 day |
| R5 | Either compute and report a bootstrap interval for NER F1, or explicitly state in Section 4.4 that entity-level F1 is excluded from the bootstrap protocol and why | R1 (W2) | Major | 4.4 / Table 1 | 1-2 days |
| R6 | Revise Section 6's use of the NLLB comparison so it no longer reads as corroborating LLM-specific memorization when it is equally consistent with a genre-difficulty explanation; state this alternative explicitly and note it is not fully ruled out for the unprobed systems | DA (M1) | Major | 6 | < 1 day |
| R7 | Add a statement on the licensing/redistribution basis for the MCQ exam-question source text | R2 (W1) | Major | Data Availability | 1-3 days (may require external confirmation) |
| R8 | Scope the abstract and conclusion's contamination-validation language to match Section 5.4's own honesty about the temporal probe being inconclusive, and to state clearly that causal probe validation covers three of the six evaluated systems | EIC (Detailed Comments), DA (M2) | Major | Abstract, Conclusion | < 1 day |

### Required Item Details

**R1: Report the probe numbers**
- **Problem**: Section 5.4 makes quantitative claims in qualitative language only.
- **Source**: EIC W1, DA C1.
- **Requirement**: Add a compact table with model, probe, side/register, statistic (chrF delta, verbatim rate, or recall), and CI where available.
- **Acceptance criteria**: A reader can reconstruct the magnitude of every claim currently stated only in words ("well above," "a smaller but still positive gap," "a meaningful share") from a number in the paper.

**R2: Resolve the bound-direction contradiction**
- **Problem**: Section 3.4 says upper bound; Section 7 says lower bound and claims completed validation.
- **Source**: EIC W2, R3 W1, DA C2.
- **Requirement**: Both sections must agree on "upper bound," and Section 7 must not claim the validation has occurred until it has.
- **Acceptance criteria**: Sections 3.4 and 7 make the same factual claim about the bound direction, and Section 7's tense accurately reflects the validation's actual (not-yet-complete) status.

---

## Suggested Revisions (Should Fix)

| # | Revision Item | Source Reviewer | Priority | Section | Expected Improvement |
|---|--------------|----------------|----------|---------|---------------------|
| S1 | Add a length- or repetition-matched control between scripture and secular MT strata | R1 (W4) | P2 | 5.3/5.4 | Strengthens the causal contamination claim for the three unprobed systems |
| S2 | State the basis for selecting which three of five LLMs received contamination probes | DA (M3) | P2 | 4.3 | Forecloses a cherry-picking objection |
| S3 | Add a compact baselines table (majority-position, random, majority-class) | R2 (W2) | P3 | 5.1/3.3 | Presentation completeness, values already computed |
| S4 | State the redistribution/consent basis for the sentiment corpus's social-media source | R2 (W3) | P3 | Data Availability / Ethics | Closes a smaller version of R7 |
| S5 | Confirm whether institutional review has been sought for the planned MCQ and MT validation panels | R3 (W2) | P2 | Ethics Statement | Addresses a likely reviewer question at re-review |
| S6 | State an actual model version identifier somewhere (footnote or appendix), matching the reproducibility claim in Section 4.1 | EIC (Detailed Comments), R1 (Detailed Comments) | P3 | 4.1 | Reproducibility |
| S7 | Note in Table 3's caption which cells (GPT OSS 120B, five-shot Gemma) are omitted from the underlying data and why | R1 (Minor Issues) | P3 | Table 3 | Reduces reliance on prose below the table |

---

## Revision Roadmap

### Priority 1 — Correctness Fixes (Estimated total effort: 2-3 days)
- [ ] R2: Resolve the Section 3.4/7 contradiction and validation-status claim
- [ ] R3: Correct the five-shot sentiment gain numbers in Section 5.1
- [ ] R1: Report the probe numbers in Section 5.4
- [ ] R8: Scope the abstract/conclusion contamination-validation language accurately

### Priority 2 — Missing Analysis and Framing (Estimated total effort: 3-5 days)
- [ ] R4: Add the pairwise MCQ significance table
- [ ] R5: Resolve the NER F1 confidence-interval gap
- [ ] R6: Reframe the NLLB comparison in Section 6
- [ ] R7: Address MCQ source-text licensing

### Priority 3 — Completeness and Polish (Estimated total effort: 2-3 days)
- [ ] S1-S7 as time and data availability permit

### Total Estimated Effort
- **Major Revision**: 1.5-2 weeks, most of it front-loaded in Priority 1/2 items that are text-level corrections against already-existing data rather than new experiments.

---

## Revision Deadline
- **Recommended deadline**: 4 weeks from this decision.
- **Basis**: Major Revision standard is 6-8 weeks, but every Required item here is a correction against existing data rather than new data collection, so the standard timeline can reasonably be compressed. R7 (licensing) is the one item that may require external confirmation outside the authors' direct control and could extend this if it stalls.
- **Extension policy**: Notify 1 week before the deadline if R7 is pending external confirmation.

---

## Response Letter Instructions

Respond to each Required and Suggested item above individually, in the format of `templates/revision_response_template.md`: what was changed, where, and why. For R2 specifically, state explicitly which of "upper bound" or "lower bound" is correct and confirm the validation's actual current status, since this was independently flagged by three reviewers as the paper's most serious internal inconsistency.

---

## Closing

We found real value in this manuscript: MizoEval fills a genuine and well-documented coverage gap, its data-repair work is rigorous and traceable, and its contamination-detection idea is a needed contribution to low-resource MT evaluation practice generally, not only for Mizo. The issues raised in this round are, without exception, issues of what the manuscript says about data that already exists, not issues with the data or the underlying experiments themselves. We look forward to receiving a revised version.

---

## Appendix: Full Reviewer Reports

See `paper/review/01_eic_report.md`, `02_methodology_reviewer.md`, `03_domain_reviewer.md`, `04_perspective_reviewer.md`, `05_devils_advocate.md`.
