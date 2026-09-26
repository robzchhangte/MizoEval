# Verification Review Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 2 (re-review, per `academic-paper-reviewer` re-review mode)
- **Basis**: `paper/review/06_editorial_decision.md` (Round 1, Major Revision)

---

## Decision

### Accept (with copyediting only; no further review round required)

---

## Revision Response Checklist

### Priority 1 — Required Revisions

| # | Original Review Comment | Author's Claim | Response Status | Revision Location | Verified? | Quality Assessment |
|---|---|---|---|---|---|---|
| R1 | Section 5.4 reports the probe evidence with no numbers | Added the actual chrF deltas, verbatim rates, canary recall, and temporal deltas with intervals | FULLY_ADDRESSED | Section 5.4, new Tables 6 and 7 | ✅ Yes | Every figure checked against `results/contamination/CONTAMINATION_REPORT.md` and matches exactly (e.g. Gemini 3.5 Flash 54.0 point English-side gap, 0.567 verbatim rate; canary recall 0.260/0.200/0.180) |
| R2 | Sections 3.4/7 contradicted each other on the secular-share bound direction, and Section 7 claimed a completed validation | Both sections now say "upper bound"; Section 7 states the validation is planned, not complete | FULLY_ADDRESSED | Sections 3.4, 7 | ✅ Yes | Read both sections side by side; they now agree, and Section 3.4 forward-references Section 7's precise status statement rather than asserting completion |
| R3 | Section 5.1's five-shot gain claim (Gemma 4 31B and GPT 5.4, 15-20 points) contradicted Table 1 | Corrected to GPT 5.4 and GPT 5.4 mini, ~10-12 points; noted Gemma 4 31B gains least | FULLY_ADDRESSED | Section 5.1 | ✅ Yes | Recomputed from Table 1: GPT 5.4 +11.7, GPT 5.4 mini +9.9, Gemma 4 31B +5.7 (smallest of five). Text matches |
| R4 | Computed pairwise MCQ significance table never shown | Added as new Table 3 | FULLY_ADDRESSED | Section 5.1 | ✅ Yes | All ten rows checked against `results/tables/mcq_pairwise_significance.csv`; corrected p-values and significance flags match exactly |
| R5 | NER F1 reported with no interval, contradicting Section 4.4's blanket claim | Added a sentence-level bootstrap interval to `score_ner`, regenerated Table 1's NER columns | FULLY_ADDRESSED | Table 1; `src/mizoeval/metrics/tasks.py` | ✅ Yes | Independently reran the targeted computation; Table 1's intervals match the regenerated `table1_main_results.csv` to three decimals. Full test suite (102 tests) passes |
| R6 | Section 6/5.3's NLLB comparison read as corroborating LLM memorization when a genre-difficulty confound was not ruled out | Reframed as two competing explanations Table 5 cannot separate on its own; added a directly measured lexical-repetition statistic in 5.4 | FULLY_ADDRESSED | Section 5.3, 5.4 | ✅ Yes | The repetition measurement (top-50-token share ~0.50 scripture vs. ~0.37-0.44 secular) is a new, real computation over already-repaired data (`results/tables/register_text_statistics.json`), not an assertion. This exceeds what was asked: the confound is measured, not just disclosed |
| R7 | No statement on MCQ exam-text redistribution licensing | Added a statement naming the government-exam provenance and committing to confirm the redistribution basis before release | PARTIALLY_ADDRESSED | Data Availability Statement | ⚠️ Partial | The paper now discloses the question honestly rather than eliding it, which is what a manuscript revision can do; the license itself is an external fact the authors do not yet have. This is the correct manuscript-level fix and is accepted as such, but it is not a fully "resolved" real-world state, so is flagged for the authors to close out before submission proper, not before this internal sign-off |
| R8 | Abstract/Conclusion's "validated by three probes" overstated the temporal probe's inconclusive result | Abstract and Conclusion rescoped to "two of three probes corroborate" | PARTIALLY_ADDRESSED at first check → **FULLY_ADDRESSED after this round's fix** | Abstract, Conclusion, Introduction (paragraph 4), Section 2.2 | ✅ Yes | The original fix correctly touched Abstract and Conclusion but the identical unscoped phrase ("we validate the resulting contamination signal with three complementary probes" and "validated by contamination probes") survived in the Introduction and in Section 2.2. Found during this verification pass and corrected in the same commit as this report, so the manuscript now handed off is fully consistent |

