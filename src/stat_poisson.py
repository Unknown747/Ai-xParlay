"""Poisson probabilities for one match using only earlier results in the same league."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

from src.inspect_football_data import _parse_score


DEFAULT_CSV = Path("data/historis/matches_clean.csv")

# Prior goals per match from READ.md, keyed by football-data league code.
PRIOR_GPM: dict[str, float] = {
    "E0": 2.88,   # Premier League
    "SP1": 2.96,  # La Liga
    "D1": 3.86,   # Bundesliga
    "I1": 2.85,   # Serie A
    "F1": 2.88,   # Ligue 1
    "E1": 2.83,   # Championship
    "N1": 3.74,   # Eredivisie
    "P1": 2.72,   # Primeira Liga
    "T1": 2.92,   # Turkey
}


class InsufficientHistoryError(ValueError):
    """Raised when there is not enough prior match history for a prediction."""


@dataclass(frozen=True)
class HistoricalMatch:
    match_date: date
    league_code: str
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class PoissonSettings:
    k: float = 6.0
    last_n: int = 10
    min_n: int = 3
    w_prior: float = 100.0
    home_share: float = 0.50
    prior_gpm: Mapping[str, float] = field(default_factory=lambda: PRIOR_GPM.copy())

    def validate(self) -> None:
        if self.k < 0 or self.w_prior < 0:
            raise ValueError("K dan W_PRIOR harus bernilai non-negatif.")
        if self.last_n < 1 or self.min_n < 1 or self.min_n > self.last_n:
            raise ValueError("LAST_N harus >= MIN_N dan keduanya harus positif.")
        if not 0 < self.home_share < 1:
            raise ValueError("HOME_SHARE harus lebih besar dari 0 dan lebih kecil dari 1.")
        if any(not math.isfinite(value) or value <= 0 for value in self.prior_gpm.values()):
            raise ValueError("Semua nilai prior_gpm harus positif dan berhingga.")


def _team_key(team: str) -> str:
    return " ".join(team.casefold().split())


def _smoothed_rate(goals: Iterable[int], baseline: float, k: float) -> float:
    values = list(goals)
    return (sum(values) + k * baseline) / (len(values) + k)


def _poisson_vector(rate: float, max_goals: int) -> list[float]:
    values = [math.exp(-rate)]
    for goals in range(1, max_goals + 1):
        values.append(values[-1] * rate / goals)
    return values


def scoreline_probabilities(lambda_home: float, lambda_away: float) -> dict[str, float]:
    """Convert expected goals into 1x2, O/U 2.5, and BTTS probabilities."""
    rates = (lambda_home, lambda_away)
    if any(not math.isfinite(rate) or rate < 0 or rate > 15 for rate in rates):
        raise ValueError("Expected goals must be finite and between 0 and 15.")

    max_rate = max(rates)
    max_goals = max(12, math.ceil(max_rate + 8 * math.sqrt(max_rate) + 10))
    if max_goals > 60:
        raise ValueError("Expected-goals range is too large for a reliable score grid.")
    home_probs = _poisson_vector(lambda_home, max_goals)
    away_probs = _poisson_vector(lambda_away, max_goals)

    home_win = draw = away_win = over_25 = btts = captured_mass = 0.0
    for home_goals, p_home_goals in enumerate(home_probs):
        for away_goals, p_away_goals in enumerate(away_probs):
            probability = p_home_goals * p_away_goals
            captured_mass += probability
            if home_goals > away_goals:
                home_win += probability
            elif home_goals == away_goals:
                draw += probability
            else:
                away_win += probability
            if home_goals + away_goals > 2:
                over_25 += probability
            if home_goals > 0 and away_goals > 0:
                btts += probability

    if captured_mass <= 0:
        raise ValueError("Tidak ada probabilitas skor yang dapat dihitung.")

    # Normalize the tiny tail omitted by the finite score grid.
    home_win /= captured_mass
    draw /= captured_mass
    away_win /= captured_mass
    over_25 /= captured_mass
    btts /= captured_mass
    return {
        "p_over_2_5": over_25,
        "p_under_2_5": 1.0 - over_25,
        "p_home": home_win,
        "p_draw": draw,
        "p_away": away_win,
        "p_btts": btts,
        "p_no_btts": 1.0 - btts,
    }


def predict_match(
    history: Iterable[HistoricalMatch],
    *,
    league_code: str,
    home_team: str,
    away_team: str,
    prediction_date: date,
    settings: PoissonSettings | None = None,
) -> dict[str, object]:
    """Estimate match probabilities from strictly earlier same-league results.

    The league's supplied goals-per-match prior is blended with observations
    using W_PRIOR. For leagues without a prior in READ.md, the observed
    pre-match league average is used and identified in the returned metadata.
    Team attack/defence rates use the last N matches at the same venue, shrunk
    toward the corresponding league scoring baseline with K pseudo-matches.
    """
    model_settings = settings or PoissonSettings()
    model_settings.validate()
    if not league_code.strip() or not home_team.strip() or not away_team.strip():
        raise ValueError("Kode liga dan kedua nama tim wajib diisi.")
    if _team_key(home_team) == _team_key(away_team):
        raise ValueError("Tim kandang dan tandang harus berbeda.")

    code_key = league_code.strip().upper()
    home_key = _team_key(home_team)
    away_key = _team_key(away_team)
    past_matches = [
        match for match in history
        if match.match_date < prediction_date
        and match.league_code.strip().upper() == code_key
        and match.home_goals >= 0
        and match.away_goals >= 0
    ]
    past_matches.sort(key=lambda match: match.match_date)
    if len(past_matches) < model_settings.min_n:
        raise InsufficientHistoryError(
            f"Hanya ada {len(past_matches)} laga liga sebelum tanggal prediksi; "
            f"minimal {model_settings.min_n} diperlukan."
        )

    home_form = [
        match for match in past_matches
        if _team_key(match.home_team) == home_key
    ][-model_settings.last_n:]
    away_form = [
        match for match in past_matches
        if _team_key(match.away_team) == away_key
    ][-model_settings.last_n:]
    if len(home_form) < model_settings.min_n:
        raise InsufficientHistoryError(
            f"{home_team} hanya memiliki {len(home_form)} laga kandang sebelumnya; "
            f"minimal {model_settings.min_n} diperlukan."
        )
    if len(away_form) < model_settings.min_n:
        raise InsufficientHistoryError(
            f"{away_team} hanya memiliki {len(away_form)} laga tandang sebelumnya; "
            f"minimal {model_settings.min_n} diperlukan."
        )

    league_matches = len(past_matches)
    home_goals_total = sum(match.home_goals for match in past_matches)
    away_goals_total = sum(match.away_goals for match in past_matches)
    prior_gpm = model_settings.prior_gpm.get(code_key)
    if prior_gpm is None:
        league_home_rate = home_goals_total / league_matches
        league_away_rate = away_goals_total / league_matches
        prior_source = "observed_pre_match_league_average"
    else:
        prior_home_rate = prior_gpm * model_settings.home_share
        prior_away_rate = prior_gpm * (1.0 - model_settings.home_share)
        denominator = league_matches + model_settings.w_prior
        if denominator <= 0:
            raise InsufficientHistoryError("Tidak ada data untuk menghitung prior liga.")
        league_home_rate = (
            home_goals_total + model_settings.w_prior * prior_home_rate
        ) / denominator
        league_away_rate = (
            away_goals_total + model_settings.w_prior * prior_away_rate
        ) / denominator
        prior_source = "READ.md_prior_blended_with_past_league_matches"

    if league_home_rate <= 0 or league_away_rate <= 0:
        raise InsufficientHistoryError(
            "Rata-rata gol kandang/tandang liga belum positif; data sebelumnya belum cukup."
        )

    home_attack = _smoothed_rate(
        (match.home_goals for match in home_form),
        league_home_rate,
        model_settings.k,
    ) / league_home_rate
    home_defence_leak = _smoothed_rate(
        (match.away_goals for match in home_form),
        league_away_rate,
        model_settings.k,
    ) / league_away_rate
    away_attack = _smoothed_rate(
        (match.away_goals for match in away_form),
        league_away_rate,
        model_settings.k,
    ) / league_away_rate
    away_defence_leak = _smoothed_rate(
        (match.home_goals for match in away_form),
        league_home_rate,
        model_settings.k,
    ) / league_home_rate

    lambda_home = league_home_rate * home_attack * away_defence_leak
    lambda_away = league_away_rate * away_attack * home_defence_leak
    probabilities = scoreline_probabilities(lambda_home, lambda_away)

    return {
        "league_code": code_key,
        "home_team": home_team,
        "away_team": away_team,
        "prediction_date": prediction_date.isoformat(),
        "lambda_home": lambda_home,
        "lambda_away": lambda_away,
        "league_home_rate": league_home_rate,
        "league_away_rate": league_away_rate,
        "league_matches_before_prediction": league_matches,
        "home_form_matches": len(home_form),
        "away_form_matches": len(away_form),
        "prior_source": prior_source,
        "probabilities": probabilities,
    }


def _load_history(
    csv_path: Path,
    *,
    league_code: str,
    prediction_date: date,
    encoding: str = "utf-8-sig",
) -> list[HistoricalMatch]:
    """Load only completed, same-league matches strictly before the target date."""
    matches: list[HistoricalMatch] = []
    with csv_path.open("r", encoding=encoding, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        required = {
            "date",
            "league_code",
            "home_team",
            "away_team",
            "home_goals",
            "away_goals",
        }
        available = {name.strip().casefold() for name in (reader.fieldnames or [])}
        missing = required - available
        if missing:
            raise ValueError(
                "Gunakan CSV ringkas dari prepare_football_data.py; "
                "kolom tidak ditemukan: " + ", ".join(sorted(missing))
            )

        for row in reader:
            code = (row.get("league_code") or "").strip()
            if code.upper() != league_code.strip().upper():
                continue
            try:
                match_date = date.fromisoformat((row.get("date") or "").strip())
            except ValueError:
                continue
            if match_date >= prediction_date:
                continue
            home_goals = _parse_score(row.get("home_goals") or "")
            away_goals = _parse_score(row.get("away_goals") or "")
            home_team = (row.get("home_team") or "").strip()
            away_team = (row.get("away_team") or "").strip()
            if home_goals is None or away_goals is None or not home_team or not away_team:
                continue
            matches.append(
                HistoricalMatch(
                    match_date=match_date,
                    league_code=code,
                    home_team=home_team,
                    away_team=away_team,
                    home_goals=home_goals,
                    away_goals=away_goals,
                )
            )
    return matches


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Hitung probabilitas Poisson untuk satu laga dari hasil sebelumnya."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help=f"CSV ringkas (default: {DEFAULT_CSV})")
    parser.add_argument("--league", required=True, help="Kode liga, misalnya E0 atau SP1.")
    parser.add_argument("--home", required=True, help="Nama tim kandang sesuai CSV.")
    parser.add_argument("--away", required=True, help="Nama tim tandang sesuai CSV.")
    parser.add_argument("--date", required=True, help="Tanggal prediksi, format YYYY-MM-DD.")
    parser.add_argument("--encoding", default="utf-8-sig", help="Encoding CSV (default: utf-8-sig).")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        prediction_date = date.fromisoformat(args.date)
        history = _load_history(
            args.csv,
            league_code=args.league,
            prediction_date=prediction_date,
            encoding=args.encoding,
        )
        prediction = predict_match(
            history,
            league_code=args.league,
            home_team=args.home,
            away_team=args.away,
            prediction_date=prediction_date,
        )
    except (FileNotFoundError, PermissionError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Prediksi tidak dapat dihitung: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(prediction, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
