"""Upload the MizoEval release to a PRIVATE Hugging Face dataset repo.

Usage: python release/upload_hf.py OWNER/MizoEval [--dry-run]
Flip to public later with: python release/upload_hf.py OWNER/MizoEval --publish
"""
import sys, pathlib
from huggingface_hub import HfApi

repo = sys.argv[1]
dry = "--dry-run" in sys.argv
publish = "--publish" in sys.argv
root = pathlib.Path(__file__).resolve().parent.parent
proc = root / "data" / "processed"

def folder(name):
    if "-keyword-" in name: return "keyword"
    if "-ner-" in name: return "ner"
    if "-mcq-" in name: return "mcq"
    if "-mt-" in name: return "mt"
    if "-sentiment-" in name: return "sentiment"
    return None

files = {"README.md": root / "release" / "DATASET_CARD.md",
         "REPAIR_REPORT.md": proc / "REPAIR_REPORT.md"}
for p in sorted(proc.iterdir()):
    f = folder(p.name)
    if f and p.suffix in (".jsonl", ".conll"):
        files[f + "/" + p.name] = p

api = HfApi()
if publish:
    api.update_repo_settings(repo, repo_type="dataset", private=False)
    print("now public:", repo); sys.exit()
for dst, src in files.items():
    print(("would upload " if dry else "uploading ") + dst)
if not dry:
    api.create_repo(repo, repo_type="dataset", private=True, exist_ok=True)
    for dst, src in files.items():
        api.upload_file(path_or_fileobj=str(src), path_in_repo=dst, repo_id=repo, repo_type="dataset")
    print("done (private):", repo)
