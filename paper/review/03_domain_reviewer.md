# Peer Review Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 1

---

## Reviewer Information

### Reviewer Role
Peer Reviewer 2 (Domain)

### Reviewer Identity
Researcher in low-resource and Indic NLP with prior experience building Indic-language benchmarks.

### Review Focus
Completeness of related-work coverage; whether already-computed baselines are surfaced; data licensing and redistribution risk.

---

## Overall Assessment

### Recommendation
- [x] **Minor Revision** — leaning toward Major given the licensing gap below; see Weaknesses

### Confidence Score
4

### Summary Assessment
The related-work section (2.1-2.8) is unusually well organized for a benchmark paper: it correctly separates the Indic-benchmark coverage gap from the Mizo-specific prior-work literature from the contamination-detection literature, and it cites the user's own four prior Mizo papers with the same weight and tone as every other citation, which is the right practice. The benchmark itself, once released, will be a genuine and needed resource: no existing suite (MILU, IndicGLUE, IndicXTREME, Global MMLU) reaches Tibeto-Burman languages, and the paper documents this correctly. My concerns are about completeness of what is reported (baselines that exist are not tabulated) and about a real practical risk to the paper's central promise: that the data will actually be redistributable.

---

## Strengths

### S1: The literature positioning is precise, not padded
Section 2.1 distinguishes MILU's exam-based paradigm from IndicGLUE/IndicXTREME's broader task suite from Global MMLU's translation-based multilingual extension, and states plainly that all three families are Indo-Aryan/Dravidian only. This is exactly the coverage-gap argument the paper needs and it does not overstate it.

### S2: Prior Mizo-specific computational work is cited comprehensively and without special pleading for the authors' own contributions
Section 2.3 covers POS tagging (Nunsanga et al. 2021), rule-based NER (Bentham et al. 2016), NMT baselines (Pathak and Pakray 2019), parallel corpus construction (Thangkhanhau and Hussain 2023), sentiment (Lalthangmawii and Singh 2025), summarization (Bala et al. 2024), and the authors' own MizBERT, two news-classification papers, and an abusive-comment paper, all in the same sentence-length, same-tone register. This is a good-faith literature review, not a citation dump built around the authors' own work.

### S3: The regional-comparanda section (2.8) situates the paper against genuinely contemporary work
Citing 2026 papers on BM25-augmented translation for eleven Northeast Indian languages and a Meitei encoder shows the authors are tracking the most current work in the specific regional niche, not only the broader Indic literature.

---

## Weaknesses

### W1: Data Availability does not address whether the MCQ source material can legally be redistributed
**Problem**: Section 3.1 states the MCQ task is "drawn from Mizoram civil service examination questions." The Data Availability Statement says "all four MizoEval task datasets... will be made publicly available upon publication" without qualification. Government or examination-board exam questions frequently carry copyright or usage restrictions distinct from the authors' own annotations of them.
**Why it matters**: If this is not resolved before publication, the paper's central promise, that the benchmark itself will be usable by others, may not be deliverable as stated, and a reviewer or reader attempting to use the released MCQ set could face an unexpected licensing obstacle the paper never flagged.
**Suggestion**: State explicitly what license or permission basis applies to redistributing the exam-question text itself (as opposed to the repair harness and derived annotations, which the authors clearly can license).
**Severity**: Major

### W2: Already-computed baseline values are scattered across prose rather than tabulated
**Problem**: The majority-position MCQ baseline (30.1%), the random 4-way baseline (25%), and the majority-class sentiment baseline (56.8%) each appear only as an inline clause (Sections 5.1, 3.3) even though a complete baselines table already exists in the underlying analysis output.
**Why it matters**: A reader comparing model performance against chance and majority baselines has to hunt through two different sections' prose rather than reading one table; this is a presentation gap in an otherwise well-tabulated paper.
**Suggestion**: Add a compact baselines table, even a small one, since the values are already computed.
**Severity**: Minor

### W3: No discussion of how the MT and sentiment source datasets' provenance was verified for licensing/consent before release
**Problem**: The sentiment corpus is sourced from social media text with `[PERSON]` placeholders already applied (Section 3.3), suggesting the original source anonymized personal names, but the paper does not say whether the platform's terms of service or the original annotators' consent covers redistribution as part of a new benchmark.
**Why it matters**: This is a smaller version of W1's concern but for a different dataset; TACL's data statement expectations increasingly ask for this explicitly rather than leaving it implicit.
**Suggestion**: A sentence in the Ethics Statement or Data Availability Statement addressing the sentiment corpus's redistribution basis would close this gap alongside W1.
**Severity**: Minor

---

## Detailed Comments

### Literature Review
Complete for the paper's scope. No missing citation identified.

### Methodology / Research Design
The absence of a fine-tuned baseline (e.g., a supervised classifier for sentiment, a fine-tuned span extractor for NER) alongside the LLM comparisons is a reasonable scope decision given the paper's focus on general-purpose model evaluation rather than task-specific modeling, and I do not think it needs to be added; NLLB already serves this role for the MT task specifically.

### Conclusion
"MizoEval... assembled through a systematic audit... released together with the audit's findings" is an accurate and appropriately modest characterization of the paper's actual contribution; I would not want this softened.

---

## Questions for Authors

1. What is the licensing basis for redistributing the Mizoram civil-service exam question text itself, as distinct from the repair annotations layered on top of it?
2. Was consent obtained, or can it be documented, for the sentiment corpus's original social-media source material?

---

## Minor Issues

### Figures and Tables
A single baselines table (majority-position, random, majority-class) would improve the paper's completeness at negligible cost, since the values already exist.

---

## Dimension Scores

| Dimension | Score (0-100) | Descriptor | Notes |
|-----------|--------------|------------|-------|
| Originality (20%) | 80 | Strong | |
| Methodological Rigor (25%) | 68 | Adequate | Domain-review lens; deferring statistical detail to R1 |
| Evidence Sufficiency (25%) | 70 | Adequate | |
| Argument Coherence (15%) | 72 | Adequate | |
| Writing Quality (15%) | 80 | Strong | |
| Literature Integration | 88 | Exceptional | |
| **Weighted Average** | 74 | | **Minor-to-Major Revision** |
