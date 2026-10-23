from __future__ import annotations

from typing import Any

import duckdb
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.filters import DelayFilters


def impacted(filters: DelayFilters) -> dict[str, Any]:
    if not settings.passenger_impact_file.is_file():
        raise HTTPException(
            503,
            "Estimativas de passageiros indisponíveis; importe os Dados Estatísticos da ANAC.",
        )
    start, end_exclusive = filters.validated_range()
    clauses = ["scheduled_departure_local >= ?", "scheduled_departure_local < ?"]
    params: list[Any] = [str(settings.passenger_impact_file), start, end_exclusive]
    if filters.market == "domestic":
        clauses.append("line_type='N'")
    elif filters.market == "international":
        clauses.append("line_type='I'")
    for column, value in (
        ("airline_icao", filters.airline),
        ("origin_icao", filters.origin),
        ("destination_icao", filters.destination),
        ("delay_bucket", filters.delay_bucket),
        ("flight_status", filters.flight_status),
    ):
        if value:
            clauses.append(f"{column}=?")
            params.append(value)
    where = " AND ".join(clauses)
    sql = f"""
      SELECT
        count(*)::BIGINT AS impacted_flights,
        count(*) FILTER (WHERE estimate_matched)::BIGINT AS matched_flights,
        round(100.0 * count(*) FILTER (WHERE estimate_matched) / nullif(count(*),0), 2)
          AS coverage_percent,
        round(sum(estimated_paid_passengers_impacted), 0)::BIGINT AS estimated_paid_passengers,
        round(sum(estimated_total_passengers_impacted), 0)::BIGINT AS estimated_total_passengers
      FROM read_parquet(?) WHERE {where}
    """
    try:
        with duckdb.connect(":memory:") as connection:
            cursor = connection.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            values = dict(zip(columns, cursor.fetchone(), strict=True))
    except Exception as exc:
        raise HTTPException(500, "Falha ao consultar estimativas de passageiros.") from exc
    return {
        **values,
        "estimated": True,
        "method": "Média mensal de passageiros por decolagem, empresa e rota.",
        "limitations": "Não representa a lista real de passageiros de cada voo.",
    }
