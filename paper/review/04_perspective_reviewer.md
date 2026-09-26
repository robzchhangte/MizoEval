# Peer Review Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 1

---

## Reviewer Information

### Reviewer Role
Peer Reviewer 3 (Perspective)

### Reviewer Identity
Language-documentation and data-sovereignty scholar, working on community-centered NLP for Indigenous and minority languages.

### Review Focus
Whether claims resting on not-yet-completed human validation are appropriately scoped; consent and provenance for exam and social-media text; practical value of the benchmark for the Mizo-speaking community.

---

## Overall Assessment

### Recommendation
- [x] **Major Revision**

### Confidence Score
4

### Summary Assessment
This paper treats a small, low-resource language community's data with more care than most benchmark papers I review: quarantining conflicting MCQ items rather than guessing at them, and planning a native-speaker adjudication panel rather than resolving disagreements unilaterally, are both genuinely community-respecting choices. My concern is narrower and more serious than a general request for more sensitivity: Section 7 describes a native-speaker validation of the MT register classifier as already completed ("validated against a native speaker annotated sample"), and Section 3.4 and Section 5 make clear this has not happened yet. A paper that asks a reader to trust its central claim partly on the strength of community validation should not describe that validation as done when it is not. This is fixable with accurate tense and scoping, not with new fieldwork, so I am not recommending reject, but it must be fixed before this goes further.

---

## Strengths

### S1: The MCQ conflict-adjudication decision respects the difference between "resolved" and "guessed"
Section 3.1's decision to quarantine, rather than auto-resolve, the 283 items with conflicting gold answers, pending a native-speaker panel, is the right call: an automated heuristic would have silently introduced label noise attributed to a decision no Mizo speaker actually made.

### S2: The Ethics Statement names the annotators' role rather than treating them as an invisible resource
Stating that "annotation guidelines, compensation, and consent procedures for this panel will be documented alongside its release" (Ethics Statement) is a meaningful commitment, though see W2 below on timing.

### S3: The register stratification treats religious text as data with a specific cultural and historical role, not merely as noise to be filtered
Distinguishing scripture from other religious text from secular text (Section 3.4), rather than collapsing all non-secular content into one bucket, reflects an accurate understanding that Bible translation has a distinct history and distribution pattern from other religious writing, which matters for a community where scripture translation is a significant part of the written-language record.

---

## Weaknesses

### W1: Section 7 describes a completed validation that has not occurred
**Problem**: Section 7 states the 27.0% secular-share figure is "validated against a native speaker annotated sample as described in Section 3.4." Section 3.4 itself only says a sample "is held for native speaker validation... reported alongside the main results in Section 5," and Section 5 contains no such report.
**Why it matters**: For a paper whose ethical framing rests on deferring judgment calls to native-speaker review rather than making them unilaterally, describing that review as complete when it has not started undermines the credibility of the deferral itself. A reader has no way to distinguish this from any other unvalidated classifier claim once the "validated" language is used incorrectly.
**Suggestion**: State plainly that the validation is planned/in progress, not completed, matching the honest framing already used correctly in Section 3.4 and in the Ethics Statement for the MCQ panel.
**Severity**: Critical

### W2: The Ethics Statement defers compensation and consent documentation to a future release rather than the current submission
**Problem**: "Annotation guidelines, compensation, and consent procedures for this panel will be documented alongside its release" (Ethics Statement) describes future work for a panel that has not yet been convened, for both the MCQ adjudication and the MT register validation.
**Why it matters**: This is not necessarily a problem if disclosed clearly and if institutional review has already covered the planned annotation work, but the manuscript does not state whether any ethics review board has approved the planned annotator compensation and consent procedures, which a TACL reviewer working in this area will likely ask about directly.
**Suggestion**: Add a sentence confirming whether institutional review has been sought or obtained for the planned annotation work, even if the work itself has not yet started.
**Severity**: Major

### W3: No statement on what benefit, if any, flows back to the Mizo-speaking community from this benchmark's construction
**Problem**: The paper's stated purpose is enabling future LLM evaluation on Mizo (Introduction, Conclusion), which is a genuine research contribution, but nothing in the paper addresses whether or how the exam-question source material, the news outlet whose text underlies the NER corpus, or the social-media users whose posts underlie the sentiment corpus, are acknowledged, compensated, or informed as data sources, beyond the planned annotator panel discussed elsewhere.
**Why it matters**: This is increasingly an explicit expectation for benchmark papers built from community-generated or community-relevant text, particularly for a minority language, and its absence will likely draw comment from at least one TACL reviewer working in this space.
**Suggestion**: A short paragraph, even a few sentences, addressing data provenance and any community engagement beyond the annotator panel would close this gap.
**Severity**: Minor

---

## Detailed Comments

### Introduction
The framing that "what is missing is a benchmark" (paragraph 2) correctly credits the existing Mizo computational literature rather than implying the language lacked prior NLP attention; this is a small but meaningful choice of words that avoids a common pattern in benchmark papers of erasing prior local work.

### Data / Ethics
See W1 and W2 above; these are the review's central concerns.

---

## Questions for Authors

1. Has the native-speaker validation of the MT register classifier (Section 3.4) actually been conducted, and if not, will Section 7's claim be corrected to reflect that?
2. Has any institutional review process been engaged for the planned MCQ adjudication panel and MT validation panel, including compensation and consent procedures?

---

## Minor Issues

None beyond W3 above.

---

## Dimension Scores

| Dimension | Score (0-100) | Descriptor | Notes |
|-----------|--------------|------------|-------|
| Originality (20%) | 76 | Strong | |
| Methodological Rigor (25%) | 60 | Weak | Perspective lens on W1 specifically |
| Evidence Sufficiency (25%) | 62 | Weak | |
| Argument Coherence (15%) | 62 | Weak | Same self-contradiction flagged by EIC, viewed as an ethics/credibility issue here |
| Writing Quality (15%) | 78 | Strong | |
| Significance & Impact | 78 | Strong | |
| **Weighted Average** | 68 | | **Major Revision** |
