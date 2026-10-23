from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from backend.app.core.config import settings


MAX_METRICS_BYTES = 1024 * 1024
REQUIRED_FIELDS = {"status", "model", "objective", "sampling", "target", "metrics", "limitations"}


def load_metrics(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(resolved)
    if resolved.stat().st_size > MAX_METRICS_BYTES:
        raise ValueError("Arquivo de métricas excede o limite permitido.")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not REQUIRED_FIELDS.issubset(value):
        raise ValueError("Schema de métricas de ML incompatível.")
    return value


def analysis() -> dict[str, Any]:
    try:
        return load_metrics(settings.ml_delay_metrics_file)
    except FileNotFoundError as exc:
        raise HTTPException(503, "Experimento de machine learning ainda não processado.") from exc
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(500, "Falha ao ler métricas do experimento de machine learning.") from exc
