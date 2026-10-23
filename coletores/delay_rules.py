from __future__ import annotations


REGULAR_PASSENGER_LINE_TYPES = frozenset({"N"})


def classify_departure(*, delay_minutes: int | None, flight_status: str) -> str:
    status = flight_status.strip().upper()
    if status == "CANCELADO":
        return "cancelado"
    if status != "REALIZADO" or delay_minutes is None:
        return "nao_informado"
    if delay_minutes < 0:
        return "antecipado"
    if delay_minutes < 10:
        return "pontual"
    if delay_minutes < 20:
        return "atraso_10_19"
    if delay_minutes < 30:
        return "atraso_20_29"
    if delay_minutes < 40:
        return "atraso_30_39"
    if delay_minutes < 50:
        return "atraso_40_49"
    if delay_minutes < 60:
        return "atraso_50_59"
    if delay_minutes < 90:
        return "atraso_60_89"
    if delay_minutes < 120:
        return "atraso_90_119"
    return "atraso_critico_120_mais"
