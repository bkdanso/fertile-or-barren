#!/usr/bin/env python3
"""04_sample_types.py - tag each sample by type and assemble the benchmark table.

Plain-language note: indices are only fair when compared on the same kind of sample.
This script gives every sample one tag, using transparent rules on the information
GEOROC records (rock name, texture, alteration code, location notes, loss on ignition,
MgO). The rules are listed below and in docs/SCORING.md. Each tag also records which
rule fired and whether the rule is a strong or weak one, so the authors can review the
weak ones (docs/review/sample_type_review.csv). It then writes the final benchmark table
data/processed/benchmark_samples.csv and the intrusion table data/processed/intrusions.csv.

Tags, in priority order (first match wins):
  ALTERED                 LOI > 5 wt%, GEOROC alteration code M/E (moderate/extensive),
                          or an alteration word in the rock name (serpentinite, altered, meta-).
  CHILLED_MARGIN          chill/quench/marginal/contact/border words in name, texture or notes.
  CUMULATE                cumulate words or textures; ultramafic or monomineralic cumulate
                          rock names (dunite, pyroxenite, anorthosite, chromitite ...);
                          or MgO > 25 wt% (weak rule).
  FINE_GRAINED_DIKE_SILL  dolerite/diabase/picrite, or a dike/sill unit, with no cumulate sign.
  UNRESOLVED              everything else (mostly gabbros and norites without a texture note).
"""
import json
import os
import re

import numpy as np
import pandas as pd
import warnings
warnings.simplefilter("ignore", pd.errors.PerformanceWarning)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERIM = os.path.join(ROOT, "data", "interim")
PROC = os.path.join(ROOT, "data", "processed")
REVIEW = os.path.join(ROOT, "docs", "review")
os.makedirs(PROC, exist_ok=True)
SEED = 20270801

ALTER_NAME = re.compile(r"SERPENTIN|ALTERED|\bMETA-?|AMPHIBOLITI[SZ]ED|SAUSSURIT|URALITI[SZ]ED|TALC|WEATHERED|RODINGITE")
CHILL = re.compile(r"CHILL|QUENCH|MARGINAL|MARGIN|CONTACT|BORDER|SPINIFEX|APHYRIC")
CUM_TEXT = re.compile(r"CUMUL|ADCUMUL|ORTHOCUMUL|MESOCUMUL|HETERADCUMUL|LAYERED|POIKILITIC")
CUM_ROCK = re.compile(r"DUNITE|PERIDOTITE|PYROXENITE|WEBSTERITE|HARZBURGITE|LHERZOLITE|WEHRLITE|BRONZITITE|"
                      r"ANORTHOSITE|TROCTOLITE|CHROMITITE|HARRISITE|CUMULATE")
DIKE_ROCK = re.compile(r"DOLERITE|DIABASE|PICRITE|MICROGABBRO")
DIKE_UNIT = re.compile(r"\bDIKES?\b|\bDYKES?\b|\bSILLS?\b|FEEDER")

KEEP = ["UNIQUE_ID", "SAMPLE NAME", "CITATIONS", "LOCATION", "LOCATION COMMENT", "lat", "lon", "rock_name",
        "ROCK TEXTURE", "ALTERATION", "intrusion_key", "intrusion_name", "intrusion_unit", "georoc_file"]


