from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORICAL_FEATURES = ["airline_icao", "origin_icao", "destination_icao"]
NUMERIC_FEATURES = [
    "planned_seats",
    "month_sin",
    "month_cos",
    "dow_sin",
    "dow_cos",
    "hour_sin",
    "hour_cos",
    "precipitation_mm",
    "rainy_hours",
    "average_temperature_c",
    "average_wind_speed_ms",
    "maximum_wind_gust_ms",
    "average_humidity_percent",
    "average_pressure_hpa",
]
FEATURE_LABELS = {
    "airline_icao": "Companhia aérea",
    "origin_icao": "Aeroporto de origem",
    "destination_icao": "Aeroporto de destino",
    "planned_seats": "Assentos planejados",
    "month_sin": "Mês do ano (seno)",
    "month_cos": "Mês do ano (cosseno)",
    "dow_sin": "Dia da semana (seno)",
    "dow_cos": "Dia da semana (cosseno)",
    "hour_sin": "Hora prevista (seno)",
    "hour_cos": "Hora prevista (cosseno)",
    "precipitation_mm": "Precipitação mensal",
    "rainy_hours": "Horas com chuva",
    "average_temperature_c": "Temperatura média",
    "average_wind_speed_ms": "Velocidade média do vento",
    "maximum_wind_gust_ms": "Rajada máxima",
    "average_humidity_percent": "Umidade média",
    "average_pressure_hpa": "Pressão média",
}


def _sample(
    delay_file: Path,
    weather_file: Path,
    years: tuple[int, ...],
    rows: int,
    seed: int,
) -> pd.DataFrame:
    year_list = ",".join(str(year) for year in years)
    query = f"""
      WITH eligible AS (
        SELECT
          f.airline_icao,
          f.origin_icao,
          f.destination_icao,
          try_cast(f.planned_seats AS DOUBLE) AS planned_seats,
          sin(2 * pi() * month(f.scheduled_departure_local) / 12.0) AS month_sin,
          cos(2 * pi() * month(f.scheduled_departure_local) / 12.0) AS month_cos,
          sin(2 * pi() * dayofweek(f.scheduled_departure_local) / 7.0) AS dow_sin,
          cos(2 * pi() * dayofweek(f.scheduled_departure_local) / 7.0) AS dow_cos,
          sin(2 * pi() * hour(f.scheduled_departure_local) / 24.0) AS hour_sin,
          cos(2 * pi() * hour(f.scheduled_departure_local) / 24.0) AS hour_cos,
          w.precipitation_mm,
          w.rainy_hours,
          w.average_temperature_c,
          w.average_wind_speed_ms,
          w.maximum_wind_gust_ms,
          w.average_humidity_percent,
          w.average_pressure_hpa,
          CASE WHEN f.departure_delay_minutes >= 30 THEN 1 ELSE 0 END AS delayed_30_plus
        FROM read_parquet(?) f
        JOIN read_parquet(?) w
          ON w.airport_icao=f.origin_icao
          AND w.year=year(f.scheduled_departure_local)
          AND w.month=month(f.scheduled_departure_local)
        WHERE f.line_type='N'
          AND f.flight_status='REALIZADO'
          AND f.scheduled_departure_local IS NOT NULL
          AND f.departure_delay_minutes BETWEEN -360 AND 1440
          AND year(f.scheduled_departure_local) IN ({year_list})
      ), sampled AS (
        SELECT * FROM eligible USING SAMPLE {rows} ROWS (reservoir, {seed})
      )
      SELECT * FROM sampled
    """
    with duckdb.connect(":memory:") as connection:
        connection.execute("SET memory_limit='2GB'")
        connection.execute("SET threads=2")
        return connection.execute(query, [str(delay_file), str(weather_file)]).fetchdf()


