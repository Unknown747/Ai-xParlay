import csv
import tempfile
import unittest
from pathlib import Path

from src.inspect_football_data import DatasetFormatError, inspect_csv
from src.prepare_football_data import prepare_csv


HEADERS = [
    "Date",
    "HomeTeam",
    "AwayTeam",
    "FTHG",
    "FTAG",
    "FTR",
    "League",
    "LeagueCode",
    "Season",
]


class InspectFootballDataTests(unittest.TestCase):
    def write_csv(self, directory: str, rows: list[list[str]]) -> Path:
        path = Path(directory) / "matches.csv"
        with path.open("w", newline="", encoding="utf-8") as output:
            writer = csv.writer(output)
            writer.writerow(HEADERS)
            writer.writerows(rows)
        return path

    def test_summarizes_leagues_seasons_and_scores(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(
                directory,
                [
                    ["06/08/05", "Crewe", "Burnley", "2.0", "1.0", "H", "Championship", "E1", "0506"],
                    ["07/08/05", "Team C", "Team D", "1", "1", "D", "Championship", "E1", "0506"],
                    ["2022-08-06", "Home X", "Away Y", "0", "2", "A", "Premier League", "E0", "2223"],
                ],
            )

            summary = inspect_csv(path)

            self.assertEqual(summary["rows_analyzed"], 3)
            self.assertEqual(summary["league_match_counts"], {"E0": 1, "E1": 2})
            self.assertEqual(summary["season_match_counts"], {"0506": 2, "2223": 1})
            self.assertEqual(summary["date_range"], {"first": "2005-08-06", "last": "2022-08-06"})
            self.assertEqual(summary["rows_without_complete_score"], 0)
            self.assertEqual(summary["result_score_mismatches"], 0)

    def test_counts_duplicate_fixtures_and_result_mismatches(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            row = ["06/08/05", "Crewe", "Burnley", "2", "1", "A", "Championship", "E1", "0506"]
            path = self.write_csv(directory, [row, row])

            summary = inspect_csv(path)

            self.assertEqual(summary["duplicate_fixture_rows"], 1)
            self.assertEqual(summary["result_score_mismatches"], 2)
            self.assertTrue(summary["warnings"])

    def test_counts_missing_scores_and_invalid_score_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(
                directory,
                [
                    ["06/08/05", "Crewe", "Burnley", "", "", "", "Championship", "E1", "0506"],
                    ["07/08/05", "Team C", "Team D", "-1", "2", "A", "Championship", "E1", "0506"],
                ],
            )

            summary = inspect_csv(path)

            self.assertEqual(summary["rows_without_complete_score"], 2)
            self.assertEqual(summary["invalid_score_values"], 1)
            self.assertEqual(summary["missing_required_values"]["home_goals"], 1)

    def test_max_rows_marks_summary_as_partial(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_csv(
                directory,
                [
                    ["06/08/05", "A", "B", "1", "0", "H", "League", "L1", "0506"],
                    ["07/08/05", "C", "D", "0", "0", "D", "League", "L1", "0506"],
                ],
            )

            summary = inspect_csv(path, max_rows=1)

            self.assertEqual(summary["rows_analyzed"], 1)
            self.assertFalse(summary["full_file_scan"])
            self.assertTrue(any("--max-rows" in warning for warning in summary["warnings"]))

    def test_requires_match_identification_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("Date,HomeTeam\n06/08/05,Crewe\n", encoding="utf-8")

            with self.assertRaises(DatasetFormatError):
                inspect_csv(path)

    def test_prepares_compact_csv_and_preserves_odds_and_unplayed_fixtures(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "wide.csv"
            output = Path(directory) / "clean" / "matches_clean.csv"
            with source.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(HEADERS + ["AvgH", "Avg>2.5", "AvgCH"])
                writer.writerow(
                    ["06/08/05", "Crewe", "Burnley", "2.0", "1.0", "H",
                     "Championship", "E1", "0506", "2.3", "1.9", "2.2"]
                )
                writer.writerow(
                    ["07/08/05", "Team C", "Team D", "", "", "",
                     "Championship", "E1", "0506", "2.5", "2.0", ""]
                )

            summary = prepare_csv(source, output)

            with output.open(newline="", encoding="utf-8") as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(summary["rows_read"], 2)
            self.assertEqual(summary["rows_written"], 2)
            self.assertEqual(summary["rows_without_complete_score"], 1)
            self.assertEqual(summary["odds_columns_preserved"], ["AvgH", "Avg>2.5", "AvgCH"])
            self.assertEqual(rows[0]["date"], "2005-08-06")
            self.assertEqual(rows[0]["home_goals"], "2")
            self.assertEqual(rows[0]["result"], "H")
            self.assertEqual(rows[0]["AvgH"], "2.3")
            self.assertEqual(rows[1]["home_goals"], "")

    def test_prepare_refuses_to_overwrite_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(
                directory,
                [["06/08/05", "Crewe", "Burnley", "2", "1", "H", "Championship", "E1", "0506"]],
            )

            with self.assertRaises(ValueError):
                prepare_csv(source, source)

    def test_prepare_reports_and_skips_rows_without_fixture_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = self.write_csv(
                directory,
                [["", "", "", "", "", "", "Championship", "E1", "0506"]],
            )
            output = Path(directory) / "clean.csv"

            summary = prepare_csv(source, output)

            self.assertEqual(summary["rows_read"], 1)
            self.assertEqual(summary["rows_written"], 0)
            self.assertEqual(summary["rows_skipped_missing_identity"], 1)
            self.assertEqual(summary["missing_dates"], 1)
            self.assertEqual(summary["missing_home_teams"], 1)
            self.assertEqual(summary["missing_away_teams"], 1)
            self.assertEqual(summary["invalid_dates"], 0)


if __name__ == "__main__":
    unittest.main()
