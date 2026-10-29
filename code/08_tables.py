#!/usr/bin/env python3
"""08_tables.py - write the result tables for the authors' manuscript.

Plain-language note: this script turns the pipeline outputs into publication tables
(paper/tables/*.csv and one Excel workbook, paper/tables/Fertile_or_Barren_tables.xlsx)
plus a captions file with every number already filled in from the data. It writes no
manuscript text; the authors write the paper. Re-run it after any data change and the
tables update.
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, "paper", "tables")
os.makedirs(T, exist_ok=True)
S = json.load(open(os.path.join(ROOT, "paper", "stats.json")))
L2 = json.load(open(os.path.join(ROOT, "data", "interim", "02_log.json")))
L3 = json.load(open(os.path.join(ROOT, "data", "interim", "03_log.json")))
L4 = json.load(open(os.path.join(ROOT, "data", "interim", "04_log.json")))
RES = pd.read_csv(os.path.join(ROOT, "leaderboard", "results.csv"))
INTR = pd.read_csv(os.path.join(ROOT, "data", "processed", "intrusions.csv"))
BENCH = pd.read_csv(os.path.join(ROOT, "data", "processed", "benchmark_samples.csv"), low_memory=False,
                    usecols=["intrusion_key", "label", "sample_type", "label_confidence"])
CUR = pd.read_csv(os.path.join(ROOT, "data", "curated", "intrusion_labels_curated.csv")).fillna("")
STRATA = [("ALL", "All samples"), ("CUMULATE", "Cumulates"),
          ("LIQUID_PROXY", "Chilled margins + fine-grained dikes/sills"),
          ("ALTERED", "Altered"), ("UNRESOLVED", "Unresolved type")]


def ci(r, st):
    if pd.isna(r[f"{st}_auc_w"]):
        return "insufficient"
    return f"{r[f'{st}_auc_w']:.2f} ({r[f'{st}_ci_low']:.2f}-{r[f'{st}_ci_high']:.2f})"


tables = {}

# Table 1. Data sources
tables["Table1_Sources"] = pd.DataFrame([
    ["GEOROC precompiled compilations (10 tectonic-setting compilations)", "DIGIS Team, GRO.data", "September 2026 (v13.0)",
     "Whole-rock geochemistry", f"{S['georoc_unique_samples']:,} unique analyses", "CC BY-SA 4.0", "doi:10.25625/1KRR1P and 9 others (code/01_fetch.py)"],
    ["GEOROC Compilation: Rock Types (mafic-ultramafic files)", "DIGIS Team, GRO.data", "September 2026 (v15.0)",
     "Completeness cross-check", f"{L2['rocktypes_plutonic_ids']:,} plutonic analyses; {L2['rocktypes_ids_missing_from_settings_union']} absent from the union",
     "CC BY-SA 4.0", "doi:10.25625/2JETOA"],
    ["Critical Mineral Deposits of the United States", "Hammarstrom, Woodruff and Dicken (USGS)", "ver. 3.0, September 2026",
     "Deposit locations (US)", f"{L3['usgs_cm_ni_pge_deposits']} Ni-Cu-PGE / PGE deposits used", "CC0", "doi:10.5066/P9K1HBNT"],
    ["Magmatic Ni-Cu-PGE inventory", "Parks et al. (USGS)", "2026",
     "Host intrusions and resources (US)", "Intrusion names matched", "CC0", "doi:10.5066/P1YLGLUZ"],
    ["Mineral Resources Data System (MRDS)", "USGS", "Full CSV export",
     "Deposit and occurrence locations (global)", f"{S['mrds_records']} magmatic Ni or PGE records used", "Public domain", "https://mrdata.usgs.gov/mrds/"],
], columns=["Source", "Producer", "Version", "Used for", "Records", "License", "Identifier"])

# Table 2. Sample selection (row counts at each stage)
tables["Table2_Selection"] = pd.DataFrame([
    ["GEOROC rows read (10 compilations)", L2["rows_read"]],
    ["Unique analyses in the union", L2["unique_samples_in_georoc_union"]],
    ["Plutonic rows", L2["rows_plutonic"]],
    ["Plutonic with a mafic-ultramafic rock name (unique)", L2["mafic_ultramafic_plutonic_samples"]],
    ["  removed: mantle xenoliths / kimberlite-hosted", -L2["dropped_xenolith_or_kimberlite"]],
    ["  removed: ophiolite / abyssal mantle", -L2["dropped_ophiolite_or_abyssal_mantle"]],
    ["  removed: alkaline-carbonatite complexes", -L2["dropped_alkaline_carbonatite_complex"]],
    ["  removed: orogenic mantle massifs", -L2["dropped_orogenic_mantle_massif"]],
    ["  removed: samples named as ore", -L2["dropped_ore_sample"]],
    ["  removed: no intrusion name in GEOROC", -L2["samples_without_intrusion_name"]],
    ["Samples assigned to a named intrusion", L2["samples_kept"]],
    ["Intrusions (any size)", L2["intrusions"]],
    ["Intrusions with >= 5 samples", L3["intrusions_with_min_samples"]],
    ["  removed: excluded by the authors (groups, ophiolites, generic names)", -S["intrusions_excluded_curated"]],
    ["Benchmark intrusions", S["benchmark_intrusions"]],
    ["Benchmark samples", S["benchmark_samples"]],
], columns=["Stage", "Count"])

# Table 3. Labels by confidence
lab = INTR.groupby(["label", "confidence"]).agg(intrusions=("intrusion_key", "size"),
                                                 samples=("n_samples", "sum")).reset_index()
lab["label"] = pd.Categorical(lab["label"], ["FERTILE", "WEAK", "BARREN"], ordered=True)
lab["confidence"] = pd.Categorical(lab["confidence"], ["HIGH", "MEDIUM", "LOW"], ordered=True)
tables["Table3_Labels"] = lab.sort_values(["label", "confidence"]).rename(columns={
    "label": "Label", "confidence": "Confidence", "intrusions": "Intrusions", "samples": "Samples"})

# Table 4. Sample types by label
order = ["CUMULATE", "UNRESOLVED", "FINE_GRAINED_DIKE_SILL", "ALTERED", "CHILLED_MARGIN"]
t4 = BENCH.groupby(["label", "sample_type"]).size().unstack(fill_value=0).reindex(["FERTILE", "WEAK", "BARREN"])[order]
ni = BENCH.groupby(["label", "sample_type"])["intrusion_key"].nunique().unstack(fill_value=0).reindex(
    ["FERTILE", "WEAK", "BARREN"])[order]
rows = []
for lb in t4.index:
    tot = t4.loc[lb].sum()
    rows.append([lb] + [f"{t4.loc[lb, c]:,} ({100 * t4.loc[lb, c] / tot:.0f}%; {ni.loc[lb, c]} intr.)" for c in order]
                + [f"{tot:,}"])
tables["Table4_SampleTypes"] = pd.DataFrame(rows, columns=["Label", "Cumulate", "Unresolved", "Fine-grained dike/sill",
                                                           "Altered", "Chilled margin", "Total samples"])

# Table 5. Index definitions
from importlib.machinery import SourceFileLoader  # noqa: E402
_ixm = SourceFileLoader("indices", os.path.join(ROOT, "code", "indices.py")).load_module()
IX, DISPLAY = _ixm.INDICES, _ixm.DISPLAY
formula = {"cu_pd": "log10(Cu/Pd)", "cu_pd_dev": "|log10(Cu/Pd) - log10(Cu/Pd)PM|", "pd_ir": "log10(Pd/Ir)",
           "pt_pd": "-log10(Pt/Pd)", "cu_zr": "-log10(Cu/Zr)", "ni_cu": "-log10(Ni/Cu)",
           "ni_depletion": "-(log10 Ni - quadratic fit of log10 Ni on MgO, 5-50 wt%)", "th_nb": "log10(Th/Nb)",
           "la_sm": "log10(La/Sm)", "zr_y": "log10(Zr/Y)", "s": "log10(S)", "s_se": "log10(S/Se)"}
tables["Table5_Indices"] = pd.DataFrame([[DISPLAY[ix["id"]], ix["id"], ix["family"], formula[ix["id"]], " + ".join(ix["needs"]),
                                          ix["hypothesis"], ix["ref"]] for ix in IX],
                                        columns=["Index", "Code name", "Family", "Score (higher = predicted fertile)",
                                                 "Elements needed", "Hypothesis tested", "Reference"])

# Table 6. Leaderboard
res = RES.sort_values("ALL_auc_w", ascending=False)
t6 = []
for rank, (_, r) in enumerate(res.iterrows(), 1):
    t6.append([rank, DISPLAY[r["index"]], r["family"]] + [ci(r, st) for st, _ in STRATA] +
              [f"{int(r['ALL_n_fert'])} / {int(r['ALL_n_barr'])}", f"{r['ALL_coverage']:.0%}"])
tables["Table6_Leaderboard"] = pd.DataFrame(t6, columns=["Rank", "Index", "Family"] + [n for _, n in STRATA] +
                                            ["Fertile / barren intrusions (all)", "Coverage (all)"])

# Table 7. Robustness: intrusion-level AUC, sensitivity, held-out test split
t7 = []
for _, r in res.iterrows():
    f = lambda v: "" if pd.isna(v) else f"{v:.2f}"  # noqa: E731
    t7.append([DISPLAY[r["index"]], f(r["ALL_auc_w"]), f(r["ALL_auc_intrusion"]), f(r["ALL_auc_w_sensitivity"]),
               f(r["ALL_auc_w_test"])])
tables["Table7_Robustness"] = pd.DataFrame(t7, columns=["Index", "AUC_w (all)", "AUC on intrusion medians",
                                                        "AUC_w, LOW-confidence barren removed",
                                                        "AUC_w, test split only (30% of intrusions)"])

# Table S1. Fertile and weak intrusions with deposits and references
s1 = INTR[INTR.label.isin(["FERTILE", "WEAK"])].merge(
    CUR[["intrusion_key", "deposit_type", "note"]], on="intrusion_key", how="left", suffixes=("", "_cur"))
s1 = s1.assign(label=pd.Categorical(s1.label, ["FERTILE", "WEAK"], ordered=True)).sort_values(["label", "intrusion_key"])
s1["Coordinates"] = s1.apply(lambda r: f"{r.lat:.2f}, {r.lon:.2f}", axis=1)
tables["TableS1_FertileWeak"] = s1[["intrusion_key", "label", "n_samples", "region", "Coordinates", "deposit",
                                   "deposit_type_cur" if "deposit_type_cur" in s1 else "deposit_type", "reference",
                                   "label_source"]].rename(columns={
    "intrusion_key": "Intrusion", "label": "Label", "n_samples": "Samples", "region": "GEOROC region",
    "deposit": "Deposit / occurrence", "deposit_type_cur": "Deposit type", "deposit_type": "Deposit type",
    "reference": "Reference", "label_source": "Label source"})

# Table S2. All benchmark intrusions
s2 = INTR.sort_values(["label", "n_samples"], ascending=[True, False])
tables["TableS2_AllIntrusions"] = s2[["intrusion_key", "label", "confidence", "label_source", "n_samples", "region",
                                     "lat", "lon", "split"] + order].rename(columns={
    "intrusion_key": "Intrusion", "label": "Label", "confidence": "Confidence", "label_source": "Label source",
    "n_samples": "Samples", "region": "GEOROC region", "lat": "Latitude", "lon": "Longitude", "split": "Split"})

# Table S3. Data corrections
tables["TableS3_Corrections"] = pd.DataFrame([
    ["PGE unit correction", "References [23290], [24352]: Pt, Pd, Ir, Ru, Rh, Os divided by 1,000 (ppb entered as ppm)",
     L4["pge_unit_corrected_samples"], "Checked by the authors against the original papers"],
    ["MgO guard", "MgO < 0.5 wt% blanked in non-anorthosite rocks", L4["mgo_values_blanked_non_anorthosite"],
     "Remaining low-MgO samples confirmed as anorthosites by the authors"],
    ["Ore filter", "Samples whose rock name says ore or massive sulfide removed", L2["dropped_ore_sample"], ""],
    ["Duplicate analyses", "Same UNIQUE_ID in more than one GEOROC compilation", L2["duplicate_rows_dropped"], "Kept once"],
], columns=["Correction", "Rule", "Samples affected", "Note"])

for name, df in tables.items():
    df.to_csv(os.path.join(T, f"{name}.csv"), index=False)

# Excel workbook
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from openpyxl.utils import get_column_letter  # noqa: E402

TITLES = {
    "Table1_Sources": "Table 1. Data sources",
    "Table2_Selection": "Table 2. Sample selection: counts at each stage (negative = removed)",
    "Table3_Labels": "Table 3. Benchmark intrusions by label and label confidence",
    "Table4_SampleTypes": "Table 4. Samples by sample type and label: count (share of label; intrusions with that type)",
    "Table5_Indices": "Table 5. Fertility indices scored on the benchmark",
    "Table6_Leaderboard": "Table 6. Leaderboard: intrusion-weighted AUC (95% bootstrap CI) by sample type",
    "Table7_Robustness": "Table 7. Robustness of the all-sample AUC",
    "TableS1_FertileWeak": "Table S1. Fertile and weakly mineralized intrusions, with deposits and references",
    "TableS2_AllIntrusions": "Table S2. All benchmark intrusions",
    "TableS3_Corrections": "Table S3. Data corrections applied before scoring",
}
wb = Workbook()
wb.remove(wb.active)
readme = wb.create_sheet("README")
readme["A1"] = "Fertile or Barren v0.1.0: result tables"
readme["A1"].font = Font(name="Arial", bold=True, size=12)
notes = [
    "Every value is written by code/08_tables.py from the pipeline outputs (paper/stats.json, leaderboard/results.csv, data/processed/*).",
    "Do not edit numbers here; change the data or decisions and re-run ./run_all.sh.",
    "AUC = intrusion-weighted ROC area for FERTILE vs BARREN (WEAK not scored). 0.5 = no skill; below 0.5 = the index ranks barren above fertile.",
    "95% CI from 2,000 bootstrap resamples of intrusions (seed 20270801). 'insufficient' = fewer than 5 fertile or 5 barren intrusions with data.",
    "Each sheet is also saved as CSV in paper/tables/.",
]
for i, t in enumerate(notes, 3):
    readme.cell(row=i, column=1, value=t).font = Font(name="Arial", size=10)
readme.column_dimensions["A"].width = 130
head_fill = PatternFill("solid", fgColor="E4E3DF")
for name, df in tables.items():
    ws = wb.create_sheet(name.replace("Table", "T")[:31])
    ws["A1"] = TITLES[name]
    ws["A1"].font = Font(name="Arial", bold=True, size=11)
    for j, c in enumerate(df.columns, 1):
        cell = ws.cell(row=3, column=j, value=str(c))
        cell.font = Font(name="Arial", bold=True, size=10)
        cell.fill = head_fill
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    for i, row in enumerate(df.itertuples(index=False), 4):
        for j, v in enumerate(row, 1):
            if isinstance(v, (np.integer,)):
                v = int(v)
            elif isinstance(v, (np.floating,)):
                v = None if np.isnan(v) else float(v)
            cell = ws.cell(row=i, column=j, value=v)
            cell.font = Font(name="Arial", size=10)
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if isinstance(v, int):
                cell.number_format = "#,##0;(#,##0);-"
            elif isinstance(v, float):
                cell.number_format = "0.00"
    for j, c in enumerate(df.columns, 1):
        longest = max([len(str(c))] + [len(str(x)) for x in df.iloc[:, j - 1].head(200)])
        ws.column_dimensions[get_column_letter(j)].width = min(max(10, longest + 2), 60)
    ws.freeze_panes = "A4"
wb.save(os.path.join(T, "Fertile_or_Barren_tables.xlsx"))

# Figure captions, numbers filled from the data
R = {r["index"]: r for _, r in RES.iterrows()}
caps = f"""# Figure captions (numbers filled in from the data; edit the wording freely)

