#!/usr/bin/env python3
"""05_leaderboard.py - score every published index and write the leaderboard.

Plain-language note: this script calculates each fertility index for every sample,
saves each as a "submission" file (exactly the format an outside researcher would
send in), grades each one with the public scoring program code/score.py, and writes
the results table (leaderboard/LEADERBOARD.md and leaderboard/results.csv), plus the
QA report and the stats file every number in the paper is taken from.
"""
import datetime
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "code"))
from indices import DISPLAY, INDICES, compute_all  # noqa: E402
from score import STRATA, evaluate  # noqa: E402

PROC = os.path.join(ROOT, "data", "processed")
LB = os.path.join(ROOT, "leaderboard")
SUBS = os.path.join(LB, "submissions")
PAPER = os.path.join(ROOT, "paper")
INTERIM = os.path.join(ROOT, "data", "interim")
os.makedirs(SUBS, exist_ok=True)
os.makedirs(PAPER, exist_ok=True)
FINAL = "--final" in sys.argv


def fmt(r):
    if r.get("status") != "ok":
        return "insufficient"
    return f"{r['auc_w']:.2f} ({r['ci_low']:.2f}-{r['ci_high']:.2f})"


def main():
    bench = pd.read_csv(os.path.join(PROC, "benchmark_samples.csv"), low_memory=False)
    scores = compute_all(bench)
    rows, full = [], {}
    for ix in INDICES:
        sub = pd.DataFrame({"UNIQUE_ID": bench["UNIQUE_ID"], "score": scores[ix["id"]]})
        sub.to_csv(os.path.join(SUBS, f"{ix['id']}.csv"), index=False)
        res_all = evaluate(bench, sub, "all")
        res_sens = evaluate(bench, sub, "all", barren_conf=["MEDIUM", "HIGH"])
        res_test = evaluate(bench, sub, "test")
        full[ix["id"]] = {"all": res_all, "barren_medium_high_only": res_sens, "test": res_test}
        row = {"index": ix["id"], "family": ix["family"], "needs": "+".join(ix["needs"]),
               "hypothesis": ix["hypothesis"], "reference": ix["ref"]}
        for st in STRATA:
            r = res_all[st]
            row[f"{st}_auc_w"] = r.get("auc_w", np.nan)
            row[f"{st}_ci_low"] = r.get("ci_low", np.nan)
            row[f"{st}_ci_high"] = r.get("ci_high", np.nan)
            row[f"{st}_auc_intrusion"] = r.get("auc_intrusion", np.nan)
            row[f"{st}_n_fert"] = r["n_fertile_intrusions"]
            row[f"{st}_n_barr"] = r["n_barren_intrusions"]
            row[f"{st}_n_samples"] = r["n_samples"]
            row[f"{st}_coverage"] = r["coverage"]
        row["ALL_auc_w_sensitivity"] = res_sens["ALL"].get("auc_w", np.nan)
        row["ALL_auc_w_test"] = res_test["ALL"].get("auc_w", np.nan)
        rows.append(row)
        print(f"{ix['id']:14s} ALL {fmt(res_all['ALL'])}  CUM {fmt(res_all['CUMULATE'])}  LIQ {fmt(res_all['LIQUID_PROXY'])}")
    res = pd.DataFrame(rows).sort_values("ALL_auc_w", ascending=False, na_position="last")
    res.to_csv(os.path.join(LB, "results.csv"), index=False)
    with open(os.path.join(LB, "results_full.json"), "w") as f:
        json.dump(full, f, indent=2)

    # Leaderboard markdown
    stamp = "" if FINAL else "> **DRAFT: not yet verified by the authors. Do not cite.**\n\n"
    L = [f"# Fertile or Barren leaderboard\n\n{stamp}"
         "Score = intrusion-weighted ROC AUC for separating FERTILE from BARREN intrusions "
         "(0.5 = coin flip, 1.0 = perfect, below 0.5 = the index points the wrong way). "
         "95% confidence interval from 2,000 bootstrap resamples of intrusions in brackets. "
         "\"insufficient\" = fewer than 5 fertile or 5 barren intrusions have the elements the index needs. "
         "See docs/SCORING.md. * = exploratory index (direction set by the authors, not a published test).\n",
         "| Rank | Index | Family | All samples | Cumulates | Chilled margins + fine-grained dikes/sills | Altered | Unresolved type | Fertile / barren intrusions (all) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for i, (_, r) in enumerate(res.iterrows(), 1):
        f = full[r["index"]]["all"]
        L.append(f"| {i} | {DISPLAY[r['index']]} (`{r['index']}`) | {r['family']} | {fmt(f['ALL'])} | {fmt(f['CUMULATE'])} | "
                 f"{fmt(f['LIQUID_PROXY'])} | {fmt(f['ALTERED'])} | {fmt(f['UNRESOLVED'])} | "
                 f"{f['ALL']['n_fertile_intrusions']} / {f['ALL']['n_barren_intrusions']} |")
    L.append("\n## Submit your method\n\nSee [SUBMITTING.md](SUBMITTING.md). Methods fitted on this benchmark "
             "are scored on the held-out test intrusions only (`--split test`).\n")
    L.append(f"\n*Generated {datetime.date.today().isoformat()} by code/05_leaderboard.py from "
             "data/processed/benchmark_samples.csv.*\n")
    with open(os.path.join(LB, "LEADERBOARD.md"), "w") as f:
        f.write("\n".join(L))

    # Stats file: every number quoted in documents comes from here.
    log2 = json.load(open(os.path.join(INTERIM, "02_log.json")))
    log3 = json.load(open(os.path.join(INTERIM, "03_log.json")))
    log4 = json.load(open(os.path.join(INTERIM, "04_log.json")))
    lab = bench.drop_duplicates("intrusion_key")
    scored = bench[bench["label"].isin(["FERTILE", "BARREN"])]
    best = res.iloc[0]
    ok = res[res["ALL_auc_w"].notna()]
    stats = {
        "generated": datetime.date.today().isoformat(),
        "draft": not FINAL,
        "georoc_unique_samples": log2["unique_samples_in_georoc_union"],
        "georoc_rows_read": log2["rows_read"],
        "mafic_um_plutonic_samples": log2["mafic_ultramafic_plutonic_samples"],
        "samples_without_intrusion_name": log2["samples_without_intrusion_name"],
        "samples_with_intrusion": log2["samples_kept"],
        "intrusions_any_size": log2["intrusions"],
        "intrusions_min5": log3["intrusions_with_min_samples"],
        "intrusions_excluded_curated": int(log3["label_counts"].get("EXCLUDE", 0)),
        "benchmark_samples": int(len(bench)),
        "benchmark_intrusions": int(bench["intrusion_key"].nunique()),
        "fertile_intrusions": int((lab["label"] == "FERTILE").sum()),
        "weak_intrusions": int((lab["label"] == "WEAK").sum()),
        "barren_intrusions": int((lab["label"] == "BARREN").sum()),
        "barren_low_conf_intrusions": int(((lab["label"] == "BARREN") & (lab["label_confidence"] == "LOW")).sum()),
        "fertile_samples": int((bench["label"] == "FERTILE").sum()),
        "barren_samples": int((bench["label"] == "BARREN").sum()),
        "weak_samples": int((bench["label"] == "WEAK").sum()),
        "samples_by_type": bench["sample_type"].value_counts().to_dict(),
        "scored_samples_by_type_label": scored.groupby(["sample_type", "label"]).size().unstack(fill_value=0).to_dict(),
        "fertile_intrusions_with_liquid_proxy": int(scored[(scored.label == "FERTILE") & scored.sample_type.isin(
            ["CHILLED_MARGIN", "FINE_GRAINED_DIKE_SILL"])]["intrusion_key"].nunique()),
        "fertile_intrusions_with_chilled_margin": int(scored[(scored.label == "FERTILE") &
                                                             (scored.sample_type == "CHILLED_MARGIN")]["intrusion_key"].nunique()),
        "mrds_records": log3["mrds_magmatic_ni_pge_records"],
        "curated_vs_auto_disagreements": log3["curated_vs_auto_disagreements"],
        "n_indices": len(INDICES),
        "n_indices_scored_all": int(len(ok)),
        "best_index": best["index"], "best_auc_w": round(float(best["ALL_auc_w"]), 3),
        "best_ci_low": round(float(best["ALL_ci_low"]), 3), "best_ci_high": round(float(best["ALL_ci_high"]), 3),
        "n_indices_ci_above_half": int((ok["ALL_ci_low"] > 0.5).sum()),
        "n_indices_ci_below_half": int((ok["ALL_ci_high"] < 0.5).sum()),
        "results": {r["index"]: {k: (None if pd.isna(v) else (round(v, 3) if isinstance(v, float) else v))
                                 for k, v in r.items() if k.endswith(("auc_w", "ci_low", "ci_high", "n_fert", "n_barr",
                                                                      "coverage", "sensitivity", "test", "auc_intrusion"))}
                    for _, r in res.iterrows()},
    }
    with open(os.path.join(PAPER, "stats.json"), "w") as f:
        json.dump(stats, f, indent=2, default=str)
    print("stats written; best:", stats["best_index"], stats["best_auc_w"])


if __name__ == "__main__":
    main()
