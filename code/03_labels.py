#!/usr/bin/env python3
"""03_labels.py - label each intrusion FERTILE, WEAK or BARREN, with the evidence behind it.

Plain-language note: this script decides, for every intrusion, whether it hosts a known
nickel-copper-platinum sulfide deposit. It combines three kinds of evidence:
  (1) the authors' curated list (data/curated/intrusion_labels_curated.csv), which names
      well-documented ore-hosting and barren intrusions with a reference for each;
  (2) the two USGS deposit lists (US only), matched by distance and by intrusion name;
  (3) the USGS worldwide mine list (MRDS), matched by distance.
Where the evidence disagrees, or is thin, the intrusion is written to
docs/review/label_review.csv for the authors to rule on. You WILL open that review file.

Rules (see docs/BUILD_SPEC.md):
  FERTILE  curated FERTILE; or USGS Ni-Cu-PGE inventory intrusion; or USGS critical-mineral
           Ni-Cu-PGE/PGE deposit within RADIUS_KM; or MRDS producer/past producer with Ni or
           PGE as a primary commodity within RADIUS_KM.
  WEAK     curated WEAK; or MRDS occurrence/prospect within RADIUS_KM (and not FERTILE).
  BARREN   none of the above. Confidence HIGH when curated BARREN from literature, MEDIUM
           when in a country with dense MRDS coverage, otherwise LOW.
A curated label always overrides the automatic one; disagreements are logged.
Curated confidence: HIGH = deposit (or other-type mineralization) documented in the literature;
MEDIUM = automatic evidence reviewed and confirmed by the authors (Oct 2026). The authors' completed
review files are archived in data/curated/author_review/.
"""
import json
import os
import re
import zipfile

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
INTERIM = os.path.join(ROOT, "data", "interim")
CURATED = os.path.join(ROOT, "data", "curated", "intrusion_labels_curated.csv")
REVIEW = os.path.join(ROOT, "docs", "review")
os.makedirs(REVIEW, exist_ok=True)
RADIUS_KM = 10.0
MIN_SAMPLES = 5            # intrusions with fewer samples are kept in the data but not labeled
DENSE_MRDS = {"United States", "Canada", "Australia", "South Africa", "Finland"}
# GEOROC region (first LOCATION level) -> country, only where it is unambiguous.
REGION_COUNTRY = {"MIDCONTINENT RIFT SYSTEM-KEWEENAWAN": "United States",
                  "CENTRAL ATLANTIC MAGMATIC PROVINCE - CAMP": None}


def haversine_min(lat, lon, plat, plon):
    """Minimum great-circle distance (km) from point arrays (lat, lon) to points (plat, plon)."""
    if len(plat) == 0 or len(lat) == 0:
        return np.full(len(plat), np.inf)
    la1, lo1 = np.radians(lat)[:, None], np.radians(lon)[:, None]
    la2, lo2 = np.radians(plat)[None, :], np.radians(plon)[None, :]
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return (2 * 6371.0 * np.arcsin(np.sqrt(a))).min(axis=0)


