from __future__ import annotations

from datetime import date
from typing import Any

import duckdb
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.filters import DashboardFilters


BASE_RELATION = "read_parquet(?)"


def _connection() -> duckdb.DuckDBPyConnection:
    if not settings.data_file.is_file():
        raise HTTPException(503, "Base analítica indisponível.")
    connection = duckdb.connect(":memory:")
    connection.execute("SET memory_limit = '1GB'")
    connection.execute("SET threads = 4")
    return connection


def _where(filters: DashboardFilters) -> tuple[str, list[Any]]:
    start, end_exclusive = filters.validated_range()
    clauses = [
        "dt_partida_prevista_utc >= ?",
        "dt_partida_prevista_utc < ?",
        "NULLIF(TRIM(sg_icao_origem), '') IS NOT NULL",
    ]
    params: list[Any] = [start, end_exclusive]
    if filters.market == "domestic":
        clauses.append("ds_tipo_servico ILIKE '%DOMÉSTICA%'")
    elif filters.market == "international":
        clauses.append("ds_tipo_servico ILIKE '%INTERNACIONAL%'")
    for column, value in (
        ("sg_empresa_icao", filters.airline),
        ("sg_icao_origem", filters.origin),
        ("sg_icao_destino", filters.destination),
        ("ds_tipo_servico", filters.service_type),
    ):
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    return " AND ".join(clauses), params


def _rows(sql: str, params: list[Any]) -> list[dict[str, Any]]:
    try:
        with _connection() as connection:
            cursor = connection.execute(sql, [str(settings.data_file), *params])
            columns = [item[0] for item in cursor.description]
            return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, "Falha ao consultar a base analítica.") from exc


def summary(filters: DashboardFilters) -> dict[str, Any]:
    where, params = _where(filters)
    sql = f"""
        SELECT
            COUNT(*)::BIGINT AS scheduled_departures,
            COALESCE(SUM(GREATEST(TRY_CAST(qt_assentos_previstos AS BIGINT), 0)), 0)::BIGINT AS planned_seats,
            COUNT(DISTINCT sg_icao_origem)::BIGINT AS origin_airports,
            COUNT(DISTINCT sg_icao_origem || '>' || sg_icao_destino)::BIGINT AS active_routes,
            COUNT(DISTINCT sg_empresa_icao)::BIGINT AS active_airlines
        FROM {BASE_RELATION}
        WHERE {where}
    """
    return _rows(sql, params)[0]


def timeseries(filters: DashboardFilters) -> list[dict[str, Any]]:
    where, params = _where(filters)
    sql = f"""
        SELECT
            strftime(date_trunc('month', dt_partida_prevista_utc), '%Y-%m') AS month,
            COUNT(*)::BIGINT AS scheduled_departures,
            COALESCE(SUM(GREATEST(TRY_CAST(qt_assentos_previstos AS BIGINT), 0)), 0)::BIGINT AS planned_seats
        FROM {BASE_RELATION}
        WHERE {where}
        GROUP BY 1 ORDER BY 1
    """
    return _rows(sql, params)


def ranking(filters: DashboardFilters, dimension: str, limit: int) -> list[dict[str, Any]]:
    dimensions = {
        "airports": ("sg_icao_origem", "code"),
        "airlines": ("sg_empresa_icao", "code"),
        "routes": ("sg_icao_origem || ' → ' || sg_icao_destino", "code"),
    }
    if dimension not in dimensions:
        raise HTTPException(400, "Dimensão inválida.")
    expression, alias = dimensions[dimension]
    where, params = _where(filters)
    sql = f"""
        SELECT
            {expression} AS {alias},
            COUNT(*)::BIGINT AS scheduled_departures,
            COALESCE(SUM(GREATEST(TRY_CAST(qt_assentos_previstos AS BIGINT), 0)), 0)::BIGINT AS planned_seats
        FROM {BASE_RELATION}
        WHERE {where}
        GROUP BY 1
        ORDER BY scheduled_departures DESC, {alias}
        LIMIT ?
    """
    return _rows(sql, [*params, limit])


def metadata() -> dict[str, Any]:
    sql = f"""
        SELECT
            strftime(MIN(dt_referencia), '%Y-%m-%d') AS min_date,
            strftime(MAX(dt_referencia), '%Y-%m-%d') AS max_date,
            COUNT(*)::BIGINT AS records
        FROM {BASE_RELATION}
    """
    result = _rows(sql, [])
    return {
        **result[0],
        "source": "ANAC / SIROS",
        "scope": "Programação de voos e assentos previstos",
        "limitations": [
            "Os registros não comprovam que o voo foi realizado.",
            "Assentos previstos não representam passageiros transportados.",
            "A base não contém cancelamentos nem horários realizados.",
        ],
    }


def filter_options() -> dict[str, list[str]]:
    sql = f"""
        SELECT
            list_sort(list_distinct(list(sg_empresa_icao))) AS airlines,
            list_sort(list_distinct(list(sg_icao_origem))) AS origins,
            list_sort(list_distinct(list(sg_icao_destino))) AS destinations,
            list_sort(list_distinct(list(ds_tipo_servico))) AS service_types
        FROM {BASE_RELATION}
    """
    return _rows(sql, [])[0]
