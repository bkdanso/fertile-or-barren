#!/usr/bin/env python3
"""01_fetch.py - download every raw input and log its provenance.

Plain-language note: this script downloads the public data the benchmark is built
from (GEOROC rock-chemistry files and three USGS deposit lists) into data/raw/, and
writes one line per file to data/raw/PROVENANCE.txt saying where it came from, when,
and its fingerprint (SHA-256). You do not need to open it.

File URLs are discovered at run time from each repository's public API (GRO.data
Dataverse for GEOROC, ScienceBase for USGS), so a stranger re-running it gets the
same files as long as the pinned dataset versions still exist.
"""
import json
import os
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
LOG = os.path.join(RAW, "PROVENANCE.txt")
os.makedirs(os.path.join(RAW, "georoc"), exist_ok=True)

# GEOROC precompiled files (GRO.data), all tectonic-setting compilations. Together they
# hold every GEOROC sample, including rocks the Rock Types compilation omits (e.g. the
# Stillwater samples named only "CUMULATE", and troctolites). Versions pinned.
GEOROC_SETTINGS = {
    "doi:10.25625/1KRR1P": ("13.0", "Archaean Cratons"),
    "doi:10.25625/KAIVCT": ("13.0", "Rift Volcanics"),
    "doi:10.25625/PVFZCE": ("13.0", "Convergent Margins"),
    "doi:10.25625/1VOFM5": ("13.0", "Complex Volcanic Settings"),
    "doi:10.25625/WSTPOX": ("13.0", "Continental Flood Basalts"),
    "doi:10.25625/RZZ9VM": ("13.0", "Intraplate Volcanic Rocks"),
    "doi:10.25625/JRZIJF": ("13.0", "Oceanic Plateaus"),
    "doi:10.25625/WFJZKY": ("13.0", "Ocean Island Groups"),
    "doi:10.25625/AVLFC2": ("13.0", "Ocean Basin Flood Basalts"),
    "doi:10.25625/JUQK7N": ("13.0", "Seamounts"),
}
# Rock Types compilation: downloaded for the mafic-ultramafic rock files only, as a
# completeness cross-check (every one of its intrusive samples must appear above).
GEOROC_DOI = "doi:10.25625/2JETOA"
GEOROC_VERSION = "15.0"
GEOROC_ROCKS = [
    "ANORTHOSITE", "CLINOPYROXENITE", "DOLERITE", "DUNITE", "GABBRO", "GABBRONORITE",
    "HARZBURGITE", "LHERZOLITE", "MONZOGABBRO", "NORITE", "ORTHOPYROXENITE", "PERIDOTITE",
    "PICRITE", "PYROXENITE", "WEBSTERITE", "WEHRLITE",
]
SCIENCEBASE = {
    "usgs_critical_minerals_v3": ("6464de5bd34ec179a83d9e6c", ["critical_mineral_deposits_all_tables_v3.xlsx.xlsx"]),
    "usgs_nicupge_2026": ("69cad8dcb66b01c9d489733f", ["NiCuPGE_FS_Csv_files.zip", "NiCuPGE_FS_Shapefiles.zip"]),
}
MRDS_URL = "https://mrdata.usgs.gov/mrds/mrds-csv.zip"
UA = {"User-Agent": "fertile-or-barren-benchmark/0.1 (research; contact via GitHub repo)"}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return json.load(r)


def download(url, dest, note=""):
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"  exists, skipping: {os.path.relpath(dest, ROOT)}")
        return
    print(f"  downloading {os.path.relpath(dest, ROOT)}")
    import time
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=600) as r, open(dest + ".part", "wb") as f:
                while True:
                    chunk = r.read(1 << 20)
                    if not chunk:
                        break
                    f.write(chunk)
            break
        except OSError as e:
            print(f"  retry {attempt + 1} after error: {e}")
            time.sleep(10 * (attempt + 1))
    else:
        raise RuntimeError(f"failed to download {url}")
    os.replace(dest + ".part", dest)
    subprocess.run([sys.executable, os.path.join(ROOT, "code", "provenance.py"), dest, url,
                    "--log", LOG, "--note", note], check=True)


def georoc_settings():
    from concurrent.futures import ThreadPoolExecutor
    jobs = []
    for doi, (ver, label) in GEOROC_SETTINGS.items():
        meta = get_json("https://data.goettingen-research-online.de/api/datasets/:persistentId/versions/"
                        f"{ver}?persistentId={doi}")["data"]
        sub = os.path.join(RAW, "georoc_settings", doi.split("/")[-1])
        os.makedirs(sub, exist_ok=True)
        for f in meta["files"]:
            name = f["dataFile"]["filename"].replace(" ", "")
            if not name.lower().endswith(".csv"):
                continue
            fid = f["dataFile"]["id"]
            jobs.append((f"https://data.goettingen-research-online.de/api/access/datafile/{fid}",
                         os.path.join(sub, name), f"GRO.data {doi} ({label}) v{ver} file id {fid}"))
    print(f"GEOROC tectonic-setting compilations: {len(jobs)} files")
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda j: download(*j), jobs))


def main():
    georoc_settings()
    print("GEOROC Rock Types compilation (cross-check)", GEOROC_DOI, "version", GEOROC_VERSION)
    meta = get_json("https://data.goettingen-research-online.de/api/datasets/:persistentId/versions/"
                    f"{GEOROC_VERSION}?persistentId={GEOROC_DOI}")["data"]
    for f in meta["files"]:
        name = f["dataFile"]["filename"]
        stem = name.split("_", 1)[1].rsplit(".", 1)[0]          # e.g. GABBRO_part1
        rock = stem.split("_part")[0]
        if rock in GEOROC_ROCKS:
            fid = f["dataFile"]["id"]
            download(f"https://data.goettingen-research-online.de/api/access/datafile/{fid}",
                     os.path.join(RAW, "georoc", name),
                     note=f"GRO.data {GEOROC_DOI} v{GEOROC_VERSION} file id {fid}")
    for key, (item, wanted) in SCIENCEBASE.items():
        print("ScienceBase", key, item)
        os.makedirs(os.path.join(RAW, key), exist_ok=True)
        files = get_json(f"https://www.sciencebase.gov/catalog/item/{item}?format=json")["files"]
        for f in files:
            if f["name"] in wanted:
                download(f["url"], os.path.join(RAW, key, f["name"]),
                         note=f"ScienceBase item {item}; URL found via item JSON 'files' list")
    print("USGS MRDS")
    os.makedirs(os.path.join(RAW, "mrds"), exist_ok=True)
    download(MRDS_URL, os.path.join(RAW, "mrds", "mrds-csv.zip"), note="USGS MRDS full CSV export")
    print("done")


if __name__ == "__main__":
    main()
