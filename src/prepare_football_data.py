"""Convert the user's wide CSV into a compact, model-ready CSV in one streaming pass."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable

from src.config import LEAGUES, SEASONS
from src.inspect_football_data import (
    ALIASES,
    DEFAULT_CSV,
    DatasetFormatError,
    _header_key,
    _parse_match_date,
    _parse_score,
)


DEFAULT_OUTPUT = Path("data/historis/matches_clean.csv")
CORE_COLUMNS = (
    "date",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result",
    "league",
    "league_code",
    "season",
)
ODDS_COLUMNS = (
    "AvgH", "AvgD", "AvgA", "Avg>2.5", "Avg<2.5",
    "AvgCH", "AvgCD", "AvgCA", "AvgC>2.5", "AvgC<2.5",
    "B365H", "B365D", "B365A", "B365>2.5", "B365<2.5",
    "B365CH", "B365CD", "B365CA", "B365C>2.5", "B365C<2.5",
)


def _resolve_columns(fieldnames: list[str]) -> tuple[dict[str, str], dict[str, str]]:
    normalized = [_header_key(name or "") for name in fieldnames]
    resolved: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = fieldnames[normalized.index(alias)]
                break
    odds = {
        expected: fieldnames[normalized.index(expected.casefold())]
        for expected in ODDS_COLUMNS
        if expected.casefold() in normalized
    }
    return resolved, odds


def prepare_csv(
    csv_path: str | Path = DEFAULT_CSV,
    output_path: str | Path = DEFAULT_OUTPUT,
    *,
    max_rows: int | None = None,
    encoding: str = "utf-8-sig",
    leagues: Iterable[str] | None = None,
    seasons: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Write a normalized match CSV while keeping memory use independent of row count."""
    source = Path(csv_path)
    output = Path(output_path)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.resolve() == output.resolve():
        raise ValueError("File output tidak boleh sama dengan file sumber.")
    if max_rows is not None and max_rows < 1:
        raise ValueError("max_rows harus berupa bilangan bulat positif.")

    output.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    summary: dict[str, Any]
    try:
        with source.open("r", encoding=encoding, newline="") as input_file:
            reader = csv.DictReader(input_file)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DatasetFormatError("CSV kosong atau tidak memiliki header.")
            columns, odds = _resolve_columns(fieldnames)
            missing = [
                name for name in CORE_COLUMNS
                if name not in {"league", "league_code"} and name not in columns
            ]
            if "league_code" not in columns and "league_name" not in columns:
                missing.append("league_code atau league")
            if missing:
                raise DatasetFormatError(
                    "Kolom wajib tidak ditemukan: "
                    + ", ".join(missing)
                    + f". Kolom tersedia: {', '.join(name for name in fieldnames if name)}"
                )

            output_columns = list(CORE_COLUMNS) + list(odds)
            rows_read = 0
            rows_written = 0
            skipped_missing_identity = 0
            invalid_dates = 0
            missing_dates = 0
            missing_home_teams = 0
            missing_away_teams = 0
            missing_seasons = 0
            missing_leagues = 0
            invalid_score_values = 0
            incomplete_scores = 0
            inferred_results = 0
            result_score_mismatches = 0
            scan_limit_reached = False
            rows_out_of_scope = 0
            league_filter = {c.strip().upper() for c in leagues} if leagues else set()
            season_filter = {c.strip() for c in seasons} if seasons else set()

            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="",
                prefix=f".{output.name}.",
                suffix=".tmp",
                dir=output.parent,
                delete=False,
            ) as temp_file:
                temp_path = Path(temp_file.name)
                writer = csv.DictWriter(temp_file, fieldnames=output_columns)
                writer.writeheader()

                for row in reader:
                    if max_rows is not None and rows_read >= max_rows:
                        scan_limit_reached = True
                        break
                    rows_read += 1
                    values = {
                        canonical: (row.get(column) or "").strip()
                        for canonical, column in columns.items()
                    }
                    raw_league_code = values.get("league_code", "")
                    league_name = values.get("league_name", "") or raw_league_code
                    league_code = raw_league_code
                    if not league_code:
                        # Some combined files retain the source's original Div column.
                        div_column = next(
                            (name for name in fieldnames if _header_key(name) == "div"),
                            None,
                        )
                        league_code = (row.get(div_column) or "").strip() if div_column else ""

                    raw_date = values.get("date", "")
                    match_date = _parse_match_date(raw_date)
                    if not raw_date:
                        missing_dates += 1
                    elif match_date is None:
                        invalid_dates += 1
                    home_team = values.get("home_team", "")
                    away_team = values.get("away_team", "")
                    season = values.get("season", "")
                    if not home_team:
                        missing_home_teams += 1
                    if not away_team:
                        missing_away_teams += 1
                    if not season:
                        missing_seasons += 1
                    if not (league_code or league_name):
                        missing_leagues += 1
                    if (
                        match_date is None
                        or not home_team
                        or not away_team
                        or not season
                        or not (league_code or league_name)
                    ):
                        skipped_missing_identity += 1
                        continue
                    if (league_filter and league_code.upper() not in league_filter) or (
                        season_filter and season not in season_filter
                    ):
                        rows_out_of_scope += 1
                        continue

                    raw_home_score = values.get("home_goals", "")
                    raw_away_score = values.get("away_goals", "")
                    home_score = _parse_score(raw_home_score)
                    away_score = _parse_score(raw_away_score)
                    if raw_home_score and home_score is None:
                        invalid_score_values += 1
                    if raw_away_score and away_score is None:
                        invalid_score_values += 1
                    if home_score is None or away_score is None:
                        incomplete_scores += 1

                    result = values.get("result", "").upper()
                    if result not in {"H", "D", "A"}:
                        if home_score is not None and away_score is not None:
                            result = (
                                "H" if home_score > away_score
                                else "A" if home_score < away_score
                                else "D"
                            )
                            inferred_results += 1
                        else:
                            result = ""
                    elif home_score is not None and away_score is not None:
                        derived = (
                            "H" if home_score > away_score
                            else "A" if home_score < away_score
                            else "D"
                        )
                        if result != derived:
                            result_score_mismatches += 1

                    prepared = {
                        "date": match_date.isoformat(),
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_goals": "" if home_score is None else home_score,
                        "away_goals": "" if away_score is None else away_score,
                        "result": result,
                        "league": league_name,
                        "league_code": league_code,
                        "season": season,
                    }
                    for odds_name, source_column in odds.items():
                        prepared[odds_name] = (row.get(source_column) or "").strip()
                    writer.writerow(prepared)
                    rows_written += 1

        temp_path.replace(output)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    warnings: list[str] = []
    if skipped_missing_identity:
        warnings.append("Ada baris yang dilewati karena tanggal, tim, liga, atau musim tidak lengkap; file sumber tidak diubah.")
    if invalid_score_values:
        warnings.append("Nilai gol yang tidak valid dikosongkan; periksa sebelum pemodelan.")
    if incomplete_scores:
        warnings.append("Baris tanpa skor lengkap dipertahankan sebagai fixture, bukan hasil pertandingan.")
    if result_score_mismatches:
        warnings.append("Ada hasil FTR yang tidak cocok dengan skor; data sumber tidak diperbaiki otomatis.")
    if scan_limit_reached:
        warnings.append("Pemindaian dibatasi oleh --max-rows; hasil bukan ringkasan seluruh file.")

    summary = {
        "source_file": source.name,
        "source_size_bytes": source.stat().st_size,
        "output_file": str(output),
        "output_size_bytes": output.stat().st_size,
        "rows_read": rows_read,
        "full_file_scan": not scan_limit_reached,
        "rows_written": rows_written,
        "rows_skipped_missing_identity": skipped_missing_identity,
        "rows_out_of_scope": rows_out_of_scope,
        "league_filter": sorted(league_filter),
        "season_filter": sorted(season_filter),
        "missing_dates": missing_dates,
        "invalid_dates": invalid_dates,
        "missing_home_teams": missing_home_teams,
        "missing_away_teams": missing_away_teams,
        "missing_seasons": missing_seasons,
        "missing_leagues": missing_leagues,
        "invalid_score_values": invalid_score_values,
        "rows_without_complete_score": incomplete_scores,
        "inferred_results": inferred_results,
        "result_score_mismatches": result_score_mismatches,
        "odds_columns_preserved": list(odds),
        "warnings": warnings,
    }
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rapikan CSV sepak bola lebar menjadi CSV kecil untuk model."
    )
    parser.add_argument(
        "csv_path",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=f"CSV sumber (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV hasil (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        help="Batasi jumlah baris untuk uji cepat; hasil hanya mencakup bagian awal file.",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Encoding CSV sumber (default: utf-8-sig).",
    )
    parser.add_argument("--leagues", default=",".join(LEAGUES),
                        help="Kode liga dipisah koma (default: src/config.py).")
    parser.add_argument("--seasons", default=",".join(SEASONS),
                        help="Kode musim dipisah koma (default: src/config.py).")
    parser.add_argument("--all", action="store_true",
                        help="Nonaktifkan filter liga/musim.")
    return parser


def _split(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        summary = prepare_csv(
            args.csv_path,
            args.output,
            max_rows=args.max_rows,
            encoding=args.encoding,
            leagues=None if args.all else _split(args.leagues),
            seasons=None if args.all else _split(args.seasons),
        )
    except (
        DatasetFormatError,
        FileNotFoundError,
        PermissionError,
        UnicodeError,
        csv.Error,
        ValueError,
    ) as exc:
        print(f"Gagal menyiapkan CSV: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
