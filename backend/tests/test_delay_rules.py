import pytest

from coletores.delay_rules import REGULAR_PASSENGER_LINE_TYPES, classify_departure


@pytest.mark.parametrize(
    ("minutes", "expected"),
    [
        (-1, "antecipado"),
        (0, "pontual"),
        (9, "pontual"),
        (10, "atraso_10_19"),
        (19, "atraso_10_19"),
        (20, "atraso_20_29"),
        (29, "atraso_20_29"),
        (30, "atraso_30_39"),
        (39, "atraso_30_39"),
        (40, "atraso_40_49"),
        (49, "atraso_40_49"),
        (50, "atraso_50_59"),
        (59, "atraso_50_59"),
        (60, "atraso_60_89"),
        (89, "atraso_60_89"),
        (90, "atraso_90_119"),
        (119, "atraso_90_119"),
        (120, "atraso_critico_120_mais"),
    ],
)
def test_delay_bucket_boundaries(minutes, expected):
    assert classify_departure(delay_minutes=minutes, flight_status="REALIZADO") == expected


def test_cancelled_is_never_reclassified_as_delay():
    assert classify_departure(delay_minutes=300, flight_status="CANCELADO") == "cancelado"


def test_missing_or_unknown_flight_is_not_informed():
    assert classify_departure(delay_minutes=None, flight_status="REALIZADO") == "nao_informado"
    assert classify_departure(delay_minutes=10, flight_status="NÃO INFORMADO") == "nao_informado"


def test_regular_passenger_scope_is_an_explicit_allowlist():
    assert REGULAR_PASSENGER_LINE_TYPES == {"N"}
    assert not ({"C", "G"} & REGULAR_PASSENGER_LINE_TYPES)
