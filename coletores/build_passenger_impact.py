from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_passenger_impact(statistics_csv: Path, delays_parquet: Path, output_file: Path) -> None:
    for source in (statistics_csv, delays_parquet):
        if not source.resolve().is_file():
            raise FileNotFoundError(source)
    output = output_file.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)

    with duckdb.connect() as connection:
        connection.execute("SET memory_limit='2GB'")
        target = str(temporary).replace("'", "''")
        query = f"""
          COPY (
            WITH passenger_month AS (
              SELECT
                upper(trim(empresa_sigla)) AS airline_icao,
                try_cast(ano AS INTEGER) AS year,
                try_cast(mes AS INTEGER) AS month,
                upper(trim(aeroporto_de_origem_sigla)) AS origin_icao,
                upper(trim(aeroporto_de_destino_sigla)) AS destination_icao,
                upper(trim(natureza)) AS market,
                sum(try_cast(replace(nullif(passageiros_pagos,''), ',', '.') AS DOUBLE)) AS paid_passengers,
                sum(try_cast(replace(nullif(passageiros_gratis,''), ',', '.') AS DOUBLE)) AS free_passengers,
                sum(try_cast(replace(nullif(decolagens,''), ',', '.') AS DOUBLE)) AS departures,
                sum(try_cast(replace(nullif(assentos,''), ',', '.') AS DOUBLE)) AS seats
              FROM read_csv(?, header=true, all_varchar=true)
              WHERE upper(trim(grupo_de_voo)) = 'REGULAR'
                AND try_cast(ano AS INTEGER) BETWEEN 2018 AND 2025
              GROUP BY ALL
            ), estimates AS (
              SELECT *, paid_passengers / nullif(departures, 0) AS estimated_paid_per_departure,
                (paid_passengers + free_passengers) / nullif(departures, 0) AS estimated_total_per_departure
              FROM passenger_month
            ), impacted AS (
              SELECT
                f.airline_icao, f.flight_number, f.digit_identifier, f.origin_icao,
                f.destination_icao, f.line_type, f.scheduled_departure_local, f.flight_status,
                f.departure_delay_minutes, f.delay_bucket,
                e.estimated_paid_per_departure AS estimated_paid_passengers_impacted,
                e.estimated_total_per_departure AS estimated_total_passengers_impacted,
                CASE WHEN e.airline_icao IS NULL THEN false ELSE true END AS estimate_matched
              FROM read_parquet(?) f
              LEFT JOIN estimates e ON e.airline_icao=f.airline_icao
                AND e.year=year(f.scheduled_departure_local)
                AND e.month=month(f.scheduled_departure_local)
                AND e.origin_icao=f.origin_icao AND e.destination_icao=f.destination_icao
                AND ((f.line_type='N' AND e.market LIKE 'DOM%') OR (f.line_type='I' AND e.market LIKE 'INTER%'))
              WHERE f.flight_status='CANCELADO' OR f.departure_delay_minutes >= 10
            )
            SELECT * FROM impacted
          ) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)
        """
        connection.execute(
            query,
            [str(statistics_csv.resolve()), str(delays_parquet.resolve())],
        )
    temporary.replace(output)


def main() -> int:
    parser = argparse.ArgumentParser(description="Estima passageiros impactados por atrasos e cancelamentos.")
    parser.add_argument(
        "--statistics-file", type=Path,
        default=PROJECT_ROOT / "data" / "staging" / "anac_statistics.csv",
    )
    parser.add_argument(
        "--delays-file", type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "flight_delay_analysis.parquet",
    )
    parser.add_argument(
        "--output-file", type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "passenger_impact_analysis.parquet",
    )
    args = parser.parse_args()
    build_passenger_impact(args.statistics_file, args.delays_file, args.output_file)
    print(args.output_file.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
