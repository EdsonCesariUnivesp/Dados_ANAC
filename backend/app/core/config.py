from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


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
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    max_period_months: int = int(os.getenv("MAX_PERIOD_MONTHS", "120"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))


settings = Settings()
