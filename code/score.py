#!/usr/bin/env python3
"""score.py - the public scoring program for the Fertile or Barren benchmark.

Plain-language note: give this program a file with one score per sample (higher =
"more likely to come from an ore-bearing intrusion") and it tells you how well
those scores separate fertile from barren intrusions, for every sample type. It is
the same program that produces the leaderboard, so anyone's method is graded
exactly the same way.

Usage:
  python code/score.py --submission my_scores.csv [--benchmark data/processed/benchmark_samples.csv]
                       [--split all|test] [--out results.json]

Submission format: CSV with columns UNIQUE_ID,score. Missing or blank scores mean
"this method cannot score this sample"; they lower coverage but are not penalised
in the AUC. Methods with fitted parameters (anything trained on this benchmark)
must be reported with --split test.

Metric (see docs/SCORING.md):
  * Classes: intrusion label FERTILE (positive) vs BARREN (negative); WEAK excluded.
  * AUC_w: area under the ROC curve with each sample weighted 1/(samples of its
    intrusion in the stratum), so every intrusion counts equally however many
    samples it has. 0.5 = no skill, 1.0 = perfect, <0.5 = works backwards.
  * 95% CI: 2,000 bootstrap resamples of intrusions within each class (seed 20270801).
  * AUC_intrusion: AUC on the per-intrusion median score.
  * A stratum needs >= 5 fertile and >= 5 barren intrusions with scores, else it is
    reported as insufficient.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_BENCH = os.path.join(ROOT, "data", "processed", "benchmark_samples.csv")
STRATA = {
    "ALL": None,
    "LIQUID_PROXY": ["CHILLED_MARGIN", "FINE_GRAINED_DIKE_SILL"],
    "CUMULATE": ["CUMULATE"],
    "ALTERED": ["ALTERED"],
    "UNRESOLVED": ["UNRESOLVED"],
}
MIN_INTRUSIONS = 5
N_BOOT = 2000
SEED = 20270801


def weighted_auc(y, s, w):
    """ROC AUC with sample weights; tied scores count half. y in {0,1}."""
    y, s, w = np.asarray(y), np.asarray(s, dtype=float), np.asarray(w, dtype=float)
    _, inv = np.unique(s, return_inverse=True)
    P = np.bincount(inv, weights=w * (y == 1))
    N = np.bincount(inv, weights=w * (y == 0))
    below = np.cumsum(N) - N
    tp, tn = P.sum(), N.sum()
    return float((P * (below + 0.5 * N)).sum() / (tp * tn)) if tp > 0 and tn > 0 else np.nan


def score_stratum(df, rng):
    df = df.dropna(subset=["score"])
    fert = np.array(sorted(df.loc[df.y == 1, "intrusion_key"].unique()))
    barr = np.array(sorted(df.loc[df.y == 0, "intrusion_key"].unique()))
    res = {"n_samples": int(len(df)), "n_fertile_intrusions": int(len(fert)),
           "n_barren_intrusions": int(len(barr))}
    if len(fert) < MIN_INTRUSIONS or len(barr) < MIN_INTRUSIONS:
        res["status"] = "insufficient"
        return res
    w = 1.0 / df.groupby("intrusion_key")["score"].transform("size").values
    res["auc_w"] = weighted_auc(df.y.values, df.score.values, w)
    med = df.groupby("intrusion_key").agg(score=("score", "median"), y=("y", "first"))
    res["auc_intrusion"] = weighted_auc(med.y.values, med.score.values, np.ones(len(med)))
    groups = {k: (g.score.values, g.y.values) for k, g in df.groupby("intrusion_key")}
    boots = np.empty(N_BOOT)
    for i in range(N_BOOT):
        pick = np.concatenate([rng.choice(fert, len(fert)), rng.choice(barr, len(barr))])
        ss = np.concatenate([groups[k][0] for k in pick])
        yy = np.concatenate([groups[k][1] for k in pick])
        ww = np.concatenate([np.full(len(groups[k][0]), 1.0 / len(groups[k][0])) for k in pick])
        boots[i] = weighted_auc(yy, ss, ww)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    res.update(ci_low=float(lo), ci_high=float(hi), status="ok")
    return res


def evaluate(bench, sub, split="all", barren_conf=None):
    b = bench[bench["label"].isin(["FERTILE", "BARREN"])].copy()
    if split == "test":
        b = b[b["split"] == "test"]
    if barren_conf:
        b = b[(b["label"] == "FERTILE") | b["label_confidence"].isin(barren_conf)]
    b["y"] = (b["label"] == "FERTILE").astype(int)
    b = b.merge(sub[["UNIQUE_ID", "score"]], on="UNIQUE_ID", how="left")
    out = {}
    for name, types in STRATA.items():
        df = b if types is None else b[b["sample_type"].isin(types)]
        rng = np.random.default_rng(SEED)
        r = score_stratum(df, rng)
        r["coverage"] = float(df["score"].notna().mean()) if len(df) else 0.0
        out[name] = r
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submission", required=True)
    ap.add_argument("--benchmark", default=DEFAULT_BENCH)
    ap.add_argument("--split", choices=["all", "test"], default="all")
    ap.add_argument("--out")
    a = ap.parse_args()
    bench = pd.read_csv(a.benchmark, low_memory=False)
    sub = pd.read_csv(a.submission)
    sub["score"] = pd.to_numeric(sub["score"], errors="coerce").replace([np.inf, -np.inf], np.nan)
    res = evaluate(bench, sub, a.split)
    txt = json.dumps(res, indent=2)
    print(txt)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt)


if __name__ == "__main__":
    main()
