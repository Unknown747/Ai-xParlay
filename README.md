# Ai-xParlay

Python tools for inspecting football results and odds before building the prediction models described in `READ.md`.

Current progress: CSV inspection/preparation and a first single-match Poisson predictor are implemented. The xG model, AI integrations, ensemble, and backtesting are still planned.

## Inspect the local CSV

Put the CSV at `data/historis/all_football_data.csv`, or pass another file path:

```bash
python -m src.inspect_football_data
python -m src.inspect_football_data path/to/all_football_data.csv
```

The inspector reads the file row by row, so a CSV larger than 50 MB does not need to be loaded into memory or split by season. It reports the columns, leagues, seasons, date coverage, missing values, invalid scores, inconsistent results, and duplicate fixtures. Duplicate checking uses a temporary SQLite file that is deleted after the scan.

For a quick partial scan:

```bash
python -m src.inspect_football_data --max-rows 1000
```

To save the JSON summary:

```bash
python -m src.inspect_football_data --output data_summary.json
```

## Prepare a compact CSV for the models

After inspecting the source, create the normalized file:

```bash
python -m src.prepare_football_data
```

The default input is `data/historis/all_football_data.csv`; the compact output is `data/historis/matches_clean.csv`. To use another source path:

```bash
python -m src.prepare_football_data path/to/all_football_data.csv --output data/historis/matches_clean.csv
```

Preparation also streams the input. It retains every identifiable league/season match, standardizes dates and scores, keeps fixtures without results, and preserves available average/Bet365 1x2 and O/U odds columns. Rows missing a match date or teams are counted in the report and skipped; the original CSV is never changed. It does not split the source by season.

The imported CSV and Understat JSON files are ignored by Git. Keep the original dataset in its existing source or local storage; do not commit another copy of the large file. No external API key or third-party Python package is required for these data-preparation steps.

## Calculate first Poisson probabilities

After creating the compact CSV, calculate probabilities for one fixture:

```bash
python -m src.stat_poisson --league E0 --home "Home Team" --away "Away Team" --date 2026-10-06
```

The default input is `data/historis/matches_clean.csv`; use `--csv path/to/matches_clean.csv` to choose another file. Team names must match the compact CSV. The prediction uses only completed matches in the same league dated strictly before the requested date; matches on the same date are excluded.

The first model uses the last 10 home matches for the home team and last 10 away matches for the away team, requiring at least 3 of each. `K=6` shrinks team rates toward the league scoring rate; `W_PRIOR=100` blends the prior goals-per-match values from `READ.md` with previous league results. For league codes without a prior in `READ.md`, the model uses the observed pre-match league average and identifies that in its output.

The command reports probabilities for Over/Under 2.5, home/draw/away, and BTTS. It does not select a bet or place bets. This is a first statistical baseline, not a validated strategy or a guarantee of return.

Run the tests with:

```bash
python -m unittest discover -s tests -v
```

The CSV inspector does not send data to an AI service. Review the source's usage terms before adding automated downloads or external AI processing.
