# Verification record (v0.1.0)

*Plain-language note: a record of what the authors checked and decided before release, so anyone can see how the labels were reached. The authors' completed files are kept unchanged in `data/curated/author_review/`.*

## Checked by the authors (October 2026)

- The pipeline was re-run and the headline numbers matched; the QA report showed no failures.
- All five source links were checked, and so was the CC BY-SA 4.0 data license.
- Eleven samples were checked by hand against the GEOROC source files (six named, five random): all matched.
- The two references flagged by the unit guard ([23290], [24352]) were checked against the original papers: their platinum-group element values were in ppb and were converted to ppm.
- Samples with MgO < 0.5 wt% were confirmed as anorthosites. Low-MgO values in other rock types were blanked as source errors.
- All 127 intrusions in `label_review.csv` were reviewed and given a decision.
- Deposit names, types and short references were supplied in `intrusion_deposit_reference.csv`. Full citations were then located through Crossref metadata and recorded in `data/curated/intrusion_labels_curated.csv`.

## Decisions

| Item | Decision |
|---|---|
| Reef-type PGE intrusions (Bushveld, Stillwater, Great Dyke, Panton, Fedorova-Pana) | FERTILE |
| Dumont | FERTILE |
| Kongsberg, Modum (Ertelien mine), Haines (Shebandowan mine) | FERTILE |
| Katiniq (Raglan) | kept (intrusive komatiitic sill) |
| Skaergaard, Caraíba | WEAK |
| Agnew | WEAK (the Shakespeare deposit is in a separate intrusion) |
| Närankävaara, Kivakka | WEAK (reef-type PGE prospects) |
| Monts de Cristal | BARREN (no documented occurrence) |
| 22 regional groups, ophiolites, mantle massifs, carbonatites, greenstone belts and generic names | EXCLUDE |
| 15 medium-confidence barren intrusions | BARREN (no occurrence named) |
| Kammikivi high-Ni dunites | kept |
| "Jinchuan area" samples | assigned to the Jinchuan intrusion |
| Index directions (including the four exploratory indices) | kept as defined |
| Deposit-matching radius | 10 km |
| Josephine Opare Dankwa | ORCID 0009-0000-6105-1213 |

## Not yet done (stated in the paper and in LIMITATIONS)

- The systematic expert review of sample-type tags (`sample_type_review.csv`) is deferred to v0.2. No agreement rate is reported.
- No full citation was located for the chromite occurrences the authors reported at Chilas (Jan and Windley). Chilas is BARREN either way.

## Release approval

On 29 October 2026 the corresponding author approved releasing v0.1.0 (benchmark data, labels, scoring program, leaderboard, figures and tables; no manuscript) under the three authors' names. The README summary was written by the authors. Zenodo DOI reserved: 10.5281/zenodo.23777406.
