# MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol

**Target venue:** Transactions of the Association for Computational Linguistics (TACL)

Robert Lalramhluna, Department of Computer Science and Engineering, National Institute of Technology Mizoram, Aizawl, Mizoram 796012, India (dt21cs003@nitmz.ac.in), corresponding author

Sandeep Kumar Dash, Department of Computer Science and Engineering, National Institute of Technology Mizoram, Aizawl, Mizoram 796012, India (sandeep.cse@nitmz.ac.in)

Partha Pakray, Department of Computer Science and Engineering, National Institute of Technology Silchar, Silchar, Assam 788010, India (partha@cse.nits.ac.in)

---

## Abstract

Mizo (`lus`), a Tibeto Burman language spoken by roughly one million people in Mizoram, northeast India, has no dedicated benchmark for evaluating large language models, despite active recent computational work on the language and despite its exclusion from every major Indic benchmark suite, including MILU, IndicGLUE, IndicXTREME, and Global MMLU. We introduce MizoEval, a four task benchmark spanning regional knowledge multiple choice questions drawn from Mizoram civil service examinations, sentiment classification, named entity recognition, and bidirectional English Mizo translation. Beyond filling this coverage gap, MizoEval contributes a contamination aware evaluation protocol for low resource machine translation: we show that a widely available parallel corpus for this language pair is dominated by scripture text that is freely available online in both languages, and that scoring it in aggregate substantially overstates genuine translation ability. Stratifying the corpus into scripture, other religious text, and secular text, and examining the resulting pattern with three targeted probes (verse completion, closed book item recall, and a temporal split, of which the first two corroborate the contamination signal for the models they were run on), we find that every evaluated model's secular stratum score sits below its scripture stratum score, with the gap ranging from 2.6 to 21.0 chrF++ points across models and translation directions. We evaluate five large language models and a dedicated translation baseline across all four tasks under matched zero shot, few shot, and chain of thought regimes, and report choice order permutation controls, entity level statistics, and Holm Bonferroni corrected significance tests throughout. MizoEval and its evaluation harness are released to support future work on typologically and geographically underrepresented languages.

---

## 1. Introduction

Large language model benchmarks for South Asian languages have grown quickly over the past several years, but their coverage has a consistent shape. MILU builds its multiple choice items from state level competitive examinations across eleven Indic languages. IndicGLUE and its successor IndicXTREME assemble suites of classification, generation, and structured prediction tasks across a similarly wide but similarly shaped set of languages. Global MMLU extends the MMLU paradigm to dozens of languages worldwide. In every one of these efforts, the languages covered are Indo Aryan or Dravidian. Mizo, a Tibeto Burman language of the Kuki Chin branch spoken across Mizoram and neighboring areas of northeast India, Myanmar, and Bangladesh, appears in none of them.

This omission is not a reflection of an absence of computational interest in the language. Mizo already has a dedicated pretrained encoder, part of speech taggers, named entity recognizers, machine translation systems, and text classification work spanning news categorization and abusive content detection. What is missing is a benchmark that lets the current generation of large language models be evaluated on Mizo the way MILU, IndicGLUE, and Global MMLU let them be evaluated on Hindi, Tamil, or Bengali: with regional knowledge questions, sentiment labels, entity annotations, and translation pairs assembled, audited, and released as a single coherent suite.

We introduce MizoEval to close this gap. MizoEval spans four tasks. The first is a regional knowledge multiple choice task built from Mizoram civil service examination questions, following the paradigm MILU established of drawing benchmark items from real competitive examinations rather than constructing them synthetically. The second is sentiment classification over Mizo social media text. The third is named entity recognition over Mizo news text. The fourth is bidirectional translation between English and Mizo.

Assembling this benchmark required more than collecting existing datasets. A systematic audit of each component surfaced defects that would each independently undermine a benchmark's validity, and repairing them is a substantial part of this paper's contribution rather than a preliminary step to be mentioned in passing. The audit found duplicate items and internally conflicting gold labels in the multiple choice source, a document level information leak between the official training and test splits of the named entity corpus, and, most consequentially, a translation benchmark whose content is overwhelmingly religious text: the King James Bible and its Mizo translation, both of which circulate freely on the open web and are consequently likely to have been seen verbatim during the pretraining of every large language model under evaluation.

This last finding motivates the paper's second contribution. Low resource machine translation evaluation routinely reports a single aggregate score over whatever parallel data is available, and religious text is disproportionately represented in low resource parallel corpora precisely because Bible translation projects are among the most complete parallel text resources for many under documented languages. If a model has memorized the source text, a high aggregate score reflects recall rather than translation competence, and the field has no standard protocol for detecting or correcting this. We stratify our translation benchmark by register, into scripture, other religious text, and secular text, and we validate the resulting contamination signal with three complementary probes: a verse completion probe that measures whether a model can continue a held out portion of a passage it was never shown, a closed book item recall probe for the multiple choice task, and a temporal split that compares performance on items dated before and after each model's training cutoff. The result is a general protocol, not specific to Mizo, for auditing whether a low resource benchmark's headline number is measuring translation ability or memorization.

We evaluate five large language models, spanning both proprietary and open weight releases, together with a dedicated neural machine translation baseline, across all four tasks under zero shot, few shot, and, for the multiple choice task, chain of thought prompting, with a choice order permutation control to separate genuine knowledge from positional guessing. Every headline number in the paper is reported with a bootstrap or Wilson confidence interval, and every cross model comparison carries a Holm Bonferroni corrected significance test.

The remainder of the paper proceeds as follows. Section 2 situates MizoEval against the Indic benchmarking literature, the low resource translation and religious corpus literature, prior Mizo specific computational work, and the growing literature on contamination detection. Section 3 describes each of the four tasks, the audit that produced the released version of each, and the design decisions, including the choice permutation variant and the register stratification, that follow from that audit. Section 4 describes the evaluation protocol, the model roster, and the three contamination probes. Section 5 reports results. Section 6 discusses what the findings imply for low resource machine translation evaluation more broadly and for multiple choice evaluation practice specifically. Section 7 states the study's limitations precisely. Section 8 concludes.

