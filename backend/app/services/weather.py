from __future__ import annotations

from typing import Any

import duckdb
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.models.filters import DelayFilters


def correlation(filters: DelayFilters) -> dict[str, Any]:
    if not settings.airport_weather_file.is_file():
        raise HTTPException(503, "Base meteorológica indisponível; execute o pipeline INMET.")
    if not settings.delay_data_file.is_file():
        raise HTTPException(503, "Base de pontualidade indisponível; execute o pipeline VRA.")
    start, end_exclusive = filters.validated_range()
    flight_clauses = ["scheduled_departure_local >= ?", "scheduled_departure_local < ?"]
    params: list[Any] = [str(settings.delay_data_file), start, end_exclusive]
    if filters.market == "domestic":
        flight_clauses.append("line_type='N'")
    elif filters.market == "international":
        flight_clauses.append("line_type='I'")
    for column, value in (
        ("airline_icao", filters.airline),
        ("origin_icao", filters.origin),
        ("destination_icao", filters.destination),
        ("delay_bucket", filters.delay_bucket),
        ("flight_status", filters.flight_status),
    ):
        if value:
            flight_clauses.append(f"{column}=?")
            params.append(value)
    params.append(str(settings.airport_weather_file))
    where = " AND ".join(flight_clauses)
    sql = f"""
      WITH monthly_flights AS (
        SELECT origin_icao AS airport_icao, year(scheduled_departure_local) AS year,
          month(scheduled_departure_local) AS month, count(*) AS flights,
          100.0 * count(*) FILTER (WHERE departure_delay_minutes >= 30) / nullif(count(*),0)
            AS delayed_30_percent,
          100.0 * count(*) FILTER (WHERE flight_status='CANCELADO') / nullif(count(*),0)
            AS cancelled_percent,
          avg(departure_delay_minutes) FILTER (WHERE departure_delay_minutes >= 0)
            AS average_delay_minutes
        FROM read_parquet(?) WHERE {where}
        GROUP BY ALL
      ), joined AS (
        SELECT f.*, w.precipitation_mm, w.rainy_hours, w.average_wind_speed_ms,
          w.maximum_wind_gust_ms, w.station_distance_km, w.observed_hours
        FROM monthly_flights f
        JOIN read_parquet(?) w USING (airport_icao, year, month)
      )
      SELECT count(*)::BIGINT AS airport_month_observations,
        count(DISTINCT airport_icao)::BIGINT AS airports,
        round(avg(station_distance_km),2) AS average_station_distance_km,
        round(corr(delayed_30_percent, precipitation_mm),4) AS delay_precipitation_correlation,
        round(corr(delayed_30_percent, maximum_wind_gust_ms),4) AS delay_wind_gust_correlation,
        round(corr(cancelled_percent, precipitation_mm),4) AS cancellation_precipitation_correlation
      FROM joined
    """
    try:
        with duckdb.connect(":memory:") as connection:
            cursor = connection.execute(sql, params)
            columns = [column[0] for column in cursor.description]
            result = dict(zip(columns, cursor.fetchone(), strict=True))
    except Exception as exc:
        raise HTTPException(500, "Falha ao calcular associação meteorológica.") from exc
    return {
        **result,
        "causal": False,
        "interpretation": "Correlação descritiva por aeroporto/mês; não comprova causa do atraso.",
    }
