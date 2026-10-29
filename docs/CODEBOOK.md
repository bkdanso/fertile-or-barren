# Codebook

*Plain-language summary: what every column in the two main data files means and where it comes from. Open this when you look at the spreadsheets.*

## data/processed/benchmark_samples.csv (one row per rock analysis)

| Column | Meaning | Source / transformation |
|---|---|---|
| UNIQUE_ID | GEOROC's permanent sample-analysis ID | GEOROC, unchanged |
| SAMPLE NAME | Sample name with GEOROC reference number in brackets | GEOROC |
| CITATIONS | GEOROC reference number(s) for the source paper | GEOROC; look up at georoc.eu |
| LOCATION, LOCATION COMMENT | GEOROC location hierarchy and free-text note | GEOROC |
| lat, lon | Midpoint of GEOROC's latitude/longitude min-max (decimal degrees, WGS84) | computed |
| rock_name | GEOROC rock name, upper case, reference numbers removed | GEOROC, cleaned |
| ROCK TEXTURE, ALTERATION | GEOROC texture text and alteration code as recorded by GEOROC (F, S, M or E); codes M and E are treated as altered | GEOROC |
| intrusion_name | Location level (or comment) used to identify the intrusion | code/02_intrusions.py |
| intrusion_key | Normalized intrusion name used for grouping | code/02_intrusions.py + data/curated/intrusion_aliases.csv |
| intrusion_unit | Deepest location level (e.g. a sub-unit or drill core) | GEOROC |
| georoc_file | GEOROC compilation file the row came from | provenance |
| sample_type | CUMULATE, CHILLED_MARGIN, FINE_GRAINED_DIKE_SILL, ALTERED or UNRESOLVED | code/04_sample_types.py rules |
| type_rule, type_rule_strength | Which rule assigned the type; strong / weak / none | code/04_sample_types.py |
| label | FERTILE, WEAK or BARREN (of the intrusion) | code/03_labels.py + data/curated/intrusion_labels_curated.csv |
| label_confidence | HIGH (deposit or other-type mineralization documented in the literature), MEDIUM (author-reviewed, or automatic evidence in a well-covered area), LOW (barren with no positive evidence in a poorly covered area) | code/03_labels.py |
| split | train / test (70/30 by intrusion, stratified by label, seed 20270801) | code/04_sample_types.py |
| *X*(WT%) | Major-element oxides and volatiles, weight percent | GEOROC, unchanged, except MgO below 0.5 wt% blanked in non-anorthosite rocks (docs/review/mgo_blanked.csv) |
| *X*(PPM) | Trace elements, parts per million | GEOROC, unchanged, except platinum-group elements for references [23290] and [24352] converted from ppb to ppm (author-confirmed; data/curated/pge_unit_corrections.csv) |

In the indices, sulfur combines S(PPM) with S(WT%) x 10,000, and nickel falls back to NiO(WT%) converted to Ni ppm. Zero and negative values are treated as missing.

## data/processed/intrusions.csv (one row per intrusion)

| Column | Meaning |
|---|---|
| intrusion_key, names, region | Normalized key, the GEOROC name, and the top GEOROC location level |
| n_samples | Samples in the benchmark |
| lat, lon, coord_precise_share | Median coordinates; share of samples whose latitude range is under 0.05 degrees |
| label, label_source, confidence | Final label, whether it came from the curated list or automatic rules, and its confidence |
| auto_label, curated_label | The automatic label, and the curated label if there is one |
| deposit, deposit_type, reference | Deposit hosted, its type, and the full supporting reference (curated; citations checked against Crossref) |
| evidence, n_mrds_near | Automatic evidence: USGS / MRDS records within 10 km |
| split | train / test |
| CUMULATE ... UNRESOLVED | Sample counts by type |
