#!/usr/bin/env python3
"""02_intrusions.py - select mafic-ultramafic intrusive samples and assign each to an intrusion.

Plain-language note: this script reads the GEOROC rock files, keeps only rocks that
cooled underground as intrusions (dropping lavas, mantle fragments carried up in
volcanoes, and ophiolite mantle), removes duplicate analyses, and works out which
named intrusion each sample belongs to from GEOROC's location text. Output:
data/interim/samples_with_intrusion.csv.gz and a log of what was dropped and why.
You do not need to open it; the counts it prints appear in data/processed/qa_report.txt.
"""
import glob
import warnings
import json
import os
import re

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw", "georoc_settings")
RAW_ROCKTYPES = os.path.join(ROOT, "data", "raw", "georoc")
INTERIM = os.path.join(ROOT, "data", "interim")
os.makedirs(INTERIM, exist_ok=True)

# Rock names (GEOROC ROCK NAME, brackets removed) kept as mafic-ultramafic intrusive rocks.
MAFIC_UM_RE = re.compile(
    r"GABBRO|NORITE|TROCTOLITE|ANORTHOSITE|PERIDOTITE|DUNITE|HARZBURGITE|LHERZOLITE|WEHRLITE|"
    r"PYROXENITE|WEBSTERITE|BRONZITITE|HARRISITE|DOLERITE|DIABASE|PICRITE|CUMULATE|CHROMITITE|"
    r"ULTRAMAFIC|SERPENTINITE|TROCTOLITIC|MELANORITE|LEUCONORITE")
NOT_MAFIC_RE = re.compile(r"GRANIT|DIORITE|SYENITE|TONALITE|MONZONITE|RHYOLIT|DACIT|ANDESIT|TRACHY|CARBONATITE|KIMBERLIT|LAMPRO")

# Location or rock-name text that marks a sample as NOT a crustal mafic-ultramafic intrusion.
EXCLUDE_PATTERNS = {
    "xenolith_or_kimberlite": r"XENOLITH|KIMBERLITE|NODULE|INCLUSION IN",
    "ophiolite_or_abyssal_mantle": r"OPHIOLITE|ABYSSAL|MID-OCEAN RIDGE|FRACTURE ZONE|FOREARC PERIDOTITE",
    "alkaline_carbonatite_complex": r"ALKALINE|CARBONATITE|KOVDOR|LOVOZERO|KHIBIN|VUORIYARVI|SALMAGORA|AFRIKANDA|TURIY|IJOLITE",
    "orogenic_mantle_massif": r"HOROMAN|RONDA|LANZO|BENI BOUSERA|ZABARGAD|LHERZ\b|BALDISSERO|BALMUCCIA|ERRO-TOBBIO|ALPE ARAMI|FINERO PERIDOTITE",
}
# Words that identify a location level as a named intrusion.
INTRUSION_RE = re.compile(
    r"\b(INTRUSIONS?|INTRUSIVE|COMPLEX|SILLS?|LAYERED|PLUTON|CHONOLITH|LOPOLITH|"
    r"GABBRO|NORITE|TROCTOLITE|PERIDOTITE|DUNITE|PYROXENITE|DOLERITE|DIABASE|DIKE|DYKE|STOCK)\b")
GROUP_RE = re.compile(r"GROUP OF INTRUSIONS|SWARM|PROVINCE|BELT\b|TERRANE|CRATON|SUPERGROUP|GNEISS|GRANIT|"
                      r"VOLCANIC|METAMORPHIC|BASAL COMPLEX|NEVADO|OROGEN|MASSIF CENTRAL|FORMATION|BOHEMIAN MASSIF|ARMORICAN MASSIF")
# Generic words stripped to make an intrusion key ("BUSHVELD IGNEOUS COMPLEX" -> "BUSHVELD").
STRIP_RE = re.compile(
    r"\b(THE|IGNEOUS|LAYERED|INTRUSIVE|INTRUSIONS?|COMPLEX|MAFIC|ULTRAMAFIC|MAFIC-ULTRAMAFIC|"
    r"ULTRAMAFIC-MAFIC|SILL|PLUTON|MASSIF|BODY|METAGABBRO|LOPOLITH|CHONOLITH|STOCK|SUITE|SERIES|GABBROIC|PLUTONIC)\b")
