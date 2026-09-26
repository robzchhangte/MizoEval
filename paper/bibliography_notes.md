# MizoEval Bibliography Notes

34 sources, organized by theme. Citation keys match `references.bib`. Verified via live WebSearch/WebFetch on 2026-09-26; two minor gaps are flagged explicitly rather than guessed.

## 1. Indic-language benchmarking

- **`verma2025milu`** — MILU, NAACL 2025 (AI4Bharat/IBM). 85,000 MCQs across 8 domains and 41 subjects in 11 Indic languages, drawn from regional and state exams. This is the paradigm MizoEval extends: all 11 MILU languages are Indo-Aryan or Dravidian, none Tibeto-Burman, so Mizo is structurally outside its coverage.
- **`kakwani2020indicnlpsuite`** — IndicNLPSuite / IndicGLUE, Findings of EMNLP 2020. Founding NLU benchmark for Indian languages (11 languages, tasks including classification, NER, QA). Establishes the benchmark-building precedent MizoEval follows for a language IndicGLUE does not cover.
- **`doddapaneni2023indicxtreme`** — IndicXTREME, ACL 2023. Human-supervised benchmark, 9 tasks across 20 Indic languages, 105 evaluation sets. Same coverage gap as IndicGLUE: no Tibeto-Burman languages.
- **`singh2024globalmmlu`** — Global-MMLU, arXiv 2024. 42-language MMLU translation with cultural-bias annotation; 28% of questions require culturally sensitive knowledge, heavily Western-centric. Cited to make the point that even the broadest multilingual MMLU effort has no Mizo coverage and inherits translation-artifact concerns MizoEval avoids by using native exam questions.

## 2. Low-resource MT resources / the religious-corpus problem

- **`akerman2023ebible`** — The eBible Corpus, arXiv 2023. 1,009 Bible translations across 833 languages; explicitly built as an MT resource and benchmark for extremely low-resource languages. Directly relevant precedent for why religious text dominates low-resource MT data generally, not just for Mizo.
- **`nllbteam2022`** — No Language Left Behind, Meta AI 2022. Introduces FLORES-200 and NLLB-200 models covering ~200 languages. NLLB-200-3.3B is one of MizoEval's evaluated models; the paper is the standard citation for both the model and the FLORES-200 evaluation methodology MizoEval's chrF/BLEU choices follow.

## 3. Mizo-specific resources establishing the "data exists, benchmark does not" gap

- **`lalrempuii2023lus`** — LUS Mizo Monolingual Corpus, IEEE DataPort 2023. 101,827 sentences crawled from Mizo news sites. Evidence that Mizo NLP resources exist at meaningful scale despite no evaluation benchmark existing.
- **`mwirelabs2024corpus`** — Mizo-Language-Corpus-4M, Hugging Face dataset. 4 million monolingual Mizo sentences. No accompanying paper was found; cited as a dataset, not a publication — flag this distinction if a reviewer asks for a DOI.

## 4. Contamination / memorization detection surveys

- **`xu2024contaminationsurvey`** — Benchmark Data Contamination of LLMs: A Survey, arXiv 2024. Organizes detection into matching-based and comparison-based methods, white/gray/black-box access levels. Positions MizoEval's contamination protocol within the existing detection taxonomy.
- **`cheng2025contaminationsurvey`** — A Survey on Data Contamination for LLMs, arXiv 2025. Complementary survey; cited alongside the above to show two independent surveys converge on contamination as an unresolved, active concern the field has not standardized around.

## 5. Mizo-specific computational prior work

- **`nunsanga2021postagging`** — CRF POS tagger for Mizo, Computación y Sistemas 2021. 89.42% precision on a 26-tag set over a 30,000-word corpus. Establishes that Mizo has had sequence-labeling work before MizoEval's NER task, useful context for the NER results.
- **`bentham2016ner`** — Rule-based Mizo NER, MICAI 2016. Identifies person/organization/location/designation classes via rules on a news corpus. Direct predecessor to the NER task in MizoEval, though rule-based rather than learned.
- **`pathak2019mizonmt`** — English-Mizo NMT vs. SMT, Neural Computing and Applications 2019. Comparative study of translation approaches for Mizo, a foundational MT paper for the language pair MizoEval evaluates.
- **`thangkhanhau2023parallelcorpus`** — 529K-sentence Mizo-English parallel corpus, ACM TALLIP 2023. The largest parallel-corpus construction effort for this language pair on record; relevant comparandum for the scale (3,000 pairs) and composition (religious/secular stratified) of MizoEval's own MT benchmark.
- **`lalthangmawii2025sentiment`** — Mizo sentiment analysis with lexical features and XLM-R, Natural Language Processing Journal 2025. First comprehensive Mizo sentiment framework (82% accuracy with logistic regression, 78% with XLM-R). Direct prior work for MizoEval's sentiment task; note the dataset differs from MizoEval's (this paper's own annotated set vs. MizoEval's `hillbyte/mizo-sentiment`).
- **`bala2024summarization`** — Mizo news summarization, arXiv 2024. Extends Mizo NLP into generation/summarization, evidence of an active and growing subfield rather than an isolated benchmark effort.

## 6. User's own prior papers — cite plainly and minimally, no special emphasis

