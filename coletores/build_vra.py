from __future__ import annotations

import argparse
from pathlib import Path

import duckdb


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _sql_paths(paths: list[Path]) -> str:
    return "[" + ",".join("'" + str(path).replace("'", "''") + "'" for path in paths) + "]"


def build_vra(raw_dir: Path, output_file: Path) -> None:
    raw_root = raw_dir.resolve()
    files = sorted(raw_root.glob("**/VRA_????_??.csv"))
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo VRA encontrado em {raw_root}")

    output = output_file.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".part")
    temporary.unlink(missing_ok=True)
    sources = _sql_paths(files)

    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='2GB'")
    connection.execute("SET threads=4")
    query = f"""
        COPY (
          WITH source AS (
            SELECT *
            FROM read_csv(
              {sources}, delim=';', header=true, all_varchar=true,
              union_by_name=true, strict_mode=true, encoding='utf-8'
            )
          ), normalized AS (
            SELECT
              upper(trim("Sigla ICAO Empresa Aérea")) AS airline_icao,
              trim("Empresa Aérea") AS airline_name,
              lpad(trim("Número Voo"), 4, '0') AS flight_number,
              trim("Código DI") AS digit_identifier,
              upper(trim("Código Tipo Linha")) AS line_type,
              upper(trim("Modelo Equipamento")) AS equipment_icao,
              try_cast(nullif(trim("Número de Assentos"), '') AS INTEGER) AS planned_seats,
              upper(trim("Sigla ICAO Aeroporto Origem")) AS origin_icao,
              trim("Descrição Aeroporto Origem") AS origin_name,
              try_strptime(trim("Partida Prevista"), '%d/%m/%Y %H:%M') AS scheduled_departure_local,
              try_strptime(trim("Partida Real"), '%d/%m/%Y %H:%M') AS actual_departure_local,
              upper(trim("Sigla ICAO Aeroporto Destino")) AS destination_icao,
              trim("Descrição Aeroporto Destino") AS destination_name,
              try_strptime(trim("Chegada Prevista"), '%d/%m/%Y %H:%M') AS scheduled_arrival_local,
              try_strptime(trim("Chegada Real"), '%d/%m/%Y %H:%M') AS actual_arrival_local,
              CASE
                WHEN upper(trim("Situação Voo")) IN ('NÃO INFORMADO', 'NAO INFORMADO') THEN 'NAO_INFORMADO'
                ELSE upper(trim("Situação Voo"))
              END AS flight_status,
              nullif(trim("Justificativa"), '') AS justification,
              try_strptime(trim("Referência"), '%d/%m/%Y %H:%M:%S') AS reference_month,
              nullif(trim("Codeshare"), '') AS codeshare
            FROM source
          ), scoped AS (
            SELECT *,
              CASE
                WHEN flight_status = 'REALIZADO'
                  AND scheduled_departure_local IS NOT NULL
                  AND actual_departure_local IS NOT NULL
                THEN date_diff('minute', scheduled_departure_local, actual_departure_local)
              END AS departure_delay_minutes
            FROM normalized
            WHERE line_type = 'N'
              AND (
                scheduled_departure_local >= TIMESTAMP '2018-01-01 00:00:00'
                AND scheduled_departure_local < TIMESTAMP '2026-01-01 00:00:00'
                OR scheduled_departure_local IS NULL
                  AND reference_month >= TIMESTAMP '2018-01-01 00:00:00'
                  AND reference_month < TIMESTAMP '2026-01-01 00:00:00'
              )
          ), classified AS (
            SELECT *,
              CASE
                WHEN flight_status = 'CANCELADO' THEN 'cancelado'
                WHEN flight_status <> 'REALIZADO' OR departure_delay_minutes IS NULL THEN 'nao_informado'
                WHEN departure_delay_minutes < 0 THEN 'antecipado'
                WHEN departure_delay_minutes < 10 THEN 'pontual'
                WHEN departure_delay_minutes < 20 THEN 'atraso_10_19'
                WHEN departure_delay_minutes < 30 THEN 'atraso_20_29'
                WHEN departure_delay_minutes < 40 THEN 'atraso_30_39'
                WHEN departure_delay_minutes < 50 THEN 'atraso_40_49'
                WHEN departure_delay_minutes < 60 THEN 'atraso_50_59'
                WHEN departure_delay_minutes < 90 THEN 'atraso_60_89'
                WHEN departure_delay_minutes < 120 THEN 'atraso_90_119'
                ELSE 'atraso_critico_120_mais'
              END AS delay_bucket,
              row_number() OVER (
                PARTITION BY airline_icao, flight_number, digit_identifier,
                  origin_icao, destination_icao, scheduled_departure_local
                ORDER BY reference_month DESC NULLS LAST
              ) AS duplicate_rank
            FROM scoped
          )
          SELECT * EXCLUDE (duplicate_rank)
          FROM classified
          WHERE duplicate_rank = 1
        ) TO '{str(temporary).replace("'", "''")}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """
    try:
        connection.execute(query)
        temporary.replace(output)
    finally:
        connection.close()
        temporary.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza o VRA em Parquet analítico.")
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw" / "vra")
    parser.add_argument(
        "--output-file",
        type=Path,
        default=PROJECT_ROOT / "data" / "curated" / "flight_delay_analysis.parquet",
    )
    args = parser.parse_args()
    build_vra(args.raw_dir, args.output_file)
    print(args.output_file.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