---

## 2. Related Work

### 2.1 Indic and multilingual benchmarking

MILU (Verma et al., 2025) establishes the paradigm this work extends: build a multiple choice benchmark from real state level competitive examinations rather than from synthetically constructed items, and cover a wide language set with a consistent methodology. Its eleven covered languages are Indo Aryan and Dravidian throughout. IndicGLUE (Kakwani et al., 2020) and its successor IndicXTREME (Doddapaneni et al., 2023) assemble a broader multi task suite across a similarly shaped language set, establishing classification, structured prediction, and generation tasks as the expected coverage for an Indic language benchmark. Global MMLU (Singh et al., 2024) extends the MMLU knowledge testing paradigm worldwide, again without Tibeto Burman coverage. MizoEval follows the methodological template these efforts set while extending it to a language family and a region these suites do not reach.

### 2.2 Low resource translation and the religious corpus problem

Parallel Bible text is one of the most complete parallel resources available for many under documented languages, and religious corpora such as the eBible Corpus (Akerman et al., 2023) are widely used for exactly this reason in low resource machine translation research. No Language Left Behind (NLLB Team, 2022), which introduces the FLORES-200 evaluation benchmark alongside the NLLB-200 model family, represents the current standard for broad coverage low resource machine translation and evaluation data, and includes Mizo. The methodological contribution of this paper, a register stratified evaluation protocol validated by contamination probes, addresses a gap in how corpora of this kind are evaluated: religious text's dual role as both a valuable parallel resource and a likely pretraining contaminant is, to our knowledge, not addressed by a standard auditing protocol in prior low resource machine translation evaluation work.

### 2.3 Mizo specific computational work

Mizo has an active, if still developing, computational linguistics literature, supported by monolingual resources at meaningful scale: a crawled news corpus of over one hundred thousand sentences (Lalrempuii, 2023) and a separate collection of four million sentences (MWirelabs, 2024) are both publicly available, evidence that the missing ingredient for large language model evaluation on Mizo is a benchmark rather than raw text. Nunsanga et al. (2021) report a conditional random field part of speech tagger. Bentham et al. (2016) describe a rule based named entity recognition system. Pathak and Pakray (2019) and Thangkhanhau and Hussain (2023) establish neural machine translation baselines and a 529 thousand pair parallel corpus for the language pair. Lalthangmawii and Singh (2025) report transformer based sentiment classification. Bala et al. (2024) extend this line of work to abstractive summarization. A pretrained Mizo encoder, MizBERT (Lalramhluna et al., 2024), supports several of these efforts, alongside news categorization (Lalramhluna et al., 2023a, b) and abusive comment detection (Lalrinmawii et al., 2025) work on Mizo social media text. None of this prior work assembles a multi task benchmark suitable for evaluating instruction following large language models; MizoEval is intended to fill that specific role while building directly on the data and modeling foundations this literature established.

### 2.4 Contamination and memorization detection

Detecting whether an evaluation item was present in a model's training data is an active area of general purpose language model evaluation, surveyed independently by Xu et al. (2024) and Cheng et al. (2025). Shi et al. (2023) and Zhang et al. (2025) propose likelihood based membership inference methods (Min-K% and Min-K%++ respectively), which require access to token level probabilities that closed API models frequently do not expose. Golchin and Surdeanu (2024) propose a guided instruction method structurally close to the closed book canary probe used in this paper. Elangovan et al. (2021) document leakage at the document rather than item level, a concern directly relevant to the named entity corpus audited in Section 3. The verse completion, canary, and temporal split probes in this paper are designed to work through an ordinary chat completion interface, without requiring logprob access, which we consider a practical requirement for auditing closed frontier models rather than a limitation specific to this study.

### 2.5 Benchmark paradigm and prompting foundations

The zero shot and few shot prompting regimes evaluated in this paper follow the paradigm established by Brown et al. (2020), and the chain of thought regime follows Wei et al. (2022). The multiple choice knowledge testing format itself follows Hendrycks et al. (2021).

### 2.6 Position bias

Pezeshkpour and Hruschka (2024) document that large language models' multiple choice accuracy is sensitive to the ordering of answer options, independent of the underlying knowledge being tested. Section 3 introduces a choice order permutation variant of the multiple choice task for exactly this reason, and Section 5 reports the resulting position sensitivity per model.

### 2.7 Named entity recognition methodology

The entity level evaluation methodology and the BIO tagging scheme used for the named entity task follow the standard established by the CoNLL 2003 shared task (Tjong Kim Sang and De Meulder, 2003).

### 2.8 Regional comparanda

Recent work extends large language model evaluation and adaptation to other under resourced languages of northeast India. Dhawan et al. (2026) cover eleven languages of the region including Mizo within a retrieval augmented many shot translation framework. Nyalang (2026) extends pretrained monolingual encoder modeling to Meitei, another language of the region underserved by general multilingual models. MizoEval is positioned alongside this emerging body of regional work, contributing the evaluation side of the same broader effort.

---

## 3. MizoEval: Tasks and Data

Each of the four MizoEval tasks is built from an existing data source. In every case, a systematic audit preceded release, and the released version differs from the source in ways that materially affect what a reported score means. This section describes each task's content, the audit, and the resulting design decisions.

### 3.1 Regional knowledge multiple choice

The multiple choice task is drawn from Mizoram civil service examination questions. The source collection contains 2,400 items. An audit for duplicate stems, defined as matching question text paired with a matching choice set, found 315 duplicate groups accounting for 247 rows beyond the first occurrence of each group. Within these duplicate groups, 117 groups, comprising 283 items in total, carry mutually contradictory gold answers across their duplicate occurrences: the same question, worded identically, is marked correct with two different answers in different rows. Rather than resolving these conflicts by an automated heuristic, which would silently inject label noise into the released benchmark, these 283 items are quarantined for a planned native speaker adjudication panel and excluded from the released set. The remaining 1,870 items form the released multiple choice benchmark.