COMMENT_RE = re.compile(
    r"([A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){0,3}) (?:LAYERED |MAFIC |ULTRAMAFIC |MAFIC-ULTRAMAFIC |IGNEOUS )*"
    r"(INTRUSION|COMPLEX|SILL|CHONOLITH|LOPOLITH|PLUTON)\b")

warnings.simplefilter("ignore", pd.errors.PerformanceWarning)


def clean_rock(s):
    return re.sub(r"\s*\[\d+\]\s*", " ", str(s)).strip()


BODY_RE = re.compile(r"\b(BODY|SUITE|MASSIF|METAGABBRO|METADOLERITE)\b")
DEPOSIT_RE = re.compile(r"([A-Z][A-Z'\-]+(?: [A-Z][A-Z'\-]+){0,2}) (?:CU-NI|NI-CU|NI|NICKEL|CU-NI-PGE|NI-CU-PGE|PGE) "
                        r"(?:SULFIDE |SULPHIDE )?(?:DEPOSIT|ORE BODY)|([A-Z][A-Z'\-]+) ORE BODY")


def intrusion_from_location(loc):
    parts = [p.strip() for p in str(loc).split(" / ")]
    named = [p for p in parts if INTRUSION_RE.search(p) and not GROUP_RE.search(p)]
    if named:
        return named[0], parts[-1]      # shallowest named level = parent intrusion; deepest = unit
    # Second rule: the deepest level names a body, suite or massif (not a province, belt or swarm).
    if len(parts) >= 2 and BODY_RE.search(parts[-1]) and not GROUP_RE.search(parts[-1]):
        return parts[-1], parts[-1]
    return None, None


def intrusion_from_comment(txt):
    t = str(txt).upper()
    m = COMMENT_RE.search(t)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    m = DEPOSIT_RE.search(t)                # host of a named Ni-Cu(-PGE) deposit or ore body
    if m:
        return (m.group(1) or m.group(2)) + " INTRUSION"
    return None


def key_of(name):
    import unicodedata
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    k = STRIP_RE.sub(" ", name.upper().replace("(H)", "H").replace("-", " - "))
    k = re.sub(r"[^A-Z0-9' ]", " ", k)
    k = re.sub(r"\s+", " ", k).strip()
    return k or name.upper().strip()


