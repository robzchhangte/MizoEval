"""Build release/MizoEval-v1.0.0.zip for the Zenodo upload (same layout as the HF repo)."""
import zipfile, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
proc = root / "data" / "processed"
def folder(n):
    for k, f in (("-keyword-", "keyword"), ("-ner-", "ner"), ("-mcq-", "mcq"), ("-mt-", "mt"), ("-sentiment-", "sentiment")):
        if k in n: return f
out = root / "release" / "MizoEval-v1.0.0.zip"
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.write(root / "release" / "DATASET_CARD.md", "MizoEval/README.md")
    z.write(proc / "REPAIR_REPORT.md", "MizoEval/REPAIR_REPORT.md")
    for p in sorted(proc.iterdir()):
        f = folder(p.name)
        if f and p.suffix in (".jsonl", ".conll"):
            z.write(p, "MizoEval/" + f + "/" + p.name)
print(out, round(out.stat().st_size / 1e6, 1), "MB")