**Standing project rule, confirmed explicitly by the user this project: these four entries must be cited exactly like any other source in this list — same sentence length, same tone, no "our prior work," no first-person framing, no highlighting them as more important than surrounding citations.**

- **`lalramhluna2024mizbert`** — MizBERT, ACM TALLIP 2024. A Mizo-specific BERT model, 98.92% accuracy on its evaluation task, outperforming multilingual BERT baselines.
- **`lalramhluna2023newsclassificationa`** — Mizo news classification via ML, FICTA 2022 proceedings (Springer, published 2023).
- **`lalramhluna2023newsclassificationb`** — A second, separate Mizo news classification paper, FICTA 2023 proceedings (Springer, published 2023). Distinct title and Springer volume from the entry above; confirmed as two separate publications, not a duplicate.
- **`lalrinmawii2025abusive`** — Mizo abusive-comment detection, IEEE AVSS 2025. Lalramhluna is a co-author, not sole or first author.

## 7. MT evaluation metric justification

- **`popovic2015chrf`** — chrF, WMT 2015. Character n-gram F-score for MT evaluation; the metric family MizoEval reports.
- **`popovic2017chrfpp`** — chrF++, WMT 2017. Adds word n-grams to chrF, correlates better with human judgment than chrF alone. MizoEval reports chrF++ (word_order=2) as its primary MT metric per this paper's own recommendation.

## 8. Benchmark-paradigm / prompting foundations

- **`hendrycks2021mmlu`** — MMLU, ICLR 2021. Founding multitask knowledge benchmark; the paradigm MILU, Global-MMLU, and by extension MizoEval's MCQ task all descend from.
- **`brown2020fewshot`** — GPT-3 / few-shot learning, NeurIPS 2020. Establishes the few-shot in-context prompting paradigm MizoEval's five-shot regime uses.
- **`wei2022chainofthought`** — Chain-of-thought prompting, NeurIPS 2022. Establishes the CoT prompting method MizoEval's CoT regime is built on.

## 9. Contamination detection methods

- **`shi2023detecting`** — Min-K% Prob, arXiv 2023. Likelihood-based contamination detection needing model logprobs. MizoEval's canary probe is explicitly designed to avoid this dependency (API-only access), worth contrasting directly.
- **`zhang2024minkpp`** — Min-K%++, ICLR 2025 (preprint 2024). Improves on Min-K% via second-order statistics; same logprob-access limitation as its predecessor.
- **`golchin2024timetravel`** — Time Travel in LLMs / guided instruction, ICLR 2024. The method most directly parallel to MizoEval's MCQ canary probe (prompting with a partial reference and checking for near-exact completion), and does not require logprob access.

## 10. Position bias

- **`pezeshkpour2024positionbias`** — MCQ option-order sensitivity, Findings of NAACL 2024. Documents 13-75% accuracy swings under answer reordering across benchmarks. Directly motivates MizoEval's permuted-MCQ variant and the position-bias analysis in the results.

## 11. Document-level leakage

- **`elangovan2021memorization`** — Memorization vs. generalization, EACL 2021. Introduces train/test overlap quantification via bag-of-words cosine similarity. Directly relevant to the NER official-split leakage MizoEval identifies as a limitation (train and official-test sentences sharing source articles).

## 12. NER methodology standard

- **`tjongkimsang2003conll`** — CoNLL-2003 shared task, 2003. The standard reference for BIO-tagged NER task design and entity-level evaluation; MizoEval's NER task follows this convention.

## 13. NE-India regional comparanda

- **`dhawan2026bm25`** — BM25-augmented many-shot translation, arXiv 2026 (WMT26 shared task submission). Covers 11 North-Eastern Indian languages including Mizo, using retrieval-augmented prompting with Gemini 2.5 Flash rather than fine-tuning. Closest contemporary comparandum for MizoEval's own MT evaluation of Mizo via prompting rather than fine-tuned MT systems.
- **`nyalang2026meiteiroberta`** — MeiteiRoBERTa, SIGTYP 2026. First monolingual RoBERTa for Meitei (Manipuri), another NE-Indian language; demonstrates the same "build a dedicated resource because general multilingual models underserve this language family" pattern MizoEval follows for Mizo.
- **`explainablenmt2026`** — Explainable multilingual NMT with adapters/MoE, International Journal of Speech Technology 2026. Covers bidirectional translation for six low-resource Indic languages including Mizo, using adapters and mixture-of-experts layers. **Author names unverified** — the publisher page (Springer) required authentication and did not expose an accessible author list; title, journal, and DOI (10.1007/s10772-026-10267-8) are confirmed from search result snippets only. Verify authorship directly before the paper is submitted if this citation is retained.

---

## Verification summary

- **34 of 34 themed sources** are represented in `references.bib` with a real, findable source behind each entry.
- **32 of 34** have a fully verified author list, title, venue, and year via direct WebFetch or corroborating WebSearch snippets.
- **2 known gaps**, both disclosed above and in `references.bib` rather than filled with a guess:
  - `mwirelabs2024corpus` has no accompanying paper (it is a dataset release only) — this is a fact about the source, not a verification failure.
  - `explainablenmt2026`'s author list could not be retrieved (paywalled publisher page); everything else about the entry is confirmed.
- No source was dropped — all 34 themed items from the original bibliography resolved to a real, verifiable match.