**Figure 1.** Locations of the {S['benchmark_intrusions']} benchmark intrusions with at least five GEOROC samples, colored by label: fertile ({S['fertile_intrusions']}), weakly mineralized ({S['weak_intrusions']}) and barren ({S['barren_intrusions']}). Robinson projection; coordinates are the median of each intrusion's sample coordinates.

**Figure 2.** Intrusion-weighted ROC AUC and 95% bootstrap confidence interval for each of the {S['n_indices']} indices, for all sample types (left) and cumulates only (right). The dashed line marks 0.5 (no skill). Values below 0.5 mean the index ranks barren intrusions above fertile ones. Asterisks mark exploratory indices whose direction was set by the authors; |Δlog(Cu/Pd)| is the absolute departure of log10(Cu/Pd) from the primitive-mantle value.

**Figure 3.** Share of each sample type within fertile, weakly mineralized and barren intrusions ({S['fertile_samples']:,}, {S['weak_samples']:,} and {S['barren_samples']:,} samples). Cumulates make up {100 * S['scored_samples_by_type_label']['FERTILE']['CUMULATE'] / sum(S['scored_samples_by_type_label']['FERTILE'].values()):.0f}% of fertile samples.

**Figure 4.** AUC by index and sample type. Cells with fewer than five fertile or five barren intrusions with data are left blank and marked "n/a". Diverging scale centered on 0.5. Asterisks as in Figure 2.