def tag(row):
    name = row["rock_name"]
    tex = str(row.get("ROCK TEXTURE", "")).upper()
    notes = " ".join(str(row.get(c, "")) for c in ["LOCATION COMMENT", "intrusion_unit", "SAMPLE NAME"]).upper()
    loi = row.get("LOI(WT%)")
    mgo = row.get("MGO(WT%)")
    alt = str(row.get("ALTERATION", "")).strip().upper()
    if pd.notna(loi) and loi > 5:
        return "ALTERED", "LOI>5", "strong"
    if alt in {"M", "E"}:
        return "ALTERED", "GEOROC alteration code " + alt, "strong"
    if ALTER_NAME.search(name):
        return "ALTERED", "alteration word in rock name", "strong"
    if CHILL.search(name) or CHILL.search(tex):
        return "CHILLED_MARGIN", "chill word in rock name/texture", "strong"
    if CHILL.search(notes):
        return "CHILLED_MARGIN", "chill word in location/sample notes", "weak"
    if CUM_TEXT.search(name) or CUM_TEXT.search(tex):
        return "CUMULATE", "cumulate word in rock name/texture", "strong"
    if CUM_ROCK.search(name):
        return "CUMULATE", "ultramafic/monomineralic rock name", "strong"
    if pd.notna(mgo) and mgo > 25:
        return "CUMULATE", "MgO>25", "weak"
    if DIKE_ROCK.search(name) and not CUM_TEXT.search(tex):
        return "FINE_GRAINED_DIKE_SILL", "dolerite/diabase/picrite rock name", "weak"
    if DIKE_UNIT.search(notes + " " + str(row.get("intrusion_name", "")).upper()):
        return "FINE_GRAINED_DIKE_SILL", "dike/sill unit", "weak"
    return "UNRESOLVED", "no rule fired", "none"


