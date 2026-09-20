from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.app.models.filters import DashboardFilters, dashboard_filters
from backend.app.services import analytics


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
