from __future__ import annotations

import argparse
import csv
import io
import math
import re
import zipfile
from datetime import datetime
from pathlib import Path

import duckdb

from coletores.import_anac_statistics import canonical_header


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEATHER_FIELDS = {
    "precipitacao_total_horario_mm": "precipitation_mm",
    "pressao_atmosferica_ao_nivel_da_estacao_horaria_mb": "pressure_hpa",
    "temperatura_do_ar_bulbo_seco_horaria_c": "temperature_c",
    "umidade_relativa_do_ar_horaria": "humidity_percent",
    "vento_rajada_maxima_m_s": "wind_gust_ms",
    "vento_velocidade_horaria_m_s": "wind_speed_ms",
}


def _decimal(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.strip().replace(",", "."))
    except ValueError:
        return None


def _timestamp(day: str, hour: str) -> str | None:
    digits = re.sub(r"\D", "", hour or "")[:4].zfill(4)
    for pattern in ("%Y/%m/%d%H%M", "%Y-%m-%d%H%M", "%d/%m/%Y%H%M"):
        try:
            return datetime.strptime(day.strip() + digits, pattern).strftime("%Y-%m-%dT%H:%M:00")
        except ValueError:
            continue
    return None


def normalize_inmet_archives(raw_dir: Path, output_csv: Path) -> int:
    archives = sorted(raw_dir.resolve().glob("20??.zip"))
    if not archives:
        raise FileNotFoundError(f"Nenhum ZIP INMET encontrado em {raw_dir}")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_csv.with_suffix(output_csv.suffix + ".part")
    fields = [
        "station_code", "station_name", "state", "latitude", "longitude", "altitude_m",
        "observed_at_utc", *WEATHER_FIELDS.values(),
    ]
    records = 0
    with temporary.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        for archive_path in archives:
            with zipfile.ZipFile(archive_path) as archive:
                for info in archive.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".csv"):
                        continue
                    if info.flag_bits & 0x1 or info.file_size > 100 * 1024 * 1024:
                        raise ValueError(f"Membro ZIP inseguro ou grande demais: {info.filename}")
                    payload = archive.read(info)
                    try:
                        text = payload.decode("utf-8-sig")
                    except UnicodeDecodeError:
                        text = payload.decode("latin-1")
                    lines = text.splitlines()
                    if len(lines) < 10:
                        continue
                    metadata: dict[str, str] = {}
                    header_index = None
                    for index, line in enumerate(lines[:15]):
                        columns = [canonical_header(item) for item in line.split(";")]
                        if columns[0].startswith("data") and any(item.startswith("hora_utc") for item in columns):
                            header_index = index
                            break
                        key, _, value = line.partition(";")
                        metadata[canonical_header(key)] = value.strip().rstrip(";")
                    if header_index is None:
                        continue
                    reader = csv.DictReader(io.StringIO("\n".join(lines[header_index:])), delimiter=";")
                    if not reader.fieldnames:
                        continue
                    source_names = {canonical_header(name): name for name in reader.fieldnames}
                    date_name = next((value for key, value in source_names.items() if key.startswith("data")), None)
                    hour_name = next((value for key, value in source_names.items() if key.startswith("hora_utc")), None)
                    if not date_name or not hour_name:
                        continue
                    for row in reader:
                        observed_at = _timestamp(row.get(date_name, ""), row.get(hour_name, ""))
                        if not observed_at:
                            continue
                        result = {
                            "station_code": metadata.get("codigo_wmo", ""),
                            "station_name": metadata.get("estacao", ""),
                            "state": metadata.get("uf", ""),
                            "latitude": _decimal(metadata.get("latitude")),
                            "longitude": _decimal(metadata.get("longitude")),
                            "altitude_m": _decimal(metadata.get("altitude")),
                            "observed_at_utc": observed_at,
                        }
                        for normalized, target in WEATHER_FIELDS.items():
                            source_name = source_names.get(normalized)
                            result[target] = _decimal(row.get(source_name, "")) if source_name else None
                        writer.writerow(result)
                        records += 1
    temporary.replace(output_csv)
    return records


