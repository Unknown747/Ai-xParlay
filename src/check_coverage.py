"""Periksa kelengkapan odds dan xG per liga dari CSV gabungan football-data."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from src.config import CURRENT_SEASON, LEAGUES

DEFAULT_CSV = Path("data/historis/all_football_data.csv")
# label -> (kolom, nilai harus lebih besar dari angka ini)
CHECKS = {
    "1x2Avg": ("AvgH", 1.0),
    "1x2AvgC": ("AvgCH", 1.0),
    "1x2B365": ("B365H", 1.0),
    "OUAvg": ("Avg>2.5", 1.0),
    "OUAvgC": ("AvgC>2.5", 1.0),
    "OUB365": ("B365>2.5", 1.0),
    "xG": ("HxG", -1.0),
}
THRESHOLD = 90.0


def _valid(value: str, minimum: float) -> bool:
    try:
        return float(value) > minimum
    except (TypeError, ValueError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_path", nargs="?", type=Path, default=DEFAULT_CSV)
    args = parser.parse_args(argv)

    total: dict[tuple[str, str], int] = defaultdict(int)
    valid: dict[tuple[str, str, str], int] = defaultdict(int)
    with args.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        btts = [f for f in fields if "BTT" in f.upper() or "BTS" in f.upper()]
        for row in reader:
            key = (row["Div"], row["Season"])
            total[key] += 1
            for label, (column, minimum) in CHECKS.items():
                if _valid(row.get(column, ""), minimum):
                    valid[key + (label,)] += 1

    full = sorted({season for _, season in total if season != CURRENT_SEASON})
    labels = list(CHECKS)

    def pct(league: str, seasons: list[str], label: str) -> float:
        n = sum(total.get((league, s), 0) for s in seasons)
        v = sum(valid.get((league, s, label), 0) for s in seasons)
        return 100.0 * v / n if n else 0.0

    sections = (
        (f"MUSIM PENUH {full[0]}-{full[-1]}", full),
        (f"MUSIM BERJALAN {CURRENT_SEASON}", [CURRENT_SEASON]),
    )
    for title, seasons in sections:
        print(f"\n{title} (% laga dengan data valid)")
        print("liga ".ljust(6) + "".join(label.rjust(8) for label in labels))
        for league in LEAGUES:
            print(league.ljust(6) + "".join(f"{pct(league, seasons, l):8.0f}" for l in labels))

    print(f"\nCelah odds musim penuh (<{THRESHOLD:.0f}%):")
    gaps = 0
    for league in LEAGUES:
        for season in full:
            for label in labels:
                if label == "xG":
                    continue
                value = pct(league, [season], label)
                if value < THRESHOLD:
                    gaps += 1
                    print(f"  {league} {season} {label}: {value:.0f}%")
    if not gaps:
        print("  tidak ada")
    print("\nKolom BTTS di sumber:", ", ".join(btts) if btts else "TIDAK ADA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