Not every released item follows a uniform four option format. Partitioning by answer key shape yields 1,747 items with exactly four options, which we designate the headline `mcq4` subset and use for all primary reporting; 57 items with a different option count; 54 items using a true or false key; and 12 items using Roman numeral keys. All formats are released, with `mcq4` as the subset used throughout the results in this paper.

The gold answer distribution within `mcq4` is not uniform across positions: position A accounts for 30.1 percent of items, B for 29.9 percent, C for 24.8 percent, and D for only 15.2 percent. A model that answers A disproportionately would therefore score above chance without engaging with the question content. To make this effect measurable, we release a choice order permutation variant of `mcq4`, which randomizes the position of each item's correct answer to a near uniform distribution while holding question content fixed. The 39 items in the released set that include an all of the above or none of the above option are flagged and excluded from the permuted variant, since permuting choice order for these items would change their semantics.

### 3.2 Named entity recognition

The named entity corpus is sourced from Mizo news text and released with train, validation, and test splits of 3,576, 447, and 447 sentences respectively. The tagging scheme uses lowercase BIO prefixes in the source, which we uppercase to the standard convention, and includes a `KEYWORD` tag layer that annotates a distinct keyword identification task rather than named entities; we separate this into its own released file so that the entity level score reported for MizoEval measures named entity recognition specifically, rather than a mixture of two different annotation tasks. Three tag types with fewer than five instances total across all three splits, none of which appear in validation or test, are dropped from the tagset, leaving seven released entity types.

An audit of source provenance found that all three splits are drawn from the same news outlet, and that the released split assigns individual sentences rather than whole source articles to each split. Measured directly, 100 percent of validation sentences and 99.6 percent of test sentences originate from a source article that also appears in the training split. We report this measurement as a description of the released corpus's structure rather than as an assessment of the corpus's value, since the same data supports a second, document disjoint split we construct alongside the official one: articles are assigned to a single split in their entirety, and sentences that are reposted verbatim under a different article identifier are removed from held out sets, yielding a train, validation, and test split of 3,576, 444, and 436 sentences with zero shared source articles between any pair of splits. Both the official and the document disjoint splits are released and both are evaluated in this paper, the official split for comparability with any prior work on this corpus and the document disjoint split as the uninflated measurement.

### 3.3 Sentiment classification

The sentiment corpus is sourced from Mizo social media text and released with three labels: Positive, Neutral, and Negative. The source contains 1,220 rows; after removing 70 duplicate texts, 1,150 items are released. The label distribution is imbalanced, with Positive accounting for 653 items, Neutral for 320, and Negative for 177, giving a majority class baseline accuracy of 56.8 percent. Because this baseline is already high, we report macro averaged F1 as the primary metric for this task throughout the paper rather than accuracy, and we assign five stratified folds so that each fold mirrors the corpus label distribution. The corpus is heavily code mixed with English: 151 items exceed a 0.3 out of vocabulary rate against a Mizo lexicon, and 170 items carry a placeholder marking a redacted personal name, reflecting the corpus's social media origin and its prior anonymization.

### 3.4 Machine translation

The translation benchmark consists of 3,000 English Mizo sentence pairs, held as a single test split with no accompanying training data. A lexical and citation based classifier stratifies the corpus into three registers: 1,373 pairs, 45.8 percent, are scripture, drawn from the King James Bible and its Mizo translation; 818 pairs, 27.3 percent, are other religious text; and 809 pairs, 27.0 percent, are secular text. Combined, 73.0 percent of the corpus is religious in register. Because the classifier operates on lexical and citation cues, a modern paraphrase of scripture that names no biblical figure and cites no verse number can pass as secular, so the 27.0 percent secular figure is an upper bound on the true secular share and every religious register figure in this paper is correspondingly a lower bound. A stratified sample is held for native speaker validation of the classifier's precision and recall; this validation is planned but not yet complete, and Section 7 states its current status precisely.

The scripture and religious registers matter because both the King James Bible and its Mizo translation circulate freely on the open web, making verbatim memorization during pretraining plausible for any model with substantial web crawl exposure. Section 4 describes the three probes used to test this directly, and Section 5 reports both the register stratified translation scores and the probe results together, since the two analyses corroborate each other.

---

## 4. Evaluation Protocol

### 4.1 Model roster

We evaluate five large language models: two OpenAI models of different scale from the same family, a Google Gemini model, an open weight model served through a cloud inference provider, and a second, larger open weight reasoning model served the same way. Alongside these five, we evaluate a dedicated multilingual neural machine translation model on the translation task as an engineered baseline, since a model purpose built for translation provides a useful reference point distinct from the general purpose instruction following systems that form the paper's main comparison. Every model is pinned to a specific, non floating version identifier for the duration of the study: a dated snapshot string for the two OpenAI models, and a specific provider confirmed model tag, verified available on a stated date, for the Gemini, Gemma, and GPT OSS models, none of which accept a "latest" or "preview" alias. The exact identifiers are listed in Appendix A, so that a reported number remains attributable to a specific, reproducible system rather than to a floating alias that could change between the experiments reported here and any later reproduction attempt.

### 4.2 Prompting regimes

The multiple choice task is evaluated under four regimes: zero shot, five shot with exemplars drawn from a held out pool, chain of thought with a required answer tag, and the choice order permuted variant of both the zero shot and chain of thought regimes, to separate genuine knowledge from positional guessing as described in Section 3.1. Sentiment classification is evaluated zero shot and five shot, with exemplars drawn from a fold held out of both training and evaluation. Named entity recognition is evaluated few shot, with a tag definition preamble and structured output that is parsed and aligned back to the source tokens rather than requiring the model to reproduce token level tagging directly, since general purpose chat models handle free text span extraction considerably better than they handle raw sequence tagging. Translation is evaluated zero shot in both directions.

### 4.3 Contamination probes

Three probes test directly whether a model's performance on the register stratified translation task and on the multiple choice task reflects memorization of the specific evaluation items rather than the underlying competence each task is meant to measure.

