# Devil's Advocate Report

## Manuscript Information
- **Title**: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- **Review Round**: 1

---

## Strongest Counter-Argument

The paper's central claim is that the scripture-versus-secular chrF gap reflects pretraining memorization of freely available religious text, not genuine translation ability. But the paper's own evidence, read skeptically, supports an equally plausible alternative: scripture and religious register text is simply an easier translation genre, independent of whether any specific test item was memorized.

The strongest piece of evidence for this alternative is one the paper presents as corroboration for its own thesis. NLLB-200, a supervised multilingual MT model, shows a scripture-secular gap (15.2 mz-to-en, 11.7 en-to-mz) comparable in size to GPT 5.4's gap (15.3/12.0), a general-purpose LLM. Section 6 reads this as support: "any system trained on commonly available parallel data in which scripture text is heavily represented will tend to show inflated scores on that register... whether that system acquired the pattern through raw text pretraining or through direct exposure to near identical sentence pairs during supervised training." This sentence quietly redefines "contamination" to include ordinary supervised training on in-domain data, which is not memorization in the sense the paper's introduction and abstract use the word; it is simply a model doing better on a register it saw more of during ordinary training, which is unremarkable and true of essentially every MT system for every register imbalance that has ever existed. If a bilingual dictionary app performed better on cooking vocabulary because its training corpus had more cooking sentences, no one would call that contamination.

This matters because the verse-completion probe, the paper's one piece of genuinely causal evidence (a model completing withheld text it was never shown at test time), was run on only three of the five LLMs and not on NLLB at all. For the two unprobed LLMs and for NLLB, the paper's evidence for "contamination" rather than "genre is easier" is the score gap alone, which cannot distinguish the two explanations without a length- or repetition-matched control the paper does not report. The paper's title and abstract claim a general contamination-aware protocol; what has actually been validated causally is a contamination finding for three specific models, generalized in the prose to cover six systems on the strength of a pattern that has at least one alternative reading the paper does not rule out.

---

## Issue List

### CRITICAL

**[C1] Section 5.4 presents the paper's only causal evidence with no numbers, making it unverifiable as written.**
Dimension: Evidence sufficiency. Location: Section 5.4, all three paragraphs.
The chrF deltas, verbatim-match rates, and confidence intervals that would let a reader judge the strength of the memorization claim (e.g., 57% near-verbatim reproduction of held-out scripture for one model, versus 0.007 for another) exist in the underlying probe output and are absent from the manuscript. A claim this important should not be unfalsifiable as printed.

**[C2] Sections 3.4 and 7 directly contradict each other on whether the 27.0% secular-share estimate is an upper or lower bound, and Section 7 claims a validation occurred that Section 5 does not report and Section 3.4 describes as pending.**
Dimension: Argument coherence. Location: Section 3.4 vs. Section 7.
This is a factual claim asserted both ways in the same document. Whichever direction is correct, one of the two sections is wrong, and the paper cannot currently tell a reader which.

### MAJOR

**[M1] The "any system trained on in-domain data will show this pattern" framing in Section 6 uses NLLB's result to blur the distinction between memorization and ordinary register-frequency effects, weakening rather than strengthening the causal claim on inspection.**
Dimension: Logical validity. Location: Section 6, paragraph 1.
See Strongest Counter-Argument above. The paper should either show the NLLB gap is a distinct, separately interesting finding about supervised training, and not use it as corroboration for LLM-specific memorization, or add a control that rules out genre difficulty as the explanation for both.

**[M2] Overgeneralization from three probed models to "every evaluated model" in the abstract.**
Dimension: Scope of claim. Location: Abstract, sentence 4; Conclusion, sentence 2.
The abstract's register-gap claim ("every evaluated model's secular stratum score sits well below its scripture stratum score") is true of the score comparison in Table 3, which does cover five of six systems (all but GPT OSS 120B, excluded for a different reason). But the *causal* validation via probes covers three of five LLMs only, and the Conclusion's "validated by three independent probes" reads as validating the whole finding, when one of the three probes (temporal) is explicitly reported in Section 5.4 as not supporting the claim. The paper is honest about this in the body text; the abstract and conclusion are not equally careful.

**[M3] Cherry-picking risk in probe model selection is not addressed.**
Dimension: Selection bias. Location: Section 4.3, first sentence ("Three probes test directly whether a model's performance...").
The paper does not state the basis on which gemini-3.5-flash, gpt-5.4-mini, and gemma4-31b (rather than, say, gpt-5.4 and gpt-oss-120b) were selected for probing. If this selection happened after the register-gap results were already known (Table 3 shows the largest gaps belong to gemini-3.5-flash and gpt-5.4, but only gemini-3.5-flash and gpt-5.4-mini were probed, not gpt-5.4), a reader is entitled to ask whether the probe subset was chosen to build the strongest possible case rather than an unbiased one. This may well have an innocent, resource-driven explanation (API cost, availability), but the paper should say so explicitly rather than leaving the question open.

---

## Ignored Alternative Explanations / Paths

1. **Genre difficulty independent of memorization** (see Strongest Counter-Argument). Not tested via a length/repetition control.
2. **Translation memory effects distinct from LLM pretraining memorization.** NLLB and any web-crawled LLM pretraining corpus may both have ingested near-identical OPUS-style religious parallel corpora as *aligned sentence pairs* rather than raw monolingual text; this is a different contamination mechanism (direct parallel-data exposure) from the "verbatim monolingual memorization, then internal alignment" mechanism the verse-completion probe actually tests. The paper does not distinguish these two contamination pathways, even though they would call for different mitigations.
3. **Register-specific translation consistency effects.** Scripture translations, especially KJV-style English and its Mizo counterpart, are highly standardized across the entire text (consistent vocabulary choices for recurring terms like "Lord," "unto," "thee"), which could raise chrF scores through internal consistency of the reference itself, independent of what the model does. This was not tested.

---

## Missing Stakeholder Perspectives

- **The native Mizo speakers whose planned validation the paper leans on rhetorically (Section 7) before it has occurred** (see R3's report, W1, for the same finding from the ethics angle).
- **Future users of the released register classifier**, who will need the paper to state clearly and correctly which direction its known bias runs (upper vs. lower bound), since this affects how they should interpret the secular stratum as "the honest number" the paper's own contamination report calls it.

---

## Observations (Non-Defects)

- The decision to quarantine rather than resolve the 137/283 conflicting MCQ items is a genuinely careful choice and is not undermined by anything in this report.
- The paper's own contamination report (not part of the manuscript, but part of the underlying project) is considerably more careful about scoping model-specific findings than the manuscript prose that summarizes it; the manuscript's Section 5.4 undersells the rigor of the underlying work rather than misrepresenting it in the other direction. This is a data-presentation problem, not a data-quality problem.
