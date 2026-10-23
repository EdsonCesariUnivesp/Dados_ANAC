from pathlib import Path
import zipfile

import duckdb

from coletores.build_weather import build_airport_weather, normalize_inmet_archives


def test_inmet_normalization_and_airport_mapping(tmp_path: Path):
    raw = tmp_path / "raw"
    raw.mkdir()
    station_csv = """REGIAO;SE
UF;SP
ESTACAO;TESTE
CODIGO (WMO);A000
LATITUDE;-23,5
LONGITUDE;-46,6
ALTITUDE;750
DATA DE FUNDACAO;01/01/2000
DATA (YYYY-MM-DD);HORA (UTC);PRECIPITAÇÃO TOTAL, HORÁRIO (mm);PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB);TEMPERATURA DO AR - BULBO SECO, HORARIA (°C);UMIDADE RELATIVA DO AR, HORARIA (%);VENTO, RAJADA MAXIMA (m/s);VENTO, VELOCIDADE HORARIA (m/s)
2025/01/01;0000 UTC;2,0;930,0;20,0;80;5,0;2,0
"""
    with zipfile.ZipFile(raw / "2025.zip", "w") as archive:
        archive.writestr("INMET_A000_2025.CSV", station_csv.encode("utf-8"))

    staging = tmp_path / "staging.csv"
    assert normalize_inmet_archives(raw, staging) == 1

    airports = tmp_path / "airports.csv"
    airports.write_text(
        "Agrupamento;;;;;;\n"
        "CÓDIGO OACI;LATITUDE;LONGITUDE\n"
        "SBXX;23° 30' 00'' S;46° 36' 00'' W\n",
        encoding="utf-8",
    )
    mapping = tmp_path / "mapping.csv"
    weather = tmp_path / "weather.parquet"
    build_airport_weather(staging, airports, mapping, weather)

    with duckdb.connect() as connection:
        result = connection.execute(
            "SELECT airport_icao, precipitation_mm, rainy_hours FROM read_parquet(?)",
            [str(weather)],
        ).fetchone()
    assert result == ("SBXX", 2.0, 1)