def _dms(value: str) -> float:
    match = re.search(r"(\d+)[^\d]+(\d+)[^\d]+(\d+(?:[.,]\d+)?)?[^NSEW]*([NSEW])", value.upper())
    if not match:
        raise ValueError(f"Coordenada inválida: {value}")
    degrees, minutes, seconds, direction = match.groups()
    decimal = float(degrees) + float(minutes) / 60 + float((seconds or "0").replace(",", ".")) / 3600
    return -decimal if direction in {"S", "W"} else decimal


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    delta_p = math.radians(lat2 - lat1)
    delta_l = math.radians(lon2 - lon1)
    a = math.sin(delta_p / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(delta_l / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def build_airport_weather(
    staging_csv: Path,
    airports_csv: Path,
    mapping_csv: Path,
    output_parquet: Path,
    max_distance_km: float = 50.0,
) -> None:
    with duckdb.connect() as connection:
        stations = connection.execute(
            "SELECT station_code, any_value(station_name), any_value(latitude), any_value(longitude) "
            "FROM read_csv(?, header=true, all_varchar=true) "
            "WHERE try_cast(latitude AS DOUBLE) IS NOT NULL AND try_cast(longitude AS DOUBLE) IS NOT NULL "
            "GROUP BY station_code",
            [str(staging_csv.resolve())],
        ).fetchall()

    airports: list[tuple[str, float, float]] = []
    with airports_csv.open("r", encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, delimiter=";", skipinitialspace=True)
        # O arquivo oficial possui uma linha de agrupamento antes do cabeçalho real.
        if not reader.fieldnames or "CÓDIGO OACI" not in reader.fieldnames:
            source.seek(0)
            next(source)
            reader = csv.DictReader(source, delimiter=";")
        for row in reader:
            try:
                airports.append((row["CÓDIGO OACI"].strip(), _dms(row["LATITUDE"]), _dms(row["LONGITUDE"])))
            except (KeyError, ValueError, AttributeError):
                continue

    mapping_csv.parent.mkdir(parents=True, exist_ok=True)
    with mapping_csv.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["airport_icao", "station_code", "station_name", "distance_km", "within_limit"],
        )
        writer.writeheader()
        for airport, lat, lon in airports:
            candidates = [
                (_distance_km(lat, lon, float(slat), float(slon)), code, name)
                for code, name, slat, slon in stations
            ]
            if not candidates:
                continue
            distance, code, name = min(candidates)
            writer.writerow(
                {
                    "airport_icao": airport,
                    "station_code": code,
                    "station_name": name,
                    "distance_km": round(distance, 3),
                    "within_limit": distance <= max_distance_km,
                }
            )

    output_parquet.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_parquet.with_suffix(output_parquet.suffix + ".part")
    target = str(temporary.resolve()).replace("'", "''")
    with duckdb.connect() as connection:
        connection.execute(
            f"""
              COPY (
                SELECT m.airport_icao, m.station_code, any_value(m.station_name) AS station_name,
                  any_value(try_cast(m.distance_km AS DOUBLE)) AS station_distance_km,
                  year(try_cast(w.observed_at_utc AS TIMESTAMP)) AS year,
                  month(try_cast(w.observed_at_utc AS TIMESTAMP)) AS month,
                  count(*)::BIGINT AS observed_hours,
                  round(sum(try_cast(w.precipitation_mm AS DOUBLE)), 2) AS precipitation_mm,
                  count(*) FILTER (WHERE try_cast(w.precipitation_mm AS DOUBLE) > 0)::BIGINT AS rainy_hours,
                  round(avg(try_cast(w.temperature_c AS DOUBLE)), 2) AS average_temperature_c,
                  round(avg(try_cast(w.wind_speed_ms AS DOUBLE)), 2) AS average_wind_speed_ms,
                  round(max(try_cast(w.wind_gust_ms AS DOUBLE)), 2) AS maximum_wind_gust_ms,
                  round(avg(try_cast(w.humidity_percent AS DOUBLE)), 2) AS average_humidity_percent,
                  round(avg(try_cast(w.pressure_hpa AS DOUBLE)), 2) AS average_pressure_hpa
                FROM read_csv(?, header=true, all_varchar=true) w
                JOIN read_csv(?, header=true, all_varchar=true) m USING (station_code)
                WHERE lower(m.within_limit)='true'
                GROUP BY m.airport_icao, m.station_code, year, month
              ) TO '{target}' (FORMAT PARQUET, COMPRESSION ZSTD)
            """,
            [str(staging_csv.resolve()), str(mapping_csv.resolve())],
        )
    temporary.replace(output_parquet)


def main() -> int:
    parser = argparse.ArgumentParser(description="Normaliza INMET e agrega meteorologia por aeroporto/mês.")
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data" / "raw" / "inmet")
    parser.add_argument("--airports-file", type=Path, default=PROJECT_ROOT / "data_aerodromos" / "AerodromosPublicos.csv")
    parser.add_argument("--max-distance-km", type=float, default=50.0)
    args = parser.parse_args()
    staging = PROJECT_ROOT / "data" / "staging" / "inmet_hourly.csv"
    mapping = PROJECT_ROOT / "data" / "curated" / "airport_station_mapping.csv"
    output = PROJECT_ROOT / "data" / "curated" / "airport_weather.parquet"
    records = normalize_inmet_archives(args.raw_dir, staging)
    build_airport_weather(staging, args.airports_file, mapping, output, args.max_distance_km)
    print(f"{records} observações normalizadas; saída: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