def load_mrds():
    with zipfile.ZipFile(os.path.join(RAW, "mrds", "mrds-csv.zip")) as z:
        m = pd.read_csv(z.open("mrds.csv"), low_memory=False, encoding="latin1")
    com1 = m["commod1"].fillna("")
    com = com1 + "," + m["commod2"].fillna("") + "," + m["commod3"].fillna("")
    txt = (m["dep_type"].fillna("") + " " + m["model"].fillna("") + " " + m["hrock_type"].fillna("") + " " +
           m["hrock_unit"].fillna("") + " " + m["ore"].fillna("")).str.upper()
    magmatic = txt.str.contains(
        r"MAGMATIC|STILLWATER|MERENSKY|DULUTH|NORIL|KOMATI|DUNITIC|SYNOROGENIC|LAYERED|SULFIDE SEGREG|"
        r"GABBRO|NORITE|PERIDOTITE|DUNITE|PYROXENITE|TROCTOLITE|ULTRAMAFIC|PENTLANDITE")
    excluded = txt.str.contains(
        r"PLACER|LATERIT|RESIDUAL|ALLUVIAL|BEACH|VEIN|SKARN|PORPHYRY|PODIFORM|ALASKAN CR|EXHALATIVE|"
        r"BESSHI|LIMASSOL|SEDIMENT-HOSTED")
    s = m[com.str.contains(r"Nickel|Platinum|Palladium|PGE") & magmatic & ~excluded].copy()
    s["primary_ni_pge"] = com1.loc[s.index].str.contains(r"Nickel|Platinum|Palladium|PGE")
    s["producer"] = s["dev_stat"].isin(["Producer", "Past Producer"]) & s["primary_ni_pge"]
    return s[["dep_id", "site_name", "country", "latitude", "longitude", "dev_stat", "producer", "url"]]


def load_usgs():
    x = os.path.join(RAW, "usgs_critical_minerals_v3", "critical_mineral_deposits_all_tables_v3.xlsx.xlsx")
    cm = pd.read_excel(x, sheet_name="2026_CM_deposits")
    cm = cm[cm["DepType"].astype(str).str.contains(r"Nickel-copper-PGE|PGE \(low sulfide\)")]
    cm = cm[~cm["Deposit_na"].astype(str).str.contains("placer|Bench", case=False)]
    with zipfile.ZipFile(os.path.join(RAW, "usgs_nicupge_2026", "NiCuPGE_FS_Csv_files.zip")) as z:
        inv = pd.read_csv(z.open("NiCuPGE_FS_Resources_table.csv"), encoding="utf-8-sig")
    return cm, sorted(inv["Intrusion"].dropna().unique())


def name_tokens(s):
    return set(re.findall(r"[A-Z]{4,}", str(s).upper())) - {
        "COMPLEX", "INTRUSION", "INTRUSIONS", "INTRUSIVE", "LAYERED", "STOCK", "GABBRO", "RELATED", "ROCKS",
        "ULTRAMAFIC", "PERIDOTITE", "EAST", "WEST", "NORTH", "SOUTH", "ALPHA", "LAKE", "RIVER", "MOUNTAIN", "CREEK"}


