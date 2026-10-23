from __future__ import annotations

import json
from typing import Any

import duckdb
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.filters import DelayFilters


BASE_RELATION = "read_parquet(?)"


def _connection() -> duckdb.DuckDBPyConnection:
    if not settings.delay_data_file.is_file():
        raise HTTPException(503, "Base de pontualidade indisponível; execute o pipeline VRA.")
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit='1GB'")
    connection.execute("SET threads=4")
    return connection


def _where(filters: DelayFilters) -> tuple[str, list[Any]]:
    start, end_exclusive = filters.validated_range()
    clauses = ["scheduled_departure_local >= ?", "scheduled_departure_local < ?"]
    params: list[Any] = [start, end_exclusive]
    clauses.append("line_type = 'N'")
    for column, value in (
        ("airline_icao", filters.airline),
        ("origin_icao", filters.origin),
        ("destination_icao", filters.destination),
        ("delay_bucket", filters.delay_bucket),
        ("flight_status", filters.flight_status),
    ):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    return " AND ".join(clauses), params


def _rows(sql: str, params: list[Any]) -> list[dict[str, Any]]:
    try:
        with _connection() as connection:
            cursor = connection.execute(sql, [str(settings.delay_data_file), *params])
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Falha ao consultar a base de pontualidade.") from exc


def summary(filters: DelayFilters) -> dict[str, Any]:
    where, params = _where(filters)
    sql = f"""
        SELECT
          count(*)::BIGINT AS scheduled_flights,
          count(*) FILTER (WHERE flight_status = 'REALIZADO')::BIGINT AS operated_flights,
          count(*) FILTER (WHERE flight_status = 'CANCELADO')::BIGINT AS cancelled_flights,
          round(100.0 * count(*) FILTER (WHERE delay_bucket IN ('antecipado','pontual'))
            / nullif(count(*) FILTER (WHERE flight_status = 'REALIZADO'), 0), 2) AS punctuality_percent,
          round(avg(departure_delay_minutes) FILTER (WHERE departure_delay_minutes >= 0), 2) AS average_delay_minutes,
          round(median(departure_delay_minutes) FILTER (WHERE departure_delay_minutes >= 0), 2) AS median_delay_minutes,
          count(*) FILTER (WHERE departure_delay_minutes >= 10)::BIGINT AS delayed_10_plus,
          count(*) FILTER (WHERE departure_delay_minutes >= 30)::BIGINT AS delayed_30_plus,
          count(*) FILTER (WHERE departure_delay_minutes >= 60)::BIGINT AS delayed_60_plus,
          count(*) FILTER (WHERE departure_delay_minutes >= 90)::BIGINT AS delayed_90_plus,
          count(*) FILTER (WHERE departure_delay_minutes >= 120)::BIGINT AS delayed_120_plus
        FROM {BASE_RELATION}
        WHERE {where}
    """
    return _rows(sql, params)[0]


def buckets(filters: DelayFilters) -> list[dict[str, Any]]:
    where, params = _where(filters)
    return _rows(
        f"""
          SELECT delay_bucket AS bucket, count(*)::BIGINT AS flights
          FROM {BASE_RELATION} WHERE {where}
          GROUP BY 1
          ORDER BY CASE delay_bucket
            WHEN 'antecipado' THEN 1 WHEN 'pontual' THEN 2 WHEN 'atraso_10_19' THEN 3
            WHEN 'atraso_20_29' THEN 4 WHEN 'atraso_30_39' THEN 5 WHEN 'atraso_40_49' THEN 6
            WHEN 'atraso_50_59' THEN 7 WHEN 'atraso_60_89' THEN 8 WHEN 'atraso_90_119' THEN 9
            WHEN 'atraso_critico_120_mais' THEN 10 WHEN 'cancelado' THEN 11 ELSE 12 END
        """,
        params,
    )


def timeseries(filters: DelayFilters) -> list[dict[str, Any]]:
    where, params = _where(filters)
    return _rows(
        f"""
          SELECT strftime(date_trunc('month', scheduled_departure_local), '%Y-%m') AS month,
            count(*)::BIGINT AS scheduled_flights,
            count(*) FILTER (WHERE flight_status='REALIZADO')::BIGINT AS operated_flights,
            count(*) FILTER (WHERE flight_status='CANCELADO')::BIGINT AS cancelled_flights,
            count(*) FILTER (WHERE departure_delay_minutes >= 30)::BIGINT AS delayed_30_plus,
            round(avg(departure_delay_minutes) FILTER (WHERE departure_delay_minutes >= 0), 2)
              AS average_delay_minutes
          FROM {BASE_RELATION} WHERE {where}
          GROUP BY 1 ORDER BY 1
        """,
        params,
    )