### Priority 2 — Suggested Revisions

| # | Original Review Comment | Response Status | Notes |
|---|---|---|---|
| S1 | Add a length/repetition control between MT strata | FULLY_ADDRESSED | Went beyond "should fix": a real measurement was computed and disclosed, not merely acknowledged as a gap |
| S2 | State the basis for which 3 of 5 LLMs got contamination probes | FULLY_ADDRESSED | Section 4.3 now discloses that one of the two unprobed models shows one of the largest register gaps, an honest disclosure rather than a fabricated ex-ante rationale |
| S3 | Add a compact baselines table | FULLY_ADDRESSED | New Table 2 |
| S4 | State the sentiment corpus's redistribution/consent basis | FULLY_ADDRESSED | Data Availability Statement |
| S5 | Confirm institutional review for planned panels | FULLY_ADDRESSED | Ethics Statement |
| S6 | State an actual model version identifier | FULLY_ADDRESSED | New Appendix A, cross-checked against `configs/models.yaml`; identifiers match exactly |
| S7 | Note in Table 3 (now Table 5)'s caption which cells are omitted | FULLY_ADDRESSED | Caption now states this directly rather than leaving it to prose alone |

### Priority 3 — Nice to Fix

| # | Original Review Comment | Response Status |
|---|---|---|
| N1 | Table renumbering consistency (a consequence of adding Tables 2/3/6/7) | FULLY_ADDRESSED — checked every "Table N" reference in the document; all seven are sequential and every inline reference matches its target |

---

## New Issues (Discovered During Revision)

| # | Type | Location | Description |
|---|------|----------|--------------|
| NEW-1 | Overclaim scope gap | Introduction (paragraph 4), Section 2.2 | The Round-1 fix for the "validated by three probes" overclaim (R8) was applied to the Abstract and Conclusion, the two locations the original review cited by name, but the same phrase existed verbatim in two more places. Caught by re-checking every occurrence of "validat" in the document rather than trusting the two cited locations were exhaustive. **Resolved in this round**, so it is not a residual item, but it is worth naming so the pattern (fixing a cited location without searching for the same defect elsewhere) is not repeated in a future revision. |

No other new issues were found. No previously-passing content was broken by the revision: the full test suite (102 tests) passes, the regenerated `table1_main_results.csv` and `SUMMARY.md` changed only in the NER columns as intended, and every other results table is untouched.

---

## Decision Rationale

Every Priority 1 item from the Round 1 Editorial Decision is now FULLY_ADDRESSED, including R8 after this round's own additional fix, and every claim was independently verified against either the manuscript's own tables or the underlying data files (`REPAIR_REPORT.md`, `CONTAMINATION_REPORT.md`, `configs/models.yaml`, `results/tables/*.csv`), not against the authors' description of their own changes. R7 remains formally PARTIALLY_ADDRESSED only because it depends on an external fact (the exam board's actual licensing terms) that no text edit can resolve; the manuscript now handles this correctly by disclosing rather than eliding the question, which is the right editorial outcome and does not block acceptance. All seven Priority 2 items are addressed, several beyond what was asked (S1 in particular: a real measurement in place of a caveat). No new blocking issues were introduced by the revision, and the one gap this round's own check surfaced (NEW-1) was closed in the same pass rather than deferred. This paper is ready to move forward.

---

## Residual Issues

- **R7 (external, not textual):** the authors should confirm the actual redistribution basis for the Mizoram civil-service exam question text with the relevant examination body before the data release goes out, since the manuscript's Data Availability Statement now commits to stating that basis explicitly. This does not block manuscript acceptance; it blocks the data release the manuscript promises, which is a downstream operational step outside the peer-review scope.
- **MT/sentiment license confirmation and the planned native-speaker panels** (adjudication and register validation) remain, as before, genuinely pending future work, correctly disclosed as such throughout Sections 3, 7, and the back matter. No action needed for this manuscript; carry forward as acknowledged limitations, consistent with Round 1's assessment.
