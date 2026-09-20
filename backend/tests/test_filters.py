import pytest
from fastapi import HTTPException

from backend.app.models.filters import DashboardFilters


def test_normalizes_codes():
    filters = DashboardFilters(
        start_month="2025-01", end_month="2025-12", origin="sbgr", airline="glo"
    )
    assert filters.origin == "SBGR"
    assert filters.airline == "GLO"


def test_rejects_inverted_period():
    filters = DashboardFilters(start_month="2025-12", end_month="2025-01")
    with pytest.raises(HTTPException):
        filters.validated_range()