def ranking(filters: DelayFilters, dimension: str, limit: int) -> list[dict[str, Any]]:
    dimensions = {"airports": "origin_icao", "airlines": "airline_icao"}
    column = dimensions.get(dimension)
    if column is None:
        raise HTTPException(400, "Dimensão inválida.")
    where, params = _where(filters)
    return _rows(
        f"""
          SELECT {column} AS code, count(*)::BIGINT AS scheduled_flights,
            count(*) FILTER (WHERE flight_status='CANCELADO')::BIGINT AS cancelled_flights,
            count(*) FILTER (WHERE departure_delay_minutes >= 30)::BIGINT AS delayed_30_plus,
            round(avg(departure_delay_minutes) FILTER (WHERE departure_delay_minutes >= 0), 2)
              AS average_delay_minutes
          FROM {BASE_RELATION} WHERE {where}
          GROUP BY 1 ORDER BY delayed_30_plus DESC, code LIMIT ?
        """,
        [*params, limit],
    )


def cancellations(filters: DelayFilters) -> list[dict[str, Any]]:
    where, params = _where(filters)
    return _rows(
        f"""
          SELECT strftime(date_trunc('month', scheduled_departure_local), '%Y-%m') AS month,
            count(*)::BIGINT AS cancellations
          FROM {BASE_RELATION}
          WHERE {where} AND flight_status='CANCELADO'
          GROUP BY 1 ORDER BY 1
        """,
        params,
    )


def flight_details(filters: DelayFilters, limit: int, offset: int) -> list[dict[str, Any]]:
    where, params = _where(filters)
    return _rows(
        f"""
          SELECT airline_icao, flight_number, origin_icao, destination_icao,
            strftime(scheduled_departure_local, '%Y-%m-%dT%H:%M:%S') AS scheduled_departure,
            strftime(actual_departure_local, '%Y-%m-%dT%H:%M:%S') AS actual_departure,
            flight_status, departure_delay_minutes, delay_bucket
          FROM {BASE_RELATION} WHERE {where}
          ORDER BY scheduled_departure_local DESC, airline_icao, flight_number
          LIMIT ? OFFSET ?
        """,
        [*params, limit, offset],
    )


def data_quality() -> dict[str, Any]:
    sql = f"""
      SELECT count(*)::BIGINT AS records,
        strftime(min(scheduled_departure_local), '%Y-%m-%d') AS min_date,
        strftime(max(scheduled_departure_local), '%Y-%m-%d') AS max_date,
        count(*) FILTER (WHERE scheduled_departure_local IS NULL)::BIGINT AS missing_scheduled_departure,
        count(*) FILTER (WHERE flight_status='REALIZADO' AND actual_departure_local IS NULL)::BIGINT
          AS operated_missing_actual_departure,
        count(*) FILTER (WHERE delay_bucket='nao_informado')::BIGINT AS not_informed,
        count(*) FILTER (WHERE planned_seats IS NULL)::BIGINT AS missing_planned_seats,
        count(*) FILTER (WHERE abs(departure_delay_minutes) > 1440)::BIGINT AS delay_over_24_hours
      FROM {BASE_RELATION}
    """
    result = _rows(sql, [])[0]
    return {
        **result,
        "scope": "Fase inicial: voos domésticos regulares de passageiros; tipo de linha N.",
        "timezone": "Horário de Brasília conforme definição da fonte; timestamps preservados sem conversão implícita.",
    }


def collection_status() -> dict[str, Any]:
    root = settings.collection_manifest_dir
    if not root.is_dir():
        return {"available": False, "collected_files": 0, "last_collection_utc": None}
    metadata_files = list(root.glob("**/*.metadata.json"))
    collected: list[str] = []
    for path in metadata_files:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if value.get("collected_at_utc"):
                collected.append(value["collected_at_utc"])
        except (OSError, ValueError, TypeError):
            continue
    return {
        "available": bool(metadata_files),
        "collected_files": len(metadata_files),
        "last_collection_utc": max(collected, default=None),
    }
