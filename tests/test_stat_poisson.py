import unittest
from datetime import date

from src.stat_poisson import (
    HistoricalMatch,
    InsufficientHistoryError,
    PoissonSettings,
    predict_match,
    scoreline_probabilities,
)


def match(day: int, home: str, away: str, home_goals: int, away_goals: int) -> HistoricalMatch:
    return HistoricalMatch(
        match_date=date(2024, 1, day),
        league_code="E0",
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
    )


class PoissonModelTests(unittest.TestCase):
    def sample_history(self) -> list[HistoricalMatch]:
        return [
            match(1, "Home FC", "Club A", 2, 0),
            match(2, "Club B", "Away FC", 1, 1),
            match(3, "Home FC", "Club C", 1, 0),
            match(4, "Club D", "Away FC", 2, 1),
            match(5, "Home FC", "Club E", 3, 2),
            match(6, "Club F", "Away FC", 0, 2),
            match(7, "Club G", "Club H", 1, 0),
        ]

    def test_market_probabilities_are_bounded_and_coherent(self) -> None:
        probabilities = scoreline_probabilities(1.45, 1.1)

        self.assertAlmostEqual(
            probabilities["p_home"] + probabilities["p_draw"] + probabilities["p_away"],
            1.0,
            places=12,
        )
        self.assertAlmostEqual(
            probabilities["p_over_2_5"] + probabilities["p_under_2_5"],
            1.0,
            places=12,
        )
        self.assertAlmostEqual(probabilities["p_btts"] + probabilities["p_no_btts"], 1.0, places=12)
        self.assertTrue(all(0 <= value <= 1 for value in probabilities.values()))

    def test_prediction_uses_past_matches_and_reports_probabilities(self) -> None:
        prediction = predict_match(
            self.sample_history(),
            league_code="E0",
            home_team="Home FC",
            away_team="Away FC",
            prediction_date=date(2024, 1, 8),
        )

        self.assertEqual(prediction["home_form_matches"], 3)
        self.assertEqual(prediction["away_form_matches"], 3)
        self.assertEqual(prediction["prior_source"], "READ.md_prior_blended_with_past_league_matches")
        self.assertGreater(prediction["lambda_home"], 0)
        self.assertGreater(prediction["lambda_away"], 0)

    def test_same_day_and_future_matches_do_not_change_prediction(self) -> None:
        history = self.sample_history()
        baseline = predict_match(
            history,
            league_code="E0",
            home_team="Home FC",
            away_team="Away FC",
            prediction_date=date(2024, 1, 8),
        )
        with_later_matches = history + [
            match(8, "Home FC", "Away FC", 10, 0),
            HistoricalMatch(
                match_date=date(2025, 1, 1),
                league_code="E0",
                home_team="Home FC",
                away_team="Away FC",
                home_goals=0,
                away_goals=10,
            ),
        ]
        after_later_matches = predict_match(
            with_later_matches,
            league_code="E0",
            home_team="Home FC",
            away_team="Away FC",
            prediction_date=date(2024, 1, 8),
        )

        self.assertEqual(baseline["lambda_home"], after_later_matches["lambda_home"])
        self.assertEqual(baseline["lambda_away"], after_later_matches["lambda_away"])
        self.assertEqual(baseline["probabilities"], after_later_matches["probabilities"])

    def test_unknown_league_prior_uses_observed_past_mean(self) -> None:
        history = [
            HistoricalMatch(
                match_date=m.match_date,
                league_code="X1",
                home_team=m.home_team,
                away_team=m.away_team,
                home_goals=m.home_goals,
                away_goals=m.away_goals,
            )
            for m in self.sample_history()
        ]
        prediction = predict_match(
            history,
            league_code="X1",
            home_team="Home FC",
            away_team="Away FC",
            prediction_date=date(2024, 1, 8),
        )

        self.assertEqual(prediction["prior_source"], "observed_pre_match_league_average")

    def test_insufficient_team_history_fails_explicitly(self) -> None:
        with self.assertRaises(InsufficientHistoryError):
            predict_match(
                self.sample_history()[:2],
                league_code="E0",
                home_team="Home FC",
                away_team="Away FC",
                prediction_date=date(2024, 1, 8),
                settings=PoissonSettings(min_n=3, last_n=10),
            )


if __name__ == "__main__":
    unittest.main()
