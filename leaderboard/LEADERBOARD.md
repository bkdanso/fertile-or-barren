# Fertile or Barren leaderboard

Score = intrusion-weighted ROC AUC for separating FERTILE from BARREN intrusions (0.5 = coin flip, 1.0 = perfect, below 0.5 = the index points the wrong way). 95% confidence interval from 2,000 bootstrap resamples of intrusions in brackets. "insufficient" = fewer than 5 fertile or 5 barren intrusions have the elements the index needs. See docs/SCORING.md. * = exploratory index (direction set by the authors, not a published test).

| Rank | Index | Family | All samples | Cumulates | Chilled margins + fine-grained dikes/sills | Altered | Unresolved type | Fertile / barren intrusions (all) |
|---|---|---|---|---|---|---|---|---|
| 1 | Pd/Ir (`pd_ir`) | Chalcophile ratio | 0.75 (0.62-0.85) | 0.76 (0.62-0.88) | insufficient | insufficient | insufficient | 10 / 40 |
| 2 | Pt/Pd* (`pt_pd`) | Chalcophile ratio (exploratory) | 0.71 (0.59-0.83) | 0.73 (0.60-0.85) | insufficient | insufficient | insufficient | 9 / 46 |
| 3 | S/Se (`s_se`) | Sulfur | 0.60 (0.35-0.83) | insufficient | insufficient | insufficient | insufficient | 7 / 7 |
| 4 | S (`s`) | Sulfur | 0.60 (0.47-0.72) | 0.69 (0.54-0.83) | 0.41 (0.20-0.61) | 0.66 (0.42-0.85) | 0.60 (0.41-0.77) | 21 / 48 |
| 5 | Th/Nb (`th_nb`) | Crustal contamination | 0.56 (0.47-0.65) | 0.52 (0.40-0.63) | insufficient | 0.58 (0.45-0.71) | 0.54 (0.43-0.64) | 26 / 351 |
| 6 | |Δlog(Cu/Pd)|* (`cu_pd_dev`) | Chalcophile ratio (exploratory) | 0.55 (0.42-0.69) | 0.69 (0.53-0.83) | insufficient | 0.44 (0.26-0.63) | insufficient | 9 / 31 |
| 7 | La/Sm (`la_sm`) | Crustal contamination | 0.51 (0.42-0.59) | 0.55 (0.44-0.65) | insufficient | 0.53 (0.42-0.64) | 0.51 (0.41-0.61) | 28 / 370 |
| 8 | Zr/Y* (`zr_y`) | Crustal contamination (exploratory) | 0.49 (0.41-0.57) | 0.52 (0.41-0.63) | 0.46 (0.20-0.72) | 0.46 (0.34-0.59) | 0.49 (0.40-0.60) | 29 / 384 |
| 9 | Cu/Pd (`cu_pd`) | Chalcophile ratio | 0.37 (0.19-0.58) | 0.44 (0.19-0.72) | insufficient | 0.51 (0.26-0.77) | insufficient | 9 / 31 |
| 10 | Ni/Cu* (`ni_cu`) | Chalcophile ratio (exploratory) | 0.37 (0.30-0.43) | 0.55 (0.44-0.64) | 0.37 (0.17-0.63) | 0.55 (0.43-0.66) | 0.43 (0.35-0.51) | 29 / 264 |
| 11 | Ni depletion (vs MgO) (`ni_depletion`) | Ni depletion | 0.34 (0.28-0.41) | 0.40 (0.31-0.51) | 0.40 (0.14-0.67) | 0.36 (0.26-0.48) | 0.41 (0.30-0.52) | 27 / 358 |
| 12 | Cu/Zr (`cu_zr`) | Chalcophile ratio | 0.31 (0.23-0.38) | 0.35 (0.25-0.46) | insufficient | 0.20 (0.11-0.30) | 0.41 (0.30-0.52) | 25 / 266 |

## Submit your method

See [SUBMITTING.md](SUBMITTING.md). Methods fitted on this benchmark are scored on the held-out test intrusions only (`--split test`).


*Generated 2026-10-29 by code/05_leaderboard.py from data/processed/benchmark_samples.csv.*