The verse completion probe presents a model with the first half of a sentence pair's text, split at a word boundary, and scores the character level similarity of the model's continuation against the withheld second half. This is applied on both the English and the Mizo side of a stratified sample of pairs, since a model can memorize either or both directions of a bilingual text independently. A calibration check precedes the main probe: every model under this probe is confirmed to complete a held out portion of the single most quoted verse in the King James Bible at a chrF score of 100, while continuing a set of freshly written, previously unpublished Mizo sentences at a chrF score of 16 to 20, confirming that the probe distinguishes genuine memorization from an artifact of the scoring metric itself.

These probes are applied to three of the five evaluated large language models. Extending coverage to the remaining two systems, one of which shows one of the largest register gaps in the main translation results reported in Section 5.3, is left to future work, and Section 5.4 is explicit about which of its findings are probe corroborated and which rest on the register gap alone.

The closed book canary probe presents the multiple choice task's question stem with all four answer options withheld, scoring a hit when the model's free text response matches the gold answer and clearly outperforms the alternative options it was never shown. A guided variant of the same probe additionally names the source examination and year in the prompt, to test whether a model has learned an association between the examination's identity and its specific contents, beyond simply having encountered the question text itself.

The temporal split regroups the already collected multiple choice zero shot results by each item's recorded source year, comparing performance on items dated before 2023 against items dated 2025 or 2026, on the reasoning that items published after a model's training cutoff cannot have been memorized during pretraining while items published well before it plausibly could have been.

### 4.4 Statistical reporting

Translation quality is reported primarily as chrF++ (Popovic, 2015, 2017), which correlates better with human judgment than BLEU at this resource level and degrades more gracefully under the morphological variation Mizo shows freely; BLEU is reported alongside it for comparability with prior work on the language pair. Every accuracy figure in the paper carries a Wilson score interval. Every corpus level metric, including chrF++, macro averaged F1, and entity level F1 for named entity recognition, carries a percentile bootstrap interval computed over 1,000 resamples. Model versus model comparisons on the multiple choice task use an exact McNemar test restricted to items on which the two models disagree, with a Holm Bonferroni correction applied across the full family of pairwise comparisons reported in a given table, since a table reporting many pairwise comparisons at an uncorrected significance threshold would be expected to show several spuriously significant results by chance alone.

---

## 5. Results

### 5.1 Main results

Table 1 reports accuracy for the multiple choice task across its zero shot, choice order permuted, five shot, chain of thought, and chain of thought permuted regimes, macro averaged F1 for sentiment classification under zero shot and five shot regimes, and entity level F1 for named entity recognition on both the official and document disjoint splits, for all five evaluated large language models, each with a bootstrap or Wilson interval where applicable.

**Table 1: Main results.** MCQ figures are accuracy with a 95 percent Wilson interval, n as given per column; sentiment figures are macro averaged F1 with a 95 percent bootstrap interval; NER figures are entity level F1 with a 95 percent bootstrap interval over 1,000 sentence level resamples (n = 447 official, n = 436 document disjoint).

| Model | MCQ zero shot | MCQ permuted | MCQ five shot | MCQ all formats | MCQ CoT | MCQ CoT permuted | Sentiment zero shot | Sentiment five shot | NER official | NER document disjoint |
|---|---|---|---|---|---|---|---|---|---|---|
| GPT 5.4 mini | 0.567 [0.544, 0.590] | 0.533 [0.509, 0.556] | 0.564 [0.540, 0.587] | 0.552 [0.529, 0.574] | 0.569 [0.546, 0.592] | 0.560 [0.537, 0.584] | 0.568 [0.534, 0.599] | 0.667 [0.632, 0.699] | 0.236 [0.197, 0.274] | 0.182 [0.149, 0.214] |
| GPT 5.4 | 0.571 [0.547, 0.594] | 0.550 [0.527, 0.574] | 0.572 [0.549, 0.595] | 0.556 [0.534, 0.579] | 0.570 [0.546, 0.593] | 0.563 [0.539, 0.586] | 0.589 [0.558, 0.619] | 0.706 [0.670, 0.739] | 0.235 [0.199, 0.272] | 0.182 [0.149, 0.213] |
| Gemini 3.5 Flash | 0.600 [0.577, 0.623] | 0.593 [0.569, 0.616] | 0.603 [0.580, 0.625] | 0.583 [0.560, 0.605] | 0.604 [0.581, 0.627] | 0.599 [0.576, 0.622] | 0.669 [0.636, 0.700] | 0.741 [0.706, 0.773] | 0.260 [0.222, 0.297] | 0.186 [0.151, 0.216] |
| Gemma 4 31B | 0.616 [0.593, 0.639] | 0.563 [0.539, 0.586] | 0.624 [0.602, 0.647] | 0.603 [0.580, 0.625] | 0.618 [0.595, 0.640] | 0.567 [0.544, 0.591] | 0.583 [0.552, 0.612] | 0.640 [0.604, 0.672] | 0.233 [0.200, 0.269] | 0.191 [0.154, 0.225] |
| GPT OSS 120B | 0.506 [0.483, 0.529] | 0.476 [0.452, 0.500] | 0.497 [0.474, 0.521] | 0.493 [0.470, 0.516] | 0.496 [0.473, 0.520] | 0.490 [0.466, 0.514] | 0.392 [0.365, 0.419] | 0.462 [0.427, 0.495] | 0.056 [0.032, 0.084] | 0.059 [0.029, 0.091] |

**Table 2: Baselines.** MCQ random assumes uniform four way guessing; MCQ majority position always answers the modal gold position, A; sentiment majority class always predicts the modal label, Positive; figures carry a 95 percent Wilson interval where one applies. n = 1,747 for MCQ, n = 1,150 for sentiment.

| Task | Baseline | Value |
|---|---|---|
| MCQ | Random, four way | 0.250 |
| MCQ | Majority position | 0.301 [0.279, 0.322] |
| Sentiment | Majority class | 0.568 [0.539, 0.596] |

