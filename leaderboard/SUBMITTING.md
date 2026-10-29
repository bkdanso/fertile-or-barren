# Submitting a method to the leaderboard

*Plain-language summary: send a file with one score per sample and a short description. The maintainers run the same scoring program on it and add a row to the table.*

1. Compute a score for each `UNIQUE_ID` in `data/processed/benchmark_samples.csv`. Higher = more likely fertile. Leave blank where your method cannot score a sample.
2. Save it as `submissions/<your_method_id>.csv` with columns `UNIQUE_ID,score`.
3. Run `python code/score.py --submission submissions/<your_method_id>.csv` (add `--split test` if anything in your method was fitted or tuned on this benchmark).
4. Open a pull request on GitHub containing the submission file and a short entry: method name, reference (DOI), elements used, whether it was fitted on the benchmark, and your contact.
5. The maintainers re-run the scoring and add your row to `LEADERBOARD.md`.

Rules: do not use the `label`, `label_confidence` or `intrusion_key` columns, or intrusion names, as inputs. Report the benchmark version you scored against.
