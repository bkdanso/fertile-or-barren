#!/usr/bin/env bash
# Rebuild the whole benchmark from the public sources, in order.
# Plain-language note: run this one file and every result is rebuilt from scratch.
# Downloading GEOROC takes about 20 minutes the first time; the rest takes about 3 minutes.
set -euo pipefail
cd "$(dirname "$0")"
FINAL="${1:-}"            # pass --final only after the authors' verification
python3 code/01_fetch.py
python3 code/02_intrusions.py
python3 code/03_labels.py
python3 code/04_sample_types.py
python3 code/05_leaderboard.py $FINAL
python3 code/06_figures.py $FINAL
python3 code/07_qa.py
python3 code/08_tables.py
echo "Done. Headline numbers are in paper/stats.json; checks in data/processed/qa_report.txt."
