# Zenodo form values

- DOI reserved: https://doi.org/10.5281/zenodo.23022114 (do not click Publish until the paper is accepted; the reserved DOI already resolves once you do)

- Resource type: Dataset
- Title: MizoEval: A Multi Task Benchmark for Mizo with a Contamination Aware Machine Translation Protocol
- Authors (Family, Given; affiliation):
  1. Lalramhluna, Robert; National Institute of Technology Mizoram
  2. Dash, Sandeep Kumar; National Institute of Technology Mizoram
  3. Pakray, Partha; National Institute of Technology Silchar
- Version: 1.0.0
- Publication date: date of public release
- License: Creative Commons Attribution 4.0 International
- Keywords: Mizo; low resource languages; large language model evaluation; benchmark; machine translation; data contamination; named entity recognition; sentiment analysis
- Languages: lus, eng
- Related works: "is supplement to" -> https://huggingface.co/datasets/robzchhangte/MizoEval (URL); "is supplement to" -> https://github.com/robzchhangte/MizoEval (URL); add the paper DOI when available
- Software > Repository URL: https://github.com/robzchhangte/MizoEval
- Files: release/MizoEval-v1.0.0.zip

## Description (paste)

MizoEval is a four task benchmark for evaluating large language models on Mizo (ISO 639-3: lus), a Tibeto Burman language of Mizoram, northeast India. The tasks are regional knowledge multiple choice questions, sentiment classification, named entity recognition with a separate keyword identification layer, and bidirectional English Mizo translation stratified by register (scripture, other religious text, secular).

All tasks were assembled from publicly available text and audited and repaired before release: duplicate and conflicting MCQ items removed or quarantined, the keyword layer separated from entity tags, NER splits made document disjoint, and the translation set labelled by register to support contamination aware evaluation. Full before and after counts are in REPAIR_REPORT.md; per task sources and terms are in README.md.

Licensing: the CC-BY-4.0 licence applies to the authors' compilation, annotations, repair and stratification labels. Underlying source texts remain with their respective rights holders: MCQ questions from the Mizoram Public Service Commission (https://mpsc.mizoram.gov.in/); NER text from the Mizo NER Datasets on India Data, used under the India Data for NLP Data User Agreement; sentiment text from hillbyte/mizo-sentiment (MIT); English Mizo translation pairs from publicly available parallel text. Rights holders who wish text removed or re-attributed can contact the corresponding author (dt21cs003@nitmz.ac.in).

Also available at https://huggingface.co/datasets/robzchhangte/MizoEval. Code: MizoEval data repair and evaluation harness (GitHub, linked on release).
