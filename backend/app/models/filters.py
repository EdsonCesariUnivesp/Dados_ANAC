from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from backend.app.core.config import settings


class DashboardFilters(BaseModel):
    start_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    end_month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    market: str = Field(default="all", pattern=r"^(all|domestic|international)$")
    airline: str | None = Field(default=None, pattern=r"^[A-Z0-9]{2,4}$")
    origin: str | None = Field(default=None, pattern=r"^[A-Z0-9]{3,4}$")
    destination: str | None = Field(default=None, pattern=r"^[A-Z0-9]{3,4}$")
    service_type: str | None = Field(default=None, max_length=100)

    @field_validator("airline", "origin", "destination", mode="before")
    @classmethod
    def uppercase_codes(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else None

    def validated_range(self) -> tuple[date, date]:
        start = date.fromisoformat(f"{self.start_month}-01")
        end_base = date.fromisoformat(f"{self.end_month}-01")
        if start > end_base:
            raise HTTPException(422, "O mês inicial não pode ser posterior ao mês final.")
        months = (end_base.year - start.year) * 12 + end_base.month - start.month + 1
        if months > settings.max_period_months:
            raise HTTPException(422, f"O intervalo máximo é de {settings.max_period_months} meses.")
        if end_base.month == 12:
            end_exclusive = date(end_base.year + 1, 1, 1)
        else:
            end_exclusive = date(end_base.year, end_base.month + 1, 1)
        return start, end_exclusive


def dashboard_filters(
    start_month: str = Query("2025-01", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    end_month: str = Query("2025-12", pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    market: str = Query("all", pattern=r"^(all|domestic|international)$"),
    airline: str | None = Query(None, pattern=r"^[A-Za-z0-9]{2,4}$"),
    origin: str | None = Query(None, pattern=r"^[A-Za-z0-9]{3,4}$"),
    destination: str | None = Query(None, pattern=r"^[A-Za-z0-9]{3,4}$"),
    service_type: str | None = Query(None, max_length=100),
) -> DashboardFilters:
    filters = DashboardFilters(
        start_month=start_month,
        end_month=end_month,
        market=market,
        airline=airline,
        origin=origin,
        destination=destination,
        service_type=service_type,
    )
    filters.validated_range()
    return filters