# Key numbers (for the text)

- GEOROC analyses screened: {S['georoc_unique_samples']:,}; mafic-ultramafic plutonic samples: {S['mafic_um_plutonic_samples']:,}; without an intrusion name: {S['samples_without_intrusion_name']:,}.
- Benchmark: {S['benchmark_samples']:,} samples, {S['benchmark_intrusions']} intrusions ({S['fertile_intrusions']} fertile, {S['weak_intrusions']} weak, {S['barren_intrusions']} barren; {S['barren_low_conf_intrusions']} barren at LOW confidence).
- Fertile intrusions with chilled-margin samples: {S['fertile_intrusions_with_chilled_margin']}; with any chilled-margin or fine-grained dike/sill sample: {S['fertile_intrusions_with_liquid_proxy']}.
- Best index: {DISPLAY[S['best_index']]}, AUC {S['best_auc_w']:.2f} (95% CI {S['best_ci_low']:.2f}-{S['best_ci_high']:.2f}); with LOW-confidence barren removed: {R[S['best_index']]['ALL_auc_w_sensitivity']:.2f}.
- Indices with CI entirely above 0.5: {', '.join(k for k, r in R.items() if r['ALL_ci_low'] > 0.5)}.
- Indices with CI entirely below 0.5: {', '.join(k for k, r in R.items() if r['ALL_ci_high'] < 0.5)}.
"""
open(os.path.join(T, "CAPTIONS_AND_KEY_NUMBERS.md"), "w").write(caps)
print("tables written to", T)

# README headline block, interpolated from the stats file.
rd = os.path.join(ROOT, "README.md")
txt = open(rd).read()
back = [DISPLAY[k].rstrip("*") for k, r in R.items() if r["ALL_ci_high"] < 0.5]
head = (f"**Headline numbers (from paper/stats.json):** {S['benchmark_samples']:,} samples from "
        f"{S['benchmark_intrusions']} intrusions ({S['fertile_intrusions']} fertile, {S['weak_intrusions']} weakly "
        f"mineralized, {S['barren_intrusions']} barren). Best index: {DISPLAY[S['best_index']]}, AUC {S['best_auc_w']:.2f} "
        f"(95% CI {S['best_ci_low']:.2f}-{S['best_ci_high']:.2f}). {len(back)} indices rank barren intrusions "
        f"above fertile ones ({', '.join(back)}). Full table: [leaderboard/LEADERBOARD.md](leaderboard/LEADERBOARD.md).")
a, b = txt.index("<!-- HEADLINE:START -->"), txt.index("<!-- HEADLINE:END -->")
open(rd, "w").write(txt[:a] + "<!-- HEADLINE:START -->\n" + head + "\n" + txt[b:])
