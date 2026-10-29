# How the benchmark is scored

*Plain-language summary: each method gives every rock sample a number, with higher meaning "more likely from an ore-bearing intrusion". The scoring program checks how often fertile intrusions get higher numbers than barren ones. A score of 1.0 is perfect, 0.5 is a coin flip, and below 0.5 means the method points the wrong way. Every intrusion counts equally, however many samples it has.*

## Classes
- Positive: intrusions labeled **FERTILE** (they host a magmatic Ni-Cu-PGE sulfide deposit, or a reef-type PGE deposit, with a reported resource or production).
- Negative: intrusions labeled **BARREN**.
- **WEAK** intrusions (only occurrences or prospects) are kept in the data but not scored in v0.1.

## Metric
- **AUC_w**: the area under the ROC curve, with each sample weighted by 1 / (number of samples from its intrusion in the stratum). Tied scores count half.
- **95% CI**: 2,000 bootstrap resamples of intrusions, resampled separately within fertile and barren (seed 20270801).
- **AUC_intrusion**: AUC on the median score of each intrusion (in `leaderboard/results.csv`).
- **Coverage**: the share of samples in the stratum that the method could score (the needed elements were measured).
- A stratum is scored only if at least **5 fertile and 5 barren intrusions** have scores; otherwise it is reported as "insufficient".

## Strata (sample types)
| Stratum | Sample types included |
|---|---|
| ALL | everything |
| LIQUID_PROXY | CHILLED_MARGIN + FINE_GRAINED_DIKE_SILL (closest to magma composition) |
| CUMULATE | CUMULATE |
| ALTERED | ALTERED |
| UNRESOLVED | UNRESOLVED |

Sample-type rules are listed at the top of `code/04_sample_types.py`.

## Splits
`split` = `train` (70%) or `test` (30%) of intrusions, fixed by seed and stratified by label. Indices with no fitted parameters are reported on all intrusions. **Any method whose parameters were fitted or tuned on this benchmark must report `--split test` only.**

## Sensitivity
`results.csv` also reports `ALL_auc_w_sensitivity`, which drops LOW-confidence barren intrusions (those only "barren" because no deposit is on record).

## Direction convention
Scores must be oriented so that higher = more fertile. The 12 built-in indices are oriented according to the hypothesis in their source paper (see `code/indices.py`); an AUC below 0.5 therefore means the published hypothesis does not hold on this benchmark.