def main():
    files = sorted(glob.glob(os.path.join(RAW, "*", "*.csv")))
    frames, all_ids = [], set()
    log = {"files": len(files), "rows_read": 0, "rows_plutonic": 0, "rows_plutonic_mafic_um_name": 0}
    for f in files:
        df = pd.read_csv(f, encoding="latin1", low_memory=False)
        uid = pd.to_numeric(df["UNIQUE_ID"], errors="coerce")
        log["rows_malformed_unique_id"] = log.get("rows_malformed_unique_id", 0) + int((uid.isna() & df["UNIQUE_ID"].notna()).sum())
        df = df[uid.notna()].assign(UNIQUE_ID=uid[uid.notna()].astype(int))
        all_ids |= set(df["UNIQUE_ID"].astype(int))
        log["rows_read"] += len(df)
        df = df[df["ROCK TYPE"] == "PLU"]
        log["rows_plutonic"] += len(df)
        rn = df["ROCK NAME"].map(clean_rock).str.upper()
        keep = rn.str.contains(MAFIC_UM_RE) & ~rn.str.contains(NOT_MAFIC_RE)
        df = df[keep].assign(rock_name=rn[keep], georoc_file=os.path.basename(f))
        log["rows_plutonic_mafic_um_name"] += len(df)
        frames.append(df.loc[:, ~df.columns.str.startswith("Unnamed")])
    d = pd.concat(frames, ignore_index=True)
    d["UNIQUE_ID"] = d["UNIQUE_ID"].astype(int)
    log["unique_samples_in_georoc_union"] = len(all_ids)
    before = len(d)
    d = d.drop_duplicates("UNIQUE_ID")
    log["duplicate_rows_dropped"] = before - len(d)
    log["mafic_ultramafic_plutonic_samples"] = int(len(d))

    text = (d["LOCATION"].fillna("") + " | " + d["ROCK NAME"].fillna("") + " | " +
            d["LOCATION COMMENT"].fillna("")).str.upper()
    for reason, pat in EXCLUDE_PATTERNS.items():
        m = text.str.contains(pat, regex=True)
        log[f"dropped_{reason}"] = int(m.sum())
        d, text = d[~m], text[~m]
    # Ore samples (rock name says ore or massive sulfide) would make "fertile" trivially detectable;
    # disseminated or net-textured sulfide-bearing rocks are kept (they are what exploration samples look like).
    # Applied to the rock name only, so "ore district" or "ore body" in a location note does not remove a sample.
    ore = d["rock_name"].str.contains(r"\bORES?\b(?!-)|MASSIVE SUL[FP]HIDE|\bGOSSAN\b", regex=True)
    log["dropped_ore_sample"] = int(ore.sum())
    d = d[~ore].copy()
    loc = d["LOCATION"].map(intrusion_from_location)
    d["intrusion_name"] = [x[0] for x in loc]
    d["intrusion_unit"] = [x[1] for x in loc]
    d["intrusion_source"] = np.where(d["intrusion_name"].notna(), "LOCATION", None)
    # Curated location-comment patterns (data/curated/location_patterns.csv) come before generic rules.
    pat_file = os.path.join(ROOT, "data", "curated", "location_patterns.csv")
    if os.path.exists(pat_file):
        for _, p in pd.read_csv(pat_file).iterrows():
            m = d["intrusion_name"].isna() & d["LOCATION COMMENT"].fillna("").str.upper().str.contains(p["pattern"], regex=True)
            log.setdefault("curated_pattern_matches", {})[p["pattern"]] = int(m.sum())
            d.loc[m, "intrusion_name"] = p["intrusion_name"]
            d.loc[m, "intrusion_source"] = "curated location pattern"
    need = d["intrusion_name"].isna()
    from_comment = d.loc[need, "LOCATION COMMENT"].map(intrusion_from_comment)
    d.loc[need, "intrusion_name"] = from_comment
    d.loc[need & d["intrusion_name"].notna(), "intrusion_source"] = "LOCATION COMMENT"
    log["samples_without_intrusion_name"] = int(d["intrusion_name"].isna().sum())
    d = d[d["intrusion_name"].notna()].copy()
    d["intrusion_key"] = d["intrusion_name"].map(key_of)
    alias_file = os.path.join(ROOT, "data", "curated", "intrusion_aliases.csv")
    if os.path.exists(alias_file):
        al = pd.read_csv(alias_file)
        amap = dict(zip(al["alias_key"], al["canonical_key"]))
        log["samples_renamed_by_alias"] = int(d["intrusion_key"].isin(amap).sum())
        d["intrusion_key"] = d["intrusion_key"].replace(amap)
    d["lat"] = d[["LATITUDE MIN", "LATITUDE MAX"]].mean(axis=1)
    d["lon"] = d[["LONGITUDE MIN", "LONGITUDE MAX"]].mean(axis=1)
    d["region"] = d["LOCATION"].str.split(" / ").str[0]

    # Completeness cross-check against the Rock Types compilation (mafic-UM files).
    rt = pd.concat([pd.read_csv(f, encoding="latin1", low_memory=False, usecols=["UNIQUE_ID", "ROCK TYPE"])
                    for f in glob.glob(os.path.join(RAW_ROCKTYPES, "*.csv"))])
    rt_ids = set(rt.loc[rt["ROCK TYPE"] == "PLU", "UNIQUE_ID"].dropna().astype(int))
    log["rocktypes_plutonic_ids"] = len(rt_ids)
    log["rocktypes_ids_missing_from_settings_union"] = len(rt_ids - all_ids)
    log["samples_kept"] = int(len(d))
    log["intrusions"] = int(d["intrusion_key"].nunique())
    d.to_csv(os.path.join(INTERIM, "samples_with_intrusion.csv.gz"), index=False)

    g = d.groupby("intrusion_key").agg(
        n_samples=("UNIQUE_ID", "size"),
        names=("intrusion_name", lambda s: "; ".join(sorted(set(s))[:3])),
        region=("region", lambda s: s.dropna().mode().iat[0] if s.notna().any() else ""),
        lat=("lat", "median"), lon=("lon", "median"),
        n_pd=("PD(PPM)", lambda s: int(s.notna().sum())),
        n_cu=("CU(PPM)", lambda s: int(s.notna().sum())),
    ).sort_values("n_samples", ascending=False)
    g.to_csv(os.path.join(INTERIM, "intrusion_candidates.csv"))
    with open(os.path.join(INTERIM, "02_log.json"), "w") as f:
        json.dump(log, f, indent=2)
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
