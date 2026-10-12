"""Unduh CSV football-data.co.uk per liga/musim lalu gabungkan jadi satu CSV.

Hanya untuk penggunaan pribadi. Memakai cache dan jeda antar-unduhan.
Musim berjalan selalu diunduh ulang; musim penuh hanya jika belum ada di cache.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import tempfile
import time
import urllib.request
from pathlib import Path

from src.config import CURRENT_SEASON, LEAGUES, SEASONS

BASE_URL = "https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
CACHE_DIR = Path("cache/footballdata")
DEFAULT_OUTPUT = Path("data/historis/all_football_data.csv")
USER_AGENT = "Ai-xParlay personal research (non-commercial)"


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _looks_like_csv(text: str) -> bool:
    lines = text.lstrip().splitlines()
    return bool(lines) and "HomeTeam" in lines[0] and "FTHG" in lines[0]


def _download(season: str, league: str, delay: float) -> bytes:
    request = urllib.request.Request(
        BASE_URL.format(season=season, league=league),
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    time.sleep(delay)
    return raw


def fetch_all(leagues, seasons, *, refresh=False, delay=1.0):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    files, failed = [], []
    downloaded = from_cache = 0
    for season in seasons:
        for league in leagues:
            path = CACHE_DIR / f"{season}_{league}.csv"
            if refresh or season == CURRENT_SEASON or not path.exists():
                try:
                    raw = _download(season, league, delay)
                    if not _looks_like_csv(_decode(raw)):
                        raise ValueError("isi bukan CSV football-data")
                    path.write_bytes(raw)
                    downloaded += 1
                except (OSError, ValueError) as exc:
                    failed.append(f"{season}/{league}: {exc}")
                    if not path.exists():
                        continue
            else:
                from_cache += 1
            files.append((season, league, path))
    return files, downloaded, from_cache, failed


def merge(files, output: Path):
    fieldnames = ["Div", "Season"]
    rows = []
    for season, league, path in files:
        reader = csv.DictReader(io.StringIO(_decode(path.read_bytes()), newline=""))
        for name in reader.fieldnames or []:
            name = (name or "").strip()
            if name and name not in fieldnames:
                fieldnames.append(name)
        for row in reader:
            clean = {
                k.strip(): (v or "").strip()
                for k, v in row.items()
                if k and k.strip()
            }
            if not clean.get("HomeTeam") or not clean.get("Date"):
                continue
            clean["Div"] = league
            clean["Season"] = season
            rows.append(clean)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=output.parent,
        prefix=f".{output.name}.", suffix=".tmp", delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)
        writer = csv.DictWriter(tmp, fieldnames=fieldnames, restval="")
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(output)
    return len(rows), len(fieldnames)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Unduh dan gabungkan CSV football-data.co.uk.")
    parser.add_argument("--leagues", default=",".join(LEAGUES))
    parser.add_argument("--seasons", default=",".join(SEASONS))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--refresh", action="store_true", help="Unduh ulang semua file.")
    parser.add_argument("--delay", type=float, default=1.0, help="Jeda antar unduhan (detik).")
    args = parser.parse_args(argv)

    leagues = [x.strip() for x in args.leagues.split(",") if x.strip()]
    seasons = [x.strip() for x in args.seasons.split(",") if x.strip()]
    files, downloaded, from_cache, failed = fetch_all(
        leagues, seasons, refresh=args.refresh, delay=args.delay
    )
    if not files:
        print("Tidak ada file yang berhasil diunduh:", *failed, sep="\n")
        return 2
    rows, columns = merge(files, args.output)
    print(json.dumps({
        "files_expected": len(leagues) * len(seasons),
        "files_used": len(files),
        "downloaded": downloaded,
        "from_cache": from_cache,
        "failed": failed,
        "rows_merged": rows,
        "columns": columns,
        "output": str(args.output),
    }, indent=2, ensure_ascii=False))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
