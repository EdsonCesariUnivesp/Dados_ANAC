import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.models.filters import DashboardFilters, DelayFilters


def test_normalizes_codes():
    filters = DashboardFilters(
        start_month="2025-01", end_month="2025-12", origin="sbgr", airline="glo"
    )
    assert filters.origin == "SBGR"
    assert filters.airline == "GLO"


def test_accepts_official_service_regularity_filter():
    regular = DashboardFilters(
        start_month="2025-01", end_month="2025-12", regularity="regular"
    )
    non_regular = DashboardFilters(
        start_month="2025-01", end_month="2025-12", regularity="non_regular"
    )
    assert regular.regularity == "regular"
    assert non_regular.regularity == "non_regular"


def test_rejects_unknown_service_regularity():
    with pytest.raises(ValidationError):
        DashboardFilters(
            start_month="2025-01", end_month="2025-12", regularity="charter"
        )


def test_rejects_inverted_period():
    filters = DashboardFilters(start_month="2025-12", end_month="2025-01")
    with pytest.raises(HTTPException):
        filters.validated_range()


def test_delay_filter_normalizes_codes_and_accepts_bucket():
    filters = DelayFilters(
        start_month="2025-01",
        end_month="2025-01",
        origin="sbgr",
        delay_bucket="atraso_30_39",
    )
    assert filters.origin == "SBGR"
    assert filters.delay_bucket == "atraso_30_39"
    assert filters.market == "domestic"