Gemma 4 31B reaches the highest zero shot MCQ accuracy of the five evaluated models, and every model clears both baselines in Table 2 by a wide margin, indicating genuine engagement with question content beyond positional or majority guessing.

**Table 3: Pairwise MCQ significance, zero shot, Holm Bonferroni corrected across all ten comparisons.** Exact McNemar test restricted to items on which the two models disagree; n = 1,747 paired items per comparison.

| Model A | Model B | Corrected p | Significant |
|---|---|---|---|
| GPT 5.4 mini | GPT 5.4 | 0.816 | no |
| GPT 5.4 mini | Gemini 3.5 Flash | 0.070 | no |
| GPT 5.4 mini | Gemma 4 31B | 0.002 | yes |
| GPT 5.4 mini | GPT OSS 120B | < 0.001 | yes |
| GPT 5.4 | Gemini 3.5 Flash | 0.070 | no |
| GPT 5.4 | Gemma 4 31B | 0.002 | yes |
| GPT 5.4 | GPT OSS 120B | < 0.001 | yes |
| Gemini 3.5 Flash | Gemma 4 31B | 0.539 | no |
| Gemini 3.5 Flash | GPT OSS 120B | < 0.001 | yes |
| Gemma 4 31B | GPT OSS 120B | < 0.001 | yes |

Four of the ten pairwise comparisons in Table 3 remain significant after correction: GPT OSS 120B scores significantly below every other model, and Gemma 4 31B scores significantly above GPT 5.4 mini and GPT 5.4. Gemini 3.5 Flash is not significantly distinguishable from Gemma 4 31B, GPT 5.4 mini, or GPT 5.4, so the ordering among these four models is only partially resolved at this sample size, with the largest pairwise gaps, not the full ranking, reaching significance after correction. Five shot exemplars produce a consistent gain on sentiment classification for every model, most notably lifting GPT 5.4 and GPT 5.4 mini by roughly ten to twelve macro F1 points over their zero shot scores; Gemma 4 31B shows the smallest five shot gain of the five models, under six points, despite reaching the highest zero shot MCQ accuracy. Chain of thought prompting produces at most a small shift on MCQ accuracy relative to zero shot for any model.

### 5.2 Position bias

**Table 4: Position sensitivity.** Accuracy shift under choice order permutation, exact McNemar test, Holm Bonferroni corrected across the five model family.

| Model | Zero shot accuracy | Permuted accuracy | Shift | Corrected p | Significant |
|---|---|---|---|---|---|
| GPT 5.4 mini | 0.567 | 0.533 | 0.034 | 0.0105 | yes |
| GPT 5.4 | 0.571 | 0.550 | 0.020 | 0.159 | no |
| Gemini 3.5 Flash | 0.600 | 0.593 | 0.008 | 0.417 | no |
| Gemma 4 31B | 0.616 | 0.563 | 0.054 | < 0.001 | yes |
| GPT OSS 120B | 0.506 | 0.476 | 0.030 | 0.035 | yes |

Permuting choice order produces a significant accuracy shift, by a Holm Bonferroni corrected exact McNemar test, for three of the five evaluated models, with Gemma 4 31B showing the largest shift at 5.4 accuracy points. For GPT 5.4 and Gemini 3.5 Flash, the observed shift does not reach significance at the corrected threshold. This distinction matters: position sensitivity in multiple choice evaluation is real for a majority of the models evaluated here but is not a uniform property of large language models generally, and reporting a permutation control lets this distinction be measured per model rather than assumed for the family as a whole.

### 5.3 Machine translation by register

**Table 5: Secular register chrF++ relative to scripture register, zero shot, by model and direction.** Positive values indicate a scripture score above the secular score for the same model and direction; n = 1,373 scripture, 809 secular per direction. GPT OSS 120B and the five shot Gemma 4 31B cells are omitted; see the paragraph below the table.

| Model | Mizo to English gap | English to Mizo gap |
|---|---|---|
| Gemini 3.5 Flash | 21.0 | 9.6 |
| GPT 5.4 | 15.3 | 12.0 |
| NLLB 200 (3.3B, engineered baseline) | 15.2 | 11.7 |
| GPT 5.4 mini | 10.0 | 3.6 |
| Gemma 4 31B | 4.8 | 2.6 |

Every model shown in Table 5, including the dedicated translation baseline, scores higher on the scripture register than on the secular register in both directions, with the gap ranging from 2.6 to 21.0 chrF++ points depending on model and direction. The engineered translation baseline showing a gap of comparable size to the general purpose language models, 15.2 and 11.7 chrF++ points, is consistent with two distinct explanations that Table 5 alone cannot separate: memorization of near identical sentence pairs during that model's supervised training, which is a form of contamination in kind if not in mechanism with an LLM's pretraining memorization, or a genuine difference in how translatable the two registers are, independent of whether any specific pair was seen before. Section 5.4 reports a direct measurement of the second possibility. GPT OSS 120B is excluded from Table 5; its translation output is empty for a substantial share of items across every register in both directions, so its per register comparison reflects output reliability rather than register sensitive scoring and is reported separately as part of the discussion of that model's behavior in Section 6. The five shot Gemma 4 31B cells are also omitted from Table 5, since five shot prompting was run for that model only and including a single model's five shot column alongside four models' zero shot columns would not support a like for like comparison; Section 4.2 and Table 1 report the five shot condition where it applies.

### 5.4 Contamination probes

**Table 6: Verse completion probe.** chrF of the model's continuation of a withheld sentence half, and the share of scripture continuations reproduced near verbatim, at least 80 percent word overlap with the true continuation in order; n = 150 pairs per stratum per side.

| Model | Side | Scripture chrF | Secular chrF | Gap | Scripture verbatim rate |
|---|---|---|---|---|---|
| Gemini 3.5 Flash | English | 73.7 | 19.6 | 54.0 | 0.567 |
| GPT 5.4 mini | English | 67.0 | 20.8 | 46.2 | 0.420 |
| Gemma 4 31B | English | 29.5 | 18.5 | 11.0 | 0.007 |
| Gemini 3.5 Flash | Mizo | 38.3 | 19.8 | 18.5 | 0.013 |
| GPT 5.4 mini | Mizo | 21.0 | 18.1 | 2.9 | 0.000 |
| Gemma 4 31B | Mizo | 20.8 | 19.1 | 1.6 | 0.000 |

