from pathlib import Path

import duckdb

from coletores.build_passenger_impact import build_passenger_impact
from coletores.build_vra import build_vra
from coletores.import_anac_statistics import normalize_statistics
from backend.tests.test_vra_pipeline import HEADER, row


def test_import_and_estimate_passenger_impact(tmp_path: Path):
    official = tmp_path / "DadosEstatisticos.csv"
    official.write_text(
        "EMPRESA (SIGLA);ANO;MÊS;AEROPORTO DE ORIGEM (SIGLA);"
        "AEROPORTO DE DESTINO (SIGLA);NATUREZA;GRUPO DE VOO;PASSAGEIROS PAGOS;"
        "PASSAGEIROS GRÁTIS;DECOLAGENS;ASSENTOS\n"
        "TST;2025;1;SBGR;SBBR;DOMÉSTICA;REGULAR;100;10;2;360\n",
        encoding="utf-8",
    )
    statistics = tmp_path / "staging" / "anac_statistics.csv"
    metadata = normalize_statistics(official, statistics)
    assert metadata["rows"] == 1

    raw = tmp_path / "raw" / "2025"
    raw.mkdir(parents=True)
    (raw / "VRA_2025_01.csv").write_text(
        HEADER + row(actual="01/01/2025 10:30"), encoding="utf-8"
    )
    delays = tmp_path / "curated" / "delays.parquet"
    build_vra(tmp_path / "raw", delays)
    impact = tmp_path / "curated" / "impact.parquet"
    build_passenger_impact(statistics, delays, impact)

    with duckdb.connect() as connection:
        result = connection.execute(
            "SELECT estimated_paid_passengers_impacted, estimated_total_passengers_impacted, estimate_matched "
            "FROM read_parquet(?)", [str(impact)]
        ).fetchone()
    assert result == (50.0, 55.0, True)