def _pipeline() -> Pipeline:
    preprocessing = ColumnTransformer(
        [
            (
                "numeric",
                SimpleImputer(strategy="median"),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        (
                            "encoder",
                            OrdinalEncoder(
                                handle_unknown="use_encoded_value",
                                unknown_value=-1,
                                max_categories=254,
                            ),
                        ),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ],
        verbose_feature_names_out=False,
    )
    categorical_indexes = list(
        range(len(NUMERIC_FEATURES), len(NUMERIC_FEATURES) + len(CATEGORICAL_FEATURES))
    )
    model = HistGradientBoostingClassifier(
        learning_rate=0.08,
        max_iter=150,
        max_leaf_nodes=31,
        max_depth=7,
        min_samples_leaf=100,
        l2_regularization=1.0,
        class_weight="balanced",
        early_stopping=True,
        validation_fraction=0.1,
        categorical_features=categorical_indexes,
        random_state=42,
    )
    return Pipeline([("preprocessing", preprocessing), ("model", model)])


def train(
    delay_file: Path,
    weather_file: Path,
    model_file: Path,
    metrics_file: Path,
    train_rows: int,
    test_rows: int,
) -> dict[str, object]:
    for path in (delay_file, weather_file):
        if not path.resolve().is_file():
            raise FileNotFoundError(path)
    training_years = (2018, 2019, 2022, 2023)
    test_years = (2024, 2025)
    train_frame = _sample(delay_file, weather_file, training_years, train_rows, 42)
    test_frame = _sample(delay_file, weather_file, test_years, test_rows, 84)
    if train_frame.empty or test_frame.empty:
        raise ValueError("A amostra temporal não retornou registros suficientes.")

    feature_columns = [*NUMERIC_FEATURES, *CATEGORICAL_FEATURES]
    x_train, y_train = train_frame[feature_columns], train_frame.pop("delayed_30_plus")
    x_test, y_test = test_frame[feature_columns], test_frame.pop("delayed_30_plus")
    estimator = _pipeline()
    estimator.fit(x_train, y_train)
    probability = estimator.predict_proba(x_test)[:, 1]
    prediction = (probability >= 0.5).astype(int)

    importance_rows = min(5000, len(x_test))
    importance = permutation_importance(
        estimator,
        x_test.iloc[:importance_rows],
        y_test.iloc[:importance_rows],
        scoring="average_precision",
        n_repeats=3,
        random_state=42,
        n_jobs=1,
    )
    ranked = sorted(
        zip(feature_columns, importance.importances_mean, strict=True),
        key=lambda item: item[1],
        reverse=True,
    )[:8]
    matrix = confusion_matrix(y_test, prediction, labels=[0, 1])
    metrics: dict[str, object] = {
        "status": "experimental",
        "model": "HistGradientBoostingClassifier",
        "objective": "Estimar a probabilidade de atraso de partida de 30 minutos ou mais.",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "library": f"scikit-learn {sklearn.__version__}",
        "scope": "Voos domésticos regulares realizados com meteorologia disponível.",
        "sampling": {
            "method": "Amostragem reservoir determinística por período.",
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "train_years": list(training_years),
            "test_years": list(test_years),
            "pandemic_years_excluded_from_training": [2020, 2021],
        },
        "target": {
            "name": "departure_delay_minutes >= 30",
            "test_positive_rate": round(float(y_test.mean()), 4),
        },
        "metrics": {
            "roc_auc": round(float(roc_auc_score(y_test, probability)), 4),
            "average_precision": round(float(average_precision_score(y_test, probability)), 4),
            "balanced_accuracy": round(float(balanced_accuracy_score(y_test, prediction)), 4),
            "precision": round(float(precision_score(y_test, prediction, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, prediction, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, prediction, zero_division=0)), 4),
            "brier_score": round(float(brier_score_loss(y_test, probability)), 4),
        },
        "confusion_matrix": {
            "true_negative": int(matrix[0, 0]),
            "false_positive": int(matrix[0, 1]),
            "false_negative": int(matrix[1, 0]),
            "true_positive": int(matrix[1, 1]),
        },
        "top_features": [
            {"feature": FEATURE_LABELS[name], "importance": round(float(value), 5)}
            for name, value in ranked
        ],
        "limitations": [
            "Experimento demonstrativo com amostragem reduzida; não deve orientar decisões operacionais.",
            "Importância por permutação indica contribuição preditiva, não causalidade.",
            "A meteorologia é um agregado observado do mês inteiro e impede o uso como previsão em tempo real.",
            "Cancelamentos não integram a variável-alvo.",
        ],
    }

    model_file.parent.mkdir(parents=True, exist_ok=True)
    metrics_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_model = model_file.with_suffix(model_file.suffix + ".part")
    temporary_metrics = metrics_file.with_suffix(metrics_file.suffix + ".part")
    joblib.dump(estimator, temporary_model, compress=3)
    with temporary_metrics.open("w", encoding="utf-8") as destination:
        json.dump(metrics, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())
    temporary_model.replace(model_file)
    temporary_metrics.replace(metrics_file)
    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Treina o experimento de previsão de atraso 30+.")
    parser.add_argument("--delay-file", type=Path, default=PROJECT_ROOT / "data" / "curated" / "flight_delay_analysis.parquet")
    parser.add_argument("--weather-file", type=Path, default=PROJECT_ROOT / "data" / "curated" / "airport_weather.parquet")
    parser.add_argument("--model-file", type=Path, default=PROJECT_ROOT / "data" / "models" / "delay_hgb.joblib")
    parser.add_argument("--metrics-file", type=Path, default=PROJECT_ROOT / "data" / "curated" / "delay_ml_metrics.json")
    parser.add_argument("--train-rows", type=int, default=120_000)
    parser.add_argument("--test-rows", type=int, default=50_000)
    args = parser.parse_args()
    if not 10_000 <= args.train_rows <= 500_000 or not 5_000 <= args.test_rows <= 200_000:
        parser.error("Use 10.000–500.000 registros de treino e 5.000–200.000 de teste.")
    result = train(
        args.delay_file.resolve(),
        args.weather_file.resolve(),
        args.model_file.resolve(),
        args.metrics_file.resolve(),
        args.train_rows,
        args.test_rows,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