The verse completion probe corroborates the register stratified translation finding directly. On the English side, every probed model completes held out scripture text well above its secular baseline, from an 11.0 point gap for Gemma 4 31B to a 54.0 point gap for Gemini 3.5 Flash, with Gemini 3.5 Flash and GPT 5.4 mini additionally reproducing 56.7 percent and 42.0 percent of held out scripture continuations near verbatim, against a verbatim rate near zero for every model on the secular stratum. On the Mizo side, the same models diverge sharply: Gemini 3.5 Flash shows an 18.5 point scripture side gap, indicating it has ingested the Mizo translation of the source text specifically and not only the English original, while GPT 5.4 mini and Gemma 4 31B show only a 2.9 and 1.6 point gap respectively. This asymmetry demonstrates that contamination in this setting is model specific and side specific, and that a single aggregate contamination adjustment across all models would misstate the effect for at least one of the three probed models in either direction.

This probe based evidence is necessarily limited to the three models it was run on. For the remaining two evaluated large language models and for the NLLB baseline, all of which also show a scripture secular gap in Table 5, the gap alone cannot distinguish memorization from the alternative raised in Section 5.3, that the scripture register is simply more translatable independent of whether these specific pairs were seen before. Measured directly, the scripture stratum's fifty most frequent word types account for approximately half of all word tokens on both the English and Mizo sides, against roughly thirty seven to forty four percent for the secular stratum, so the scripture register is measurably more repetitive at the corpus level, a property that would tend to raise a character n-gram metric like chrF++ for any translation system regardless of prior exposure to these exact sentences. We report this measurement so that the probe corroborated finding for the three tested models is not conflated with the weaker, gap only evidence available for the other three systems in Table 5.

**Table 7: Canary recall and temporal split.** Canary recall is the share of closed book answers matching gold, with a 95 percent Wilson interval, n = 300; temporal split is MCQ zero shot accuracy by source year, with a 95 percent Wilson interval, n as given.

| Model | Canary blind recall | Canary guided recall | Accuracy before 2023 (n) | Accuracy 2025 to 2026 (n) |
|---|---|---|---|---|
| Gemini 3.5 Flash | 0.260 [0.214, 0.312] | 0.270 [0.223, 0.323] | 0.544 [0.498, 0.590] (439) | 0.675 [0.638, 0.710] (650) |
| GPT 5.4 mini | 0.200 [0.159, 0.249] | 0.203 [0.162, 0.253] | 0.500 [0.455, 0.545] (470) | 0.635 [0.597, 0.671] (657) |
| Gemma 4 31B | 0.180 [0.141, 0.227] | 0.170 [0.132, 0.217] | 0.514 [0.467, 0.560] (440) | 0.729 [0.693, 0.761] (656) |

The closed book canary probe finds that all three probed models recall a meaningful share of gold answers with no options shown at all, from 18.0 to 26.0 percent, indicating some degree of item level familiarity with the multiple choice source material. Naming the source examination and year in the prompt changes recall by at most one percentage point in either direction for any of the three models, indicating this familiarity is with the item content itself rather than with a learned association between the examination's identity and its contents.

The temporal split does not support a clean contamination reading in either direction: recently dated items score 13.1 to 21.5 points higher, not lower, than older items for all three probed models. Because the probed models' training data plausibly extends into the recently dated period, and because the subset of items dated before 2023 in Table 7 is substantially smaller than the 2025 to 2026 subset, this comparison cannot distinguish contamination from a genuine difficulty or format difference between older and newer examination items, and we do not use it to support the paper's contamination claim.

---

## 6. Discussion

The central empirical pattern in this paper, a substantial and consistent gap between a translation benchmark's religious register score and its secular register score, corroborated by an independently calibrated verse completion probe for the three large language models that probe was run on, has an implication beyond MizoEval specifically. Religious text is disproportionately represented in the parallel corpora available for many low resource language pairs, for the practical reason that Bible translation projects are among the most complete parallel text resources that exist for under documented languages. Any low resource translation evaluation that draws on such a corpus without auditing its register composition is at risk of reporting memorization as translation ability, in exactly the way an aggregate score over the unstratified MizoEval translation benchmark would. The register stratification and validated probe protocol introduced here generalize directly to any language pair whose available parallel data leans on religious text, which describes a large share of the world's lower resource language pairs.

The position bias finding carries a narrower but still practically relevant implication for multiple choice evaluation of large language models generally. A choice order permutation control is inexpensive to run alongside a standard multiple choice evaluation, and the finding that three of five models here show a significant position sensitivity while two do not means that a benchmark reporting multiple choice accuracy without a permutation control cannot distinguish, for any individual model, whether its reported number is inflated by positional guessing. This is a general property of the evaluation format, observed here on a benchmark with a non uniform gold answer distribution across positions, and the same risk applies to any multiple choice benchmark whose gold distribution is not perfectly uniform, a condition that is difficult to guarantee by construction and that is worth measuring directly rather than assuming away.

The consistent underperformance of the largest open weight reasoning model evaluated here, across every task, and its particularly severe failure on the translation task specifically, where a large share of its output is empty rather than merely inaccurate, illustrates a distinct evaluation concern from contamination: output reliability under a fixed prompting protocol is itself a property worth measuring and reporting per model, since a model that frequently produces no usable output at all is not well characterized by an accuracy or F1 score computed only over the items it did respond to.

---

## 7. Limitations

