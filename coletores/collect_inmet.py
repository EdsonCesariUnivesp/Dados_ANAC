from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from coletores.common import download_file


BASE_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta os arquivos anuais oficiais do INMET.")
    parser.add_argument("--start-year", type=int, default=2018, choices=range(2018, 2026))
    parser.add_argument("--end-year", type=int, default=2025, choices=range(2018, 2026))
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "data" / "raw" / "inmet"
    )
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("O ano inicial não pode ser posterior ao ano final.")
    output_root = args.output_dir.resolve()
    project_data = (PROJECT_ROOT / "data").resolve()
    if output_root != project_data and project_data not in output_root.parents:
        parser.error("O diretório de saída deve permanecer dentro de data/.")

    failures = 0
    for year in range(args.start_year, args.end_year + 1):
        try:
            metadata = download_file(
                url=f"{BASE_URL}{year}.zip",
                destination=output_root / f"{year}.zip",
                allowed_url_prefix=BASE_URL,
                force=args.force,
                timeout_seconds=180,
            )
            print(json.dumps({"year": year, **asdict(metadata)}, ensure_ascii=False))
        except Exception as exc:
            failures += 1
            print(json.dumps({"year": year, "error": str(exc)}, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
