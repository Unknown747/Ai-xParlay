"""Backtest walk-forward Poisson untuk pasar O/U 2.5 dan 1x2.

Satu kali jalan: status liga/tim diperbarui bertahap, tanpa membaca ulang CSV
per laga. Prediksi tiap laga hanya memakai laga bertanggal sebelumnya
(laga di tanggal yang sama dikecualikan), sama seperti stat_poisson.py.

Asumsi ROI (dicatat juga di Plan.MD):
- stake tetap 1 unit; profit = odds - 1 jika menang, -1 jika kalah
- tidak ada push (O/U 2.5 dan 1x2 tidak punya garis bulat)
- odds = rata-rata pasar football-data (default Avg), dianggap bisa didapat
- tanpa batas taruhan, komisi, atau slippage
- laga tanpa odds valid dilewati untuk pasar itu
- mode "semua": taruh pada pilihan model di setiap laga
- mode "filter": O/U |p-0.5| > 0.1 (READ.md); 1x2 p_pilihan > 0.6 (analog)
- tanpa tuning: ambang tetap, tidak dicari kombinasi terbaik
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import sys
from collections import defaultdict, deque
from datetime import date
from itertools import groupby
from pathlib import Path

from src.config import CURRENT_SEASON, LEAGUES
from src.inspect_football_data import _parse_score
from src.stat_poisson import (
    InsufficientHistoryError,
    PoissonSettings,
    _load_history,
    _smoothed_rate,
    _team_key,
    predict_match,
    scoreline_probabilities,
)

DEFAULT_CSV = Path("data/historis/matches_clean.csv")
DEFAULT_OUTPUT = Path("data/hasil/backtest_poisson.csv")
# urutan: home, draw, away, over 2.5, under 2.5
ODDS_SETS = {
    "avg": ("AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5"),
    "close": ("AvgCH", "AvgCD", "AvgCA", "AvgC>2.5", "AvgC<2.5"),
    "b365": ("B365H", "B365D", "B365A", "B365>2.5", "B365<2.5"),
}
MARKETS = ("ou25", "1x2")
MODES = ("semua", "filter")
OUTPUT_FIELDS = (
    "date", "season", "league", "home", "away", "hg", "ag",
    "lambda_h", "lambda_a", "p_over", "p_home", "p_draw", "p_away",
    "oh", "od", "oa", "o_over", "o_under",
)


def _odds(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 1.0 else None


def load_matches(path: Path, odds_cols):
    matches = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for order, row in enumerate(csv.DictReader(handle)):
            try:
                day = date.fromisoformat((row.get("date") or "").strip())
            except ValueError:
                continue
            hg = _parse_score(row.get("home_goals") or "")
            ag = _parse_score(row.get("away_goals") or "")
            home = (row.get("home_team") or "").strip()
            away = (row.get("away_team") or "").strip()
            if hg is None or ag is None or not home or not away:
                continue
            o = [_odds(row.get(column)) for column in odds_cols]
            matches.append({
                "order": order,
                "date": day,
                "season": (row.get("season") or "").strip(),
                "league": (row.get("league_code") or "").strip().upper(),
                "home": home,
                "away": away,
                "hg": hg,
                "ag": ag,
                "oh": o[0], "od": o[1], "oa": o[2],
                "o_over": o[3], "o_under": o[4],
            })
    matches.sort(key=lambda m: (m["date"], m["order"]))
    return matches


class LeagueState:
    """Ringkasan hasil liga sebelum tanggal prediksi."""

    def __init__(self, last_n: int) -> None:
        self.n = 0
        self.home_goals = 0
        self.away_goals = 0
        self.home = defaultdict(lambda: deque(maxlen=last_n))  # (dicetak, kebobolan)
        self.away = defaultdict(lambda: deque(maxlen=last_n))

    def add(self, match) -> None:
        self.n += 1
        self.home_goals += match["hg"]
        self.away_goals += match["ag"]
        self.home[_team_key(match["home"])].append((match["hg"], match["ag"]))
        self.away[_team_key(match["away"])].append((match["ag"], match["hg"]))


def predict(state: LeagueState, match, settings: PoissonSettings):
    """Sama dengan stat_poisson.predict_match; None jika data belum cukup."""
    if state.n < settings.min_n:
        return None
    home_form = state.home.get(_team_key(match["home"]))
    away_form = state.away.get(_team_key(match["away"]))
    if not home_form or not away_form:
        return None
    if len(home_form) < settings.min_n or len(away_form) < settings.min_n:
        return None

    prior = settings.prior_gpm.get(match["league"])
    if prior is None:
        league_home = state.home_goals / state.n
        league_away = state.away_goals / state.n
    else:
        denominator = state.n + settings.w_prior
        league_home = (state.home_goals + settings.w_prior * prior * settings.home_share) / denominator
        league_away = (state.away_goals + settings.w_prior * prior * (1.0 - settings.home_share)) / denominator
    if league_home <= 0 or league_away <= 0:
        return None

    k = settings.k
    home_attack = _smoothed_rate((g for g, _ in home_form), league_home, k) / league_home
    home_leak = _smoothed_rate((c for _, c in home_form), league_away, k) / league_away
    away_attack = _smoothed_rate((g for g, _ in away_form), league_away, k) / league_away
    away_leak = _smoothed_rate((c for _, c in away_form), league_home, k) / league_home

    lambda_h = league_home * home_attack * away_leak
    lambda_a = league_away * away_attack * home_leak
    p = scoreline_probabilities(lambda_h, lambda_a)
    return {
        "lambda_h": lambda_h,
        "lambda_a": lambda_a,
        "p_over": p["p_over_2_5"],
        "p_home": p["p_home"],
        "p_draw": p["p_draw"],
        "p_away": p["p_away"],
    }


def _result(record) -> str:
    if record["hg"] > record["ag"]:
        return "H"
    if record["hg"] < record["ag"]:
        return "A"
    return "D"


def make_bets(record):
    bets = []
    base = {"season": record["season"], "league": record["league"]}
    if record["o_over"] and record["o_under"]:
        pick_over = record["p_over"] > 0.5
        odds = record["o_over"] if pick_over else record["o_under"]
        win = (record["hg"] + record["ag"] > 2) == pick_over
        bets.append({**base, "market": "ou25", "mode": "semua", "odds": odds, "win": win})
        if abs(record["p_over"] - 0.5) > 0.1:
            bets.append({**base, "market": "ou25", "mode": "filter", "odds": odds, "win": win})
    if record["oh"] and record["od"] and record["oa"]:
        probs = {"H": record["p_home"], "D": record["p_draw"], "A": record["p_away"]}
        odds_map = {"H": record["oh"], "D": record["od"], "A": record["oa"]}
        pick = max(probs, key=probs.get)
        win = _result(record) == pick
        bets.append({**base, "market": "1x2", "mode": "semua", "odds": odds_map[pick], "win": win})
        if probs[pick] > 0.6:
            bets.append({**base, "market": "1x2", "mode": "filter", "odds": odds_map[pick], "win": win})
    return bets


def _row(label: str, bets) -> str:
    n = len(bets)
    if not n:
        return f"{label:<12}{0:>8}"
    profits = [(b["odds"] - 1.0) if b["win"] else -1.0 for b in bets]
    mean = sum(profits) / n
    variance = sum((x - mean) ** 2 for x in profits) / (n - 1) if n > 1 else 0.0
    ci = 1.96 * math.sqrt(variance / n) * 100
    hit = 100.0 * sum(b["win"] for b in bets) / n
    avg_odds = sum(b["odds"] for b in bets) / n
    return f"{label:<12}{n:>8}{hit:>8.1f}{avg_odds:>7.2f}{mean * 100:>8.2f}{ci:>8.1f}"


def report_roi(all_bets) -> None:
    header = f"{'grup':<12}{'taruhan':>8}{'hit%':>8}{'odds':>7}{'ROI%':>8}{'+-95%':>8}"
    for market in MARKETS:
        for mode in MODES:
            bets = [b for b in all_bets if b["market"] == market and b["mode"] == mode]
            full = [b for b in bets if b["season"] != CURRENT_SEASON]
            current = [b for b in bets if b["season"] == CURRENT_SEASON]
            print(f"\n== ROI {market} / {mode} ==")
            print(header)
            print(_row("musim penuh", full))
            print(_row(CURRENT_SEASON + "*", current))
            for season in sorted({b["season"] for b in full}):
                print(_row(season, [b for b in full if b["season"] == season]))
            for league in LEAGUES:
                print(_row(league, [b for b in full if b["league"] == league]))
    print(f"\n* {CURRENT_SEASON} = musim berjalan, belum lengkap; tidak masuk 'musim penuh'.")


def report_accuracy(records) -> None:
    full = [r for r in records if r["season"] != CURRENT_SEASON]
    print("\n== Akurasi probabilitas (musim penuh, laga dengan odds) ==")

    rows = [r for r in full if r["o_over"] and r["o_under"]]
    if rows:
        model = market = 0.0
        correct = 0
        for r in rows:
            y = 1.0 if r["hg"] + r["ag"] > 2 else 0.0
            model += (r["p_over"] - y) ** 2
            io, iu = 1.0 / r["o_over"], 1.0 / r["o_under"]
            market += (io / (io + iu) - y) ** 2
            correct += int((r["p_over"] > 0.5) == (y == 1.0))
        n = len(rows)
        print(f"O/U 2.5  n={n}  akurasi={100 * correct / n:.1f}%  "
              f"brier_model={model / n:.4f}  brier_pasar={market / n:.4f}")

    rows = [r for r in full if r["oh"] and r["od"] and r["oa"]]
    if rows:
        model = market = 0.0
        correct = 0
        for r in rows:
            probs = (r["p_home"], r["p_draw"], r["p_away"])
            outcome = "HDA".index(_result(r))
            ys = [1.0 if i == outcome else 0.0 for i in range(3)]
            model += sum((p - y) ** 2 for p, y in zip(probs, ys))
            inv = [1.0 / r["oh"], 1.0 / r["od"], 1.0 / r["oa"]]
            total = sum(inv)
            market += sum((i / total - y) ** 2 for i, y in zip(inv, ys))
            correct += int(probs.index(max(probs)) == outcome)
        n = len(rows)
        print(f"1x2      n={n}  akurasi={100 * correct / n:.1f}%  "
              f"brier_model={model / n:.4f}  brier_pasar={market / n:.4f}")
    print("Brier lebih kecil = lebih baik. brier_pasar = odds dinormalkan tanpa margin bandar.")


def selfcheck(csv_path: Path, predicted, skipped, settings, count: int):
    """Bandingkan sampel prediksi dengan stat_poisson.predict_match (jalur lambat)."""
    rng = random.Random(0)
    problems = []
    for r in rng.sample(predicted, min(count, len(predicted))):
        history = _load_history(csv_path, league_code=r["league"], prediction_date=r["date"])
        ref = predict_match(
            history, league_code=r["league"], home_team=r["home"], away_team=r["away"],
            prediction_date=r["date"], settings=settings,
        )
        probs = ref["probabilities"]
        for name, mine, theirs in (
            ("lambda_h", r["lambda_h"], ref["lambda_home"]),
            ("lambda_a", r["lambda_a"], ref["lambda_away"]),
            ("p_over", r["p_over"], probs["p_over_2_5"]),
            ("p_home", r["p_home"], probs["p_home"]),
        ):
            if abs(mine - theirs) > 1e-9:
                problems.append(f"{r['date']} {r['league']} {r['home']}-{r['away']} {name}: {mine} vs {theirs}")
    for r in rng.sample(skipped, min(count, len(skipped))):
        history = _load_history(csv_path, league_code=r["league"], prediction_date=r["date"])
        try:
            predict_match(
                history, league_code=r["league"], home_team=r["home"], away_team=r["away"],
                prediction_date=r["date"], settings=settings,
            )
            problems.append(f"{r['date']} {r['league']} {r['home']}-{r['away']}: dilewati backtest, tapi stat_poisson bisa memprediksi")
        except InsufficientHistoryError:
            pass
    return problems


def save_predictions(records, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for r in records:
            row = {name: r[name] for name in OUTPUT_FIELDS if name != "date"}
            row["date"] = r["date"].isoformat()
            writer.writerow({k: ("" if v is None else v) for k, v in row.items()})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest walk-forward Poisson (O/U 2.5 dan 1x2).")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--odds", choices=sorted(ODDS_SETS), default="avg",
                        help="Set odds untuk ROI (default: avg).")
    parser.add_argument("--eval-from", default="2022-07-01",
                        help="Mulai evaluasi; sebelumnya hanya pemanasan (default: 2022-07-01).")
    parser.add_argument("--selfcheck", type=int, default=5,
                        help="Jumlah sampel dicocokkan dengan stat_poisson.py (0 = lewati).")
    args = parser.parse_args(argv)

    try:
        eval_from = date.fromisoformat(args.eval_from)
        settings = PoissonSettings()
        settings.validate()
        matches = load_matches(args.csv, ODDS_SETS[args.odds])
    except (FileNotFoundError, ValueError) as exc:
        print(f"Backtest gagal: {exc}", file=sys.stderr)
        return 2

    states: dict[str, LeagueState] = {}
    records, skipped = [], []
    for _, group in groupby(matches, key=lambda m: m["date"]):
        day_matches = list(group)
        if day_matches[0]["date"] >= eval_from:
            for match in day_matches:
                state = states.get(match["league"])
                prediction = predict(state, match, settings) if state else None
                if prediction is None:
                    skipped.append(match)
                else:
                    records.append({**match, **prediction})
        for match in day_matches:  # pembaruan setelah semua prediksi hari itu
            states.setdefault(match["league"], LeagueState(settings.last_n)).add(match)

    if not records:
        print("Tidak ada prediksi yang dihasilkan; periksa --eval-from dan CSV.", file=sys.stderr)
        return 2

    if args.selfcheck > 0:
        problems = selfcheck(args.csv, records, skipped, settings, args.selfcheck)
        if problems:
            print("SELFCHECK GAGAL (backtest berbeda dari stat_poisson.py):", *problems[:10], sep="\n  ")
            return 3
        print(f"selfcheck OK: {min(args.selfcheck, len(records))} prediksi dan "
              f"{min(args.selfcheck, len(skipped))} penolakan cocok dengan stat_poisson.py")

    save_predictions(records, args.output)
    full = [r for r in records if r["season"] != CURRENT_SEASON]
    print(f"\nCSV: {args.csv} | odds: {args.odds} | evaluasi dari {eval_from} (sebelumnya pemanasan)")
    print(f"laga dievaluasi: {len(records) + len(skipped)} | diprediksi: {len(records)} "
          f"(musim penuh {len(full)}, {CURRENT_SEASON} {len(records) - len(full)}) | "
          f"dilewati data kurang: {len(skipped)}")
    print(f"tanpa odds O/U: {sum(1 for r in records if not (r['o_over'] and r['o_under']))} | "
          f"tanpa odds 1x2: {sum(1 for r in records if not (r['oh'] and r['od'] and r['oa']))}")
    print(f"prediksi disimpan: {args.output}")

    all_bets = [bet for r in records for bet in make_bets(r)]
    report_roi(all_bets)
    report_accuracy(records)
    print("\nIni hasil uji historis dengan asumsi odds Avg tersedia; bukan jaminan ROI.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
