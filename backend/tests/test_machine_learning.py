import json

import pytest

from backend.app.services.machine_learning import load_metrics


def test_loads_valid_ml_metrics(tmp_path):
    path = tmp_path / "metrics.json"
    expected = {
        "status": "experimental",
        "model": "HistGradientBoostingClassifier",
        "objective": "atraso 30+",
        "sampling": {"train_rows": 10000, "test_rows": 5000},
        "target": {"name": "delay"},
        "metrics": {"roc_auc": 0.7},
        "limitations": ["amostra"],
    }
    path.write_text(json.dumps(expected), encoding="utf-8")
    assert load_metrics(path) == expected


def test_rejects_incompatible_ml_metrics(tmp_path):
    path = tmp_path / "metrics.json"
    path.write_text('{"model":"unknown"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Schema"):
        load_metrics(path)
