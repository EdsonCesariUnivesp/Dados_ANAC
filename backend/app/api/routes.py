from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.models.filters import DashboardFilters, DelayFilters, dashboard_filters, delay_filters
from backend.app.services import analytics, delays, machine_learning, passengers, weather


router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metadata")
def metadata():
    return analytics.metadata()


@router.get("/filters")
def filters():
    return analytics.filter_options()


@router.get("/summary")
def summary(filters: DashboardFilters = Depends(dashboard_filters)):
    return analytics.summary(filters)


@router.get("/timeseries")
def timeseries(filters: DashboardFilters = Depends(dashboard_filters)):
    return analytics.timeseries(filters)


@router.get("/airports")
def airports(
    filters: DashboardFilters = Depends(dashboard_filters),
    limit: int = Query(15, ge=1, le=100),
):
    return analytics.ranking(filters, "airports", limit)


@router.get("/airlines")
def airlines(
    filters: DashboardFilters = Depends(dashboard_filters),
    limit: int = Query(15, ge=1, le=100),
):
    return analytics.ranking(filters, "airlines", limit)


@router.get("/routes")
def routes(
    filters: DashboardFilters = Depends(dashboard_filters),
    limit: int = Query(15, ge=1, le=100),
):
    return analytics.ranking(filters, "routes", limit)


@router.get("/delays/summary")
def delay_summary(filters: DelayFilters = Depends(delay_filters)):
    return delays.summary(filters)


@router.get("/delays/timeseries")
def delay_timeseries(filters: DelayFilters = Depends(delay_filters)):
    return delays.timeseries(filters)


@router.get("/delays/buckets")
def delay_buckets(filters: DelayFilters = Depends(delay_filters)):
    return delays.buckets(filters)


@router.get("/delays/airports")
def delay_airports(
    filters: DelayFilters = Depends(delay_filters),
    limit: int = Query(15, ge=1, le=100),
):
    return delays.ranking(filters, "airports", limit)


@router.get("/delays/airlines")
def delay_airlines(
    filters: DelayFilters = Depends(delay_filters),
    limit: int = Query(15, ge=1, le=100),
):
    return delays.ranking(filters, "airlines", limit)


@router.get("/delays/flights")
def delay_flights(
    filters: DelayFilters = Depends(delay_filters),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0, le=10_000_000),
):
    return delays.flight_details(filters, limit, offset)


@router.get("/cancellations")
def cancellations(filters: DelayFilters = Depends(delay_filters)):
    return delays.cancellations(filters)


@router.get("/data-quality")
def data_quality():
    return delays.data_quality()


@router.get("/collection/status")
def collection_status():
    return delays.collection_status()


@router.get("/passengers/impacted")
def impacted_passengers(filters: DelayFilters = Depends(delay_filters)):
    return passengers.impacted(filters)


@router.get("/weather/correlation")
def weather_correlation(filters: DelayFilters = Depends(delay_filters)):
    return weather.correlation(filters)


@router.get("/ml/delay-analysis")
def ml_delay_analysis():
    return machine_learning.analysis()