def main():
    d = pd.read_csv(os.path.join(INTERIM, "samples_with_intrusion.csv.gz"), low_memory=False).copy()
    for c in ["LOI(WT%)", "MGO(WT%)"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # Unit guard: a reference reporting any Pt or Pd above 1,000 ppm (0.1 wt%, beyond any ore) has almost
    # certainly entered ppb as ppm. Its platinum-group element values are blanked, not "corrected", and the
    # reference is listed in docs/review/pge_unit_flags.csv for the authors to check against the paper.
    pge = ["PD(PPM)", "PT(PPM)", "IR(PPM)", "RU(PPM)", "RH(PPM)", "OS(PPM)"]
    for c in pge:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # Author-confirmed unit errors are corrected first (data/curated/pge_unit_corrections.csv).
    corr_file = os.path.join(ROOT, "data", "curated", "pge_unit_corrections.csv")
    n_corrected = 0
    if os.path.exists(corr_file):
        for _, cr in pd.read_csv(corr_file).iterrows():
            m = d["CITATIONS"].astype(str) == cr["citation"]
            d.loc[m, pge] = d.loc[m, pge] * cr["factor"]
            n_corrected += int((m & d[pge].notna().any(axis=1)).sum())
    bad = (d["PD(PPM)"] > 1000) | (d["PT(PPM)"] > 1000)
    bad_refs = sorted(d.loc[bad, "CITATIONS"].astype(str).unique())
    flag = d["CITATIONS"].astype(str).isin(bad_refs) & d[pge].notna().any(axis=1)
    d.loc[flag, ["UNIQUE_ID", "intrusion_key", "CITATIONS"] + pge].to_csv(
        os.path.join(REVIEW, "pge_unit_flags.csv"), index=False)
    d.loc[flag, pge] = np.nan
    pge_log = {"pge_unit_corrected_samples": n_corrected, "pge_unit_flag_references": bad_refs,
               "pge_values_blanked_samples": int(flag.sum())}
    # MgO guard: MgO < 0.5 wt% is plausible only in anorthosite (the authors confirmed the anorthosites).
    # In any other mafic-ultramafic rock it is a source data error, so that MgO value is blanked and logged.
    d["MGO(WT%)"] = pd.to_numeric(d["MGO(WT%)"], errors="coerce")
    bad_mg = (d["MGO(WT%)"] < 0.5) & ~d["rock_name"].str.contains("ANORTHOS")
    d.loc[bad_mg, ["UNIQUE_ID", "intrusion_key", "rock_name", "MGO(WT%)", "CITATIONS"]].to_csv(
        os.path.join(REVIEW, "mgo_blanked.csv"), index=False)
    d.loc[bad_mg, "MGO(WT%)"] = np.nan
    pge_log["mgo_values_blanked_non_anorthosite"] = int(bad_mg.sum())
    t = d.apply(tag, axis=1, result_type="expand")
    d = d.assign(sample_type=t[0], type_rule=t[1], type_rule_strength=t[2])

    lab = pd.read_csv(os.path.join(INTERIM, "intrusion_labels.csv"))
    lab = lab[lab["label"] != "EXCLUDE"]
    d = d.merge(lab[["intrusion_key", "label", "confidence"]].rename(columns={"confidence": "label_confidence"}),
                on="intrusion_key", how="inner")

    # Fixed train/test split by intrusion (70/30), stratified by label, for methods with fitted parameters.
    rng = np.random.default_rng(SEED)
    split = {}
    for lbl, g in lab.groupby("label"):
        keys = np.array(sorted(g["intrusion_key"]))
        rng.shuffle(keys)
        n_test = int(round(0.3 * len(keys)))
        split.update({k: ("test" if i < n_test else "train") for i, k in enumerate(keys)})
    d = d.assign(split=d["intrusion_key"].map(split))
    lab["split"] = lab["intrusion_key"].map(split)

    analytes = [c for c in d.columns if c.endswith("(PPM)") or c.endswith("(WT%)")]
    analytes = [c for c in analytes if d[c].notna().any()]
    cols = KEEP + ["sample_type", "type_rule", "type_rule_strength", "label", "label_confidence", "split"] + analytes
    out = d[[c for c in cols if c in d.columns]].sort_values(["intrusion_key", "UNIQUE_ID"])
    out.to_csv(os.path.join(PROC, "benchmark_samples.csv"), index=False)
    st = out.groupby("intrusion_key")["sample_type"].value_counts().unstack(fill_value=0)
    lab = lab.merge(st, left_on="intrusion_key", right_index=True, how="left")
    lab.to_csv(os.path.join(PROC, "intrusions.csv"), index=False)

    # Review sample for the authors.
    # 25 random samples per tag (stratified) + 75 weak-rule tags: about 200 rows, one sitting.
    rnd = out.groupby("sample_type", group_keys=False).apply(
        lambda g: g.sample(min(len(g), 25), random_state=SEED), include_groups=False).join(out[["sample_type"]])
    weak = out[out["type_rule_strength"] == "weak"]
    weak = weak.sample(min(len(weak), 75), random_state=SEED)
    rv = pd.concat([rnd.assign(review_reason="random (25 per tag)"), weak.assign(review_reason="weak rule")])
    rv = rv.drop_duplicates("UNIQUE_ID")
    rv_cols = ["UNIQUE_ID", "intrusion_key", "SAMPLE NAME", "rock_name", "ROCK TEXTURE", "ALTERATION",
               "LOI(WT%)", "MGO(WT%)", "LOCATION COMMENT", "CITATIONS", "sample_type", "type_rule", "review_reason"]
    rv = rv[[c for c in rv_cols if c in rv.columns]].assign(author_type="", author_note="")
    rv.to_csv(os.path.join(REVIEW, "sample_type_review.csv"), index=False)

    summary = {
        "benchmark_samples": int(len(out)),
        "benchmark_intrusions": int(out["intrusion_key"].nunique()),
        "samples_by_label": out["label"].value_counts().to_dict(),
        "intrusions_by_label": lab["label"].value_counts().to_dict(),
        "samples_by_type": out["sample_type"].value_counts().to_dict(),
        "type_by_label": out.groupby(["label", "sample_type"]).size().unstack(fill_value=0).to_dict(),
        "rule_strength": out["type_rule_strength"].value_counts().to_dict(),
        "split_intrusions": lab.groupby(["split", "label"]).size().rename("n").reset_index().to_dict("records"),
        "review_rows": int(len(rv)),
        "analyte_columns": len(analytes),
        **pge_log,
    }
    with open(os.path.join(INTERIM, "04_log.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
