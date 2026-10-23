from pathlib import Path

import duckdb

from coletores.build_vra import build_vra


HEADER = (
    "Sigla ICAO Empresa Aérea;Empresa Aérea;Número Voo;Código DI;Código Tipo Linha;"
    "Modelo Equipamento;Número de Assentos;Sigla ICAO Aeroporto Origem;"
    "Descrição Aeroporto Origem;Partida Prevista;Partida Real;"
    "Sigla ICAO Aeroporto Destino;Descrição Aeroporto Destino;Chegada Prevista;"
    "Chegada Real;Situação Voo;Justificativa;Referência;Situação Partida;"
    "Situação Chegada;Codeshare\n"
)


def row(*, flight_number="0001", line_type="N", status="REALIZADO", actual="01/01/2025 10:10"):
    return (
        f"TST;EMPRESA TESTE;{flight_number};0;{line_type};A320;180;SBGR;GUARULHOS;"
        f"01/01/2025 10:00;{actual};SBBR;BRASILIA;01/01/2025 11:30;"
        f"01/01/2025 11:40;{status};;01/01/2025 00:00:00;;;\n"
    )


def test_pipeline_filters_deduplicates_and_classifies(tmp_path: Path):
    raw = tmp_path / "raw" / "2025"
    raw.mkdir(parents=True)
    source = raw / "VRA_2025_01.csv"
    source.write_text(
        HEADER
        + row()
        + row()  # duplicata operacional
        + row(line_type="G")  # carga excluída
        + row(line_type="I")  # internacional fora da fase inicial
        + row(flight_number="0002", status="CANCELADO", actual=""),
        encoding="utf-8",
    )
    output = tmp_path / "curated" / "flight_delay_analysis.parquet"

    build_vra(tmp_path / "raw", output)

    with duckdb.connect() as connection:
        rows = connection.execute(
            "SELECT flight_status, delay_bucket, departure_delay_minutes "
            "FROM read_parquet(?) ORDER BY flight_status",
            [str(output)],
        ).fetchall()
    assert rows == [
        ("CANCELADO", "cancelado", None),
        ("REALIZADO", "atraso_10_19", 10),
    ]
