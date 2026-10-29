#!/usr/bin/env python3
"""07_qa.py - quality checks; writes data/processed/qa_report.txt.

Plain-language note: this script counts, cross-checks and spot-checks the benchmark so
mistakes show up before anyone relies on it. Read the report it writes
(data/processed/qa_report.txt) before trusting any number; the verification
checklist walks you through the spot checks it lists.
"""
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROC = os.path.join(ROOT, "data", "processed")
INTERIM = os.path.join(ROOT, "data", "interim")
SPOT = ["BUSHVELD", "STILLWATER", "DULUTH", "NORILSK", "PALISADES", "SKAERGAARD"]


def main():
    out = []
    w = out.append
    b = pd.read_csv(os.path.join(PROC, "benchmark_samples.csv"), low_memory=False)
    intr = pd.read_csv(os.path.join(PROC, "intrusions.csv"))
    l2, l3, l4 = (json.load(open(os.path.join(INTERIM, f))) for f in ["02_log.json", "03_log.json", "04_log.json"])
    w("FERTILE OR BARREN - QA REPORT\n" + "=" * 40)
    w("\n1. ROW COUNTS AT EACH STAGE")
    for k, v in l2.items():
        if isinstance(v, (int, float)):
            w(f"   {k:45s} {v:>9,}")
    w(f"   {'benchmark samples (after labels, exclusions)':45s} {len(b):>9,}")
    w(f"   {'benchmark intrusions':45s} {b.intrusion_key.nunique():>9,}")
    w(f"   Completeness: {l2['rocktypes_ids_missing_from_settings_union']} of {l2['rocktypes_plutonic_ids']:,} plutonic "
      "samples in the Rock Types compilation are absent from the tectonic-setting union "
      f"({100 * l2['rocktypes_ids_missing_from_settings_union'] / l2['rocktypes_plutonic_ids']:.2f}%).")

    w("\n2. LABELS")
    w("   " + json.dumps(l3["label_counts"]))
    w(f"   curated labels used: {l3['curated_used']}; curated vs automatic disagreements: "
      f"{l3['curated_vs_auto_disagreements']} (listed in docs/review/label_review.csv)")
    w(f"   MRDS magmatic Ni/PGE records used: {l3['mrds_magmatic_ni_pge_records']}; "
      f"USGS critical-mineral Ni-Cu-PGE/PGE deposits: {l3['usgs_cm_ni_pge_deposits']}")
    w("   BARREN by confidence: " + json.dumps(
        intr[intr.label == "BARREN"].confidence.value_counts().to_dict()))

    w("\n3. SAMPLE TYPES")
    w("   " + json.dumps(l4["samples_by_type"]))
    w("   rule strength: " + json.dumps(l4["rule_strength"]))

    w("\n4. INTEGRITY CHECKS")
    checks = {
        "UNIQUE_ID is unique": b.UNIQUE_ID.is_unique,
        "every sample has a label": b.label.notna().all(),
        "no EXCLUDE labels in benchmark": not (b.label == "EXCLUDE").any(),
        "every intrusion is in exactly one split": b.groupby("intrusion_key").split.nunique().max() == 1,
        "every intrusion has >= 5 samples": b.intrusion_key.value_counts().min() >= 5,
    }
    pm = l2.get("curated_pattern_matches", {})
    checks["every curated location pattern matched samples " + json.dumps(pm)] = bool(pm) and min(pm.values()) > 0
    cur = pd.read_csv(os.path.join(ROOT, "data", "curated", "intrusion_labels_curated.csv"))
    checks["curated file parses with intrusion_key as first column"] = cur.columns[0] == "intrusion_key"
    for c in ["CU(PPM)", "NI(PPM)", "PD(PPM)", "MGO(WT%)", "S(PPM)"]:
        v = pd.to_numeric(b[c], errors="coerce")
        checks[f"{c} has no negative values"] = not (v < 0).any()
    pd_ = pd.to_numeric(b["PD(PPM)"], errors="coerce")
    checks["PD(PPM) <= 100 (no ppb mis-entered as ppm above ore grade)"] = not (pd_ > 100).any()
    mg = pd.to_numeric(b["MGO(WT%)"], errors="coerce")
    checks["MGO(WT%) <= 55"] = not (mg > 55).any()
    for k, v in checks.items():
        w(f"   [{'PASS' if v else 'FAIL'}] {k}")
    low_mg = b[mg < 0.5]
    w(f"   MgO guard: {l4.get('mgo_values_blanked_non_anorthosite')} MgO values below 0.5 wt% in non-anorthosite rocks "
      "were blanked as source errors (docs/review/mgo_blanked.csv); "
      f"{len(low_mg)} remaining samples with MgO < 0.5 wt% are anorthosites (confirmed by the authors).")
    n_hi_pd = int((pd_ > 10).sum())
    w(f"   PGE units: {l4.get('pge_unit_corrected_samples')} samples from references [23290] and [24352] converted "
      "from ppb to ppm (author-confirmed, data/curated/pge_unit_corrections.csv); references still reporting "
      f"Pt or Pd > 1,000 ppm after correction: {l4.get('pge_unit_flag_references')} "
      f"({l4.get('pge_values_blanked_samples')} samples blanked)")
    w(f"   note: {n_hi_pd} samples have Pd > 10 ppm (ore-grade reef or sulfide samples); "
      "listed for author awareness, kept in the benchmark.")

    w("\n5. SCORING PROGRAM SELF-TEST")
    sub = os.path.join(ROOT, "leaderboard", "submissions", "pd_ir.csv")
    r = subprocess.run([sys.executable, os.path.join(ROOT, "code", "score.py"), "--submission", sub],
                       capture_output=True, text=True, check=True)
    cli = json.loads(r.stdout)["ALL"]["auc_w"]
    lb = pd.read_csv(os.path.join(ROOT, "leaderboard", "results.csv")).set_index("index").loc["pd_ir", "ALL_auc_w"]
    w(f"   [{'PASS' if abs(cli - lb) < 1e-9 else 'FAIL'}] score.py run from the command line reproduces the "
      f"leaderboard value for pd_ir: {cli:.4f} vs {lb:.4f}")
    rnd = pd.DataFrame({"UNIQUE_ID": b.UNIQUE_ID, "score": np.random.default_rng(1).random(len(b))})
    rnd_path = os.path.join(INTERIM, "random_submission.csv")
    rnd.to_csv(rnd_path, index=False)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "code", "score.py"), "--submission", rnd_path],
                       capture_output=True, text=True, check=True)
    ra = json.loads(r.stdout)["ALL"]
    w(f"   [{'PASS' if ra['ci_low'] < 0.5 < ra['ci_high'] else 'FAIL'}] a random-number 'index' scores "
      f"{ra['auc_w']:.3f} ({ra['ci_low']:.3f}-{ra['ci_high']:.3f}); its interval contains 0.5 as it should")

    w("\n6. NAMED SPOT CHECKS (compare by hand with the GEOROC source file, see docs/VERIFY_CHECKLIST.md)")
    cols = ["UNIQUE_ID", "georoc_file", "SAMPLE NAME", "rock_name", "CU(PPM)", "NI(PPM)", "PD(PPM)", "MGO(WT%)",
            "label", "sample_type"]
    for k in SPOT:
        s = b[b.intrusion_key == k]
        if not len(s):
            w(f"   {k}: not in benchmark")
            continue
        has = s[s["CU(PPM)"].notna()]
        row = (has if len(has) else s).sort_values("UNIQUE_ID").iloc[0]
        w(f"   {k}: " + "; ".join(f"{c}={row[c]}" for c in cols if c in row.index))
    rep = "\n".join(out) + "\n"
    with open(os.path.join(PROC, "qa_report.txt"), "w") as f:
        f.write(rep)
    print(rep)
    if "[FAIL]" in rep:
        sys.exit("QA failures present")


if __name__ == "__main__":
    main()
