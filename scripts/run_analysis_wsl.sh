#!/usr/bin/env bash
# Run MizoEval's analysis/tables module from WSL, where background Python
# processes aren't subject to the Windows-side Bash-tool memory-pressure
# reaper that kept killing the same job when run from the Windows side.
#
# The MT contamination table is the slow step (1000-resample bootstrap chrF
# over every model x direction x regime x stratum combination); tables.py
# now parallelizes that across all available CPU cores via
# ProcessPoolExecutor, so this should finish in a few minutes rather than
# 45+.
#
# Usage (from a WSL shell):
#   bash /mnt/c/Users/Robz/ws/MizoEval/scripts/run_analysis_wsl.sh
#
# Output lands in results/tables/ inside the repo, which is the same
# directory tree on both the WSL and Windows sides (WSL sees the Windows
# filesystem under /mnt/c/...), so nothing needs to be copied back manually.

set -euo pipefail

REPO_DIR="/mnt/c/Users/Robz/ws/MizoEval"
# Deliberately NOT under /mnt/c: a venv created on the Windows-mounted DrvFs
# filesystem can silently fail to create the symlinks it needs (NTFS via
# WSL's 9p protocol doesn't support them the way ext4 does), leaving a
# directory with no bin/activate. Native WSL filesystem avoids that and is
# faster I/O besides -- only the repo/data need to live on the Windows side.
VENV_DIR="$HOME/.venvs/mizoeval-analysis"

cd "$REPO_DIR"

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found in this WSL distro -- install it first:" >&2
    echo "  sudo apt update && sudo apt install -y python3 python3-venv python3-pip" >&2
    exit 1
fi

if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "creating venv at $VENV_DIR"
    rm -rf "$VENV_DIR"  # clear out any earlier partial/broken attempt
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "installing/upgrading dependencies (only downloads what's missing)"
pip install --quiet --upgrade pip
pip install --quiet pandas numpy scipy scikit-learn seqeval sacrebleu tabulate

echo
echo "running analysis with $(nproc) CPU cores available"
PYTHONPATH=src python3 -m mizoeval.analysis.tables

echo
echo "done -- results/tables/ now has:"
ls -la results/tables/
