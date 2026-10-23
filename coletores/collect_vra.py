from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import date
from pathlib import Path

from coletores.common import download_file


BASE_URL = "https://siros.anac.gov.br/siros/registros/diversos/vra/"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_month(value: str) -> date:
    try:
        parsed = date.fromisoformat(f"{value}-01")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use o formato AAAA-MM.") from exc
    if not 2018 <= parsed.year <= 2025:
        raise argparse.ArgumentTypeError("O período aceito nesta versão é 2018-01 a 2025-12.")
    return parsed


def months_between(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current = date(current.year + (current.month == 12), current.month % 12 + 1, 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="Coleta mensal, retomável e auditável do VRA/ANAC.")
    parser.add_argument("--start-month", type=parse_month, default=parse_month("2018-01"))
    parser.add_argument("--end-month", type=parse_month, default=parse_month("2025-12"))
    parser.add_argument("--force", action="store_true", help="Baixa novamente arquivos íntegros existentes.")
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw" / "vra",
    )
    args = parser.parse_args()
    if args.start_month > args.end_month:
        parser.error("O mês inicial não pode ser posterior ao mês final.")

    output_root = args.output_dir.resolve()
    project_data = (PROJECT_ROOT / "data").resolve()
    if output_root != project_data and project_data not in output_root.parents:
        parser.error("O diretório de saída deve permanecer dentro de data/.")

    failures: list[dict[str, str]] = []

    def collect(month: date) -> dict[str, object]:
        filename = f"VRA_{month:%Y_%m}.csv"
        url = f"{BASE_URL}{month:%Y}/{filename}"
        destination = output_root / f"{month:%Y}" / filename
        try:
            metadata = download_file(
                url=url,
                destination=destination,
                allowed_url_prefix=BASE_URL,
                force=args.force,
            )
            return {"month": f"{month:%Y-%m}", **asdict(metadata)}
        except Exception as exc:  # mantém as demais competências em execução
            return {"month": f"{month:%Y-%m}", "error": str(exc)}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(collect, month) for month in months_between(args.start_month, args.end_month)]
        for future in as_completed(futures):
            result = future.result()
            if "error" in result:
                failures.append(result)  # type: ignore[arg-type]
            print(json.dumps(result, ensure_ascii=False), flush=True)

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