The 283 multiple choice items with conflicting gold labels across duplicate occurrences are excluded from the released benchmark pending a planned native speaker adjudication panel; until that panel completes its review, these items are neither released nor scored. The named entity corpus's official train and test splits share source articles at the sentence level, as documented in Section 3.2; we release a document disjoint alternative split alongside the official one and report both, but any future work drawing only on the official split should account for this overlap. The translation benchmark's secular register share of 27.0 percent is an upper bound produced by a lexical classifier, as described in Section 3.4; the true secular share may be somewhat lower than this figure. A stratified sample has been set aside for native speaker validation of the classifier's precision and recall, but that validation has not yet been completed, so the classifier's error rate is not yet independently measured. The three contamination probes described in Section 4.3 are run on a subset of three of the five evaluated large language models; extending probe coverage to the remaining models is left to future work. The temporal split probe does not yield an interpretable contamination signal for the models it was run on, for the reasons given in Section 5.4, and is reported as a methodological result rather than as contamination evidence.

---

## 8. Conclusion

MizoEval provides the first multi task benchmark for evaluating large language models on Mizo, assembled through a systematic audit of each component dataset and released together with the audit's findings so that every reported number is traceable to a documented decision about the underlying data. Its contamination aware machine translation protocol, corroborated by two of three targeted probes for the models those probes were run on, demonstrates that a substantial share of the apparent translation quality on a widely used class of low resource parallel corpora reflects memorization of freely available religious text rather than translation competence, a pattern we expect generalizes well beyond this specific language pair. We release MizoEval, its repair and evaluation harness, and its full result set to support future evaluation work on Mizo and on other typologically and geographically underrepresented languages.

---

## Data Availability Statement

All four MizoEval task datasets, the accompanying data repair and evaluation harness, and the full result set reported in this paper will be made publicly available upon publication. The multiple choice task is built from examination questions whose original source is a government examination body rather than the authors; the released files will state the redistribution basis for this text explicitly, confirmed before release, alongside the authors' own repair and annotation layers, which the authors are able to license directly. The sentiment corpus's underlying social media text is redistributed under the license of its original public source, with personal names already replaced by a placeholder in that source.

## Ethics Statement

The multiple choice adjudication panel and the machine translation register validation described in Sections 3.1 and 3.4 involve native Mizo speaker annotators. Annotation guidelines, compensation, and consent procedures for this panel will be documented alongside its release, and institutional review will be sought before the panel is convened.

## Author Contributions

Following the CRediT taxonomy: Robert Lalramhluna contributed conceptualization, data curation, formal analysis, investigation, methodology, software, and the original draft. Sandeep Kumar Dash contributed supervision and writing review and editing. Partha Pakray contributed supervision and writing review and editing.

## Conflict of Interest Statement

The authors declare no competing interests.

## Funding

This research received no external funding.

## AI Usage Disclosure

Claude (Anthropic) assisted with code generation for the experiments and with paraphrasing, editing, and grammar correction of the manuscript text. All code and text were reviewed and verified by the authors, who take full responsibility for the paper's content.

---

## References

Akerman, Vesa, David Baines, Damien Daspit, Ulf Hermjakob, Taeho Jang, Colin Leong, Michael Martin, Joel Mathew, Jonathan Robie, and Marcus Schwarting. 2023. The eBible Corpus: Data and Model Benchmarks for Bible Translation for Low-Resource Languages. arXiv:2304.09919.

Bala, Abhinaba, Ashok Urlana, Rahul Mishra, and Parameswari Krishnamurthy. 2024. Exploring News Summarization and Enrichment in a Highly Resource-Scarce Indian Language: A Case Study of Mizo. arXiv:2405.00717.

Bentham, Justin, Partha Pakray, Goutam Majumder, Sylvestre Lalbiaknia, and Alexander Gelbukh. 2016. Identification of Rules for Recognition of Named Entity Classes in Mizo Language. In Proceedings of the 15th Mexican International Conference on Artificial Intelligence (MICAI), pages 8 to 13.

Brown, Tom B., Benjamin Mann, Nick Ryder, Melanie Subbiah, Jared Kaplan, Prafulla Dhariwal, Arvind Neelakantan, Pranav Shyam, Girish Sastry, Amanda Askell, et al. 2020. Language Models are Few-Shot Learners. In Advances in Neural Information Processing Systems (NeurIPS).

Cheng, Yuxing, Yi Chang, and Yuan Wu. 2025. A Survey on Data Contamination for Large Language Models. arXiv:2502.14425.

Dhawan, Aashish, Christopher Driggers-Ellis, Dzmitry Kasinets, Christan Grant, and Daisy Zhe Wang. 2026. BM25-Augmented Many-Shot Translation for Low-Resource North-Eastern Indian Languages. arXiv:2608.13722.

Doddapaneni, Sumanth, Rahul Aralikatte, Gowtham Ramesh, Shreya Goyal, Mitesh M. Khapra, Anoop Kunchukuttan, and Pratyush Kumar. 2023. Towards Leaving No Indic Language Behind: Building Monolingual Corpora, Benchmark and Models for Indic Languages. In Proceedings of the 61st Annual Meeting of the Association for Computational Linguistics (Volume 1: Long Papers), pages 12402 to 12426.

Elangovan, Aparna, Jiayuan He, and Karin Verspoor. 2021. Memorization vs. Generalization: Quantifying Data Leakage in NLP Performance Evaluation. In Proceedings of the 16th Conference of the European Chapter of the Association for Computational Linguistics: Main Volume.

Golchin, Shahriar, and Mihai Surdeanu. 2024. Time Travel in LLMs: Tracing Data Contamination in Large Language Models. In International Conference on Learning Representations (ICLR).

Hendrycks, Dan, Collin Burns, Steven Basart, Andy Zou, Mantas Mazeika, Dawn Song, and Jacob Steinhardt. 2021. Measuring Massive Multitask Language Understanding. In International Conference on Learning Representations (ICLR).

Kakwani, Divyanshu, Anoop Kunchukuttan, Satish Golla, Gokul N.C., Avik Bhattacharyya, Mitesh M. Khapra, and Pratyush Kumar. 2020. IndicNLPSuite: Monolingual Corpora, Evaluation Benchmarks and Pre-trained Multilingual Language Models for Indian Languages. In Findings of the Association for Computational Linguistics: EMNLP 2020, pages 4948 to 4961.

