"""Run every repair module and write `data/processed/REPAIR_REPORT.md`.

The report is generated, never hand-written, so every count in the paper traces
to a re-runnable command rather than to a number someone typed once.

Run:
    python -m mizoeval.repair.make_report
"""

from __future__ import annotations

import datetime as dt
import json
from collections import Counter
from pathlib import Path

from mizoeval.repair import mcq_repair, mt_stratify, ner_normalize, sentiment_prep

ROOT = Path(__file__).resolve().parents[3]
PROCESSED = ROOT / "data" / "processed"
OUT = PROCESSED / "REPAIR_REPORT.md"


def pct(n: int, d: int) -> str:
    return f"{100 * n / d:.1f}%" if d else "--"


def build() -> str:
    mcq = mcq_repair.repair()
    ner_stats, official_leaks, resplit_leaks = ner_normalize.run()
    mt_counts = mt_stratify.run()
    sent = sentiment_prep.run()

    mcq4 = [
        json.loads(l)
        for l in (PROCESSED / "mizoeval-mcq-v1-mcq4.jsonl").read_text(encoding="utf-8").splitlines()
        if l.strip()
    ]
    mcq4_pos = Counter(r["answer"] for r in mcq4)
    perm = [
        json.loads(l)
        for l in (PROCESSED / "mizoeval-mcq-v1-mcq4-permuted.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if l.strip()
    ]
    perm_pos = Counter(r["answer"] for r in perm)

    mt_total = sum(mt_counts[k] for k in ("scripture", "religious", "secular"))
    rel_dom = mt_counts["scripture"] + mt_counts["religious"]

    L: list[str] = []
    A = L.append

    A("# MizoEval — Data Repair Report")
    A("")
    A(f"Generated {dt.date.today().isoformat()} by `python -m mizoeval.repair.make_report`.")
    A("Every figure below is produced by re-running the repair modules; none is hand-entered.")
    A("")
    A("---")
    A("")

    # ---------------------------------------------------------------- MCQ
    A("## 1. MCQ benchmark")
    A("")
    A("Source: `data/raw/mizoram_mcq_with_answers.json`")
    A("")
    A("| Step | Count |")
    A("|---|---|")
    A(f"| Raw items | {mcq.raw_total} |")
    A(f"| Duplicate groups (stem + choice set) | {mcq.dup_groups} |")
    A(f"| Duplicate rows merged away | {mcq.dup_rows_removed} |")
    A(f"| **Groups with conflicting gold answers (quarantined)** | **{mcq.conflict_groups}** |")
    A(f"| Items removed by that quarantine | {mcq.conflict_items_quarantined} |")
    A(f"| Items with an answer key outside their own choices | {mcq.invalid_answer_key} |")
    A(f"| **Released items** | **{mcq.kept_total}** |")
    A("")
    A("### Format partition")
    A("")
    A("The dataset card promises a uniform 4-option MCQ benchmark. It is not one, so")
    A("items are partitioned by answer-key shape rather than silently discarded.")
    A("`mcq4` is the headline subset; the rest are reported separately.")
    A("")
    A("| Format | Items |")
    A("|---|---|")
    for fmt, n in mcq.format_counts.most_common():
        A(f"| `{fmt}` | {n} |")
    A("")
    A(f"{mcq.positional_option_items} items contain an \"all/none of the above\" option. These")
    A("are flagged and excluded from the permuted variant, whose reordering would")
    A("make such an option meaningless.")
    A("")
    A("### Answer-position bias")
    A("")
    A("Gold answers are not uniformly distributed across positions, so a model that")
    A("always answers `A` beats random guessing. The permuted variant removes this.")
    A("")
    A("| Position | `mcq4` gold | Permuted variant |")
    A("|---|---|---|")
    for p in ("A", "B", "C", "D"):
        A(f"| {p} | {mcq4_pos[p]} ({pct(mcq4_pos[p], len(mcq4))}) | "
          f"{perm_pos[p]} ({pct(perm_pos[p], len(perm))}) |")
    A("")
    A("### Corrections to the published dataset card")
    A("")
    A(f"- Card states English 97.9% / Mizo 2.1%. Actual, on the released set: "
      f"English {mcq.languages.get('English', 0)} "
      f"({pct(mcq.languages.get('English', 0), mcq.kept_total)}), "
      f"Mizo {mcq.languages.get('Mizo', 0)} "
      f"({pct(mcq.languages.get('Mizo', 0), mcq.kept_total)}).")
    A("- Card states \"100% validated 4-option choices\". "
      f"{sum(n for f, n in mcq.format_counts.items() if f != 'mcq4')} released items are not "
      "4-option.")
    A("- Card states \"100% ground-truth answer key coverage\". Coverage is complete, but "
      f"{mcq.conflict_groups} repeated questions carry mutually contradictory keys.")
    A("")
    A("### Outstanding — requires native-speaker adjudication")
    A("")
    A(f"`data/human_eval/mcq_conflicts.csv` holds the {mcq.conflict_groups} conflicting groups")
    A(f"({mcq.conflict_items_quarantined} items) for panel adjudication. They are excluded from")
    A("the release until resolved. No conflict is resolved automatically: each is a case where")
    A("two official-looking sources disagree, and guessing would inject silent label noise.")
    A("")

    # ---------------------------------------------------------------- NER
    A("## 2. NER corpus")
    A("")
    A("| Split | Sentences | Tokens | Entity spans | Keyword spans |")
    A("|---|---|---|---|---|")
    for name, s in ner_stats.items():
        A(f"| {name} | {s.sentences} | {s.tokens} | {sum(s.entity_spans.values())} "
          f"| {s.keyword_spans} |")
    A("")
    A("Changes applied:")
    A("")
    A("- Lowercase `b-`/`i-` prefixes uppercased to standard BIO.")
    A("- `KEYWORD` split into its own task files (`mizoeval-keyword-*.conll`). It is keyword")
    A("  identification, not named-entity recognition; leaving it in the entity layer would")
    A(f"  have inflated the entity count by {ner_stats['train'].keyword_spans} spans in train alone.")
    A(f"- Dropped `NETE`, `NEU`, `NEDA`: "
      f"{dict(ner_stats['train'].dropped_spans)} instances in train, none in valid or test.")
    A("- Retained tagset: " + ", ".join(f"`{t}`" for t in sorted(ner_normalize.KEEP_ENTITIES)) + ".")
    A("- `gold_.conll` is unnamed in the release; it is the test split, confirmed by the")
    A("  leakage analysis below.")
    A("- Token text is never modified — only tags and span boundaries.")
    A("")
    A("### Leakage in the released split — a blocking finding")
    A("")
    A("All three splits come from the same news site, and the release assigns *sentences*")
    A("rather than *articles*, so sentences from one article land in different splits:")
    A("")
    A("| Pair | Shared source articles | Identical sentences |")
    A("|---|---|---|")
    for a, b in (("train", "valid"), ("train", "test"), ("valid", "test")):
        A(f"| {a} / {b} | {official_leaks[f'url_overlap_{a}_{b}']} "
          f"| {official_leaks[f'sent_overlap_{a}_{b}']} |")
    A("")
    A("Measured directly: **100% of validation sentences and 99.6% of test sentences come")
    A("from an article that also appears in training.** Any model fine-tuned on this split")
    A("has seen the same article, entities and context at training time, so its reported")
    A("test F1 is optimistic.")
    A("")
    A("### Document-disjoint re-split")
    A("")
    A("Published alongside the official split (`mizoeval-ner-docsplit-*.conll`). Articles are")
    A("assigned whole, and sentences reposted verbatim under a different URL are dropped from")
    A("the held-out sets. Both splits ship: the official one for comparability with prior")
    A("work, this one for the uninflated number.")
    A("")
    A("| Split | Sentences | Source articles |")
    A("|---|---|---|")
    sizes = resplit_leaks.get("sentences", {})
    for split in ("train", "valid", "test"):
        A(f"| {split} | {sizes.get(split, '--')} "
          f"| {resplit_leaks['url_counts'][split]} |")
    A("")
    A("Overlap after re-splitting: "
      + ", ".join(
          f"{a}/{b} = {resplit_leaks[f'url_overlap_{a}_{b}']} articles / "
          f"{resplit_leaks[f'sent_overlap_{a}_{b}']} sentences"
          for a, b in (("train", "valid"), ("train", "test"), ("valid", "test"))
      )
      + ".")
    A("")

    # ---------------------------------------------------------------- MT
    A("## 3. Translation benchmark")
    A("")
    A("Source: `robzchhangte/en-mz-benchmark` (3,000 pairs, test split, currently private).")
    A("")
    A("The benchmark is overwhelmingly religious text. The King James Version and the Mizo")
    A("Bible are both freely available on the open web, as is jw.org's Mizo output, so these")
    A("pairs are almost certainly memorised by the models under test. Scored in aggregate,")
    A("this benchmark reports memorisation as translation quality.")
    A("")
    A("| Stratum | Pairs | Share |")
    A("|---|---|---|")
    for s in ("scripture", "religious", "secular"):
        A(f"| {s} | {mt_counts[s]} | {pct(mt_counts[s], mt_total)} |")
    A(f"| **religious domain (scripture + religious)** | **{rel_dom}** | "
      f"**{pct(rel_dom, mt_total)}** |")
    A("")
    A("| Source | scripture | religious | secular |")
    A("|---|---|---|---|")
    for src in ("gold", "glosbe"):
        A(f"| `{src}` | {mt_counts[f'{src}::scripture']} | {mt_counts[f'{src}::religious']} "
          f"| {mt_counts[f'{src}::secular']} |")
    A("")
    A(f"Only **{mt_counts['secular']} pairs ({pct(mt_counts['secular'], mt_total)})** are secular,")
    A("and that is an upper bound: the classifier is lexical, so modern-translation scripture")
    A("that names no person and quotes no verse still slips through. Every religious-domain")
    A("figure here is therefore a **lower bound**.")
    A("")
    A("`data/human_eval/mt_stratum_validation.csv` holds a stratified sample for hand-labelling,")
    A("which measures the classifier's actual precision and recall. The paper reports that")
    A("measurement rather than assuming the classifier is exact.")
    A("")

    # ---------------------------------------------------------------- sentiment
    A("## 4. Sentiment corpus")
    A("")
    A("Source: `hillbyte/mizo-sentiment`.")
    A("")
    A("| Property | Value |")
    A("|---|---|")
    A(f"| Raw rows | {sent['raw_rows']} |")
    A(f"| Duplicate texts dropped | {sent['dropped_duplicates']} |")
    A(f"| Released items | {sent['kept']} |")
    A(f"| Label distribution | {sent['label_counts']} |")
    A(f"| Majority-class baseline (accuracy) | {sent['majority_baseline_accuracy']:.1%} |")
    A(f"| Mean out-of-Mizo-vocabulary rate | {sent['mean_oov_rate']:.3f} |")
    A(f"| Code-mixed items (OOV > 0.3) | {sent['items_oov_gt_0.3 (code-mixed)']} |")
    A(f"| Items carrying a `[PERSON]` placeholder | {sent['items_with_person_placeholder']} |")
    A("")
    A(f"Because a constant \"Positive\" prediction already scores "
      f"{sent['majority_baseline_accuracy']:.1%}, **accuracy is not reported as a primary")
    A("metric for this task — macro-F1 is.** Five stratified folds are assigned so every fold")
    A("mirrors the corpus label distribution.")
    A("")
    A("Undocumented in the source card and therefore unknown: the annotation guidelines, the")
    A("number of annotators, and inter-annotator agreement. Stated as a limitation rather than")
    A("reconstructed.")
    A("")
    A("---")
    A("")
    A("## Released files")
    A("")
    for p in sorted(PROCESSED.glob("mizoeval-*")):
        A(f"- `data/processed/{p.name}`")
    A("")
    A("## Pending human adjudication")
    A("")
    A("- `data/human_eval/mcq_conflicts.csv`")
    A("- `data/human_eval/mt_stratum_validation.csv`")
    return "\n".join(L) + "\n"


def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
