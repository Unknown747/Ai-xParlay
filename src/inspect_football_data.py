"""Stream and summarize a football-data-style CSV without loading it all in memory."""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import tempfile
from collections import Counter
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


DEFAULT_CSV = Path("data/historis/all_football_data.csv")

ALIASES: dict[str, tuple[str, ...]] = {
    "date": ("date", "match_date"),
    "home_team": ("hometeam", "home_team", "home"),
    "away_team": ("awayteam", "away_team", "away"),
    "home_goals": ("fthg", "home_goals", "goals_home"),
    "away_goals": ("ftag", "away_goals", "goals_away"),
    "result": ("ftr", "full_time_result", "result"),
    "league_code": ("leaguecode", "league_code", "div"),
    "league_name": ("league", "league_name", "competition"),
    "season": ("season", "season_code"),
}

REQUIRED_FIELDS = ("date", "home_team", "away_team", "home_goals", "away_goals", "season")


class DatasetFormatError(ValueError):
    """Raised when a CSV is missing fields needed to identify football matches."""


def _header_key(value: str) -> str:
    return value.strip().lstrip("\ufeff").casefold()


def _parse_match_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None

    for pattern in ("%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _parse_score(value: str) -> int | None:
    value = value.strip()
    if not value:
        return None
    try:
        score = Decimal(value)
    except InvalidOperation:
        return None
    if not score.is_finite() or score < 0 or score != score.to_integral_value():
        return None
    return int(score)


def inspect_csv(
    csv_path: str | Path,
    *,
    max_rows: int | None = None,
    encoding: str = "utf-8-sig",
) -> dict[str, Any]:
    """Return a bounded-memory summary of a football results CSV.

    A temporary on-disk SQLite index is used for exact fixture-duplicate checks,
    avoiding a Python set that would grow with the size of the input file.
    """
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows must be a positive integer")

    file_size = path.stat().st_size
    with path.open("r", encoding=encoding, newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise DatasetFormatError("CSV is empty or does not contain a header row.")

        normalized_headers = [_header_key(name or "") for name in fieldnames]
        header_counts = Counter(normalized_headers)
        duplicate_headers = sorted(name for name, count in header_counts.items() if name and count > 1)
        resolved: dict[str, str] = {}
        for canonical, aliases in ALIASES.items():
            for alias in aliases:
                if alias in normalized_headers:
                    resolved[canonical] = fieldnames[normalized_headers.index(alias)]
                    break

        missing_columns = [
            name for name in REQUIRED_FIELDS if name not in resolved
        ]
        if "league_code" not in resolved and "league_name" not in resolved:
            missing_columns.append("league_code atau league")
        if missing_columns:
            raise DatasetFormatError(
                "Kolom wajib tidak ditemukan: "
                + ", ".join(missing_columns)
                + f". Kolom tersedia: {', '.join(name for name in fieldnames if name)}"
            )

        row_count = 0
        missing_values: Counter[str] = Counter()
        leagues: Counter[str] = Counter()
        seasons: Counter[str] = Counter()
        league_seasons: Counter[tuple[str, str]] = Counter()
        invalid_dates = 0
        invalid_scores = 0
        incomplete_score_rows = 0
        invalid_result_codes = 0
        result_score_mismatches = 0
        rows_with_extra_values = 0
        extra_value_count = 0
        min_date: date | None = None
        max_date: date | None = None
        batch: list[tuple[str]] = []
        duplicate_match_rows = 0
        scan_limit_reached = False

        with tempfile.TemporaryDirectory(prefix="ai-xparlay-csv-") as temp_dir:
            database_path = Path(temp_dir) / "fixture-keys.sqlite3"
            connection = sqlite3.connect(database_path)
            try:
                connection.execute("PRAGMA journal_mode=OFF")
                connection.execute("PRAGMA synchronous=OFF")
                connection.execute("CREATE TABLE seen_matches (match_key TEXT PRIMARY KEY)")

                def flush_keys() -> None:
                    nonlocal duplicate_match_rows
                    if not batch:
                        return
                    before = connection.total_changes
                    connection.executemany(
                        "INSERT OR IGNORE INTO seen_matches (match_key) VALUES (?)",
                        batch,
                    )
                    inserted = connection.total_changes - before
                    duplicate_match_rows += len(batch) - inserted
                    connection.commit()
                    batch.clear()

                for row in reader:
                    if max_rows is not None and row_count >= max_rows:
                        scan_limit_reached = True
                        break
                    row_count += 1

                    extra_values = row.get(None, [])
                    if extra_values:
                        nonblank_extra_values = sum(bool(value.strip()) for value in extra_values if value)
                        if nonblank_extra_values:
                            rows_with_extra_values += 1
                            extra_value_count += nonblank_extra_values

                    values = {
                        canonical: (row.get(column) or "").strip()
                        for canonical, column in resolved.items()
                    }
                    for required in REQUIRED_FIELDS:
                        if not values.get(required):
                            missing_values[required] += 1

                    league = (
                        values.get("league_code", "")
                        or values.get("league_name", "")
                    ).strip()
                    season = values.get("season", "").strip()
                    if league:
                        leagues[league] += 1
                    if season:
                        seasons[season] += 1
                    if league and season:
                        league_seasons[(league, season)] += 1

                    parsed_date = _parse_match_date(values.get("date", ""))
                    if values.get("date") and parsed_date is None:
                        invalid_dates += 1
                    if parsed_date:
                        min_date = parsed_date if min_date is None else min(min_date, parsed_date)
                        max_date = parsed_date if max_date is None else max(max_date, parsed_date)

                    raw_home_goals = values.get("home_goals", "")
                    raw_away_goals = values.get("away_goals", "")
                    home_goals = _parse_score(raw_home_goals)
                    away_goals = _parse_score(raw_away_goals)
                    if raw_home_goals and home_goals is None:
                        invalid_scores += 1
                    if raw_away_goals and away_goals is None:
                        invalid_scores += 1
                    if home_goals is None or away_goals is None:
                        incomplete_score_rows += 1

                    result = values.get("result", "").upper()
                    if result and result not in {"H", "D", "A"}:
                        invalid_result_codes += 1
                    if home_goals is not None and away_goals is not None and result in {"H", "D", "A"}:
                        derived_result = (
                            "H" if home_goals > away_goals
                            else "A" if home_goals < away_goals
                            else "D"
                        )
                        if result != derived_result:
                            result_score_mismatches += 1

                    if parsed_date and league and season and values.get("home_team") and values.get("away_team"):
                        key = json.dumps(
                            [
                                parsed_date.isoformat(),
                                league.casefold(),
                                season.casefold(),
                                values["home_team"].casefold(),
                                values["away_team"].casefold(),
                            ],
                            ensure_ascii=False,
                            separators=(",", ":"),
                        )
                        batch.append((key,))
                        if len(batch) >= 2000:
                            flush_keys()
                flush_keys()
            finally:
                connection.close()

    warnings: list[str] = []
    if duplicate_headers:
        warnings.append("Header duplikat ditemukan; tinjau pemetaan kolom sebelum pemodelan.")
    if duplicate_match_rows:
        warnings.append("Ada baris fixture duplikat berdasarkan tanggal, liga, musim, dan kedua tim.")
    if invalid_dates:
        warnings.append("Ada tanggal yang tidak dapat dibaca.")
    if invalid_scores:
        warnings.append("Ada nilai gol yang bukan angka bulat non-negatif.")
    if incomplete_score_rows:
        warnings.append("Ada laga tanpa skor lengkap; laga tersebut tidak bisa dipakai untuk model hasil.")
    if invalid_result_codes:
        warnings.append("Ada kode hasil akhir selain H, D, atau A.")
    if result_score_mismatches:
        warnings.append("Kode FTR tidak cocok dengan skor penuh pada sebagian baris.")
    if rows_with_extra_values:
        warnings.append("Ada baris yang memiliki nilai tambahan di luar jumlah kolom header.")
    if any(missing_values.values()):
        warnings.append("Ada nilai kosong pada kolom penting; tinjau ringkasan sebelum pemodelan.")
    if scan_limit_reached:
        warnings.append("Pemindaian dibatasi oleh --max-rows; angka ini bukan ringkasan seluruh file.")

    return {
        "file": path.name,
        "size_bytes": file_size,
        "column_count": len(fieldnames),
        "columns": fieldnames,
        "resolved_columns": resolved,
        "rows_analyzed": row_count,
        "full_file_scan": not scan_limit_reached,
        "league_match_counts": dict(sorted(leagues.items())),
        "season_match_counts": dict(sorted(seasons.items())),
        "league_season_match_counts": {
            league: dict(sorted(
                (season, count)
                for (current_league, season), count in league_seasons.items()
                if current_league == league
            ))
            for league in sorted(leagues)
        },
        "date_range": {
            "first": min_date.isoformat() if min_date else None,
            "last": max_date.isoformat() if max_date else None,
        },
        "missing_required_values": {
            name: missing_values[name]
            for name in REQUIRED_FIELDS
            if missing_values[name]
        },
        "invalid_dates": invalid_dates,
        "invalid_score_values": invalid_scores,
        "rows_without_complete_score": incomplete_score_rows,
        "invalid_result_codes": invalid_result_codes,
        "result_score_mismatches": result_score_mismatches,
        "duplicate_fixture_rows": duplicate_match_rows,
        "rows_with_extra_values": rows_with_extra_values,
        "extra_values": extra_value_count,
        "duplicate_headers": duplicate_headers,
        "warnings": warnings,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Periksa CSV sepak bola berukuran besar dengan pemindaian streaming."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Lokasi CSV (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Batasi jumlah baris untuk pemeriksaan cepat; ringkasan tidak mencakup seluruh file.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Encoding teks CSV (default: utf-8-sig).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Simpan ringkasan JSON ke file selain menampilkannya di terminal.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = inspect_csv(args.csv_path, max_rows=args.max_rows, encoding=args.encoding)
    except (DatasetFormatError, FileNotFoundError, PermissionError, UnicodeError, csv.Error, ValueError) as exc:
        print(f"Gagal memeriksa CSV: {exc}", file=sys.stderr)
        if isinstance(exc, FileNotFoundError):
            print(
                f"Letakkan file di {DEFAULT_CSV} atau berikan jalurnya sebagai argumen.",
                file=sys.stderr,
            )
        return 2

    output = json.dumps(summary, indent=2, ensure_ascii=False)
    print(output)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