def main():
    d = pd.read_csv(os.path.join(INTERIM, "samples_with_intrusion.csv.gz"), low_memory=False,
                    usecols=["UNIQUE_ID", "intrusion_key", "intrusion_name", "lat", "lon", "region",
                             "LATITUDE MIN", "LATITUDE MAX", "LOCATION"])
    counts = d["intrusion_key"].value_counts()
    keys = counts[counts >= MIN_SAMPLES].index
    mrds = load_mrds()
    cm, inv_intrusions = load_usgs()
    inv_tokens = {name: name_tokens(name) for name in inv_intrusions}
    cur = pd.read_csv(CURATED) if os.path.exists(CURATED) else pd.DataFrame(
        columns=["intrusion_key", "label", "deposit", "reference", "note"])
    cur = cur.set_index("intrusion_key")

    rows = []
    for k in keys:
        s = d[d["intrusion_key"] == k]
        pts = s[["lat", "lon"]].dropna().drop_duplicates()
        precise = ((s["LATITUDE MAX"] - s["LATITUDE MIN"]).abs() < 0.05).mean()
        dm = haversine_min(pts["lat"].values, pts["lon"].values, mrds["latitude"].values, mrds["longitude"].values)
        near = mrds[dm <= RADIUS_KM]
        dc = haversine_min(pts["lat"].values, pts["lon"].values,
                           pd.to_numeric(cm["Lat_WGS84"], errors="coerce").values,
                           pd.to_numeric(cm["Long_WGS84"], errors="coerce").values)
        near_cm = cm[dc <= RADIUS_KM]
        ktok = name_tokens(k)
        inv_hit = [n for n, t in inv_tokens.items() if ktok & t]
        ev = []
        auto = "BARREN"
        if inv_hit:
            auto = "FERTILE"; ev.append("USGS Ni-Cu-PGE inventory intrusion: " + "; ".join(inv_hit))
        if len(near_cm):
            auto = "FERTILE"; ev.append("USGS critical-mineral deposit(s) within 10 km: " +
                                        "; ".join(near_cm["Deposit_na"].astype(str).head(4)))
        if near["producer"].any():
            auto = "FERTILE"
            ev.append("MRDS producer(s) within 10 km: " + "; ".join(near.loc[near.producer, "site_name"].astype(str).head(4)))
        elif len(near):
            auto = "WEAK" if auto == "BARREN" else auto
            ev.append("MRDS occurrence/prospect(s) within 10 km: " + "; ".join(near["site_name"].astype(str).head(4)))
        country = near["country"].mode().iat[0] if len(near) else None
        label, source, conf = auto, "automatic", None
        if k in cur.index:
            c = cur.loc[k]
            label, source = c["label"], "curated"
            conf = c["confidence"] if "confidence" in c.index and str(c["confidence"]) not in ("", "nan") else "HIGH"
        if conf is None:
            if label == "BARREN":
                dense = s["LOCATION"].str.contains(r"UNITED STATES|CANADA|AUSTRALIA|SOUTH AFRICA|FINLAND|"
                                                   r"MIDCONTINENT|SUPERIOR PROVINCE|APPALACHIAN|KAAPVAAL",
                                                   regex=True).mean() > 0.5
                conf = "MEDIUM" if dense and precise > 0.5 else "LOW"
            else:
                conf = "MEDIUM"
        rows.append(dict(
            intrusion_key=k, n_samples=int(len(s)), region=s["region"].mode().iat[0] if s["region"].notna().any() else "",
            names=s["intrusion_name"].iloc[0], lat=float(pts["lat"].median()) if len(pts) else np.nan,
            lon=float(pts["lon"].median()) if len(pts) else np.nan, coord_precise_share=round(float(precise), 2),
            label=label, label_source=source, confidence=conf, auto_label=auto,
            curated_label=cur.loc[k, "label"] if k in cur.index else "",
            deposit=cur.loc[k, "deposit"] if k in cur.index else "",
            deposit_type=cur.loc[k, "deposit_type"] if k in cur.index and "deposit_type" in cur.columns else "",
            reference=cur.loc[k, "reference"] if k in cur.index else "",
            evidence=" | ".join(ev), n_mrds_near=int(len(near))))
    lab = pd.DataFrame(rows).sort_values(["label", "n_samples"], ascending=[True, False])
    lab.to_csv(os.path.join(INTERIM, "intrusion_labels.csv"), index=False)

    review = lab[(lab["label_source"] == "automatic") & (lab["label"] != "BARREN") |
                 (lab["curated_label"].astype(str) != "") & (lab["auto_label"] != lab["curated_label"]) |
                 (lab["label"] == "BARREN") & (lab["n_samples"] >= 30) & (lab["label_source"] == "automatic")]
    review = review.assign(author_decision="", author_note="")
    review.to_csv(os.path.join(REVIEW, "label_review.csv"), index=False)
    summary = {
        "intrusions_with_min_samples": int(len(lab)),
        "label_counts": lab["label"].value_counts().to_dict(),
        "label_by_confidence": lab.groupby(["label", "confidence"]).size().rename("n").reset_index().to_dict("records"),
        "curated_used": int((lab["label_source"] == "curated").sum()),
        "curated_vs_auto_disagreements": int(((lab["curated_label"].astype(str) != "") &
                                              (lab["auto_label"] != lab["curated_label"])).sum()),
        "review_rows": int(len(review)),
        "mrds_magmatic_ni_pge_records": int(len(mrds)),
        "usgs_cm_ni_pge_deposits": int(len(cm)),
    }
    with open(os.path.join(INTERIM, "03_log.json"), "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
