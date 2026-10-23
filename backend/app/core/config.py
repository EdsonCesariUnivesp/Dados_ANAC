from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _environment_flag(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "Dashboard da Malha Aérea Brasileira"
    environment: str = os.getenv("APP_ENV", "development")
    data_file: Path = Path(
        os.getenv(
            "ANAC_DATA_FILE",
            str(PROJECT_ROOT / "data_voo" / "dados_completos.parquet"),
        )
    ).resolve()
    delay_data_file: Path = Path(
        os.getenv(
            "ANAC_DELAY_DATA_FILE",
            str(PROJECT_ROOT / "data" / "curated" / "flight_delay_analysis.parquet"),
        )
    ).resolve()
    collection_manifest_dir: Path = Path(
        os.getenv("ANAC_MANIFEST_DIR", str(PROJECT_ROOT / "data" / "raw" / "vra"))
    ).resolve()
    passenger_impact_file: Path = Path(
        os.getenv(
            "ANAC_PASSENGER_IMPACT_FILE",
            str(PROJECT_ROOT / "data" / "curated" / "passenger_impact_analysis.parquet"),
        )
    ).resolve()
    airport_weather_file: Path = Path(
        os.getenv(
            "INMET_AIRPORT_WEATHER_FILE",
            str(PROJECT_ROOT / "data" / "curated" / "airport_weather.parquet"),
        )
    ).resolve()
    ml_delay_metrics_file: Path = Path(
        os.getenv(
            "ANAC_ML_DELAY_METRICS_FILE",
            str(PROJECT_ROOT / "data" / "curated" / "delay_ml_metrics.json"),
        )
    ).resolve()
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    max_period_months: int = int(os.getenv("MAX_PERIOD_MONTHS", "120"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    serve_frontend: bool = _environment_flag("SERVE_FRONTEND")
    frontend_dir: Path = Path(
        os.getenv("FRONTEND_DIR", str(PROJECT_ROOT / "frontend" / "dist"))
    ).resolve()


settings = Settings()