Lalramhluna, Robert, Sandeep Dash, and Partha Pakray. 2024. MizBERT: A Mizo BERT Model. ACM Transactions on Asian and Low-Resource Language Information Processing, 23(7).

Lalramhluna, Robert, Lalthangmawii, and R. Das. 2023a. Mizo News Classification Using Machine Learning Techniques. In Proceedings of the Third International Conference on Frontiers in Computing and Systems (FICTA 2022). Springer.

Lalramhluna, Robert, et al. 2023b. An Approach to Mizo Language News Classification Using Machine Learning. In Proceedings of the Fourth International Conference on Frontiers in Computing and Systems (FICTA 2023). Springer.

Lalrempuii, Candy. 2023. LUS: Mizo Monolingual Corpus. IEEE DataPort. DOI: 10.21227/5601-9c25.

Lalrinmawii, R., Robert Lalramhluna, and R. Gunavathi. 2025. Detecting Abusive Comments in Mizo: A Machine Learning Approach for a Low-Resource Language. In 2025 IEEE International Conference on Advanced Visual and Signal-Based Systems (AVSS).

Lalthangmawii, M., and T. Singh. 2025. Sentiment Analysis of Mizo Using Lexical Features in Low Resource Based Models. Natural Language Processing Journal.

MWirelabs. 2024. Mizo-Language-Corpus-4M. Hugging Face Datasets.

NLLB Team. 2022. No Language Left Behind: Scaling Human-Centered Machine Translation. arXiv:2207.04672.

Nunsanga, Morrel V. L., Partha Pakray, C. Lallawmsanga, and L. Lolit Kumar Singh. 2021. Part-Of-Speech Tagging for Mizo Language Using Conditional Random Field. Computacion y Sistemas.

Nyalang, Badal. 2026. Beyond Multilinguality: Typological Limitations in Multilingual Models for Meitei Language. In Proceedings of the 8th Workshop on Research in Computational Linguistic Typology and Multilingual NLP (SIGTYP).

Pathak, Amarnath, and Partha Pakray. 2019. English-Mizo Machine Translation Using Neural and Statistical Approaches. Neural Computing and Applications.

Pezeshkpour, Pouya, and Estevam Hruschka. 2024. Large Language Models Sensitivity to the Order of Options in Multiple-Choice Questions. In Findings of the Association for Computational Linguistics: NAACL 2024.

Popovic, Maja. 2015. chrF: Character n-gram F-score for Automatic MT Evaluation. In Proceedings of the Tenth Workshop on Statistical Machine Translation, pages 392 to 395.

Popovic, Maja. 2017. chrF++: Words Helping Character n-grams. In Proceedings of the Second Conference on Machine Translation.

Shi, Weijia, Anirudh Ajith, Mengzhou Xia, Yangsibo Huang, Daogao Liu, Terra Blevins, Danqi Chen, and Luke Zettlemoyer. 2023. Detecting Pretraining Data from Large Language Models. arXiv:2310.16789.

Singh, Shivalika, Angelika Romanou, Clementine Fourrier, David I. Adelani, Jian Gang Ngui, Daniel Vila-Suero, Peerat Limkonchotiwat, Kelly Marchisio, Wei Qi Leong, Yosephine Susanto, et al. 2024. Global MMLU: Understanding and Addressing Cultural and Linguistic Biases in Multilingual Evaluation. arXiv:2412.03304.

Thangkhanhau, Haulai, and Jamal Hussain. 2023. Construction of Mizo-English Parallel Corpus for Machine Translation. ACM Transactions on Asian and Low-Resource Language Information Processing. DOI: 10.1145/3610404.

Tjong Kim Sang, Erik F., and Fien De Meulder. 2003. Introduction to the CoNLL-2003 Shared Task: Language-Independent Named Entity Recognition. In Proceedings of the Seventh Conference on Natural Language Learning at HLT-NAACL 2003, pages 142 to 147.

Verma, Sshubam, Mohammed Safi Ur Rahman Khan, Vishwajeet Kumar, Rudra Murthy, and Jaydeep Sen. 2025. MILU: A Multi-task Indic Language Understanding Benchmark. In Proceedings of the 2025 Conference of the North American Chapter of the Association for Computational Linguistics (NAACL).

Wei, Jason, Xuezhi Wang, Dale Schuurmans, Maarten Bosma, Brian Ichter, Fei Xia, Ed Chi, Quoc Le, and Denny Zhou. 2022. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models. In Advances in Neural Information Processing Systems (NeurIPS).

Xu, Cheng, Shuhao Guan, Derek Greene, and M-Tahar Kechadi. 2024. Benchmark Data Contamination of Large Language Models: A Survey. arXiv:2406.04244.

Zhang, Jingyang, Jingwei Sun, Eric Yeats, Yang Ouyang, Martin Kuo, Jianyi Zhang, Hao Yang, and Hai Li. 2025. Min-K%++: Improved Baseline for Detecting Pre-Training Data from Large Language Models. In International Conference on Learning Representations (ICLR).

---

## Appendix A: Model Version Identifiers

Referenced from Section 4.1. Each identifier is the exact string passed to the provider's API for every call reported in this paper; no alias resolves to a different underlying model over time.

| Model (as reported) | Provider identifier | Pinning basis |
|---|---|---|
| GPT 5.4 mini | gpt-5.4-mini-2026-03-17 | Dated snapshot |
| GPT 5.4 | gpt-5.4-2026-03-05 | Dated snapshot |
| Gemini 3.5 Flash | gemini-3.5-flash | Provider alias, confirmed available to the study's API key on 2026-09-08 |
| Gemma 4 31B | gemma4:31b-cloud | Provider hosted tag, cloud inference |
| GPT OSS 120B | gpt-oss:120b | Provider hosted tag, confirmed available on 2026-09-09 |
| NLLB-200 (engineered baseline) | facebook/nllb-200-3.3B | Fixed open weight release |
